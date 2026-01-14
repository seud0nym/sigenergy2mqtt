import json
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import Protocol
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmSensor, EnergyDailyAccumulationSensor, ReadableSensorMixin, Sensor, TimestampSensor
from sigenergy2mqtt.sensors.const import InputType


class DummySensor(ReadableSensorMixin):
    def __init__(self, name, unique_id, address):
        super().__init__(name=name, unique_id=unique_id, object_id=unique_id, unit="W", device_class="power", state_class="measurement", icon="mdi:flash", gain=1.0, precision=2, scan_interval=60)
        self.address = address
        self.count = 1
        self.device_address = 1
        self.input_type = InputType.HOLDING
        self.data_type = ModbusDataType.UINT16
        self._publishable = True
        # For discovery to work, these MUST be set or configured
        self["state_topic"] = f"state/{unique_id}"
        self["json_attributes_topic"] = f"state/{unique_id}/attr"

    async def _update_internal_state(self, **kwargs) -> bool:
        return False

    def configure_mqtt_topics(self, device_id):
        self["state_topic"] = f"state/{device_id}/{self.unique_id}"
        self["json_attributes_topic"] = f"state/{device_id}/{self.unique_id}/attr"
        return self["state_topic"]


@pytest.fixture
def mock_config(tmp_path):
    # Ensure logging level doesn't trigger discovery dump unless we want it
    import logging

    old_level = logging.getLogger().level

    # Patch the root Config object AND where it's imported in base and device
    with patch("sigenergy2mqtt.config.Config") as mock_conf, patch("sigenergy2mqtt.devices.device.Config", mock_conf), patch("sigenergy2mqtt.sensors.base.Config", mock_conf):
        mock_conf.home_assistant.enabled = True
        mock_conf.home_assistant.discovery_prefix = "homeassistant"
        mock_conf.home_assistant.unique_id_prefix = "sigen"
        mock_conf.home_assistant.entity_id_prefix = "sigen"
        mock_conf.home_assistant.use_simplified_topics = False
        mock_conf.home_assistant.device_name_prefix = ""
        mock_conf.home_assistant.enabled_by_default = True
        mock_conf.origin = {"name": "sigenergy2mqtt", "sw": "1.0", "url": "http://test"}
        mock_conf.persistent_state_path = tmp_path
        mock_conf.clean = False

        mock_device = MagicMock()
        mock_device.registers = None
        mock_device.scan_interval.realtime = 5
        mock_conf.devices = [mock_device]

        mock_conf.sensor_overrides = {}
        mock_conf.sensor_debug_logging = False

        yield mock_conf

    logging.getLogger().setLevel(old_level)
    DeviceRegistry._devices.clear()
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


def get_discovery_payload(mqtt_mock):
    """Helper to extract discovery payload from mqtt mock."""
    for call in mqtt_mock.publish.call_args_list:
        topic = call[0][0] if call[0] else call[1].get("topic")
        if topic and topic.endswith("/config"):
            payload = call[0][1] if len(call[0]) > 1 else call[1].get("payload")
            if payload is not None:
                return topic, json.loads(payload)
    return None, None


def test_discovery_base_structure(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    sensor = DummySensor("TestSensor", "sigen_s1", 100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    topic, discovery = get_discovery_payload(mqtt_client)

    assert topic == "homeassistant/device/sigen_uid/config"
    assert "dev" in discovery
    assert "o" in discovery
    assert "cmps" in discovery

    assert discovery["dev"]["name"] == "TestDevice"
    assert "sigen_s1" in discovery["cmps"]
    comp = discovery["cmps"]["sigen_s1"]
    assert comp["platform"] == "sensor"
    assert comp["name"] == "TestSensor"


def test_energy_daily_accumulation_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    source = DummySensor("Power", "sigen_power", 100)
    dev._add_read_sensor(cast(Sensor, source))

    sensor = EnergyDailyAccumulationSensor("Daily Energy", "sigen_daily", "sigen_daily", source)
    dev._add_to_all_sensors(sensor)

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    key = "sigen_daily"
    assert key in discovery["cmps"]
    comp = discovery["cmps"][key]
    assert comp["device_class"] == "power"
    assert comp["state_class"] == "measurement"


def test_alarm_sensor_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)

    class ConcreteAlarm(AlarmSensor):
        def decode_alarm_bit(self, bit):
            return "Error"

    sensor = ConcreteAlarm("Alarm1", "sigen_alarm1", 0, 1, 30001, Protocol.V1_8, "Equipment")
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    expected_id = "sigen_0_001_30001"
    assert expected_id in discovery["cmps"]
    comp = discovery["cmps"][expected_id]
    assert comp["platform"] == "sensor"


def test_timestamp_sensor_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)

    # name, object_id, input_type, plant_index, device_address, address, scan_interval, protocol_version
    sensor = TimestampSensor("UpdateTime", "sigen_ts1", InputType.INPUT, 0, 1, 30005, 60, Protocol.V1_8)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    expected_id = "sigen_0_001_30005"
    assert expected_id in discovery["cmps"]
    comp = discovery["cmps"][expected_id]
    assert comp["entity_category"] == "diagnostic"
    assert comp["device_class"] == "timestamp"


def test_simplified_topics_discovery(mock_config):
    mock_config.home_assistant.use_simplified_topics = True

    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    sensor = DummySensor("TestSensor", "sigen_s1", 100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)
    comp = discovery["cmps"]["sigen_s1"]

    assert "sigen_s1" in comp["state_topic"]
