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



class TestDebugLoggingBranches:
    """Cover debug_logging=True branches in property setters."""

    def test_publishable_setter_unchanged_with_debug(self):
        """Setting publishable to the same value with debug_logging=True."""
        s = _make_sensor(uid_suffix="pub_dbg", debug=True)
        assert s.publishable is True
        # Setting same value triggers the debug branch for "unchanged"
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publishable = True  # No change → debug branch
            mock_log.debug.assert_called()

    def test_publish_raw_setter_unchanged_with_debug(self):
        """Setting publish_raw to same value with debug_logging=True."""
        s = _make_sensor(uid_suffix="raw_dbg", debug=True)
        assert s.publish_raw is False
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publish_raw = False  # unchanged → debug branch
            mock_log.debug.assert_called()

    def test_publishable_setter_changed_with_debug(self):
        """Setting publishable to different value with debug_logging=True."""
        s = _make_sensor(uid_suffix="pub_chg_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publishable = False
            mock_log.debug.assert_called()

    def test_apply_gain_and_precision_none_with_debug(self):
        """_apply_gain_and_precision with None and debug_logging=True."""
        s = _make_sensor(uid_suffix="gap_none_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            result = s._apply_gain_and_precision(None)
            assert result is None
            mock_log.debug.assert_called()

    def test_apply_gain_and_precision_float_with_debug(self):
        """_apply_gain_and_precision with float and debug_logging=True."""
        s = _make_sensor(uid_suffix="gap_float_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            result = s._apply_gain_and_precision(100.0)
            assert result == 100.0
            mock_log.debug.assert_called()

    def test_log_identity_discriminator_order_and_members(self):
        """log_identity should include plant/dev (in that order) and exclude addr."""
        s = _make_sensor(uid_suffix="log_id_order", debug=False)
        object.__setattr__(s, "plant_index", 2)
        object.__setattr__(s, "device_address", 5)
        s.refresh_log_identity()
        assert "plant=2,dev=5" in s.log_identity
        assert "addr=" not in s.log_identity

    def test_log_identity_includes_optional_string_and_phase(self):
        """log_identity should include optional string/phase discriminators when present."""
        s = _make_sensor(uid_suffix="log_id_optional", debug=False)
        object.__setattr__(s, "plant_index", 1)
        object.__setattr__(s, "device_address", 9)
        object.__setattr__(s, "string_number", 3)
        object.__setattr__(s, "phase", "B")
        s.refresh_log_identity()
        assert "plant=1,dev=9,string=3,phase=B" in s.log_identity


# ─────────────────────────────────────────────────────────────────────────────
# 2. apply_sensor_overrides branches
# ─────────────────────────────────────────────────────────────────────────────



class TestApplySensorOverrides:
    """Cover each override key branch in apply_sensor_overrides."""

    def _make_with_overrides(self, overrides: dict, suffix: str) -> Sensor:
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Override Test",
                unique_id=f"sigen_{suffix}",
                object_id=f"sigen_{suffix}",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        cfg = Config()
        cfg.sensor_overrides = {f"sigen_{suffix}": overrides}
        with _swap_active_config(cfg):
            s.apply_sensor_overrides(None)
        return s

    def test_override_debug_logging(self):
        s = self._make_with_overrides({"debug-logging": True}, "ov_debug")
        assert s.debug_logging is True

    def test_override_gain(self):
        s = self._make_with_overrides({"gain": 10.0}, "ov_gain")
        assert s._gain == 10.0

    def test_override_icon(self):
        s = self._make_with_overrides({"icon": "mdi:battery"}, "ov_icon")
        assert s["icon"] == "mdi:battery"

    def test_override_max_failures(self):
        s = self._make_with_overrides({"max-failures": 3}, "ov_maxfail")
        assert s._max_failures == 3

    def test_override_max_failures_retry_interval(self):
        s = self._make_with_overrides({"max-failures-retry-interval": 60}, "ov_retry")
        assert s._max_failures_retry_interval == 60

    def test_override_precision(self):
        s = self._make_with_overrides({"precision": 0}, "ov_prec")
        assert s.precision == 0
        assert s["display_precision"] == 0

    def test_override_publishable(self):
        s = self._make_with_overrides({"publishable": False}, "ov_pub")
        assert s.publishable is False

    def test_override_publish_raw(self):
        s = self._make_with_overrides({"publish-raw": True}, "ov_pubraw")
        assert s.publish_raw is True

    def test_override_sanity_check_delta(self):
        s = self._make_with_overrides({"sanity-check-delta": True}, "ov_scd")
        assert s.sanity_check.delta is True

    def test_override_sanity_check_max_value(self):
        s = self._make_with_overrides({"sanity-check-max-value": 5000.0}, "ov_scmax")
        assert s.sanity_check.max_raw == 5000.0

    def test_override_sanity_check_min_value(self):
        s = self._make_with_overrides({"sanity-check-min-value": -100.0}, "ov_scmin")
        assert s.sanity_check.min_raw == -100.0

    def test_override_unit_of_measurement(self):
        s = self._make_with_overrides({"unit-of-measurement": "kW"}, "ov_uom")
        assert s["unit_of_measurement"] == "kW"

    def test_override_device_class(self):
        s = self._make_with_overrides({"device-class": DeviceClass.ENERGY}, "ov_dc")
        assert s["device_class"] == DeviceClass.ENERGY

    def test_override_state_class(self):
        s = self._make_with_overrides({"state-class": StateClass.TOTAL}, "ov_sc")
        assert s["state_class"] == StateClass.TOTAL

    def test_override_name(self):
        s = self._make_with_overrides({"name": "New Name"}, "ov_name")
        assert s["name"] == "New Name"

    def test_override_registers_read_only(self):
        """apply_sensor_overrides with ReadableSensorMixin + read_only=False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="ReadOnly Test",
                unique_id="sigen_ro_reg",
                object_id="sigen_ro_reg",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.read_only = False
        registers.read_write = True
        registers.write_only = True
        cfg = Config()
        with _swap_active_config(cfg):
            # DerivedSensor instance check path
            s.apply_sensor_overrides(registers)

    def test_override_registers_no_remote_ems(self):
        """Publishable set to False when no_remote_ems is True and sensor has _remote_ems."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="RemoteEMS",
                unique_id="sigen_rems",
                object_id="sigen_rems",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        s._remote_ems = True  # mark as remote EMS sensor
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = True
        cfg = Config()
        with _swap_active_config(cfg):
            s.apply_sensor_overrides(registers)
        assert s.publishable is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. publish() method branches
# ─────────────────────────────────────────────────────────────────────────────



class TestAlarmSensorBranches:
    def _make_alarm(self, suffix):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteAlarm(AlarmSensor):
                def decode_alarm_bit(self, bit_position: int):
                    return f"Error bit {bit_position}" if bit_position == 0 else None

            return ConcreteAlarm("Alarm", f"sigen_{suffix}", 0, 1, 30001, Protocol.V2_4, "Equipment")

    def test_alarm_state2raw_string_no_alarm(self):
        s = self._make_alarm("alrm_s2r_na")
        assert s.state2raw("No Alarm") == 0

    def test_alarm_state2raw_numeric_one(self):
        s = self._make_alarm("alrm_s2r_1")
        assert s.state2raw(1) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. DerivedSensor branches
# ─────────────────────────────────────────────────────────────────────────────



class TestDerivedSensorBranches:
    @pytest.mark.asyncio
    async def test_derived_sensor_get_state_no_states(self):
        """DerivedSensor.get_state returns 0 when no states."""
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src_123"
        source.latest_interval = 60.0

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            derived = EnergyLifetimeAccumulationSensor(
                "Accum",
                "sigen_accum_d",
                "sigen_accum_d",
                source,
                ModbusDataType.UINT32,
                "kWh",
                DeviceClass.ENERGY,
                StateClass.TOTAL,
                "mdi:battery",
                1.0,
                2,
            )
        result = await derived.get_state()
        assert result == 0

    @pytest.mark.asyncio
    async def test_derived_sensor_get_state_with_string_state(self):
        """DerivedSensor.get_state returns string directly without gain/precision."""
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src_str"
        source.latest_interval = 60.0

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            derived = EnergyLifetimeAccumulationSensor(
                "Accum Str",
                "sigen_accum_str",
                "sigen_accum_str",
                source,
                ModbusDataType.UINT32,
                "kWh",
                DeviceClass.ENERGY,
                StateClass.TOTAL,
                "mdi:battery",
                1.0,
                2,
            )
        derived._states.append((time.time(), "some_string"))
        result = await derived.get_state()
        assert result == "some_string"


# ─────────────────────────────────────────────────────────────────────────────
# 14. protocol_version setter edge cases
# ─────────────────────────────────────────────────────────────────────────────



class TestSetLatestState:
    def test_set_latest_state_propagates_to_derived(self):
        """set_latest_state calls set_source_values on derived sensors."""
        s = _make_sensor(uid_suffix="sls_derived")
        derived = MagicMock()
        s.derived_sensors["Mock"] = derived
        s.set_latest_state(100.0)
        derived.set_source_values.assert_called_once_with(s, s._states)

    def test_set_state_respects_max_states(self):
        """set_state trims state history to _max_states."""
        s = _make_sensor(uid_suffix="ss_trim")
        s._max_states = 2
        for i in range(5):
            s.set_state(float(i))
        assert len(s._states) == 2
        assert s._states[-1][1] == 4.0


# ─────────────────────────────────────────────────────────────────────────────
# 16. ReservedSensor branches
# ─────────────────────────────────────────────────────────────────────────────



class TestReservedSensor:
    def _make_reserved(self, suffix):
        from sigenergy2mqtt.common import InputType
        from sigenergy2mqtt.sensors.base import ReservedSensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteReserved(ReservedSensor):
                pass

            # Class name must start with "Reserved"
            ConcreteReserved.__name__ = "Reserved" + suffix
            ConcreteReserved.__qualname__ = "Reserved" + suffix

            # Directly instantiate with required args
            s = ConcreteReserved(
                "Reserved Sensor",
                f"sigen_res_{suffix}",
                InputType.INPUT,
                0,
                1,
                30002,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                None,
                None,
                None,
                None,
                Protocol.V2_4,
            )
        return s

    def test_reserved_publishable_always_false(self):
        s = self._make_reserved("pub")
        assert s.publishable is False

    def test_reserved_publishable_cannot_be_set_true(self):
        s = self._make_reserved("settrue")
        with pytest.raises(ValueError):
            s.publishable = True

    def test_reserved_apply_sensor_overrides_noop(self):
        s = self._make_reserved("noop")
        registers = MagicMock()
        # Should not raise; it's a no-op
        s.apply_sensor_overrides(registers)


# ─────────────────────────────────────────────────────────────────────────────
# 17. SanityCheck failure increment config
# ─────────────────────────────────────────────────────────────────────────────



class TestWritableSensorOverrides:
    def test_writable_sensor_read_write_false_sets_unpublishable(self):
        """WritableSensorMixin sensor becomes unpublishable when read_write=False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # WriteOnlySensor is a concrete WritableSensorMixin subclass
            wo = WriteOnlySensor("WO", "sigen_wo_rw", 0, 1, 30001, Protocol.V2_4)
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.write_only = False
        with patch.dict("sigenergy2mqtt.sensors.base.active_config.sensor_overrides", {}):
            wo.apply_sensor_overrides(registers)
        assert wo.publishable is False

    def test_write_only_sensor_write_only_false_unpublishable(self):
        """WriteOnlySensor (not WritableSensorMixin ReadWrite) also respects write_only override."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            wo = WriteOnlySensor("WO2", "sigen_wo_wo", 0, 1, 30001, Protocol.V2_4)
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.write_only = False
        with patch.dict("sigenergy2mqtt.sensors.base.active_config.sensor_overrides", {}):
            wo.apply_sensor_overrides(registers)
        assert wo.publishable is False


# ─────────────────────────────────────────────────────────────────────────────
# 19. __eq__ and __hash__
# ─────────────────────────────────────────────────────────────────────────────



class TestSensorEqualityAndHash:
    def test_eq_same_unique_id(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s1 = ConcreteSensor(
                name="S1",
                unique_id="sigen_eq1",
                object_id="sigen_eq1",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
            s2 = ConcreteSensor(
                name="S2",
                unique_id="sigen_eq1",
                object_id="sigen_eq1",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        assert s1 == s2

    def test_eq_different_unique_id(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s1 = ConcreteSensor(
                name="S1",
                unique_id="sigen_eqa",
                object_id="sigen_eqa",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
            s2 = ConcreteSensor(
                name="S2",
                unique_id="sigen_eqb",
                object_id="sigen_eqb",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        assert s1 != s2

    def test_eq_non_sensor(self):
        s = _make_sensor(uid_suffix="eq_non")
        assert s != "not a sensor"

    def test_hash_unique_id(self):
        s = _make_sensor(uid_suffix="hash1")
        assert hash(s) == hash(s["unique_id"])


# ─────────────────────────────────────────────────────────────────────────────
# 20. get_discovery_components with options
# ─────────────────────────────────────────────────────────────────────────────


