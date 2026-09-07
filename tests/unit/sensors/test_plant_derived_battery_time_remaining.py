"""Tests for BatteryTimeRemaining plant derived sensor."""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, StateClass, UnitOfTime
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import DiscoveryKeys, Sensor
from sigenergy2mqtt.sensors.plant_derived import BatteryTimeRemaining
from sigenergy2mqtt.sensors.plant_read_only import (
    BatteryPower,
    PlantBatterySoC,
    PlantRatedEnergyCapacity,
)
from sigenergy2mqtt.sensors.plant_read_write import (
    ESSChargeCutOffSOC,
    ESSDischargeCutOffSOC,
)


@pytest.fixture(autouse=True)
def mock_config():
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = True
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    mock_modbus = MagicMock()
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]
    cfg.sensor_overrides = {}

    with _swap_active_config(cfg):
        yield cfg


def _make_battery_time_remaining():
    """Instantiate BatteryTimeRemaining with mocked source sensors."""
    capacity = MagicMock(spec=PlantRatedEnergyCapacity)
    capacity.protocol_version = ProtocolVersion.V2_5

    bp = MagicMock(spec=BatteryPower)
    bp.device_class = DeviceClass.POWER
    bp.state_class = StateClass.MEASUREMENT
    bp.protocol_version = ProtocolVersion.V1_8

    discharge_soc = MagicMock(spec=ESSDischargeCutOffSOC)
    discharge_soc.protocol_version = ProtocolVersion.V2_6

    charge_soc = MagicMock(spec=ESSChargeCutOffSOC)
    charge_soc.protocol_version = ProtocolVersion.V2_6

    current_soc = MagicMock(spec=PlantBatterySoC)
    current_soc.protocol_version = ProtocolVersion.V1_8

    sensor = BatteryTimeRemaining(0, capacity, current_soc, bp, discharge_soc, charge_soc)
    return sensor, capacity, current_soc, bp, discharge_soc, charge_soc


class TestBatteryTimeRemainingProperties:
    """Test metadata, naming, and attributes of BatteryTimeRemaining."""

    def test_initial_properties(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, capacity, current_soc, bp, discharge_soc, charge_soc = _make_battery_time_remaining()

            assert sensor.name == "Battery Time Remaining"
            assert sensor.unique_id == "sigen_0_battery_time_remaining"
            assert sensor.object_id == "sigen_0_battery_time_remaining"
            assert sensor.device_class == DeviceClass.DURATION
            assert sensor.state_class == StateClass.MEASUREMENT
            assert sensor.unit == UnitOfTime.HOURS
            assert sensor.precision == 2
            assert sensor[DiscoveryKeys.ICON] == "mdi:battery-clock"
            assert sensor.protocol_version == ProtocolVersion.V2_6
            assert set(sensor.source_sensors) == {capacity, current_soc, bp, discharge_soc, charge_soc}

    def test_attributes(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            attributes = sensor.get_attributes()
            assert "PlantRatedEnergyCapacity" in attributes["source"]
            assert "PlantBatterySoC" in attributes["source"]
            assert "BatteryPower" in attributes["source"]
            assert "ESSDischargeCutOffSOC" in attributes["source"]
            assert "ESSChargeCutOffSOC" in attributes["source"]
            assert "comment" in attributes
            assert "hours" in attributes["comment"]


class TestBatteryTimeRemainingCalculations:
    """Test discharging, charging, idle, and edge cases."""

    def test_discharging_returns_negative_hours(self):
        """Discharging: 10 kWh, 50% SoC, 10% cutoff, -2000 W -> -2.0 h."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._discharge_soc = 10.0
            sensor._battery_power = -2000.0

            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == -2.0

    def test_charging_returns_positive_hours(self):
        """Charging: 10 kWh, 50% SoC, 90% cutoff, +2000 W -> +2.0 h."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._charge_soc = 90.0
            sensor._battery_power = 2000.0

            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 2.0

    def test_idle_returns_zero_hours(self):
        """Battery power is 0 -> 0.0 hours."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = 0.0

            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 0.0

    def test_discharging_at_or_below_cutoff_returns_zero(self):
        """Discharging when SoC <= discharge cut-off -> 0.0 hours."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 10.0
            sensor._discharge_soc = 10.0
            sensor._battery_power = -2000.0

            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 0.0

            # Even below cut-off
            sensor._current_soc = 8.0
            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 0.0

    def test_charging_at_or_above_cutoff_returns_zero(self):
        """Charging when SoC >= charge cut-off -> 0.0 hours."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 90.0
            sensor._charge_soc = 90.0
            sensor._battery_power = 2000.0

            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 0.0

            # Even above cut-off
            sensor._current_soc = 95.0
            result = sensor._calculate_time_remaining()
            assert result is True
            assert sensor.latest_raw_state == 0.0


class TestBatteryTimeRemainingMissingStates:
    """Test None and missing state handling."""

    def test_missing_battery_power_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = None
            assert sensor._calculate_time_remaining() is False

    def test_missing_capacity_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = -1000.0
            sensor._current_soc = 50.0
            sensor._discharge_soc = 10.0
            sensor._rated_capacity_kwh = None
            assert sensor._calculate_time_remaining() is False

    def test_missing_soc_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = -1000.0
            sensor._rated_capacity_kwh = 10.0
            sensor._discharge_soc = 10.0
            sensor._current_soc = None
            assert sensor._calculate_time_remaining() is False

    def test_missing_discharge_soc_when_discharging_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = -1000.0
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._discharge_soc = None
            assert sensor._calculate_time_remaining() is False

    def test_missing_charge_soc_when_charging_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._battery_power = 1000.0
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._charge_soc = None
            assert sensor._calculate_time_remaining() is False


class TestBatteryTimeRemainingUpdateFromSourceSensor:
    """Test update_from_source_sensor dispatching and value extraction."""

    def test_update_from_battery_power(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._discharge_soc = 10.0

            source = MagicMock(spec=BatteryPower)
            source.latest_raw_state = -2000.0
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor.latest_raw_state == -2.0

    def test_update_from_battery_power_none_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            source = MagicMock(spec=BatteryPower)
            source.latest_raw_state = None
            assert sensor.update_from_source_sensor(source) is False
            assert sensor._battery_power is None

    def test_update_from_battery_power_invalid_returns_false(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            source = MagicMock(spec=BatteryPower)
            source.latest_raw_state = "invalid"
            assert sensor.update_from_source_sensor(source) is False
            assert sensor._battery_power is None

    def test_update_from_plant_battery_soc(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._discharge_soc = 10.0
            sensor._battery_power = -2000.0

            source = MagicMock(spec=PlantBatterySoC)
            source.latest_raw_state = 500.0
            source.gain = 10.0
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor._current_soc == 50.0
            assert sensor.latest_raw_state == -2.0

    def test_update_from_discharge_soc(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._battery_power = -2000.0

            source = MagicMock(spec=ESSDischargeCutOffSOC)
            source.latest_raw_state = 100.0
            source.gain = 10.0
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor._discharge_soc == 10.0
            assert sensor.latest_raw_state == -2.0

    def test_update_from_charge_soc(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._rated_capacity_kwh = 10.0
            sensor._current_soc = 50.0
            sensor._battery_power = 2000.0

            source = MagicMock(spec=ESSChargeCutOffSOC)
            source.latest_raw_state = 900.0
            source.gain = 10.0
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor._charge_soc == 90.0
            assert sensor.latest_raw_state == 2.0

    def test_update_from_rated_capacity(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            sensor._current_soc = 50.0
            sensor._discharge_soc = 10.0
            sensor._battery_power = -2000.0

            source = MagicMock(spec=PlantRatedEnergyCapacity)
            source.latest_raw_state = 1000.0
            source.gain = 100.0
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor._rated_capacity_kwh == 10.0
            assert sensor.latest_raw_state == -2.0

    def test_update_from_unrecognized_sensor(self, caplog):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_time_remaining()
            other_sensor = MagicMock(spec=Sensor)
            assert sensor.update_from_source_sensor(other_sensor) is False
            assert "Attempt to call update_from_source_sensor" in caplog.text


class TestBatteryTimeRemainingWithRealSensors:
    """Test full flow with concrete sensor classes."""

    def test_real_sensor_workflow(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            capacity = PlantRatedEnergyCapacity(0)
            current_soc = PlantBatterySoC(0)
            bp = BatteryPower(0)
            discharge_soc = ESSDischargeCutOffSOC(0)
            charge_soc = ESSChargeCutOffSOC(0)

            sensor = BatteryTimeRemaining(0, capacity, current_soc, bp, discharge_soc, charge_soc)

            # Set raw modbus states
            # Capacity 16 kWh (Modbus register = 1600, gain = 100)
            capacity.set_latest_state(1600)
            assert sensor.update_from_source_sensor(capacity) is False  # bp is not yet known

            # SoC 75% (Modbus register = 750, gain = 10)
            current_soc.set_latest_state(750)
            assert sensor.update_from_source_sensor(current_soc) is False

            # Discharge cutoff 10% (Modbus register = 100, gain = 10)
            discharge_soc.set_latest_state(100)
            assert sensor.update_from_source_sensor(discharge_soc) is False

            # Charge cutoff 95% (Modbus register = 950, gain = 10)
            charge_soc.set_latest_state(950)
            assert sensor.update_from_source_sensor(charge_soc) is False

            # Battery discharging at 3200 W (gain = 1.0)
            # Available SoC: 75% - 10% = 65%
            # Available energy: 16 kWh * 0.65 = 10.4 kWh = 10,400 Wh
            # Duration: 10,400 / -3200 = -3.25 hours
            bp.set_latest_state(-3200)
            assert sensor.update_from_source_sensor(bp) is True
            assert sensor.latest_raw_state == -3.25

            # Battery switches to charging at 3200 W
            # Needed SoC: 95% - 75% = 20%
            # Needed energy: 16 kWh * 0.20 = 3.2 kWh = 3,200 Wh
            # Duration: 3,200 / 3200 = +1.0 hour
            bp.set_latest_state(3200)
            assert sensor.update_from_source_sensor(bp) is True
            assert sensor.latest_raw_state == 1.0

            # Battery switches to idle (0 W)
            bp.set_latest_state(0)
            assert sensor.update_from_source_sensor(bp) is True
            assert sensor.latest_raw_state == 0.0
