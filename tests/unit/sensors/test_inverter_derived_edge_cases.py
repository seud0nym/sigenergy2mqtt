"""Tests for edge cases and branches in sensors/inverter_derived.py.

Covers missing lines:
  inverter_derived.py  50, 86, 105, 108, 148, 158, 170, 264, 281, 282, 283, 286, 287, 288
"""

import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.inverter_derived import (
    InverterBatteryChargingPower,
    InverterBatteryDischargingPower,
    InverterSelfConsumedPower,
    PVStringPower,
)
from sigenergy2mqtt.sensors.inverter_read_only import (
    ActivePower,
    ChargeDischargePower,
    PVCurrentSensor,
    PVVoltageSensor,
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
    cfg.modbus = [MagicMock()]
    cfg.sensor_overrides = {}

    with _swap_active_config(cfg):
        yield cfg


def _make_pv_string_power() -> PVStringPower:
    """Helper to create PVStringPower with mocked source sensors."""
    v = MagicMock(spec=PVVoltageSensor)
    v.gain = 10
    v.protocol_version = Protocol.V2_4
    c = MagicMock(spec=PVCurrentSensor)
    c.gain = 100
    c.protocol_version = Protocol.V2_4
    return PVStringPower(0, 1, 1, v, c)


# ─────────────────────────────────────────────────────────────────────────────
# InverterBatteryChargingPower - None state early return (line 50)
# ─────────────────────────────────────────────────────────────────────────────


class TestInverterBatteryChargingPowerNoneState:
    def test_returns_false_when_state_is_none(self):
        """Line 50: early-return False when latest_raw_state is None."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryChargingPower(0, 1, cdp)

            source = MagicMock(spec=ChargeDischargePower)
            source.latest_raw_state = None  # Triggers line 50
            result = sensor.update_from_source_sensor(source)
            assert result is False

    def test_positive_raw_sets_max_0_and_raw(self):
        """Covers the positive branch (max(0, raw) = raw when raw > 0)."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryChargingPower(0, 1, cdp)

            source = MagicMock(spec=ChargeDischargePower)
            source.latest_raw_state = 500
            result = sensor.update_from_source_sensor(source)
            assert result is True
            assert sensor.latest_raw_state == 500


# ─────────────────────────────────────────────────────────────────────────────
# InverterBatteryDischargingPower - None state early return (line 86)
# ─────────────────────────────────────────────────────────────────────────────


class TestInverterBatteryDischargingPowerNoneState:
    def test_returns_false_when_state_is_none(self):
        """Line 86: early-return False when latest_raw_state is None."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            cdp = MagicMock(spec=ChargeDischargePower)
            cdp.device_class = "power"
            cdp.state_class = "measurement"
            cdp.protocol_version = Protocol.V2_4
            sensor = InverterBatteryDischargingPower(0, 1, cdp)

            source = MagicMock(spec=ChargeDischargePower)
            source.latest_raw_state = None  # Triggers line 86
            result = sensor.update_from_source_sensor(source)
            assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# PVStringPower.Value.apply (lines 105, 108)
# ─────────────────────────────────────────────────────────────────────────────


class TestPVStringPowerValueApply:
    def test_overwriting_unconsumed_value_logs_warning(self, caplog):
        """Line 105: warning when overwriting an unconsumed value."""
        caplog.set_level(logging.WARNING)
        v = PVStringPower.Value(name="test_value", divisor=1.0)
        v.value = 100.0  # Already has a value
        v.timestamp = time.time()

        mock_sensor = MagicMock(spec=Sensor)
        mock_sensor.latest_time = time.time()

        with patch("sigenergy2mqtt.sensors.inverter_derived.logger") as mock_log:
            v.apply(mock_sensor)  # Overwrites → triggers line 105
            mock_log.warning.assert_called_once()
            assert "Overwriting unconsumed value" in mock_log.warning.call_args[0][0]

    def test_none_raw_state_returns_early(self):
        """Line 108: early-return when sensor.latest_raw_state is None."""
        v = PVStringPower.Value(name="test_value", divisor=1.0)
        assert v.value is None  # Initially None

        mock_sensor = MagicMock(spec=Sensor)
        mock_sensor.latest_raw_state = None  # Triggers line 108
        mock_sensor.latest_time = time.time()

        v.apply(mock_sensor)
        assert v.value is None  # Should still be None


# ─────────────────────────────────────────────────────────────────────────────
# PVStringPower.publish - gap warning (line 148)
# ─────────────────────────────────────────────────────────────────────────────


class TestPVStringPowerPublishGapWarning:
    @pytest.mark.asyncio
    async def test_large_gap_logs_warning(self, caplog):
        """Line 148: debug warning when gap between timestamps exceeds threshold."""
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = _make_pv_string_power()
            sensor.debug_logging = True

            now = time.time()
            sensor.volts.value = 400.0
            sensor.volts.timestamp = now - 2.0  # 2 seconds ago (> 0.5s threshold)
            sensor.amperes.value = 10.0
            sensor.amperes.timestamp = now

            with patch("sigenergy2mqtt.sensors.base.DerivedSensor.publish", new_callable=AsyncMock):
                with patch("sigenergy2mqtt.sensors.inverter_derived.logger") as mock_log:
                    result = await sensor.publish(MagicMock(), None)
                    assert result is True
                    # Should have logged the gap warning (line 148)
                    debug_calls = [str(c) for c in mock_log.debug.call_args_list]
                    assert any("WARNING" in c for c in debug_calls)


# ─────────────────────────────────────────────────────────────────────────────
# PVStringPower.update_from_source_sensor (lines 158, 170)
# ─────────────────────────────────────────────────────────────────────────────


class TestPVStringPowerUpdateFromSourceSensor:
    def test_none_raw_state_returns_false(self):
        """Line 158: early-return when sensor.latest_raw_state is None."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = _make_pv_string_power()
            source = MagicMock(spec=PVVoltageSensor)
            source.latest_raw_state = None  # Triggers line 158
            result = sensor.update_from_source_sensor(source)
            assert result is False

    def test_debug_log_when_state_populated(self, caplog):
        """Line 170: debug log when both volts and amperes are populated."""
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = _make_pv_string_power()
            sensor.debug_logging = True

            v_source = MagicMock(spec=PVVoltageSensor)
            v_source.latest_raw_state = 4000  # 400V with divisor 10
            v_source.latest_time = time.time()
            sensor.update_from_source_sensor(v_source)

            c_source = MagicMock(spec=PVCurrentSensor)
            c_source.latest_raw_state = 1000  # 10A with divisor 100
            c_source.latest_time = time.time()

            with patch("sigenergy2mqtt.sensors.inverter_derived.logger") as mock_log:
                result = sensor.update_from_source_sensor(c_source)
                assert result is True  # Both populated now
                debug_calls = [str(c) for c in mock_log.debug.call_args_list]
                assert any("source values populated" in c for c in debug_calls)


# ─────────────────────────────────────────────────────────────────────────────
# InverterSelfConsumedPower.update_from_source_sensor (lines 264, 281-288)
# ─────────────────────────────────────────────────────────────────────────────


class TestInverterSelfConsumedPowerEdgeCases:
    def test_none_raw_state_returns_false(self):
        """Line 264: early-return when sensor.latest_raw_state is None."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            ap = MagicMock(spec=ActivePower)
            ap.protocol_version = Protocol.V2_4
            bp = MagicMock(spec=ChargeDischargePower)
            bp.protocol_version = Protocol.V2_4
            pv1 = MagicMock(spec=PVStringPower)
            pv1.string_number = 1
            pv1.protocol_version = Protocol.V2_4

            sensor = InverterSelfConsumedPower(0, 1, ap, bp, pv1)

            source = MagicMock(spec=ActivePower)
            source.latest_raw_state = None  # Triggers line 264
            result = sensor.update_from_source_sensor(source)
            assert result is False

    def test_negative_state_corrected_to_zero(self, caplog):
        """Lines 280-283: negative self-consumed power is corrected to 0."""
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            ap = MagicMock(spec=ActivePower)
            ap.protocol_version = Protocol.V2_4
            bp = MagicMock(spec=ChargeDischargePower)
            bp.protocol_version = Protocol.V2_4
            pv1 = MagicMock(spec=PVStringPower)
            pv1.string_number = 1
            pv1.protocol_version = Protocol.V2_4

            sensor = InverterSelfConsumedPower(0, 1, ap, bp, pv1)
            sensor.debug_logging = True

            # Setup: active_power=1000, battery=-500, pv=100
            # state = total_pv - active_power - battery_power = 100 - 1000 - (-500) = -400 (negative)
            ap.latest_raw_state = 1000
            sensor.update_from_source_sensor(ap)

            bp.latest_raw_state = -500
            sensor.update_from_source_sensor(bp)

            pv1.latest_raw_state = 100
            with patch("sigenergy2mqtt.sensors.inverter_derived.logger") as mock_log:
                result = sensor.update_from_source_sensor(pv1)
                assert result is True
                # Negative state should be corrected to 0
                assert sensor.latest_raw_state == 0
                # Should have logged the negative correction
                debug_calls = [str(c) for c in mock_log.debug.call_args_list]
                assert any("correcting negative" in c for c in debug_calls)

    def test_sanity_check_exception_handled(self, caplog):
        """Lines 286-288: SanityCheckException is caught and logged in debug."""
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            ap = MagicMock(spec=ActivePower)
            ap.protocol_version = Protocol.V2_4
            bp = MagicMock(spec=ChargeDischargePower)
            bp.protocol_version = Protocol.V2_4
            pv1 = MagicMock(spec=PVStringPower)
            pv1.string_number = 1
            pv1.protocol_version = Protocol.V2_4

            sensor = InverterSelfConsumedPower(0, 1, ap, bp, pv1)
            sensor.debug_logging = True

            ap.latest_raw_state = 100
            sensor.update_from_source_sensor(ap)
            bp.latest_raw_state = 0
            sensor.update_from_source_sensor(bp)

            from sigenergy2mqtt.sensors.base import SanityCheckException
            pv1.latest_raw_state = 100

            # Patch set_latest_state to raise SanityCheckException
            with patch.object(sensor, "set_latest_state", side_effect=SanityCheckException("test sanity check")):
                with patch("sigenergy2mqtt.sensors.inverter_derived.logger") as mock_log:
                    result = sensor.update_from_source_sensor(pv1)
                    assert result is True  # Returns True even when SanityCheckException is caught
                    debug_calls = [str(c) for c in mock_log.debug.call_args_list]
                    assert any("FAILED" in c for c in debug_calls)
