import asyncio
import time
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from paho.mqtt.client import Client as MqttClient
from pymodbus import ModbusException
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.devices.base.poller import SensorGroupPoller
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory
from sigenergy2mqtt.sensors.base import EnergyDailyAccumulationSensor, ModbusSensorMixin, ReadableSensorMixin


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
    monkeypatch.setattr(ModbusLockFactory, "get", staticmethod(lambda modbus: FakeLock()))

    # Fake modbus and mqtt
    modbus = FakeModbus()
    mqtt = object()

    # ensure the device is considered online for loop start
    dev._online = True

    # run the coroutine but limit total time so test cannot hang
    poller = SensorGroupPoller(dev)
    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, mqtt), "grp", s1, s2)

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

    poller = SensorGroupPoller(dev)
    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    await asyncio.wait_for(coro, timeout=5)

    assert modbus.read_ahead_called >= 1
    # sensor was published (states appended)
    assert len(s1._states) >= 1


@pytest.mark.asyncio
async def test_publish_updates_handles_modbus_exception_and_reconnect(monkeypatch):
    """If ModbusException occurs the device attempts to reconnect via modbus.connect."""

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

    poller = SensorGroupPoller(dev)
    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    # run but allow the reconnect logic to be exercised
    await asyncio.wait_for(coro, timeout=5)

    assert modbus.connect_called >= 1


@pytest.mark.asyncio
async def test_publish_updates_day_change_forces_daily_sensor(monkeypatch):
    """When tm_yday changes between iterations, sensors with EnergyDailyAccumulationSensor
    derived sensors are forced to publish immediately (covers device.py lines 1017-1025)."""

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

    monkeypatch.setattr(ModbusLockFactory, "get", staticmethod(lambda modbus: FakeLock()))

    # Clear initial states so _init_next_publish_times does not trigger initial publish
    daily._states = []
    regular._states = []

    # Force both sensors due immediately in the first iteration
    daily.force_publish = True
    regular.force_publish = True

    dev._online = True

    modbus = FakeModbus()
    poller = SensorGroupPoller(dev)
    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", daily, regular)
    await asyncio.wait_for(coro, timeout=5)

    # The daily sensor must have been published at least twice (initial + day-change forced)
    assert publish_log.count("daily1") >= 2, f"Expected daily sensor to be published >=2 times, got {publish_log}"


@pytest.mark.asyncio
async def test_poller_skips_unpublishable_sensors(monkeypatch):
    """Ensure _get_sensors_to_publish_now correctly skips sensors where publishable == False."""
    dev = Device("devpub5", 0, "uidpub5", "mf", "mdl", Protocol.V1_8)

    s1 = DummyModbusSensor("s1", address=1, count=1, device_address=1, scan_interval=1)
    s2 = DummyModbusSensor("s2", address=2, count=1, device_address=1, scan_interval=1)

    # Mark s1 as unpublishable
    object.__setattr__(s1, "_publishable", False)

    dev._add_read_sensor(s1)
    dev._add_read_sensor(s2)

    monkeypatch.setattr(ModbusLockFactory, "get", staticmethod(lambda modbus: FakeLock()))

    # Stop the poller loop after one iteration
    async def _mock_publish(mqtt_client, modbus_client=None, republish=False):
        dev._online = False
        return True

    monkeypatch.setattr(s2, "publish", _mock_publish)

    s1.force_publish = True
    s2.force_publish = True

    # ensure initial state has no latest_raw_state
    s1._states = []
    s2._states = []

    dev._online = True
    poller = SensorGroupPoller(dev)
    modbus = FakeModbus()

    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    await asyncio.wait_for(coro, timeout=5)

    assert len(s1._states) == 0  # Should not be published
    assert len(s2._states) == 0  # _mock_publish does not append states, but loop ran


@pytest.mark.asyncio
async def test_poller_read_ahead_exception_codes(monkeypatch, caplog):
    """Mock read_ahead_registers to return code 1, 3, 4, -1 and ensure appropriate warning logs are hit but read_ahead stays enabled."""
    import logging

    caplog.set_level(logging.WARNING)
    dev = Device("devpub6", 0, "uidpub6", "mf", "mdl", Protocol.V1_8)
    s1 = DummyModbusSensor("s1", address=10, count=2, device_address=7, scan_interval=1)
    s2 = DummyModbusSensor("s2", address=12, count=1, device_address=7, scan_interval=1)
    dev._add_read_sensor(s1)
    dev._add_read_sensor(s2)

    class ModbusExceptionCodes(FakeModbus):
        def __init__(self):
            super().__init__()
            self.read_ahead_called = 0
            self.codes_to_return = [1, 3, 4, -1, 99]

        async def read_ahead_registers(self, first_address, count, device_id, input_type, trace=False):
            if self.read_ahead_called < len(self.codes_to_return):
                code = self.codes_to_return[self.read_ahead_called]
            else:
                code = 0
            self.read_ahead_called += 1
            return code

    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    modbus = ModbusExceptionCodes()
    s1._states = []
    s2._states = []

    dev._online = True

    poller = SensorGroupPoller(dev)

    # MUST override publish because DummyModbusSensor.publish stops the loop!
    async def _mock_publish_no_stop(mqtt_client, modbus_client=None, republish=False):
        # We need to use 'self' here but it's a mock.
        # Actually it's monkeypatched on s1 and s2 directly.
        pass
        return True

    monkeypatch.setattr(s1, "publish", _mock_publish_no_stop)
    monkeypatch.setattr(s2, "publish", _mock_publish_no_stop)

    # Simulate time passing so sensors become due again
    current_time = [time.time()]
    monkeypatch.setattr(time, "time", lambda: current_time[0])

    original_sleep = asyncio.sleep

    async def _mock_sleep_no_recursion(delay, result=None):
        if modbus.read_ahead_called >= len(modbus.codes_to_return):
            dev._online = False
            return None
        current_time[0] += 60.0  # Advance time
        s1.force_publish = True
        s2.force_publish = True
        await original_sleep(0)  # Yield without recursion
        return None

    monkeypatch.setattr(asyncio, "sleep", _mock_sleep_no_recursion)

    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1, s2)
    # The timeout here ensures it doesn't hang forever if the loop breaks
    await asyncio.wait_for(coro, timeout=5)

    assert modbus.read_ahead_called >= 5

    # check that the correct logs were produced
    log_text = caplog.text
    assert "0x01 ILLEGAL FUNCTION" in log_text
    assert "0x03 ILLEGAL DATA VALUE" in log_text
    assert "0x04 SLAVE DEVICE FAILURE" in log_text
    assert "NO RESPONSE FROM DEVICE" in log_text
    assert "UNKNOWN PROBLEM" in log_text


@pytest.mark.asyncio
async def test_poller_reconnect_cancellation(monkeypatch, caplog):
    """Mock modbus.connect to raise asyncio.CancelledError and ensure _reconnect_modbus_with_backoff returns False properly."""
    dev = Device("devpub7", 0, "uidpub7", "mf", "mdl", Protocol.V1_8)
    s1 = DummyModbusSensor("s1", address=10, count=2, device_address=7, scan_interval=1)
    dev._add_read_sensor(s1)

    class ModbusCancelledConnect(FakeModbus):
        def close(self):
            pass

        async def connect(self):
            raise asyncio.CancelledError()

    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    modbus = ModbusCancelledConnect()
    monkeypatch.setattr(modbus, "read_ahead_registers", AsyncMock(side_effect=ModbusException("boom")))

    dev._online = True
    s1.force_publish = True
    s1._states = []

    poller = SensorGroupPoller(dev)

    # We expect the CancelledError from the inner _reconnect to NOT be caught
    # normally except by cancelling the task. Actually, in _reconnect_modbus_with_backoff
    # it caught CancelledError and returns False.
    res = await poller._reconnect_modbus_with_backoff(modbus)
    assert res is False

    # Test the sleep cancellation too
    class ModbusCancelledSleep(FakeModbus):
        def close(self):
            pass

        async def connect(self):
            pass

    modbus2 = ModbusCancelledSleep()
    modbus2.connected = False

    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError()))

    res2 = await poller._reconnect_modbus_with_backoff(modbus2)
    assert res2 is False


@pytest.mark.asyncio
async def test_poller_run_sleep_cancelled(monkeypatch, caplog):
    """Raise asyncio.CancelledError from the sleep task in run and ensure it's caught."""
    import logging

    dev = Device("devpub8", 0, "uidpub8", "mf", "mdl", Protocol.V1_8)
    s1 = DummyModbusSensor("s1", address=10, count=2, device_address=7, scan_interval=1)
    dev._add_read_sensor(s1)
    dev._online = True

    # Mark it as debug logging so the caught cancellation logs a specific message
    s1.debug_logging = True
    dev.debug_logging = True

    poller = SensorGroupPoller(dev)

    # MUST override publish because DummyModbusSensor.publish stops the loop!
    async def _mock_publish_no_stop(mqtt_client, modbus_client=None, republish=False):
        pass
        return True

    monkeypatch.setattr(s1, "publish", _mock_publish_no_stop)

    original_sleep = asyncio.sleep

    async def _mock_sleep(delay, result=None):
        # Stop the online flag so it exits the loop after catching
        dev._online = False
        # Cancel the task we are running in
        asyncio.current_task().cancel()
        # Yield to allow cancellation to raise
        await original_sleep(0.1)
        return None

    monkeypatch.setattr("sigenergy2mqtt.devices.base.poller.asyncio.sleep", _mock_sleep)
    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    modbus = FakeModbus()
    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1)

    with caplog.at_level(logging.DEBUG):
        try:
            logging.debug("BEFORE RUN WAIT")
            await asyncio.wait_for(coro, timeout=5)
            logging.debug("AFTER RUN WAIT")
        except asyncio.CancelledError:
            pytest.fail("CancelledError leaked out of run loop")

    # verify the sleep interrupted debug log
    assert "BEFORE RUN WAIT" in caplog.text
    assert "sleep interrupted" in caplog.text
    assert "AFTER RUN WAIT" in caplog.text


@pytest.mark.asyncio
async def test_poller_run_handles_generic_exception(monkeypatch, caplog):
    """Throw a generic Exception from sensor.publish and verify run catches it and logs an error without crashing."""
    dev = Device("devpub9", 0, "uidpub9", "mf", "mdl", Protocol.V1_8)
    s1 = DummyModbusSensor("s1", address=10, count=2, device_address=7, scan_interval=1)
    dev._add_read_sensor(s1)

    s1.force_publish = True
    s1._states = []
    dev._online = True

    async def _mock_publish(mqtt_client, modbus_client=None, republish=False):
        dev._online = False  # Stop loop
        raise Exception("generic error message")

    monkeypatch.setattr(s1, "publish", _mock_publish)
    monkeypatch.setattr("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get", lambda modbus: FakeLock())

    modbus = FakeModbus()
    poller = SensorGroupPoller(dev)

    coro = poller.run(cast(ModbusClient, modbus), cast(MqttClient, object()), "grp", s1)

    # Should not throw outside
    await asyncio.wait_for(coro, timeout=5)

    assert "encountered an error: Exception('generic error message')" in caplog.text
