import asyncio
import time
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, ReadableSensorMixin


class FakeLock:
    def __init__(self):
        self.waiters = 0

    def lock(self, timeout=None):
        class _CM:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return _CM()


class FakeModbus:
    def __init__(self):
        self.connected = True

    async def read_ahead_registers(self, first_address, count, device_id, input_type, trace=False) -> int:
        # Simulate successful pre-read
        return 0


@pytest.fixture(autouse=True)
def mock_config():
    cfg = Config()
    mock_modbus = MagicMock()
    mock_modbus.registers = {}
    mock_modbus.disable_chunking = False
    mock_modbus.scan_interval.high = 60
    cfg.modbus = [mock_modbus]
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = False
    cfg.home_assistant.republish_discovery_interval = 0
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled_by_default = True
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.persistent_state_path = Path(".")

    with _swap_active_config(cfg):
        yield cfg


class DummyModbusSensor(ModbusSensorMixin, ReadableSensorMixin):
    def __init__(self, unique_id, address=1, count=1, device_address=1, input_type="holding", scan_interval=1):
        # Sensor stores unique_id in its dict storage
        self.unique_id = self["unique_id"] = unique_id
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "input_type", input_type)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "derived_sensors", {})
        # provide internal _states used by Sensor.latest_raw_state
        import time

        object.__setattr__(self, "_states", [(time.time() - scan_interval, 1)])
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "force_publish", False)

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        return False

    def apply_sensor_overrides(self, registers):
        return None

    def configure_mqtt_topics(
        self,
        device_id: str,
    ) -> str:
        return ""

    async def publish(self, mqtt_client, modbus_client=None, republish=False):
        # mark that we published (append a new state) and force device offline to stop loop
        import time

        self._states.append((time.time(), 1))
        if hasattr(self, "parent_device"):
            self.parent_device._online = False
        return True


@pytest.mark.asyncio
async def test_publish_updates_runs_one_iteration(monkeypatch):
    # --- 1. SET UP TIME MOCKING ---
    class MockClock:
        def __init__(self):
            self.current_time = 1000.0  # Start at an arbitrary timestamp

        def get_time(self):
            return self.current_time

        def advance(self, amount):
            self.current_time += amount

    clock = MockClock()

    # Patch the standard time functions (covers whichever your code uses to measure intervals)
    monkeypatch.setattr(time, "time", clock.get_time)
    monkeypatch.setattr(time, "monotonic", clock.get_time)

    # Patch asyncio.sleep so the test runs instantly but "time" still passes
    original_sleep = asyncio.sleep

    async def mock_sleep(delay, result=None):
        clock.advance(delay)  # Fast-forward our fake clock
        return await original_sleep(0, result)  # Yield briefly to keep event loop happy

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)
    # ------------------------------

    dev = Device("devpub", 0, "uidpub", "mf", "mdl", Protocol.V1_8)

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
    from paho.mqtt.client import Client as MqttClient

    from sigenergy2mqtt.modbus.client import ModbusClient

    coro = dev.publish_updates(cast(ModbusClient, modbus), cast(MqttClient, mqtt), "grp", s1, s2)

    await asyncio.wait_for(coro, timeout=5)

    # --- 2. EXACT ASSERTIONS ---
    # Because we control the clock, there is no floating-point drift.
    # We can assert exact integers.
    assert s1.latest_interval == 1
    assert s2.latest_interval == 1


@pytest.mark.asyncio
async def test_publish_updates_read_ahead_error_code_switch(monkeypatch):
    """If read_ahead_registers returns code 2 the code should disable multiple pre-reads and still publish sensors."""
    dev = Device("devpub2", 0, "uidpub2", "mf", "mdl", Protocol.V1_8)
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
    # Force immediate publish so sensors become due right away
    s1.force_publish = True
    s2.force_publish = True
    dev._online = True
    from paho.mqtt.client import Client as MqttClient

    from sigenergy2mqtt.modbus.client import ModbusClient

    coro = dev.publish_updates(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    await asyncio.wait_for(coro, timeout=5)

    assert modbus.read_ahead_called >= 1
    # sensor was published (states appended)
    assert len(s1._states) >= 1


@pytest.mark.asyncio
async def test_publish_updates_handles_modbus_exception_and_reconnect(monkeypatch):
    """If ModbusException occurs the device attempts to reconnect via modbus.connect."""
    from pymodbus import ModbusException

    dev = Device("devpub3", 0, "uidpub3", "mf", "mdl", Protocol.V1_8)
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
    # Force immediate publish so sensors become due right away
    s1.force_publish = True
    s2.force_publish = True

    dev._online = True
    from paho.mqtt.client import Client as MqttClient

    from sigenergy2mqtt.modbus.client import ModbusClient

    coro = dev.publish_updates(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    # run but allow the reconnect logic to be exercised
    await asyncio.wait_for(coro, timeout=5)

    assert modbus.connect_called >= 1


@pytest.mark.asyncio
async def test_publish_updates_day_change_forces_daily_sensor(monkeypatch):
    """When tm_yday changes between iterations, sensors with EnergyDailyAccumulationSensor
    derived sensors are forced to publish immediately (covers device.py lines 1017-1025)."""
    from sigenergy2mqtt.sensors.base import EnergyDailyAccumulationSensor

    dev = Device("devpub4", 0, "uidpub4", "mf", "mdl", Protocol.V1_8)

    # A daily sensor whose derived_sensors include an EnergyDailyAccumulationSensor
    daily = DummyModbusSensor("daily1", address=1, count=1, device_address=3, scan_interval=60)
    # A regular sensor with no daily derived sensor
    regular = DummyModbusSensor("regular1", address=2, count=1, device_address=3, scan_interval=60)

    # Inject a mock EnergyDailyAccumulationSensor as a derived sensor of 'daily'
    class MockEDA(EnergyDailyAccumulationSensor):
        def __init__(self):
            # Skip real __init__; we just need isinstance() to pass
            self.debug_logging = False

    daily.derived_sensors = {"eda": MockEDA()}

    dev._add_read_sensor(daily)
    dev._add_read_sensor(regular)

    # Track publishes per sensor
    publish_log: list[str] = []

    async def _tracking_publish(self, mqtt_client, modbus_client=None, republish=False):
        publish_log.append(self.unique_id)
        # After the second loop iteration (day change), stop the device
        if publish_log.count("daily1") >= 2:
            dev._online = False
        return True

    monkeypatch.setattr(DummyModbusSensor, "publish", _tracking_publish)

    # --- Time control ---
    # Start at a fixed time. localtime will first return day 100, then day 101.
    call_count = 0
    base_time = 1000.0
    current_time = [base_time]

    def fake_time():
        return current_time[0]

    def fake_localtime(secs=None):
        nonlocal call_count
        call_count += 1
        s = time.struct_time((2025, 4, 10, 23, 59, 59, 3, 100, -1))
        # After the first loop iteration completes, simulate day change
        if call_count > 1:
            s = time.struct_time((2025, 4, 11, 0, 0, 1, 4, 101, -1))
        return s

    monkeypatch.setattr(time, "time", fake_time)
    monkeypatch.setattr(time, "localtime", fake_localtime)

    # Make asyncio.sleep advance our clock to trigger the sensor intervals
    _original_sleep = asyncio.sleep

    async def _fast_sleep(delay, result=None):
        current_time[0] += max(delay, 1)
        await _original_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)

    from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory

    monkeypatch.setattr(ModbusLockFactory, "get", staticmethod(lambda modbus: FakeLock()))

    # Clear initial states so _init_next_publish_times does not trigger initial publish
    daily._states = []
    regular._states = []

    # Force both sensors due immediately in the first iteration
    daily.force_publish = True
    regular.force_publish = True

    dev._online = True

    from paho.mqtt.client import Client as MqttClient

    from sigenergy2mqtt.modbus.client import ModbusClient

    modbus = FakeModbus()
    coro = dev.publish_updates(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", daily, regular)
    await asyncio.wait_for(coro, timeout=5)

    # The daily sensor must have been published at least twice (initial + day-change forced)
    assert publish_log.count("daily1") >= 2, f"Expected daily sensor to be published >=2 times, got {publish_log}"
