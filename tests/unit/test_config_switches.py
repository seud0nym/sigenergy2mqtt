import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock circular dependencies before importing sensors.base
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

from sigenergy2mqtt.common import Protocol  # noqa: E402
from sigenergy2mqtt.config import Config  # noqa: E402
from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration  # noqa: E402
from sigenergy2mqtt.sensors.base import AvailabilityMixin, Sensor  # noqa: E402
from sigenergy2mqtt.sensors.plant_read_write import MaxChargingLimit, RemoteEMSControlMode  # noqa: E402


class MockSensor(Sensor):
    def __init__(self, name="Mock Sensor", unique_id="sigenergy_mock_unique_id", object_id="sigenergy_mock_object_id", **kwargs):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            unit="unit",
            device_class=None,
            state_class=None,
            icon="mdi:icon",
            gain=1,
            precision=1,
            protocol_version=Protocol.V1_8,
            **kwargs,
        )

    async def _update_internal_state(self, **kwargs):
        return True


class TestConfigSwitches:
    """Tests for Config flags usage logic."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Reset Config to known state before each test."""
        Config.home_assistant = HomeAssistantConfiguration()
        Config.home_assistant.enabled = True
        Config.home_assistant.use_simplified_topics = False
        Config.home_assistant.discovery_prefix = "homeassistant"
        Config.home_assistant.entity_id_prefix = "sigenergy"
        Config.home_assistant.unique_id_prefix = "sigenergy"
        Config.ems_mode_check = True

        # Reset Sensor static registries
        Sensor._used_object_ids = {}
        Sensor._used_unique_ids = {}

    def test_mqtt_topics_standard(self):
        """Test MQTT topics with HA enabled and standard topics."""
        Config.home_assistant.enabled = True
        Config.home_assistant.use_simplified_topics = False

        sensor = MockSensor(object_id="sigenergy_test_obj")
        sensor.configure_mqtt_topics("test_device")

        assert sensor["state_topic"] == "homeassistant/sensor/test_device/sigenergy_test_obj/state"
        assert sensor["raw_state_topic"] == "homeassistant/sensor/test_device/sigenergy_test_obj/raw"

    def test_mqtt_topics_simplified(self):
        """Test MQTT topics with HA enabled and simplified topics."""
        Config.home_assistant.enabled = True
        Config.home_assistant.use_simplified_topics = True

        sensor = MockSensor(object_id="sigenergy_test_obj")
        sensor.configure_mqtt_topics("test_device")

        assert sensor["state_topic"] == "sigenergy2mqtt/sigenergy_test_obj/state"
        assert sensor["raw_state_topic"] == "sigenergy2mqtt/sigenergy_test_obj/raw"

    def test_mqtt_topics_ha_disabled(self):
        """Test MQTT topics with HA disabled."""
        Config.home_assistant.enabled = False
        # Simplified flag shouldn't matter if HA is disabled, logic defaults to simplified style
        Config.home_assistant.use_simplified_topics = False

        sensor = MockSensor(object_id="sigenergy_test_obj")
        sensor.configure_mqtt_topics("test_device")

        assert sensor["state_topic"] == "sigenergy2mqtt/sigenergy_test_obj/state"

    def test_sensor_attributes_ha_enabled(self):
        """Test sensor attributes when HA is enabled."""
        Config.home_assistant.enabled = True

        sensor = MockSensor()
        attrs = sensor.get_attributes()

        assert "name" not in attrs
        assert "unit-of-measurement" not in attrs

    def test_sensor_attributes_ha_disabled(self):
        """Test sensor attributes when HA is disabled."""
        Config.home_assistant.enabled = False

        sensor = MockSensor()
        attrs = sensor.get_attributes()

        assert "name" in attrs
        assert attrs["name"] == "Mock Sensor"
        assert "unit-of-measurement" in attrs
        assert attrs["unit-of-measurement"] == "unit"

    @pytest.mark.asyncio
    async def test_ems_mode_check_topics_and_publish(self):
        """Test RemoteEMSControlMode topic configuration and publishing with EMS check enabled."""
        Config.home_assistant.enabled = True
        Config.ems_mode_check = True

        mock_remote_ems = MagicMock(spec=AvailabilityMixin)
        mock_remote_ems.state_topic = "some/topic"

        sensor = RemoteEMSControlMode(0, mock_remote_ems)
        base_topic = sensor.configure_mqtt_topics("device_id")

        # Verify extra topics are created
        assert hasattr(sensor, "is_charging_mode_topic")
        assert sensor.is_charging_mode_topic == f"{base_topic}/is_charging_mode"

        # Verify publishing logic
        mock_mqtt = MagicMock()
        mock_modbus = MagicMock()

        # Mock internal update to avoid actual modbus read
        # Using AsyncMock for async method
        with patch.object(RemoteEMSControlMode, "_update_internal_state", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True

            # Set internal state directly
            sensor._states.append((time.time(), 3))  # Command Charging

            await sensor.publish(mock_mqtt, mock_modbus)

        # Verify extra topics were published
        calls = [(sensor.is_charging_mode_topic, "1"), (sensor.is_discharging_mode_topic, "0"), (sensor.is_charging_discharging_topic, "1")]
        for topic, payload in calls:
            mock_mqtt.publish.assert_any_call(topic, payload, sensor._qos, sensor._retain)

    @pytest.mark.asyncio
    async def test_ems_mode_check_disabled_topics_and_publish(self):
        """Test RemoteEMSControlMode logic when EMS check is disabled."""
        Config.home_assistant.enabled = True
        Config.ems_mode_check = False

        mock_remote_ems = MagicMock(spec=AvailabilityMixin)
        mock_remote_ems.state_topic = "some/topic"

        sensor = RemoteEMSControlMode(0, mock_remote_ems)
        sensor.configure_mqtt_topics("device_id")

        # Verify extra topics are NOT created
        assert not hasattr(sensor, "is_charging_mode_topic")

        # Verify publishing logic does NOT publish extras
        mock_mqtt = MagicMock()
        mock_modbus = MagicMock()

        # Mock internal update
        with patch.object(RemoteEMSControlMode, "_update_internal_state", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True

            sensor._states.append((time.time(), 3))  # Command Charging

            await sensor.publish(mock_mqtt, mock_modbus)

        # Should only publish standard state and raw state
        # The number of calls depends on whether get_state publishes anything else?
        # get_state publishes 'state' if changed or republish=True. And potentially 'raw' if configured?
        # Sensor.publish -> get_state -> ... -> mqtt_client.publish(state_topic, ...).
        # Sensor.publish also publishes attributes? No, attributes are separate update usually?
        # Let's check call count logic. Usually it publishes state and raw state if configured.
        # Check assertions logic: expecting 2 calls (state and raw).

        # We can also check that it did NOT call publish with "is_charging_mode_topic"

        called_topics = [call.args[0] for call in mock_mqtt.publish.call_args_list]
        assert not any("is_charging_mode" in t for t in called_topics)
        assert mock_mqtt.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_max_charging_limit_validation_enabled(self):
        """Test MaxChargingLimit validation with EMS check enabled."""
        Config.ems_mode_check = True

        mock_remote_ems = MagicMock(spec=AvailabilityMixin)
        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.latest_raw_state = 0  # Not Command Charging

        sensor = MaxChargingLimit(0, mock_remote_ems, mock_mode, 10.0)

        # Should fail because mode is not correct
        assert await sensor.value_is_valid(None, 5.0) is False

        mock_mode.latest_raw_state = 3  # Command Charging
        assert await sensor.value_is_valid(None, 5.0) is True

    @pytest.mark.asyncio
    async def test_max_charging_limit_validation_disabled(self):
        """Test MaxChargingLimit validation with EMS check disabled."""
        Config.ems_mode_check = False

        mock_remote_ems = MagicMock(spec=AvailabilityMixin)
        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.latest_raw_state = 0  # Not Command Charging

        sensor = MaxChargingLimit(0, mock_remote_ems, mock_mode, 10.0)

        # Should pass even though mode is incorrect
        assert await sensor.value_is_valid(None, 5.0) is True

    def test_max_charging_limit_attributes_comment(self):
        """Test comment attribute changes based on ems_mode_check."""
        Config.ems_mode_check = True
        mock_remote_ems = MagicMock(spec=AvailabilityMixin)
        mock_remote_ems.state_topic = "availability/topic"

        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.is_charging_mode_topic = "is_charging_mode_topic"
        mock_mode.is_discharging_mode_topic = "is_discharging_mode_topic"
        mock_mode.is_charging_discharging_topic = "is_charging_discharging_topic"

        sensor = MaxChargingLimit(0, mock_remote_ems, mock_mode, 10.0)
        sensor.configure_mqtt_topics("test_device")

        assert "Takes effect when Remote EMS control mode" in sensor.get_attributes()["comment"]

        Config.ems_mode_check = False
        sensor = MaxChargingLimit(0, mock_remote_ems, mock_mode, 10.0)
        sensor.configure_mqtt_topics("test_device")

        assert "Takes effect when Remote EMS control mode" not in sensor.get_attributes()["comment"]

    def test_edit_percentage_with_box(self):
        """Test if 'mode' attribute is 'slider' or 'box' based on edit_percentage_with_box."""
        from sigenergy2mqtt.sensors.plant_read_write import ESSBackupSOC

        Config.home_assistant.enabled = True
        Config.home_assistant.edit_percentage_with_box = False
        sensor = ESSBackupSOC(0)
        assert sensor["mode"] == "slider"

        Config.home_assistant.edit_percentage_with_box = True
        sensor = ESSBackupSOC(0)
        assert sensor["mode"] == "box"

    def test_sensor_enabled_by_default(self):
        """Test if 'enabled_by_default' is correctly set from Config."""
        Config.home_assistant.enabled_by_default = False
        sensor = MockSensor()
        assert sensor["enabled_by_default"] is False

        Config.home_assistant.enabled_by_default = True
        sensor = MockSensor()
        assert sensor["enabled_by_default"] is True

    def test_sensor_debug_logging_inheritance(self):
        """Test if sensor debug_logging is inherited from Config.sensor_debug_logging."""
        Config.sensor_debug_logging = False
        sensor = MockSensor()
        assert sensor.debug_logging is False

        Config.sensor_debug_logging = True
        sensor = MockSensor()
        assert sensor.debug_logging is True
