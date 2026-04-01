from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, Protocol, RegisterAccess, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import (
    AlarmSensor,
    ReadOnlySensor,
    Sensor,
    WriteOnlySensor,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return False


def _make_sensor(name="Test", uid_suffix="x", debug=False, **kwargs):
    """Create a fresh ConcreteSensor with cleared ID registries."""
    uid = f"sigen_{uid_suffix}"
    oid = f"sigen_{uid_suffix}"

    cfg = Config()
    cfg.home_assistant.enabled = False
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"

    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name=name,
                unique_id=uid,
                object_id=oid,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:solar-power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
                debug_logging=debug,
                **kwargs,
            )
    return s


def _mqtt_mock():
    m = MagicMock()
    m.publish = MagicMock()
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. Debug-logging branches in property setters
# ─────────────────────────────────────────────────────────────────────────────



class TestState2Raw:
    def _sensor_with_options(self, options: list, suffix: str):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Options",
                unique_id=f"sigen_{suffix}",
                object_id=f"sigen_{suffix}",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        s["options"] = options
        return s

    def test_state2raw_none(self):
        s = _make_sensor(uid_suffix="s2r_none")
        assert s.state2raw(None) is None

    def test_state2raw_string_option_match(self):
        s = self._sensor_with_options(["Off", "On"], "s2r_opt")
        assert s.state2raw("Off") == 0
        assert s.state2raw("On") == 1

    def test_state2raw_numeric_string(self):
        s = _make_sensor(uid_suffix="s2r_numstr")
        assert s.state2raw("42") == 42

    def test_state2raw_float_string(self):
        s = _make_sensor(uid_suffix="s2r_floatstr")
        result = s.state2raw("3.14")
        assert result == 3  # int conversion

    def test_state2raw_int_with_gain(self):
        s = _make_sensor(uid_suffix="s2r_gain")
        s._gain = 10.0
        result = s.state2raw(5)
        assert result == 50

    def test_state2raw_float_gain_1_no_change(self):
        s = _make_sensor(uid_suffix="s2r_gain1")
        s._gain = 1.0
        result = s.state2raw(100)
        assert result == 100

    def test_state2raw_nonnumeric_string_fallback(self):
        """Non-numeric string not in options falls back."""
        s = self._sensor_with_options(["Alpha", "Beta"], "s2r_fallback")
        assert s.state2raw("Alpha") == 0


# ─────────────────────────────────────────────────────────────────────────────
# 10. _check_register_response() exception code branches
# ─────────────────────────────────────────────────────────────────────────────



class TestProtocolVersionSetter:
    def test_protocol_version_float_valid(self):
        s = _make_sensor(uid_suffix="pv_float")
        valid_float = Protocol.V2_4.value
        s.protocol_version = float(valid_float)
        assert s.protocol_version == Protocol.V2_4

    def test_protocol_version_float_invalid_raises(self):
        s = _make_sensor(uid_suffix="pv_bad")
        with pytest.raises(AssertionError):
            s.protocol_version = 99.9  # type: ignore

    def test_protocol_version_string_raises(self):
        s = _make_sensor(uid_suffix="pv_str")
        with pytest.raises(AssertionError):
            s.protocol_version = "V2.4"  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 15. set_latest_state propagates to derived sensors
# ─────────────────────────────────────────────────────────────────────────────



class TestGainProperty:
    def test_gain_returns_1_when_none(self):
        s = _make_sensor(uid_suffix="gain_none")
        s._gain = None
        assert s.gain == 1.0

    def test_gain_returns_value_when_set(self):
        s = _make_sensor(uid_suffix="gain_val")
        s._gain = 100.0
        assert s.gain == 100.0

    def test_gain_setter(self):
        s = _make_sensor(uid_suffix="gain_set")
        s.gain = 500.0
        assert s._gain == 500.0

    def test_gain_setter_none(self):
        s = _make_sensor(uid_suffix="gain_set_none")
        s.gain = None
        assert s._gain is None


# ─────────────────────────────────────────────────────────────────────────────
# 22. ReadableSensorMixin scan-interval override
# ─────────────────────────────────────────────────────────────────────────────


