"""Tests for BatteryStatus.update_from_source_sensor branches and BatteryChargingPower/
BatteryDischargingPower None-state early-returns.

Covers missing lines:
  plant_derived.py  65, 103, 166-187
"""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, StateClass
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.plant_derived import (
    BatteryChargingPower,
    BatteryDischargingPower,
    BatteryStatus,
)
from sigenergy2mqtt.sensors.plant_read_only import (
    BatteryPower,
    PlantBatterySoC,
)
from sigenergy2mqtt.sensors.plant_read_write import (
    ESSBackupSOC,
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


def _make_battery_status():
    """Instantiate BatteryStatus with mocked source sensors."""
    bp = MagicMock(spec=BatteryPower)
    bp.device_class = DeviceClass.POWER
    bp.state_class = StateClass.MEASUREMENT
    bp.protocol_version = ProtocolVersion.V2_9

    backup_soc = MagicMock(spec=ESSBackupSOC)
    backup_soc.protocol_version = ProtocolVersion.V2_9

    discharge_soc = MagicMock(spec=ESSDischargeCutOffSOC)
    discharge_soc.protocol_version = ProtocolVersion.V2_9

    charge_soc = MagicMock(spec=ESSChargeCutOffSOC)
    charge_soc.protocol_version = ProtocolVersion.V2_9

    current_soc = MagicMock(spec=PlantBatterySoC)
    current_soc.protocol_version = ProtocolVersion.V2_9

    sensor = BatteryStatus(0, bp, current_soc, backup_soc, discharge_soc, charge_soc)
    return sensor, bp, backup_soc, discharge_soc, charge_soc, current_soc


class TestBatteryChargingPowerNoneState:
    """Cover line 65: early-return when latest_raw_state is None."""

    def test_returns_false_when_state_is_none(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = DeviceClass.POWER
            bp.state_class = StateClass.MEASUREMENT
            bp.protocol_version = ProtocolVersion.V2_4

            sensor = BatteryChargingPower(0, bp)
            source = MagicMock(spec=BatteryPower)
            source.latest_raw_state = None  # Triggers line 65
            result = sensor.update_from_source_sensor(source)
            assert result is False


class TestBatteryDischargingPowerNoneState:
    """Cover line 103: early-return when latest_raw_state is None."""

    def test_returns_false_when_state_is_none(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            bp = MagicMock(spec=BatteryPower)
            bp.device_class = DeviceClass.POWER
            bp.state_class = StateClass.MEASUREMENT
            bp.protocol_version = ProtocolVersion.V2_4

            sensor = BatteryDischargingPower(0, bp)
            source = MagicMock(spec=BatteryPower)
            source.latest_raw_state = None  # Triggers line 103
            result = sensor.update_from_source_sensor(source)
            assert result is False


class TestBatteryStatusUpdateFromSourceSensor:
    """Cover lines 166-187: all match-case branches in BatteryStatus.update_from_source_sensor."""

    def test_battery_power_none_state_returns_false(self):
        """Line 166-167: BatteryPower branch early-return when raw state is None."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, bp_mock, _, _, _, _ = _make_battery_status()
            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = None  # Triggers line 166-167
            result = sensor.update_from_source_sensor(bp_source)
            assert result is False

    def test_battery_power_charging_sets_charging_state(self):
        """Lines 168-171: raw > 0 → Charging state."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            # Seed the SoC values so we don't fall through to UNKNOWN
            sensor._current_soc = 50.0
            sensor._backup_soc = 10.0
            sensor._charge_soc = 90.0
            sensor._discharge_soc = 5.0

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 500  # raw > 0 → Charging
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Charging"

    def test_battery_power_discharging_sets_discharging_state(self):
        """Lines 172-173: raw < 0 → Discharging state."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 50.0
            sensor._backup_soc = 10.0
            sensor._charge_soc = 90.0
            sensor._discharge_soc = 5.0

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = -300  # raw < 0 → Discharging
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Discharging"

    def test_battery_power_zero_unknown_when_soc_missing(self):
        """Line 174-175: raw == 0 and SoC values are None → Unknown."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            # All SoC values remain None (default after construction)

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 0
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Unknown"

    def test_battery_power_zero_full_when_soc_100(self):
        """Lines 176-177: current_soc >= 100 → Full."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 100.0
            sensor._backup_soc = 10.0
            sensor._charge_soc = 90.0
            sensor._discharge_soc = 5.0

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 0
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Full"

    def test_battery_power_zero_empty_when_soc_0(self):
        """Lines 178-179: current_soc <= 0 → Empty."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 0.0
            sensor._backup_soc = 10.0
            sensor._charge_soc = 90.0
            sensor._discharge_soc = 5.0

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 0
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Empty"

    def test_battery_power_zero_cutoff_when_at_discharge_soc(self):
        """Line 180-181: current_soc <= discharge_soc → Cutoff."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 5.0
            sensor._backup_soc = 2.0
            sensor._charge_soc = 95.0
            sensor._discharge_soc = 5.0  # current_soc <= discharge_soc

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 0
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Cutoff"

    def test_battery_power_zero_idle_when_between_cutoffs(self):
        """Lines 183: else branch → Idle."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 50.0
            sensor._backup_soc = 10.0
            sensor._charge_soc = 90.0
            sensor._discharge_soc = 5.0

            bp_source = MagicMock(spec=BatteryPower)
            bp_source.latest_raw_state = 0
            result = sensor.update_from_source_sensor(bp_source)
            assert result is True
            assert sensor.latest_raw_state == "Idle"

    def test_plant_battery_soc_updates_current_soc_and_returns_false(self):
        """Lines 188-190: PlantBatterySoC case stores SoC and returns False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            soc_source = MagicMock(spec=PlantBatterySoC)
            soc_source.latest_raw_state = 75.0
            result = sensor.update_from_source_sensor(soc_source)
            assert result is False
            assert sensor._current_soc == 75.0

    def test_plant_battery_soc_none_clears_current_soc(self):
        """Lines 188-190: PlantBatterySoC with None state clears _current_soc."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            sensor._current_soc = 50.0
            soc_source = MagicMock(spec=PlantBatterySoC)
            soc_source.latest_raw_state = None
            result = sensor.update_from_source_sensor(soc_source)
            assert result is False
            assert sensor._current_soc is None

    def test_ess_backup_soc_updates_backup_soc(self):
        """Lines 191-193: ESSBackupSOC case stores backup SoC and returns False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            backup_source = MagicMock(spec=ESSBackupSOC)
            backup_source.latest_raw_state = 20.0
            result = sensor.update_from_source_sensor(backup_source)
            assert result is False
            assert sensor._backup_soc == 20.0

    def test_ess_charge_cutoff_soc_updates_charge_soc(self):
        """Lines 194-195: ESSChargeCutOffSOC case stores charge SoC and returns False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor, _, _, _, _, _ = _make_battery_status()
            charge_source = MagicMock(spec=ESSChargeCutOffSOC)
            charge_source.latest_raw_state = 95.0
            result = sensor.update_from_source_sensor(charge_source)
            assert result is False
            assert sensor._charge_soc == 95.0
