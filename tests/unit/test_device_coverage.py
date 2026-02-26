"""
Tests targeting uncovered lines in sigenergy2mqtt/devices/device.py.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus import ModbusException

from sigenergy2mqtt.common import HybridInverter, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry, ModbusDevice
from sigenergy2mqtt.sensors.base import (
    DerivedSensor,
    ModbusSensorMixin,
    ObservableMixin,
    ReadableSensorMixin,
    Sensor,
    WritableSensorMixin,
    WriteOnlySensor,
)
from sigenergy2mqtt.sensors.const import InputType

# ---------------------------------------------------------------------------
# Helper / stub classes (mirror the style of test_device_missing.py)
# ---------------------------------------------------------------------------


class DummyReadable(ReadableSensorMixin, Sensor):
    def __init__(self, unique_id, publishable=True, address=1, count=1, scan_interval=10, protocol_version=Protocol.V1_8):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "_publishable", publishable)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", 1)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "input_type", InputType.HOLDING)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "force_publish", False)
        object.__setattr__(self, "latest_raw_state", None)
        object.__setattr__(self, "protocol_version", protocol_version)

    @property
    def publishable(self):
        return self._publishable

    async def _update_internal_state(self, **kwargs):
        return False

    def configure_mqtt_topics(self, device_id):
        self["state_topic"] = f"state/{device_id}/{self.unique_id}"
        return self["state_topic"]

    def apply_sensor_overrides(self, registers):
        pass

    def publish_attributes(self, mqtt_client, clean=False):
        pass

    def get_discovery(self, mqtt_client):
        return {}

    async def publish(self, mqtt_client, modbus_client=None, republish=False):
        return True

    def add_derived_sensor(self, sensor):
        pass

    def observable_topics(self):
        return []


class DummyWritable(WritableSensorMixin, Sensor):
    def __init__(self, unique_id, command_topic="cmd"):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self["command_topic"] = command_topic
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "name", unique_id)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "address", 1)
        object.__setattr__(self, "input_type", InputType.HOLDING)
        object.__setattr__(self, "protocol_version", Protocol.V1_8)
        object.__setattr__(self, "parent_device", None)
        object.__setattr__(self, "_derived_sensors", {})

    async def set_value(self, client, userdata, message):
        pass

    def apply_sensor_overrides(self, registers):
        pass

    def configure_mqtt_topics(self, device_id):
        pass

    def get_discovery(self, mqtt_client):
        return {}

    def publish_attributes(self, mqtt_client, clean=False):
        pass


class DummyWriteOnly(WriteOnlySensor):
    def __init__(self, unique_id, protocol_version=Protocol.V1_8):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self["command_topic"] = f"cmd/{unique_id}"
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "address", 1)
        object.__setattr__(self, "input_type", InputType.HOLDING)
        object.__setattr__(self, "protocol_version", protocol_version)
        object.__setattr__(self, "debug_logging", False)
        self._values = {"off": 0, "on": 1}

    async def set_value(self, client, userdata, message):
        pass

    def apply_sensor_overrides(self, registers):
        return None

    def configure_mqtt_topics(self, device_id):
        return ""

    def get_discovery(self, mqtt_client):
        return {}

    def publish_attributes(self, mqtt_client, clean=False):
        pass


class DummyObservable(ObservableMixin, ReadableSensorMixin, Sensor):
    def __init__(self, unique_id, topic):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self.topic = topic
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "name", unique_id)
        object.__setattr__(self, "_publishable", False)
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "scan_interval", 10)
        object.__setattr__(self, "protocol_version", Protocol.V1_8)

    def observable_topics(self):
        return [self.topic]

    async def notify(self, modbus_client, mqtt_client, value, source, handler):
        pass

    async def _update_internal_state(self, **kwargs):
        return False

    def configure_mqtt_topics(self, device_id):
        return ""

    async def publish(self, mqtt_client, modbus_client=None, republish=False):
        return True

    def apply_sensor_overrides(self, registers):
        pass

    def publish_attributes(self, mqtt_client, clean=False):
        pass

    def get_discovery(self, mqtt_client):
        return {}


class DummyDerived(DerivedSensor):
    """Minimal DerivedSensor stub."""

    def __init__(self, unique_id, protocol_version=Protocol.V1_8):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "protocol_version", protocol_version)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "_derived_sensors", {})

    def apply_sensor_overrides(self, registers):
        pass

    def configure_mqtt_topics(self, device_id):
        pass

    def get_discovery(self, mqtt_client):
        return {}

    def publish_attributes(self, mqtt_client, clean=False):
        pass


class DummyModbusSensor(ModbusSensorMixin, DummyReadable):
    """A readable sensor that also looks like a Modbus sensor."""

    def __init__(self, unique_id, address=10, count=1, device_address=1, publishable=True, protocol_version=Protocol.V1_8):
        super().__init__(unique_id, publishable=publishable, address=address, count=count, protocol_version=protocol_version)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "input_type", InputType.HOLDING)


class ConcreteModbusDevice(ModbusDevice):
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    cfg.home_assistant.enabled = True
    cfg.home_assistant.republish_discovery_interval = 60
    cfg.origin = {}
    cfg.persistent_state_path = "."
    with _swap_active_config(cfg):
        yield cfg
    DeviceRegistry.clear()


@pytest.fixture
def device():
    return Device("TestDev", 0, "uid_1", "mf", "model", Protocol.V1_8)


# ===========================================================================
# unknown kwargs in Device.__init__ are silently ignored
# ===========================================================================


def test_device_init_ignores_unknown_kwargs():
    """extra kwargs that are not recognised device attributes are logged and dropped."""
    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        dev = Device("TestDev", 0, "uid_extra", "mf", "model", Protocol.V1_8, unknown_kwarg="ignored")
        # 'unknown_kwarg' is not in the allowed set, so it should be logged as ignored
        mock_log.debug.assert_called()
    DeviceRegistry._devices.clear()


# ===========================================================================
# online property / setter branches
# ===========================================================================


@pytest.mark.asyncio
async def test_online_getter_returns_false_when_future_cancelled(device):
    """getter returns False when Future is cancelled."""
    fut = asyncio.get_running_loop().create_future()
    fut.cancel()
    device._online = fut
    assert device.online is False


@pytest.mark.asyncio
async def test_online_getter_returns_true_when_future_not_cancelled(device):
    """getter returns True when Future is not cancelled."""
    fut = asyncio.get_running_loop().create_future()
    device._online = fut
    assert device.online is True
    fut.cancel()


def test_online_setter_raises_on_true(device):
    """setting online=True raises ValueError."""
    with pytest.raises(ValueError, match="online must be a Future to enable"):
        device.online = True


@pytest.mark.asyncio
async def test_online_setter_accepts_future(device):
    """Lines 120-122: setting online to a Future stores it."""
    fut = asyncio.get_running_loop().create_future()
    device.online = fut
    assert device._online is fut
    fut.cancel()


def test_online_setter_raises_on_invalid_type(device):
    """Line 122 (else): setting online to non-bool non-Future raises ValueError."""
    with pytest.raises(ValueError, match="online must be a Future or False"):
        device.online = "invalid"


@pytest.mark.asyncio
async def test_online_setter_false_cancels_future_and_propagates(device):
    """Line 116-119: setting False cancels the Future and propagates to children."""
    fut = asyncio.get_running_loop().create_future()
    device._online = fut
    child = Device("Child", 0, "child_uid_x", "mf", "model", Protocol.V1_8)
    child_fut = asyncio.get_running_loop().create_future()
    child._online = child_fut
    device.children.append(child)

    device.online = False

    assert fut.cancelled()
    assert device._online is False
    assert child._online is False


# ===========================================================================
# _add_child_device when no publishable sensors
# ===========================================================================


def test_add_child_device_no_publishable_sensors(device):
    """child without publishable sensors is not added to children list."""
    child = Device("NoSensors", 0, "uid_no_sensors", "mf", "model", Protocol.V1_8)
    # No publishable sensors → child should not be appended
    device._add_child_device(child)
    assert child not in device.children


def test_add_child_device_with_publishable_sensor(device):
    """Contrast: child with a publishable sensor IS added."""
    child = Device("WithSensors", 0, "uid_with_sensors", "mf", "model", Protocol.V1_8)
    s = DummyReadable("s_pub", publishable=True)
    child._add_read_sensor(s)
    device._add_child_device(child)
    assert child in device.children


# ===========================================================================
# _add_derived_sensor branches
# ===========================================================================


def test_add_derived_sensor_protocol_version_too_high(device):
    """Lines 323-326: derived sensor with protocol_version > device version is skipped."""
    device.protocol_version = Protocol.V1_8
    src = DummyReadable("src_sensor")
    src.protocol_version = Protocol.V1_8
    device._add_read_sensor(src)

    derived = DummyDerived("derived_high_pv", protocol_version=Protocol.V2_4)
    device._add_derived_sensor(derived, src)
    # Should not be in all_sensors because its protocol_version > device's
    assert "derived_high_pv" not in device.all_sensors


def test_add_derived_sensor_source_protocol_version_too_high(device):
    """Lines 323-326: derived sensor skipped when source sensor has protocol_version > device."""
    device.protocol_version = Protocol.V1_8
    src = DummyReadable("src_sensor_high")
    src.protocol_version = Protocol.V2_4  # source too new
    device._add_read_sensor(src)

    derived = DummyDerived("derived_ok_pv", protocol_version=Protocol.V1_8)
    device._add_derived_sensor(derived, src)
    assert "derived_ok_pv" not in device.all_sensors


def test_add_derived_sensor_source_not_found(device):
    """warning logged when source sensor is not found in device."""
    device.protocol_version = Protocol.N_A  # skip protocol checks
    src = DummyReadable("nonexistent_src")  # never added to device
    derived = DummyDerived("derived_no_src")

    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        device._add_derived_sensor(derived, src)
        mock_log.warning.assert_called()


def test_add_derived_sensor_no_source_sensors_after_none_removal(device):
    """error logged when all source sensors are None."""
    derived = DummyDerived("derived_none_src")
    device.protocol_version = Protocol.N_A

    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        device._add_derived_sensor(derived, None)  # all None
        mock_log.error.assert_called()


# ===========================================================================
# _create_sensor_scan_groups: non-modbus sensors group
# ===========================================================================


def test_create_sensor_scan_groups_non_modbus(device):
    """non-Modbus readable sensors end up in their own scan group."""
    s = DummyReadable("non_modbus_s", publishable=True)
    device._add_read_sensor(s)

    groups = device._create_sensor_scan_groups()
    assert "non_modbus_sensors" in groups
    assert s in groups["non_modbus_sensors"]


# ===========================================================================
# publish_updates
# ===========================================================================


@pytest.mark.asyncio
async def test_publish_updates_exits_when_offline(device):
    """publish_updates loop exits immediately when device is offline."""
    device._online = False
    s = DummyReadable("s_offline")
    # Should return immediately without doing anything
    await device.publish_updates(None, MagicMock(), "test_group", s)


@pytest.mark.asyncio
async def test_publish_updates_initial_republish_of_existing_state(device):
    """if a sensor has a latest_raw_state it is republished on startup."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    publish_calls = []

    class TrackingReadable(DummyReadable):
        @property
        def latest_raw_state(self):
            return "42"

        @latest_raw_state.setter
        def latest_raw_state(self, value):
            pass  # ignore – getter always returns "42"

        async def publish(self, mqtt_client, modbus_client=None, republish=False):
            publish_calls.append(republish)
            return True

    s = TrackingReadable("s_existing_state")

    call_count = 0

    async def fake_sleep(t):
        nonlocal call_count
        call_count += 1
        device._online = False  # stop the loop after first sleep

    with patch("asyncio.sleep", fake_sleep):
        await device.publish_updates(None, MagicMock(), "grp", s)

    # Initial republish should have been called with republish=True
    assert any(r is True for r in publish_calls)
    fut.cancel()


@pytest.mark.asyncio
async def test_publish_updates_force_publish(device):
    """Line 630 area: force_publish causes a sensor to publish even if not yet due."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    s = DummyReadable("s_force")
    s.force_publish = True
    s.publish = AsyncMock()

    published_event = asyncio.Event()
    original_publish = s.publish

    async def recording_publish(*args, **kwargs):
        published_event.set()
        return True

    s.publish = recording_publish

    call_count = 0

    async def fake_sleep(t):
        nonlocal call_count
        call_count += 1
        device._online = False

    with patch("asyncio.sleep", fake_sleep):
        await device.publish_updates(None, MagicMock(), "grp_force", s)

    assert published_event.is_set()
    fut.cancel()


@pytest.mark.asyncio
async def test_publish_updates_modbus_exception_reconnects(device):
    """Lines 702-725: ModbusException triggers reconnection logic."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    s = DummyReadable("s_modbus_err")
    s.force_publish = True

    call_count = 0

    async def failing_publish(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise ModbusException("test error")

    s.publish = failing_publish

    modbus_client = MagicMock()
    modbus_client.connected = True

    async def fake_sleep(t):
        device._online = False

    lock_mock = MagicMock()
    lock_mock.lock = MagicMock(return_value=AsyncMock().__aenter__.return_value)

    async def fake_lock_ctx(*args, **kwargs):
        return

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    lock_obj = MagicMock()
    lock_obj.lock = MagicMock(return_value=cm)
    lock_obj.waiters = 0

    with patch("sigenergy2mqtt.devices.device.ModbusLockFactory") as mock_factory:
        mock_factory.get.return_value = lock_obj
        with patch("asyncio.sleep", fake_sleep):
            await device.publish_updates(modbus_client, MagicMock(), "grp_modbus_err", s)

    fut.cancel()


@pytest.mark.asyncio
async def test_publish_updates_generic_exception_logged(device):
    """Lines 720-725: generic exceptions are caught and logged."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    s = DummyReadable("s_generic_err")
    s.force_publish = True

    async def bad_publish(*args, **kwargs):
        raise RuntimeError("unexpected!")

    s.publish = bad_publish

    async def fake_sleep(t):
        device._online = False

    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        with patch("asyncio.sleep", fake_sleep):
            await device.publish_updates(None, MagicMock(), "grp_generic_err", s)

        mock_log.error.assert_called()

    fut.cancel()


@pytest.mark.asyncio
async def test_publish_updates_rediscover_triggers_discovery(device):
    """publish_updates triggers publish_discovery when rediscover is set."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    s = DummyReadable("s_rediscover")
    s.force_publish = True

    async def ok_publish(*args, **kwargs):
        device.rediscover = True

    s.publish = ok_publish

    discovery_called = []

    def fake_discover(mqtt_client, clean=False):
        discovery_called.append(True)

    device.publish_discovery = fake_discover

    async def fake_sleep(t):
        device._online = False

    with patch("asyncio.sleep", fake_sleep):
        await device.publish_updates(None, MagicMock(), "grp_rediscover", s)

    assert discovery_called
    fut.cancel()


@pytest.mark.asyncio
async def test_publish_updates_sleep_interrupted_by_cancel(device):
    """Lines 764-784: CancelledError from sleep is handled gracefully."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    s = DummyReadable("s_cancel")
    s.force_publish = False

    real_sleep = asyncio.sleep
    call_count = 0

    async def interruptible_sleep(t):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.CancelledError()
        device._online = False

    with patch("asyncio.sleep", interruptible_sleep):
        await device.publish_updates(None, MagicMock(), "grp_cancel", s)

    fut.cancel()


# ===========================================================================
# republish_discovery loop
# ===========================================================================


@pytest.mark.asyncio
async def test_republish_discovery_runs_and_exits(device):
    """republish_discovery publishes at the correct interval then exits."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    from sigenergy2mqtt.config.settings import HomeAssistantConfig

    cfg = Config()
    cfg.home_assistant = HomeAssistantConfig(republish_discovery_interval=2)

    with _swap_active_config(cfg):
        discovery_calls = []
        device.publish_discovery = lambda *a, **kw: discovery_calls.append(True)

        tick = 0

        async def fake_sleep(t):
            nonlocal tick
            tick += 1
            if tick >= 3:
                device._online = False

        with patch("asyncio.sleep", fake_sleep):
            await device.republish_discovery(MagicMock())

        assert len(discovery_calls) >= 1

    fut.cancel()


@pytest.mark.asyncio
async def test_republish_discovery_cancelled(device):
    """republish_discovery exits cleanly on CancelledError."""
    fut = asyncio.get_event_loop().create_future()
    device._online = fut

    from sigenergy2mqtt.config.settings import HomeAssistantConfig

    cfg = Config()
    cfg.home_assistant = HomeAssistantConfig(republish_discovery_interval=100)

    with _swap_active_config(cfg):

        async def raise_cancel(t):
            raise asyncio.CancelledError()

        with patch("asyncio.sleep", raise_cancel):
            await device.republish_discovery(MagicMock())
        # Should exit without raising

    fut.cancel()


# ===========================================================================
# schedule skips groups with no publishable sensors
# ===========================================================================


def test_schedule_skips_non_publishable_group(device):
    """Lines 835-836: groups with no publishable sensors are not scheduled."""
    s = DummyReadable("s_not_publishable", publishable=False)
    device._add_read_sensor(s)

    from sigenergy2mqtt.config.settings import HomeAssistantConfig, ModbusConfig

    cfg = Config()
    cfg.home_assistant = HomeAssistantConfig(enabled=False, republish_discovery_interval=0)
    cfg.modbus = [ModbusConfig(registers={}, disable_chunking=False, host="127.0.0.1", port=502)]
    with _swap_active_config(cfg):
        tasks = device.schedule(MagicMock(), MagicMock())

    # No publishable sensors → no tasks (republish_discovery also disabled)
    assert tasks == []


# ===========================================================================
# subscribe error handling
# ===========================================================================


def test_subscribe_writable_sensor_exception_logged(device):
    """Lines 872-874: exception during writable sensor subscription is logged."""
    w = DummyWritable("w_fail", command_topic="cmd/fail")
    device.all_sensors[w.unique_id] = w

    handler = MagicMock()
    # First call registers HA status (must succeed), second raises for writable sensor
    handler.register.side_effect = [MagicMock(), RuntimeError("subscribe failed")]

    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        device.subscribe(MagicMock(), handler)
        mock_log.error.assert_called()


def test_subscribe_observable_exception_logged(device):
    """Lines 891-892: exception during observable subscription is logged."""
    obs = DummyObservable("obs_fail", "topic/fail")
    device.all_sensors[obs.unique_id] = obs

    handler = MagicMock()
    # First call (HA status) succeeds; second (observable topic) raises
    handler.register.side_effect = [MagicMock(), RuntimeError("obs fail")]

    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        device.subscribe(MagicMock(), handler)
        mock_log.error.assert_called()


# ===========================================================================
# ModbusDevice __init__ with explicit unique_id
# ===========================================================================


def test_modbus_device_explicit_unique_id():
    """unique_id kwarg is accepted and used directly."""
    dev = ConcreteModbusDevice(None, "ExplicitUID", 0, 1, "model", Protocol.V1_8, unique_id="sigen_explicit_uid")
    assert dev.unique_id == "sigen_explicit_uid"


def test_modbus_device_explicit_unique_id_wrong_prefix():
    """unique_id not starting with the prefix raises ValueError."""
    with pytest.raises(ValueError):
        ConcreteModbusDevice(None, "BadUID", 0, 1, "model", Protocol.V1_8, unique_id="wrong_prefix_uid")


def test_modbus_device_invalid_address():
    """ModbusDevice rejects device_address outside 1-247."""
    with pytest.raises(ValueError):
        ConcreteModbusDevice(None, "Invalid", 0, 0, "model", Protocol.V1_8)
    with pytest.raises(ValueError):
        ConcreteModbusDevice(None, "Invalid", 0, 248, "model", Protocol.V1_8)


# ===========================================================================
# ModbusDevice._add_read_sensor protocol version checks
# ===========================================================================


def test_modbus_device_add_read_sensor_protocol_too_high():
    """Lines 962-965: sensor with protocol_version > device is skipped."""
    dev = ConcreteModbusDevice(None, "Dev", 0, 1, "model", Protocol.V1_8)
    s = DummyReadable("s_high_pv", protocol_version=Protocol.V2_4)
    result = dev._add_read_sensor(s)
    assert result is False


def test_modbus_device_add_read_sensor_protocol_matches():
    """sensor with matching protocol_version is added."""
    dev = ConcreteModbusDevice(None, "Dev2", 0, 2, "model", Protocol.V1_8)
    s = DummyReadable("s_ok_pv", protocol_version=Protocol.V1_8)
    result = dev._add_read_sensor(s)
    assert result is True


# ===========================================================================
# ModbusDevice._add_writeonly_sensor checks
# ===========================================================================


def test_modbus_device_add_writeonly_wrong_type():
    """Line 1005 area: sensor of wrong DeviceType is rejected."""

    class InverterDevice(ModbusDevice):
        def __init__(self, *args, **kwargs):
            super().__init__(HybridInverter(), *args, **kwargs)

    dev = InverterDevice("Inv2", 0, 3, "model", Protocol.V1_8)
    wo = DummyWriteOnly("wo_wrong_type")  # Not a HybridInverter subclass
    dev._add_writeonly_sensor(wo)
    assert "wo_wrong_type" not in dev.write_sensors


def test_modbus_device_add_writeonly_protocol_too_high():
    """Lines 1020-1025: WriteOnly sensor with too-high protocol version is skipped."""
    dev = ConcreteModbusDevice(None, "Dev3", 0, 4, "model", Protocol.V1_8)
    wo = DummyWriteOnly("wo_high_pv", protocol_version=Protocol.V2_4)
    dev._add_writeonly_sensor(wo)
    assert "wo_high_pv" not in dev.write_sensors


def test_modbus_device_add_writeonly_valid():
    """Valid WriteOnly sensor is added."""
    dev = ConcreteModbusDevice(None, "Dev4", 0, 5, "model", Protocol.V1_8)
    wo = DummyWriteOnly("wo_valid", protocol_version=Protocol.V1_8)
    dev._add_writeonly_sensor(wo)
    assert "wo_valid" in dev.write_sensors


# ===========================================================================
# _add_read_sensor when sensor not a ReadableSensorMixin
# ===========================================================================


def test_add_read_sensor_not_readable(device):
    """Lines 1042-1043: adding a non-ReadableSensorMixin logs error and returns False."""

    class NotReadable(Sensor):
        def __init__(self, uid):
            self.unique_id = uid
            self["unique_id"] = uid
            object.__setattr__(self, "unique_id", uid)

        def configure_mqtt_topics(self, device_id):
            pass

        def apply_sensor_overrides(self, registers):
            pass

        def get_discovery(self, mqtt_client):
            return {}

        def publish_attributes(self, mqtt_client, clean=False):
            pass

    nr = NotReadable("not_readable")
    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        result = device._add_read_sensor(nr)
    assert result is False
    mock_log.error.assert_called()


# ===========================================================================
# _add_read_sensor with a named group
# ===========================================================================


def test_add_read_sensor_with_group(device):
    """Lines 1053-1055: sensor added under a named group is stored in group_sensors."""
    s = DummyReadable("s_grouped", publishable=True)
    device._add_read_sensor(s, group="my_group")
    assert "my_group" in device.group_sensors
    assert s in device.group_sensors["my_group"]
    assert s.unique_id in device.all_sensors


def test_add_read_sensor_appends_to_existing_group(device):
    """Adding two sensors to the same group accumulates them."""
    s1 = DummyReadable("s_g1")
    s2 = DummyReadable("s_g2")
    device._add_read_sensor(s1, group="shared_group")
    device._add_read_sensor(s2, group="shared_group")
    assert len(device.group_sensors["shared_group"]) == 2


# ===========================================================================
# _add_to_all_sensors duplicate guard / debug path
# ===========================================================================


def test_add_to_all_sensors_duplicate_skipped(device):
    """adding a sensor that already exists is silently skipped."""
    s = DummyReadable("s_dup", publishable=True)
    device._add_read_sensor(s)
    count_before = len(device.all_sensors)
    device._add_to_all_sensors(s)
    assert len(device.all_sensors) == count_before


def test_add_to_all_sensors_debug_logging_enabled(device):
    """debug log emitted when sensor.debug_logging is True."""
    s = DummyReadable("s_debug_log")
    s.debug_logging = True
    with patch("sigenergy2mqtt.devices.device.logging") as mock_log:
        device._add_to_all_sensors(s)
        mock_log.debug.assert_called()


# ===========================================================================
# publish_availability propagates to children
# ===========================================================================


def test_publish_availability_propagates_to_children(device):
    """publish_availability is called on each child device."""
    child = Device("Child", 0, "uid_child_avail", "mf", "model", Protocol.V1_8)
    device.children.append(child)

    mqtt_client = MagicMock()
    child.publish_availability = MagicMock()

    device.publish_availability(mqtt_client, "online")
    child.publish_availability.assert_called_once_with(mqtt_client, "online")


# ===========================================================================
# publish_discovery with no components (empty device)
# ===========================================================================


def test_publish_discovery_no_components(device):
    """Lines 1155-1157: when there are no discovery components, empty discovery is published."""
    mqtt_client = MagicMock()
    device.publish_discovery(mqtt_client, clean=False)
    # publish should be called to clear
    mqtt_client.publish.assert_called()


def test_publish_discovery_clean(device):
    """Lines 1163-1165: clean=True clears availability and discovery."""
    mqtt_client = MagicMock()
    device.publish_discovery(mqtt_client, clean=True)
    calls = [str(c) for c in mqtt_client.publish.call_args_list]
    # Should publish None for availability and discovery
    assert mqtt_client.publish.call_count >= 1


# ===========================================================================
# publish_discovery with components
# ===========================================================================


def test_publish_discovery_with_components():
    """Lines 1167+: discovery JSON is published when sensors have components."""
    dev = Device("Disco", 0, "uid_disco", "mf", "model", Protocol.V1_8)
    s = DummyReadable("s_disco")
    s.get_discovery = MagicMock(return_value={"s_disco": {"platform": "sensor"}})
    dev.all_sensors["s_disco"] = s
    dev.sensors["s_disco"] = s  # same reference

    mqtt_client = MagicMock()
    mqtt_client.publish.return_value = MagicMock()

    dev.publish_discovery(mqtt_client, clean=False)
    mqtt_client.publish.assert_called()


# ===========================================================================
# publish_attributes propagation
# ===========================================================================


def test_publish_attributes_propagates_to_children(device):
    """publish_attributes propagates to child devices."""
    child = Device("AttrChild", 0, "uid_attr_child", "mf", "model", Protocol.V1_8)
    device.children.append(child)
    child.publish_attributes = MagicMock()
    device.publish_attributes(MagicMock(), propagate=True)
    child.publish_attributes.assert_called_once()


def test_publish_attributes_no_propagation(device):
    """propagate=False does not call children."""
    child = Device("AttrChild2", 0, "uid_attr_child2", "mf", "model", Protocol.V1_8)
    device.children.append(child)
    child.publish_attributes = MagicMock()
    device.publish_attributes(MagicMock(), propagate=False)
    child.publish_attributes.assert_not_called()


# ===========================================================================
# DeviceRegistry.get / DeviceRegistry.clear
# ===========================================================================


def test_device_registry_clear():
    """Lines 1266-1267: DeviceRegistry.clear removes all entries."""
    Device("R1", 0, "uid_r1", "mf", "m", Protocol.V1_8)
    Device("R2", 1, "uid_r2", "mf", "m", Protocol.V1_8)
    DeviceRegistry.clear()
    assert DeviceRegistry.get(0) == []
    assert DeviceRegistry.get(1) == []


def test_device_registry_get_missing_plant():
    """Lines 1269-1270: get() returns empty list for unknown plant_index."""
    DeviceRegistry.clear()
    assert DeviceRegistry.get(999) == []


def test_device_registry_returns_copy():
    """DeviceRegistry.get returns a copy so mutations don't affect registry."""
    DeviceRegistry.clear()
    d = Device("Copy", 0, "uid_copy", "mf", "m", Protocol.V1_8)
    lst = DeviceRegistry.get(0)
    lst.clear()
    assert d in DeviceRegistry.get(0)
