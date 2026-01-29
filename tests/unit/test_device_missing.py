import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from paho.mqtt.client import MQTTMessageInfo

from sigenergy2mqtt.common import DeviceType, HybridInverter, Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry, ModbusDevice
from sigenergy2mqtt.sensors.base import (
    AlarmCombinedSensor,
    DerivedSensor,
    ObservableMixin,
    ReadableSensorMixin,
    Sensor,
    WritableSensorMixin,
    WriteOnlySensor,
)

# --- Helper Classes ---


class DummyReadable(ReadableSensorMixin, Sensor):
    def __init__(self, unique_id, publishable=True, address=1, count=1):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "_publishable", publishable)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", 1)
        object.__setattr__(self, "scan_interval", 10)
        object.__setattr__(self, "input_type", "holding")
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "force_publish", False)

    async def _update_internal_state(self, **kwargs):
        return False

    def configure_mqtt_topics(self, device_id):
        self["state_topic"] = f"state/{device_id}/{self.unique_id}"
        return self["state_topic"]

    async def publish(self, mqtt_client, modbus_client=None, republish=False):
        return True

    def observable_topics(self):
        return []


class DummyWritable(WritableSensorMixin, Sensor):
    def __init__(self, unique_id, command_topic="cmd"):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self["command_topic"] = command_topic
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "address", 1)
        object.__setattr__(self, "input_type", "holding")
        object.__setattr__(self, "protocol_version", Protocol.V1_8)
        object.__setattr__(self, "parent_device", None)

    async def set_value(self, client, userdata, message):
        pass

    def apply_sensor_overrides(self, registers):
        pass

    def configure_mqtt_topics(self, device_id):
        pass


class DummyWriteOnly(WriteOnlySensor):
    def __init__(self, unique_id):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self["command_topic"] = f"cmd/{unique_id}"
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "address", 1)
        object.__setattr__(self, "input_type", "holding")
        object.__setattr__(self, "protocol_version", Protocol.V1_8)
        object.__setattr__(self, "debug_logging", False)
        self._values = {"off": 0, "on": 1}

    async def set_value(self, client, userdata, message):
        pass

    def apply_sensor_overrides(self, registers):
        return None

    def configure_mqtt_topics(self, device_id):
        return ""


class DummyObservable(ObservableMixin, ReadableSensorMixin, Sensor):
    def __init__(self, unique_id, topic):
        self.unique_id = unique_id
        self["unique_id"] = unique_id
        self.topic = topic
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "_publishable", False)
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "scan_interval", 10)

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


class ConcreteModbusDevice(ModbusDevice):
    pass


# --- Fixtures ---


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.devices.device.Config") as mock_conf:
        mock_conf.modbus = [types.SimpleNamespace(registers={}, disable_chunking=False)]
        mock_conf.home_assistant = types.SimpleNamespace(
            device_name_prefix="",
            unique_id_prefix="sigen",
            discovery_prefix="homeassistant",
            enabled=True,
            republish_discovery_interval=60,
        )
        mock_conf.origin = {}
        mock_conf.persistent_state_path = "."
        yield mock_conf
    DeviceRegistry._devices.clear()


@pytest.fixture
def device(mock_config):
    return Device("TestDev", 0, "uid_1", "mf", "model", Protocol.V1_8)


# --- Tests ---


def test_device_schedule(device):
    s1 = DummyReadable("s1", publishable=True, address=100)
    s2 = DummyReadable("s2", publishable=False, address=101)

    device._add_read_sensor(s1)
    device._add_read_sensor(s2)

    modbus = MagicMock()
    mqtt = MagicMock()

    s3 = DummyReadable("s3", publishable=False, address=200)
    device._add_read_sensor(s3)

    tasks = device.schedule(modbus, mqtt)

    # 1. Group (s1, s2) -> Task (because s1 is publishable)
    # 2. Group (s3) -> No Task
    # 3. Republish Discovery -> Task
    assert len(tasks) == 2


def test_device_subscribe(device):
    handler = MagicMock()
    mqtt_client = MagicMock()

    writable = DummyWritable("w1", command_topic="cmd/w1")
    device.all_sensors[writable.unique_id] = writable

    observable = DummyObservable("o1", topic="obs/o1")
    device.all_sensors[observable.unique_id] = observable

    device.subscribe(mqtt_client, handler)

    handler.register.assert_any_call(mqtt_client, "homeassistant/status", device.on_ha_state_change)
    handler.register.assert_any_call(mqtt_client, "cmd/w1", writable.set_value)

    # Observable callback needs to match. Device.subscribe passes sensor.notify
    handler.register.assert_any_call(mqtt_client, "obs/o1", observable.notify)


@pytest.mark.asyncio
async def test_device_on_ha_state_change(device):
    mqtt_client = MagicMock()
    mqtt_handler = AsyncMock()
    modbus_client = MagicMock()

    s1 = DummyReadable("s1")
    s1.publish = AsyncMock()
    device._add_read_sensor(s1)

    with patch("asyncio.sleep", new_callable=AsyncMock), patch.object(device, "publish_discovery", return_value=None):
        res = await device.on_ha_state_change(modbus_client, mqtt_client, "online", "src", mqtt_handler)

        assert res is True
        mqtt_handler.wait_for.assert_awaited()
        s1.publish.assert_awaited_with(mqtt_client, modbus_client=modbus_client, republish=True)

        res_off = await device.on_ha_state_change(modbus_client, mqtt_client, "offline", "src", mqtt_handler)
        assert res_off is False


def test_device_get_sensor(device):
    child = Device("Child", 0, "child_uid", "mf", "model", Protocol.V1_8)
    s_child = DummyReadable("s_child", publishable=True)
    child._add_read_sensor(s_child)
    device._add_child_device(child)

    s_parent = DummyReadable("s_parent", publishable=True)
    device._add_read_sensor(s_parent)

    assert device.get_sensor("s_parent") == s_parent
    assert device.get_sensor("s_child", search_children=True) == s_child
    assert device.get_sensor("s_child", search_children=False) is None

    # Mock behavior of AlarmCombinedSensor
    # We must inherit from AlarmCombinedSensor for isinstance check
    class MockAlarmCombinedSensor(AlarmCombinedSensor):
        def __init__(self, unique_id):
            self.unique_id = unique_id
            self.alarms = [types.SimpleNamespace(unique_id="alarm_1")]

    # Patch AlarmCombinedSensor.__init__ to avoid complex setup
    with patch.object(AlarmCombinedSensor, "__init__", return_value=None):
        alarm_sensor = MockAlarmCombinedSensor("ac")
        device.all_sensors[alarm_sensor.unique_id] = alarm_sensor

        found = device.get_sensor("alarm_1")
        assert found is not None
        assert found.unique_id == "alarm_1"


def test_device_add_writeonly_sensor(device):
    wo = DummyWriteOnly("wo1")
    device._add_writeonly_sensor(wo)

    assert "wo1" in device.write_sensors
    assert "wo1" in device.all_sensors

    not_wo = DummyWritable("not_wo")
    device._add_writeonly_sensor(not_wo)
    assert "not_wo" not in device.write_sensors


def test_modbus_device_checks():
    class InverterDevice(ModbusDevice):
        def __init__(self, *args, **kwargs):
            super().__init__(HybridInverter(), *args, **kwargs)

    dev = InverterDevice("Inv", 0, 1, "model", Protocol.V1_8)

    s_plain = DummyReadable("s_plain")
    assert dev._add_read_sensor(s_plain) is False

    class ValidInverterSensor(DummyReadable, HybridInverter):
        def __init__(self, uid):
            super().__init__(uid)

    s_valid = ValidInverterSensor("s_valid")
    s_valid.protocol_version = Protocol.V1_8

    assert dev._add_read_sensor(s_valid) is True

    s_future = ValidInverterSensor("s_future")
    s_future.protocol_version = Protocol.V2_4
    assert dev._add_read_sensor(s_future) is False


def test_device_registry():
    DeviceRegistry._devices.clear()

    d1 = Device("d1", 0, "uid1", "mf", "md", Protocol.V1_8)
    d2 = Device("d2", 0, "uid2", "mf", "md", Protocol.V1_8)
    d3 = Device("d3", 1, "uid3", "mf", "md", Protocol.V1_8)

    l0 = DeviceRegistry.get(0)
    assert d1 in l0
    assert d2 in l0
    assert d3 not in l0

    l1 = DeviceRegistry.get(1)
    assert d3 in l1

    l2 = DeviceRegistry.get(99)
    assert l2 == []
