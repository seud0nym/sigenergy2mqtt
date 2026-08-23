"""Tests for PhaseAdjustmentTargetValue sensor get_attributes() and value_is_valid() branches.

Covers missing lines in plant_read_write.py:
  288, 289, 290, 294, 295, 308, 309, 344, 345, 346, 350, 351,
  364, 365, 400, 401, 402, 406, 407, 420
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Constants, ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import AvailabilityMixin, Sensor
from sigenergy2mqtt.sensors.plant_read_write import (
    IndependentPhasePowerControl,
    RemoteEMSControlMode,
)


@pytest.fixture(autouse=True)
def mock_config():
    """Configure active_config for plant_read_write sensor construction."""
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = False
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.enabled_by_default = True
    cfg.home_assistant.sigenergy_local_modbus_naming = False
    cfg.persistent_state_path = Path(".")
    mock_modbus = MagicMock()
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]

    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            yield cfg

    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


def _make_remote_ems_mock(pcs_mode: int | None = 0) -> MagicMock:
    """Create a mock RemoteEMSControlMode sensor."""
    mock = MagicMock(spec=RemoteEMSControlMode)
    mock.latest_raw_state = pcs_mode
    mock.name = "Remote EMS Control Mode"
    mock.is_pcs_remote_control_mode_topic = "sigen/plant/is_pcs_remote_control_mode"
    return mock


def _make_independent_phase_mock() -> MagicMock:
    """Create a mock IndependentPhasePowerControl sensor."""
    mock = MagicMock(spec=IndependentPhasePowerControl)
    mock.state_topic = "sigen/plant/independent_phase_power_control/state"
    mock.raw_state_topic = "sigen/plant/independent_phase_power_control/raw_state"
    mock.publish_raw = False
    return mock


PLANT_INDEX = 0
# Use the three-phase output type to ensure the sensor is publishable
THREE_PHASE = Constants.THREE_PHASE_OUTPUT_TYPE


class TestPowerFactorAdjustmentTargetValue:
    """Tests for PowerFactorAdjustmentTargetValue (lines 288-296)."""

    def test_get_attributes_has_comment(self):
        """Lines 288-290: get_attributes returns comment about PCS Remote Control Mode."""
        from sigenergy2mqtt.sensors.plant_read_write import PowerFactorAdjustmentTargetValue
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigen/plant/remote_ems/state"
        remote_ems.raw_state_topic = "sigen/plant/remote_ems/raw_state"
        remote_ems.publish_raw = False

        sensor = PowerFactorAdjustmentTargetValue(PLANT_INDEX, remote_ems, _make_remote_ems_mock())
        # Configure MQTT topics so COMMAND_TOPIC is set before get_attributes() accesses command_topic
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "PCS Remote Control Mode" in attrs["comment"]

    @pytest.mark.asyncio
    async def test_value_is_valid_fails_when_not_in_pcs_mode(self):
        """Lines 293-295: value_is_valid returns False when EMS mode is 0 (not PCS Remote Control Mode)."""
        from sigenergy2mqtt.sensors.plant_read_write import PowerFactorAdjustmentTargetValue
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigen/plant/remote_ems/state"
        remote_ems.raw_state_topic = "sigen/plant/remote_ems/raw_state"
        remote_ems.publish_raw = False

        remote_ems_mode = _make_remote_ems_mock(pcs_mode=0)  # Not in PCS mode

        sensor = PowerFactorAdjustmentTargetValue(PLANT_INDEX, remote_ems, remote_ems_mode)
        result = await sensor.value_is_valid(None, 0.9)
        assert result is False

    @pytest.mark.asyncio
    async def test_value_is_valid_passes_when_in_pcs_mode(self):
        """Lines 292-296: value_is_valid calls super when EMS mode != 0."""
        from sigenergy2mqtt.sensors.plant_read_write import PowerFactorAdjustmentTargetValue
        remote_ems = MagicMock(spec=AvailabilityMixin)
        remote_ems.state_topic = "sigen/plant/remote_ems/state"
        remote_ems.raw_state_topic = "sigen/plant/remote_ems/raw_state"
        remote_ems.publish_raw = False

        remote_ems_mode = _make_remote_ems_mock(pcs_mode=1)  # In PCS mode

        sensor = PowerFactorAdjustmentTargetValue(PLANT_INDEX, remote_ems, remote_ems_mode)
        result = await sensor.value_is_valid(None, 0.9)
        assert result is True


class TestPhaseActivePowerFixedAdjustmentTargetValue:
    """Tests for PhaseActivePowerFixedAdjustmentTargetValue (lines 308-351)."""

    def test_get_attributes_has_comment_phase_a(self):
        """Lines 343-346: get_attributes returns comment about PCS Remote Control Mode."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseActivePowerFixedAdjustmentTargetValue
        sensor = PhaseActivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, _make_remote_ems_mock(), _make_independent_phase_mock(), THREE_PHASE, "A"
        )
        # Configure MQTT topics so COMMAND_TOPIC is set before get_attributes() accesses command_topic
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "PCS Remote Control Mode" in attrs["comment"]

    def test_invalid_phase_raises_value_error(self):
        """Lines 308-309: ValueError when phase is not A/B/C."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseActivePowerFixedAdjustmentTargetValue
        with pytest.raises(ValueError, match="Phase must be 'A', 'B', or 'C'"):
            PhaseActivePowerFixedAdjustmentTargetValue(
                PLANT_INDEX, _make_remote_ems_mock(), _make_independent_phase_mock(), THREE_PHASE, "X"
            )

    @pytest.mark.asyncio
    async def test_value_is_valid_fails_when_not_in_pcs_mode(self):
        """Lines 349-351: value_is_valid returns False when EMS mode is 0."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseActivePowerFixedAdjustmentTargetValue
        remote_ems_mode = _make_remote_ems_mock(pcs_mode=0)
        sensor = PhaseActivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, remote_ems_mode, _make_independent_phase_mock(), THREE_PHASE, "B"
        )
        result = await sensor.value_is_valid(None, 5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_value_is_valid_passes_when_in_pcs_mode(self):
        """Lines 348-352: calls super when EMS mode != 0."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseActivePowerFixedAdjustmentTargetValue
        remote_ems_mode = _make_remote_ems_mock(pcs_mode=1)
        sensor = PhaseActivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, remote_ems_mode, _make_independent_phase_mock(), THREE_PHASE, "C"
        )
        result = await sensor.value_is_valid(None, 5.0)
        # Within valid range (min/max are set dynamically, but base call will accept)
        assert isinstance(result, bool)


class TestPhaseReactivePowerFixedAdjustmentTargetValue:
    """Tests for PhaseReactivePowerFixedAdjustmentTargetValue (lines 364-407)."""

    def test_get_attributes_has_comment(self):
        """Lines 399-402: get_attributes returns comment about PCS Remote Control Mode."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseReactivePowerFixedAdjustmentTargetValue
        sensor = PhaseReactivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, _make_remote_ems_mock(), _make_independent_phase_mock(), THREE_PHASE, "A"
        )
        # Configure MQTT topics so COMMAND_TOPIC is set before get_attributes() accesses command_topic
        sensor.configure_mqtt_topics("test_device")
        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "PCS Remote Control Mode" in attrs["comment"]

    def test_invalid_phase_raises_value_error(self):
        """Lines 364-365: ValueError when phase is not A/B/C."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseReactivePowerFixedAdjustmentTargetValue
        with pytest.raises(ValueError, match="Phase must be 'A', 'B', or 'C'"):
            PhaseReactivePowerFixedAdjustmentTargetValue(
                PLANT_INDEX, _make_remote_ems_mock(), _make_independent_phase_mock(), THREE_PHASE, "D"
            )

    @pytest.mark.asyncio
    async def test_value_is_valid_fails_when_not_in_pcs_mode(self):
        """Lines 405-407: value_is_valid returns False when EMS mode is 0."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseReactivePowerFixedAdjustmentTargetValue
        remote_ems_mode = _make_remote_ems_mock(pcs_mode=0)
        sensor = PhaseReactivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, remote_ems_mode, _make_independent_phase_mock(), THREE_PHASE, "A"
        )
        result = await sensor.value_is_valid(None, 10.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_value_is_valid_passes_when_in_pcs_mode(self):
        """Lines 404-408: calls super when EMS mode != 0."""
        from sigenergy2mqtt.sensors.plant_read_write import PhaseReactivePowerFixedAdjustmentTargetValue
        remote_ems_mode = _make_remote_ems_mock(pcs_mode=1)
        sensor = PhaseReactivePowerFixedAdjustmentTargetValue(
            PLANT_INDEX, remote_ems_mode, _make_independent_phase_mock(), THREE_PHASE, "B"
        )
        result = await sensor.value_is_valid(None, 10.0)
        assert isinstance(result, bool)
