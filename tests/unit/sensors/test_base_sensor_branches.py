"""Tests for specific branches in sensors/base/sensor.py that lack coverage.

Covers missing lines:
  sensor.py  53, 105, 109, 203, 215, 328, 360, 363, 364, 433, 438, 451, 456, 461,
             619, 620, 621, 625, 626, 627
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, InputType, ProtocolVersion, RegisterAccess, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import ReadOnlySensor, Sensor
from sigenergy2mqtt.sensors.base.mixins import WriteableSensorMixin
from sigenergy2mqtt.sensors.base.sensor import TypedSensorMixin

# ─────────────────────────────────────────────────────────────────────────────
# Concrete sensor stub for testing Sensor base class
# ─────────────────────────────────────────────────────────────────────────────


class _ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return False


def _make_cfg(enabled: bool = False) -> Config:
    cfg = Config()
    cfg.home_assistant.enabled = enabled
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.use_simplified_topics = False
    cfg.sensor_overrides = {}
    return cfg


def _make_sensor(uid_suffix: str = "x", debug: bool = False, cfg: Config | None = None) -> _ConcreteSensor:
    _cfg = cfg or _make_cfg()
    with _swap_active_config(_cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        s = _ConcreteSensor(
            name="Test",
            unique_id=f"sigen_{uid_suffix}",
            object_id=f"sigen_{uid_suffix}",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=1.0,
            precision=2,
            protocol_version=ProtocolVersion.V2_4,
            debug_logging=debug,
        )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# TypedSensorMixin tests (line 53)
# ─────────────────────────────────────────────────────────────────────────────


class TestTypedSensorMixin:
    def test_missing_data_type_raises_assertion(self):
        """Line 53: AssertionError when data_type is not in kwargs."""

        class _Typed(TypedSensorMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        with pytest.raises(AssertionError, match="Missing required parameter: data_type"):
            _Typed()


# ─────────────────────────────────────────────────────────────────────────────
# Sensor __init__ validation (lines 105, 109)
# ─────────────────────────────────────────────────────────────────────────────


class TestSensorInitValidation:
    def test_invalid_icon_raises(self):
        """Line 105: AssertionError when icon does not start with 'mdi:'."""
        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            with pytest.raises(AssertionError, match="does not start with 'mdi:'"):
                _ConcreteSensor(
                    name="Bad Icon",
                    unique_id="sigen_bad_icon",
                    object_id="sigen_bad_icon",
                    unit=None,
                    device_class=None,
                    state_class=None,
                    icon="bad_icon",  # Triggers line 105
                    gain=None,
                    precision=None,
                    protocol_version=ProtocolVersion.V2_4,
                )

    def test_invalid_protocol_version_type_raises(self):
        """Line 109: TypeError when protocol_version is not a ProtocolVersion instance."""
        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True), pytest.raises(TypeError, match="protocol_version.*is invalid"):
            _ConcreteSensor(
                name="Bad ProtocolVersion",
                unique_id="sigen_bad_proto",
                object_id="sigen_bad_proto",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version="2.4",  # Triggers line 109
            )


# ─────────────────────────────────────────────────────────────────────────────
# ID validation (lines 203, 215)
# ─────────────────────────────────────────────────────────────────────────────


class TestSensorIDValidation:
    def test_unique_id_wrong_prefix_raises(self):
        """Line 203: AssertionError when unique_id doesn't start with correct prefix."""
        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            with pytest.raises(AssertionError, match="does not start with 'sigen'"):
                _ConcreteSensor(
                    name="Wrong Prefix",
                    unique_id="wrong_prefix_uid",  # Triggers line 203
                    object_id="sigen_wrong",
                    unit=None,
                    device_class=None,
                    state_class=None,
                    icon=None,
                    gain=None,
                    precision=None,
                    protocol_version=ProtocolVersion.V2_4,
                )

    def test_object_id_wrong_prefix_raises(self):
        """Line 215: AssertionError when object_id doesn't start with correct prefix."""
        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            with pytest.raises(AssertionError, match="does not start with 'sigen'"):
                _ConcreteSensor(
                    name="Wrong OID",
                    unique_id="sigen_valid",
                    object_id="wrong_oid",  # Triggers line 215
                    unit=None,
                    device_class=None,
                    state_class=None,
                    icon=None,
                    gain=None,
                    precision=None,
                    protocol_version=ProtocolVersion.V2_4,
                )


# ─────────────────────────────────────────────────────────────────────────────
# protocol_version setter (line 328)
# ─────────────────────────────────────────────────────────────────────────────


class TestProtocolVersionSetter:
    def test_float_invalid_protocol_version_raises(self):
        """Line 328: AssertionError when float value not in ProtocolVersion enum."""
        s = _make_sensor("proto_invalid")
        with pytest.raises(AssertionError, match="Invalid protocol_version"):
            s.protocol_version = 999.9  # Not a valid ProtocolVersion value


# ─────────────────────────────────────────────────────────────────────────────
# monitorable setter (lines 360, 363, 364)
# ─────────────────────────────────────────────────────────────────────────────


class TestMonitorableSetter:
    def test_non_bool_raises_type_error(self):
        """Line 360: TypeError when monitorable set to non-bool value."""
        s = _make_sensor("mon_type")
        with pytest.raises(TypeError, match=".monitorable must be a bool"):
            s.monitorable = "yes"  # Triggers line 360

    def test_unchanged_with_debug_logs(self, caplog):
        """Lines 363-364: debug branch when monitorable is set to same value with debug_logging=True."""
        s = _make_sensor("mon_debug", debug=True)
        caplog.set_level(logging.DEBUG)
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.monitorable = s.monitorable  # unchanged → triggers lines 363-364
            mock_log.debug.assert_called()

    def test_changed_logs_debug(self, caplog):
        """Covers the else branch in monitorable setter."""
        s = _make_sensor("mon_change", debug=True)
        initial = s.monitorable
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.monitorable = not initial
            mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# apply_device_overrides (lines 433, 438, 451, 456, 461)
# ─────────────────────────────────────────────────────────────────────────────


class TestApplyDeviceOverrides:
    def test_not_publishable_skips_with_debug(self, caplog):
        """Line 433: debug log when publishable is False."""
        caplog.set_level(logging.DEBUG)
        s = _make_sensor("ado_nopub", debug=True)
        s._publishable = False
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.apply_device_overrides(MagicMock())
            mock_log.debug.assert_called()

    def test_registers_none_logs_debug(self, caplog):
        """Line 438: debug log when registers is None."""
        caplog.set_level(logging.DEBUG)
        s = _make_sensor("ado_none", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.apply_device_overrides(None)  # registers=None → line 438
            mock_log.debug.assert_called()

    def test_read_write_override_disables_when_not_read_write(self, caplog):
        """Lines 449-452: writable sensor set to not-publishable when registers.read_write=False."""

        class _MockWriteable(WriteableSensorMixin, ReadOnlySensor):
            async def value_is_valid(self, modbus_client, raw_value):
                return True

        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # Use a real _MockWriteable instance so WriteableSensorMixin is genuinely in the MRO
            s = _MockWriteable(
                name="RW Test",
                object_id="sigen_ado_rw_test",
                input_type=InputType.HOLDING,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=ProtocolVersion.V2_4,
            )
            registers = MagicMock(spec=RegisterAccess)
            registers.no_remote_ems = False
            registers.read_write = False
            registers.read_only = True
            registers.write_only = True
            # WriteableSensorMixin is genuinely in MRO — publishable should be set to False
            s.apply_device_overrides(registers)
            assert s.publishable is False

    def test_readable_sensor_overrides(self, caplog):
        """Lines 453-457: read-only sensor publishable disabled when registers.read_only=False."""

        class _ConcreteReadOnly(ReadOnlySensor):
            async def _update_internal_state(self, **kwargs):
                return False

        caplog.set_level(logging.DEBUG)
        cfg = _make_cfg()
        with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # ReadOnlySensor extends ReadableSensorMixin, so ReadableSensorMixin is in its MRO
            s = _ConcreteReadOnly(
                name="RO Test",
                object_id="sigen_ado_ro_test",
                input_type=InputType.HOLDING,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=ProtocolVersion.V2_4,
                debug_logging=True,
            )

        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.read_write = True
        registers.read_only = False  # Will disable publishable for readable sensors
        registers.write_only = True

        # ReadableSensorMixin IS in ReadOnlySensor's MRO, so the read-only branch will fire
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.apply_device_overrides(registers)
            # Should have called debug for the read-only override
            assert mock_log.debug.called

    def test_remote_ems_no_remote_ems_override(self, caplog):
        """Lines 436-439: no_remote_ems override disables _remote_ems sensors."""
        s = _make_sensor("ado_ems", debug=True)
        s._remote_ems = MagicMock()  # Makes no_remote_ems check trigger

        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = True

        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.apply_device_overrides(registers)

        assert s.publishable is False


# ─────────────────────────────────────────────────────────────────────────────
# _override_qos and _override_retain (lines 619-627)
# ─────────────────────────────────────────────────────────────────────────────


class TestOverrideHelpers:
    def test_override_qos_when_changed(self, caplog):
        """Lines 619-621: _override_qos logs and updates when value changes."""
        caplog.set_level(logging.DEBUG)
        s = _make_sensor("qos_chg")
        original_qos = s._qos
        new_qos = 1 if original_qos != 1 else 2

        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s._override_qos("test", new_qos)
            assert s._qos == new_qos
            mock_log.debug.assert_called()

    def test_override_qos_when_unchanged_no_log(self):
        """Lines 619-621: _override_qos does nothing when value is same."""
        s = _make_sensor("qos_same")
        original_qos = s._qos

        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s._override_qos("test", original_qos)
            assert s._qos == original_qos
            mock_log.debug.assert_not_called()

    def test_override_retain_when_changed(self, caplog):
        """Lines 625-627: _override_retain logs and updates when value changes."""
        caplog.set_level(logging.DEBUG)
        s = _make_sensor("retain_chg")
        original_retain = s._retain

        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s._override_retain("test", not original_retain)
            assert s._retain is not original_retain
            mock_log.debug.assert_called()

    def test_override_retain_when_unchanged_no_log(self):
        """Lines 625-627: _override_retain does nothing when value is same."""
        s = _make_sensor("retain_same")
        original_retain = s._retain

        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s._override_retain("test", original_retain)
            assert s._retain is original_retain
            mock_log.debug.assert_not_called()
