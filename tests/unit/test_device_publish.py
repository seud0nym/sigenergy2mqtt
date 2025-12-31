import asyncio
import types

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.sensors.base import ModbusSensor, ReadableSensorMixin


class FakeLock:
    def __init__(self):
        self.waiters = 0

    def lock(self, timeout=None):
        class _CM:
            async def __aenter__(self_inner):
                return None

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return _CM()


class FakeModbus:
    def __init__(self):
        self.connected = True

    async def read_ahead_registers(self, first_address, count, device_id, input_type, trace=False):
        # Simulate successful pre-read
        return 0


def setup_module(module):
    Config.devices = [types.SimpleNamespace(registers={}, disable_chunking=False)]
    defaults = dict(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
        entity_id_prefix="sigen",
        enabled_by_default=True,
    )
    ha = getattr(Config, "home_assistant", None)
    if ha is None:
        Config.home_assistant = types.SimpleNamespace(**defaults)
    else:
        for k, v in defaults.items():
            if not hasattr(ha, k):
                setattr(ha, k, v)
    if not hasattr(Config, "persistent_state_path"):
        Config.persistent_state_path = "."


class DummyModbusSensor(ModbusSensor, ReadableSensorMixin):
    def __init__(self, unique_id, address=1, count=1, device_address=1, input_type="holding", scan_interval=1):
        # Sensor stores unique_id in its dict storage
        self["unique_id"] = unique_id
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "input_type", input_type)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "_derived_sensors", {})
        # provide internal _states used by Sensor.latest_raw_state
        import time
        object.__setattr__(self, "_states", [(time.time() - scan_interval, 1)])
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "force_publish", False)

    def apply_sensor_overrides(self, registers):
        return None

    def configure_mqtt_topics(self, unique_id):
        return None

    async def publish(self, mqtt, modbus=None, republish=False):
        # mark that we published (append a new state) and force device offline to stop loop
        import time

        self._states.append((time.time(), 1))
        if hasattr(self, "parent_device"):
            self.parent_device._online = False
        return True


def test_publish_updates_runs_one_iteration(monkeypatch):
    dev = Device("devpub", 0, "uidpub", "mf", "mdl", Config)

    # create two modbus sensors
    s1 = DummyModbusSensor("s1", address=1, count=2, device_address=5, scan_interval=1)
    s2 = DummyModbusSensor("s2", address=3, count=1, device_address=5, scan_interval=1)

    # add to device via internal APIs so parent_device is set
    dev._add_read_sensor(s1)
    dev._add_read_sensor(s2)

    # monkeypatch ModbusLockFactory.get to return a FakeLock
    from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory

    monkeypatch.setattr(ModbusLockFactory, "get", staticmethod(lambda modbus: FakeLock()))

    # Fake modbus and mqtt
    modbus = FakeModbus()
    mqtt = object()

    # ensure the device is considered online for loop start
    dev._online = True

    # run the coroutine but limit total time so test cannot hang
    coro = dev.publish_updates(modbus, mqtt, "grp", s1, s2)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait_for(coro, timeout=5))

    # after run, sensors should have set latest_interval
    assert s1.latest_interval == pytest.approx(1, rel=1e-3)
    assert s2.latest_interval == pytest.approx(1, rel=1e-3)


def test_publish_updates_read_ahead_error_code_switch(monkeypatch):
    """If read_ahead_registers returns code 2 the code should disable multiple pre-reads and still publish sensors."""
    dev = Device("devpub2", 0, "uidpub2", "mf", "mdl", Config)
    s1 = DummyModbusSensor("s1", address=10, count=2, device_address=7, scan_interval=1)
    s2 = DummyModbusSensor("s2", address=12, count=1, device_address=7, scan_interval=1)
    dev._add_read_sensor(s1)
    dev._add_read_sensor(s2)

    class ModbusReadAheadError(FakeModbus):
        def __init__(self):
            super().__init__()
            self.read_ahead_called = 0

        async def read_ahead_registers(self, first_address, count, device_id, input_type, trace=False):
            self.read_ahead_called += 1
            return 2

    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    modbus = ModbusReadAheadError()
    # ensure initial state has no latest_raw_state so loop enters read_ahead
    s1._states = []
    s2._states = []
    dev._online = True
    coro = dev.publish_updates(modbus, object(), "grp", s1, s2)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait_for(coro, timeout=5))

    assert modbus.read_ahead_called >= 1
    # sensor was published (states appended)
    assert len(s1._states) >= 1


def test_publish_updates_handles_modbus_exception_and_reconnect(monkeypatch):
    """If ModbusException occurs the device attempts to reconnect via modbus.connect."""
    from pymodbus import ModbusException

    dev = Device("devpub3", 0, "uidpub3", "mf", "mdl", Config)
    s1 = DummyModbusSensor("s1", address=1, count=1, device_address=2, scan_interval=1)
    s2 = DummyModbusSensor("s2", address=2, count=1, device_address=2, scan_interval=1)
    dev._add_read_sensor(s1)
    dev._add_read_sensor(s2)

    class ModbusRaises(FakeModbus):
        def __init__(self):
            super().__init__()
            self.close_called = 0
            self.connect_called = 0
            self._first = True

        async def read_ahead_registers(self, *args, **kwargs):
            raise ModbusException("boom")

        def close(self):
            self.close_called += 1

        async def connect(self):
            # simulate connect making it connected
            self.connect_called += 1
            self.connected = True

    modbus = ModbusRaises()
    modbus.connected = False
    # override connect to stop the device loop after reconnecting
    async def _connect_and_stop():
        modbus.connect_called += 1
        modbus.connected = True
        dev._online = False

    modbus.connect = _connect_and_stop

    # speed up sleep to avoid long waits
    async def _fast_sleep(_=0):
        return None

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)
    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    # ensure initial state has no latest_raw_state so loop enters read_ahead
    s1._states = []
    s2._states = []

    dev._online = True
    coro = dev.publish_updates(modbus, object(), "grp", s1, s2)
    loop = asyncio.get_event_loop()
    # run but allow the reconnect logic to be exercised
    loop.run_until_complete(asyncio.wait_for(coro, timeout=5))

    assert modbus.connect_called >= 1
