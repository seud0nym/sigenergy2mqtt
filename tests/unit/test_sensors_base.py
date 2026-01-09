import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock circular dependencies before importing sensors.base
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.devices.types"] = mock_types

from sigenergy2mqtt.config import Protocol  # noqa: E402
from sigenergy2mqtt.sensors.base import Sensor  # noqa: E402
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass  # noqa: E402


# Concrete implementation of Sensor for testing since Sensor is abstract
class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return True


class TestSensorBase:
    @pytest.fixture
    def sensor(self):
        # We need to ensure unique_id and object_id allow re-use or are unique per test
        # The Sensor class asserts uniqueness globally in class attributes.
        # We might need to clear _used_unique_ids and _used_object_ids between tests?
        # Let's inspect Sensor code again or just use unique values.
        # Sensor._used_unique_ids = {}
        # Sensor._used_object_ids = {}
        # Actually better to patch them if possible, or just use fresh IDs.

        # Checking Sensor.__init__ assertions:
        # unique_id must start with Config.home_assistant.unique_id_prefix (default "sigenergy_")
        # object_id must start with Config.home_assistant.entity_id_prefix (default "sigenergy_")

        # We'll rely on default config values which should be loaded/mocked.

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Test Sensor",
                unique_id="sigenergy_test_unique_id",
                object_id="sigenergy_test_object_id",
                unit="W",
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:solar-power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
            yield s

    def test_init(self, sensor):
        assert sensor["name"] == "Test Sensor"
        assert sensor["unique_id"] == "sigenergy_test_unique_id"
        assert sensor.gain == 1.0
        assert sensor.precision == 2
        assert sensor.protocol_version == Protocol.V2_4.value

    def test_apply_gain_and_precision(self, sensor):
        # Default gain=1.0, precision=2
        assert sensor._apply_gain_and_precision(10.1234) == 10.12
        assert sensor._apply_gain_and_precision(10) == 10

        # Change gain
        sensor._gain = 10.0
        assert sensor._apply_gain_and_precision(100.0) == 10.0  # 100 / 10 = 10

        # Change precision
        sensor._gain = 1.0
        sensor.precision = 0
        assert sensor._apply_gain_and_precision(10.6) == 11.0

        # Raw value (no gain/precision applied)
        assert sensor._apply_gain_and_precision(10.1234, raw=True) == 10.1234

    def test_configure_mqtt_topics(self, sensor):
        # Mock Config to ensure consistent behavior
        with patch("sigenergy2mqtt.sensors.base.Config") as MockConfig:
            MockConfig.home_assistant.enabled = True
            MockConfig.home_assistant.use_simplified_topics = False
            MockConfig.home_assistant.discovery_prefix = "homeassistant"

            base_topic = sensor.configure_mqtt_topics(device_id="test_device")

            assert base_topic == "homeassistant/sensor/test_device/sigenergy_test_object_id"
            assert sensor["state_topic"] == f"{base_topic}/state"
            assert sensor["raw_state_topic"] == f"{base_topic}/raw"
            assert sensor["json_attributes_topic"] == f"{base_topic}/attributes"
            assert sensor["availability_mode"] == "all"
            assert sensor["availability"] == [{"topic": "homeassistant/device/test_device/availability"}]

    def test_properties(self, sensor):
        # publishable
        sensor.publishable = False
        assert sensor.publishable is False
        sensor.publishable = True
        assert sensor.publishable is True

        # publish_raw
        sensor.publish_raw = True
        assert sensor.publish_raw is True

        # protocol_version setter
        sensor.protocol_version = Protocol.V2_4
        assert sensor.protocol_version == Protocol.V2_4.value
