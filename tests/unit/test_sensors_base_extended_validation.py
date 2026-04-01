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



class TestCheckRegisterResponse:
    def _make_readonly_sensor(self, suffix):
        """Create a ReadOnlySensor instance for testing _check_register_response."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            s = ReadOnlySensor(
                name="RO Test",
                object_id=f"sigen_{suffix}",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        return s

    def test_check_register_response_none(self):
        s = self._make_readonly_sensor("crr_none")
        assert s._check_register_response(None, "read_input_registers") is False

    def test_check_register_response_exception_code_1(self):
        s = self._make_readonly_sensor("crr_ex1")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 1
        with pytest.raises(Exception, match="ILLEGAL FUNCTION"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_exception_code_2_sets_max_failures_zero(self):
        s = self._make_readonly_sensor("crr_ex2")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with pytest.raises(Exception, match="ILLEGAL DATA ADDRESS"):
            s._check_register_response(rr, "read_input_registers")
        assert s._max_failures == 0
        assert s._max_failures_retry_interval == 0

    def test_check_register_response_exception_code_2_write_no_max_reset(self):
        """For write_registers, max_failures NOT reset on exception code 2."""
        s = self._make_readonly_sensor("crr_ex2wr")
        original_max_failures = s._max_failures
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with pytest.raises(Exception, match="ILLEGAL DATA ADDRESS"):
            s._check_register_response(rr, "write_registers")
        assert s._max_failures == original_max_failures  # unchanged for write

    def test_check_register_response_exception_code_3(self):
        s = self._make_readonly_sensor("crr_ex3")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 3
        with pytest.raises(Exception, match="ILLEGAL DATA VALUE"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_exception_code_4(self):
        s = self._make_readonly_sensor("crr_ex4")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 4
        with pytest.raises(Exception, match="SLAVE DEVICE FAILURE"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_unknown_exception_code(self):
        s = self._make_readonly_sensor("crr_ex_unk")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 99
        with pytest.raises(Exception):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_success(self):
        s = self._make_readonly_sensor("crr_ok")
        rr = MagicMock()
        rr.isError.return_value = False
        assert s._check_register_response(rr, "read_input_registers") is True

    def test_check_register_response_exception_code_2_with_debug(self):
        s = self._make_readonly_sensor("crr_ex2_dbg")
        s.debug_logging = True
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with patch("sigenergy2mqtt.sensors.base.mixins.logging") as mock_log, pytest.raises(Exception):
            s._check_register_response(rr, "read_input_registers")
        mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 11. ReadOnlySensor._update_internal_state() branches
# ─────────────────────────────────────────────────────────────────────────────



class TestReadOnlySensorUpdateInternalState:
    def _make_ro(self, suffix):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            return ReadOnlySensor(
                name="RO",
                object_id=f"sigen_{suffix}",
                input_type=InputType.HOLDING,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )

    @pytest.mark.asyncio
    async def test_update_internal_state_cancelled_error(self):
        """asyncio.CancelledError results in result=False (lines ~1073+)."""
        s = self._make_ro("ro_cancel")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=asyncio.CancelledError())

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()
        mock_metrics.modbus_read_error = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_internal_state_timeout_error(self):
        """asyncio.TimeoutError results in result=False (lines ~1104+)."""
        s = self._make_ro("ro_timeout")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_internal_state_input_registers(self):
        """INPUT type uses read_input_registers."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            s = ReadOnlySensor(
                name="RO Input",
                object_id="sigen_ro_input",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )

        rr = MagicMock()
        rr.isError.return_value = False
        rr.registers = [100]

        modbus = MagicMock()
        modbus.read_input_registers = AsyncMock(return_value=rr)
        modbus.read_holding_registers = AsyncMock(return_value=rr)
        modbus.convert_from_registers = MagicMock(return_value=100)

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is True
        modbus.read_input_registers.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_internal_state_generic_exception_increments_metrics(self):
        """Generic exception calls Metrics.modbus_read_error and re-raises."""
        s = self._make_ro("ro_gen_exc")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=Exception("generic"))

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()
        mock_metrics.modbus_read_error = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics), pytest.raises(Exception, match="generic"):
            await s._update_internal_state(modbus_client=modbus)

        mock_metrics.modbus_read_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_internal_state_debug_logging(self):
        """Debug logging branch in _update_internal_state (line ~1151+)."""
        s = self._make_ro("ro_debug_upd")
        s.debug_logging = True

        rr = MagicMock()
        rr.isError.return_value = False
        rr.registers = [42]

        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(return_value=rr)
        modbus.convert_from_registers = MagicMock(return_value=42)

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics), patch("sigenergy2mqtt.sensors.base.readable.logging") as mock_log:
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is True
        mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 12. AlarmSensor / AlarmCombinedSensor branches
# ─────────────────────────────────────────────────────────────────────────────



class TestSanityCheckFailureIncrement:
    @pytest.mark.asyncio
    async def test_sanity_check_exception_not_counted_when_config_disabled(self):
        """SanityCheckException doesn't increment failures when sanity_check_failures_increment=False."""
        from sigenergy2mqtt.sensors.base import SanityCheckException

        s = _make_sensor(uid_suffix="sc_nocount")
        s["state_topic"] = "test/state"
        s["json_attributes_topic"] = "test/attrs"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise SanityCheckException("out of range")

        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            patch("sigenergy2mqtt.sensors.base.active_config.sanity_check_failures_increment", False),
            patch("sigenergy2mqtt.sensors.base.active_config.home_assistant.enabled", False),
            patch("sigenergy2mqtt.sensors.base.logging"),
        ):
            await s.publish(mqtt, modbus)

        assert s._failures == 0  # not counted

    @pytest.mark.asyncio
    async def test_sanity_check_exception_counted_when_config_enabled(self):
        """SanityCheckException DOES increment failures when sanity_check_failures_increment=True."""
        from sigenergy2mqtt.sensors.base import SanityCheckException

        s = _make_sensor(uid_suffix="sc_count")
        s["state_topic"] = "test/state"
        s["json_attributes_topic"] = "test/attrs"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise SanityCheckException("out of range")

        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            patch("sigenergy2mqtt.sensors.base.active_config.sanity_check_failures_increment", True),
            patch("sigenergy2mqtt.sensors.base.active_config.home_assistant.enabled", False),
            patch("sigenergy2mqtt.sensors.base.logging"),
        ):
            await s.publish(mqtt, modbus)

        assert s._failures == 1


# ─────────────────────────────────────────────────────────────────────────────
# 18. WritableSensorMixin publishable via apply_sensor_overrides
# ─────────────────────────────────────────────────────────────────────────────



class TestReadableSensorScanIntervalOverride:
    def test_scan_interval_override_applied(self):
        """scan-interval override is applied during __init__."""
        from sigenergy2mqtt.common import InputType

        with (
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
            patch(
                "sigenergy2mqtt.sensors.base.active_config.sensor_overrides",
                {"sigen_ro_si": {"scan-interval": 99}},
            ),
        ):
            s = ReadOnlySensor(
                name="ScanInterval",
                object_id="sigen_ro_si",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        assert s.scan_interval == 99
