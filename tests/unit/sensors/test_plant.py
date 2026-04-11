import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import AvailabilityMixin, DiscoveryKeys, Sensor
from sigenergy2mqtt.sensors.plant_derived import PlantConsumedPower
from sigenergy2mqtt.sensors.plant_read_only import EMSWorkMode, SystemTimeZone
from sigenergy2mqtt.sensors.plant_read_write import ActivePowerFixedAdjustmentTargetValue, IndependentPhasePowerControl, MaxChargingLimit, PlantStatus, RemoteEMSControlMode


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = True
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.modbus = [MagicMock()]
    cfg.modbus[0].scan_interval.high = 10
    cfg.modbus[0].scan_interval.realtime = 5
    cfg.modbus[0].scan_interval.low = 600
    cfg.modbus[0].scan_interval.medium = 60

    with _swap_active_config(cfg):
        yield cfg


class TestPlantReadOnly:
    def test_system_time_zone(self, mock_config):
        sensor = SystemTimeZone(plant_index=0)
        # Test state2raw
        assert sensor.state2raw("UTC+10:00") == 600
        assert sensor.state2raw("UTC-05:00") == -300

        # Test get_state (mocking super)
        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 600
            assert asyncio.run(sensor.get_state()) == "UTC+10:00"

    @pytest.mark.asyncio
    async def test_ems_work_mode(self, mock_config):
        sensor = EMSWorkMode(plant_index=0)
        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = 1
            assert await sensor.get_state() == "Sigen AI"
            mock_get.return_value = 9
            assert await sensor.get_state() == "Time-Based Control"


class TestPlantReadWrite:
    def test_plant_status(self, mock_config):
        sensor = PlantStatus(plant_index=0)
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "0:Stop 1:Start" in attrs["comment"]

    def test_active_power_adjustment(self, mock_config):
        availability = MagicMock(spec=AvailabilityMixin)
        sensor = ActivePowerFixedAdjustmentTargetValue(plant_index=0, remote_ems=availability)
        assert sensor["unit_of_measurement"] == "kW"

    def test_max_charging_limit_configure_topics_without_remote_ems_mode(self, mock_config):
        mock_config.ems_mode_check = True
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigenergy2mqtt/remote_ems/state"

        sensor = MaxChargingLimit(plant_index=0, remote_ems=remote_ems, remote_ems_mode=None, rated_charging_power=12.0)
        sensor.configure_mqtt_topics("test_device")

        availability = sensor[DiscoveryKeys.AVAILABILITY]
        assert isinstance(availability, list)
        topics = [item.get("topic") for item in availability]
        assert remote_ems.state_topic in topics
        assert all("is_charging" not in str(topic) for topic in topics if topic)

    def test_max_charging_limit_configure_topics_with_remote_ems_mode_adds_mode_topic(self, mock_config):
        mock_config.ems_mode_check = True
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigenergy2mqtt/remote_ems/state"
        remote_ems_mode = MagicMock()
        remote_ems_mode.is_charging_mode_topic = "sigenergy2mqtt/remote_ems/mode/is_charging"

        sensor = MaxChargingLimit(plant_index=0, remote_ems=remote_ems, remote_ems_mode=remote_ems_mode, rated_charging_power=12.0)
        sensor.configure_mqtt_topics("test_device")

        availability = sensor[DiscoveryKeys.AVAILABILITY]
        assert isinstance(availability, list)
        topics = [item["topic"] for item in availability]
        assert remote_ems.state_topic in topics
        assert remote_ems_mode.is_charging_mode_topic in topics

    def test_max_charging_limit_no_mode_topic_when_ems_mode_check_disabled(self, mock_config):
        mock_config.ems_mode_check = False
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigenergy2mqtt/remote_ems/state"
        remote_ems_mode = MagicMock()
        remote_ems_mode.is_charging_mode_topic = "sigenergy2mqtt/remote_ems/mode/is_charging"

        sensor = MaxChargingLimit(plant_index=0, remote_ems=remote_ems, remote_ems_mode=remote_ems_mode, rated_charging_power=12.0)
        sensor.configure_mqtt_topics("test_device")

        availability = sensor[DiscoveryKeys.AVAILABILITY]
        topics = [item["topic"] for item in availability]
        assert remote_ems.state_topic in topics
        assert remote_ems_mode.is_charging_mode_topic not in topics

    def test_max_charging_limit_no_mode_topic_when_home_assistant_disabled(self, mock_config):
        mock_config.ems_mode_check = True
        mock_config.home_assistant.enabled = False
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigenergy2mqtt/remote_ems/state"
        remote_ems_mode = MagicMock()
        remote_ems_mode.is_charging_mode_topic = "sigenergy2mqtt/remote_ems/mode/is_charging"

        sensor = MaxChargingLimit(plant_index=0, remote_ems=remote_ems, remote_ems_mode=remote_ems_mode, rated_charging_power=12.0)
        sensor.configure_mqtt_topics("test_device")

        with pytest.raises(KeyError):
            _ = sensor[DiscoveryKeys.AVAILABILITY]


class TestPlantDerived:
    @pytest.mark.asyncio
    async def test_plant_consumed_power(self, mock_config):
        sensor = PlantConsumedPower(plant_index=0, method=ConsumptionMethod.CALCULATED)
        sensor.configure_mqtt_topics("test_device")

        # Mock some source updates
        # source names are from the class itself: "battery", "grid", "pv"
        sensor._update_source("pv", 5000)
        sensor._update_source("battery", -1000)  # Discharging (it negates it internally)
        sensor._update_source("grid", 500)  # Importing

        sensor._set_latest_consumption()
        # Battery charging is positive, discharging is negative.
        # In CALCULATED: battery has negate=True.
        # grid has negate=False.
        # pv has negate=False.
        # battery.state = (-(-1000) if negate else -1000) * gain = 1000 * 1 = 1000
        # grid.state = 500 * 1 = 500
        # pv.state = 5000 * 1 = 5000
        # total = 5000 + 1000 + 500 = 6500.
        # Wait, the comment says: "PV Power + GridSensorActivePower - BatteryPower"
        # Let's re-read the code logic in _set_latest_consumption and _update_source.
        # _update_source: self._sources[source].state = (-value if self._sources[source].negate else value) * self._sources[source].gain
        # If battery power is discharging, it's negative (e.g., -1000).
        # Battery source has negate=True.
        # battery.state = (-(-1000)) * 1 = 1000.
        # If grid is importing, it's positive (e.g., 500).
        # Grid source has negate=False.
        # grid.state = 500 * 1 = 500.
        # If pv is producing, it's positive (e.g., 5000).
        # pv source has negate=False.
        # pv.state = 5000 * 1 = 5000.
        # sum = 5000 + 1000 + 500 = 6500.
        # This makes sense: 6500 is total consumption if PV is 5000, battery is supplying 1000, and grid is supplying 500.

        assert sensor._states[-1][1] == 6500

        # Test attributes
        attrs = sensor.get_attributes()
        assert "source" in attrs
        assert "TotalPVPower" in attrs["source"]

    @pytest.mark.asyncio
    async def test_remote_ems_control_mode_publish(self, mock_config):
        mock_config.ems_mode_check = True
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "some/topic"
        sensor = RemoteEMSControlMode(plant_index=0, remote_ems=remote_ems)
        sensor.configure_mqtt_topics("test_device")

        mqtt_client = MagicMock()

        # Test Charging Case (mode 3)
        sensor.set_latest_state(3)
        await sensor.publish(mqtt_client, MagicMock(), republish=True)
        mqtt_client.publish.assert_any_call(sensor.is_charging_mode_topic, "1", 0, False)
        mqtt_client.publish.assert_any_call(sensor.is_discharging_mode_topic, "0", 0, False)
        mqtt_client.publish.assert_any_call(sensor.is_charging_discharging_topic, "1", 0, False)

        # Test Discharging Case (mode 5)
        sensor.set_latest_state(5)
        await sensor.publish(mqtt_client, MagicMock(), republish=True)
        mqtt_client.publish.assert_any_call(sensor.is_charging_mode_topic, "0", 0, False)
        mqtt_client.publish.assert_any_call(sensor.is_discharging_mode_topic, "1", 0, False)

    def test_independent_phase_power_control_publishable(self, mock_config):
        # Output type 2 = L1/L2/L3/N
        sensor_ok = IndependentPhasePowerControl(plant_index=0, output_type=2)
        assert sensor_ok.publishable is True

        # Other output type
        sensor_no = IndependentPhasePowerControl(plant_index=0, output_type=1)
        assert sensor_no.publishable is False
