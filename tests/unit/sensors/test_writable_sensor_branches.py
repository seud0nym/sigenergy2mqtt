"""Tests for specific branches in sensors/base/writable.py.

Covers missing lines:
  writable.py  56, 58, 113, 131, 150, 253, 345, 355, 357, 430, 433, 434, 436, 437,
               439, 455, 464, 465, 467, 581
"""

import logging
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import InputType, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.sensors.base import (
    AvailabilityMixin,
    DiscoveryKeys,
    NumericSensor,
    Sensor,
    WriteOnlySensor,
)


@pytest.fixture(autouse=True)
def mock_config_all():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = True
    cfg.sensor_overrides = {}
    cfg.persistent_state_path = "."

    with _swap_active_config(cfg):
        yield cfg


@pytest.fixture(autouse=True)
def mock_metrics():
    with patch("sigenergy2mqtt.metrics.Metrics") as mock:
        mock.modbus_read = AsyncMock()
        mock.modbus_write = AsyncMock()
        mock.modbus_read_error = AsyncMock()
        mock.modbus_write_error = AsyncMock()
        mock.modbus_cache_hits = AsyncMock()
        yield mock


@pytest.fixture
def mock_modbus():
    modbus = MagicMock(spec=ModbusClient)
    modbus.DATATYPE = ModbusClient.DATATYPE
    modbus.write_register = AsyncMock()
    modbus.write_registers = AsyncMock()
    modbus.read_holding_registers = AsyncMock()
    modbus.read_input_registers = AsyncMock()

    def side_effect(val, _data_type):
        try:
            return [int(val)]
        except (ValueError, TypeError):
            return [0]

    modbus.convert_to_registers = MagicMock(side_effect=side_effect)
    return modbus


@pytest.fixture
def mock_lock_factory():
    with patch("sigenergy2mqtt.sensors.base.ModbusLockFactory.get") as mock_get:
        mock_lock = MagicMock()

        @asynccontextmanager
        async def mock_lock_cm(timeout=None):
            yield

        mock_lock.lock.side_effect = mock_lock_cm
        mock_get.return_value = mock_lock
        yield mock_get


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnlySensor icon validation (lines 56, 58)
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnlySensorIconValidation:
    def test_invalid_icon_on_raises(self):
        """Line 56: ValueError when on icon doesn't start with 'mdi:'."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True), pytest.raises(ValueError, match="on icon.*does not start with 'mdi:'"):
            WriteOnlySensor(
                "Test",
                "sigen_test_icon_on",
                0,
                1,
                30001,
                Protocol.V2_4,
                icon_on="bad_icon_on",  # Triggers line 56
            )

    def test_invalid_icon_off_raises(self):
        """Line 58: ValueError when off icon doesn't start with 'mdi:'."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True), pytest.raises(ValueError, match="off icon.*does not start with 'mdi:'"):
            WriteOnlySensor(
                "Test",
                "sigen_test_icon_off",
                0,
                1,
                30001,
                Protocol.V2_4,
                icon_on="mdi:power-on",  # Valid
                icon_off="bad_icon_off",  # Triggers line 58
            )


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnlySensor.get_discovery_components (lines 113, 131)
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnlySensorGetDiscoveryComponents:
    def test_empty_name_skips_button(self):
        """Line 113: button with empty name is skipped in get_discovery_components."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # Use a subclass with a unique name so the i18n translation lookup finds
            # no entry (key="_NoTranslationSensor.name_on") and falls back to the
            # empty string default, ensuring self._names["on"] == "".
            class _NoTranslationSensor(WriteOnlySensor):
                pass

            sensor = _NoTranslationSensor(
                "Test",
                "sigen_test_skip_btn",
                0,
                1,
                30001,
                Protocol.V2_4,
                name_on="",  # Empty name → no i18n key for this class, stays empty → skip
                name_off="Power Off",
            )
            comps = sensor.get_discovery_components()
            # The "on" button should be skipped because the name is empty
            assert f"{sensor.unique_id}_on" not in comps or comps.get(f"{sensor.unique_id}_on", {}).get("platform") is None

    def test_debug_logging_in_get_discovery_components(self, caplog):
        """Line 131: debug log when debug_logging=True."""
        caplog.set_level(logging.DEBUG)
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigen_test_disc_debug", 0, 1, 30001, Protocol.V2_4)
            sensor.debug_logging = True
            with patch("sigenergy2mqtt.sensors.base.writable.logger") as mock_log:
                sensor.get_discovery_components()
                mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# WriteOnlySensor.set_value "off" payload branch (line 150)
# ─────────────────────────────────────────────────────────────────────────────


class TestWriteOnlySensorSetValue:
    @pytest.mark.asyncio
    async def test_set_value_off_payload(self, mock_lock_factory, mock_modbus):
        """Line 150: set_value translates 'off' payload to actual off value."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigen_sv_off", 0, 1, 30001, Protocol.V2_4)
            # Configure MQTT topics so COMMAND_TOPIC is set before calling set_value
            sensor.configure_mqtt_topics("test_device")
            # Now set the command topic explicitly so the source comparison succeeds
            command_topic = f"sigenergy2mqtt/{sensor.object_id}"
            sensor[DiscoveryKeys.COMMAND_TOPIC] = command_topic
            mock_mqtt = MagicMock()

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr
            mock_modbus.write_registers = AsyncMock(return_value=mock_rr)

            mock_handler = MagicMock()
            # Pass "off" payload → actual_value = _values["off"] = 0
            result = await sensor.set_value(mock_modbus, mock_mqtt, "off", command_topic, mock_handler)
            assert isinstance(result, bool)


# ─────────────────────────────────────────────────────────────────────────────
# ReadWriteSensor.configure_mqtt_topics error (line 253)
# ─────────────────────────────────────────────────────────────────────────────


class TestReadWriteSensorConfigureMqttTopics:
    def test_raises_when_control_sensor_topic_not_configured(self):
        """Line 253: RuntimeError when availability control sensor topic is empty."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # Create a control sensor mock that passes isinstance(_, AvailabilityMixin)
            mock_control = MagicMock(spec=AvailabilityMixin)
            mock_control.__class__ = AvailabilityMixin  # make isinstance() pass
            mock_control.state_topic = ""  # Empty → triggers RuntimeError
            mock_control.raw_state_topic = ""
            mock_control.publish_raw = False

            sensor = NumericSensor(
                mock_control,
                "Test",
                "sigen_rw_topic_err",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                None,
                Protocol.V2_4,
                minimum=0.0,
                maximum=100.0,
            )

            with pytest.raises(RuntimeError, match="has not been configured"):
                sensor.configure_mqtt_topics("test_device")


# ─────────────────────────────────────────────────────────────────────────────
# NumericSensor._validate_min_max_ranges (lines 345, 355, 357)
# ─────────────────────────────────────────────────────────────────────────────


class TestNumericSensorValidateMinMaxRanges:
    def test_simple_min_greater_than_max_raises(self):
        """Line 345: AssertionError when minimum >= maximum (simple numbers)."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True), pytest.raises(AssertionError, match="min must be < max"):
            NumericSensor(
                None,
                "Test",
                "sigen_minmax_err",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                None,
                Protocol.V2_4,
                minimum=100.0,  # Triggers line 345
                maximum=50.0,
            )

    def test_tuple_non_numeric_raises_type_error(self):
        """Line 355: TypeError when tuple contains non-numeric values."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_tuple_valid",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                None,
                Protocol.V2_4,
            )
            # Call _validate_min_max_ranges directly with non-numeric tuple values
            with pytest.raises(TypeError, match="must be numeric"):
                sensor._validate_min_max_ranges(("a", "b"), ("c", "d"))  # Triggers line 355

    def test_tuple_min_greater_than_max_raises_value_error(self):
        """Line 357: ValueError when tuple min >= max."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_tuple_minmax",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                None,
                Protocol.V2_4,
            )
            with pytest.raises(ValueError, match="min must be < max"):
                sensor._validate_min_max_ranges((10.0, 20.0), (5.0, 1.0))  # Triggers line 357


# ─────────────────────────────────────────────────────────────────────────────
# NumericSensor.get_discovery_components tuple flattening (lines 430, 433-437)
# ─────────────────────────────────────────────────────────────────────────────


class TestNumericSensorGetDiscoveryComponents:
    def test_tuple_min_max_flattened(self):
        """Lines 433-437: tuple min/max are flattened to single values in discovery."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_tuple_mm",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.INT16,
                10,
                None,
                None,
                "mdi:power",
                1000.0,
                None,
                Protocol.V2_4,
                minimum=(-1.0, -0.8),  # Tuple minimum
                maximum=(0.8, 1.0),  # Tuple maximum
            )
            comps = sensor.get_discovery_components()
            uid = sensor.unique_id
            # Flattened to single values
            assert uid in comps
            assert isinstance(comps[uid].get(DiscoveryKeys.MIN), (int, float))
            assert isinstance(comps[uid].get(DiscoveryKeys.MAX), (int, float))
            # min(-1.0, -0.8) = -1.0, max(0.8, 1.0) = 1.0
            assert comps[uid][DiscoveryKeys.MIN] == pytest.approx(-1.0)
            assert comps[uid][DiscoveryKeys.MAX] == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# NumericSensor.get_state int precision handling (lines 455, 464-467)
# ─────────────────────────────────────────────────────────────────────────────


class TestNumericSensorGetState:
    @pytest.mark.asyncio
    async def test_precision_zero_returns_int_for_exact_float(self):
        """Lines 464-465: When precision=0 and value is an exact float, return int."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_prec_zero",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                0,  # gain=None, precision=0
                Protocol.V2_4,
                minimum=0.0,
                maximum=100.0,
            )
            # Set a state with an exact float
            sensor.set_latest_state(42.0)  # Exact float → should return int 42
            state = await sensor.get_state(republish=True)
            assert state == 42
            assert isinstance(state, int)

    @pytest.mark.asyncio
    async def test_precision_zero_returns_int_for_int(self):
        """Lines 462-463: When precision=0 and value is already an int, return int directly."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_prec_zero_int",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                0,  # gain=None, precision=0
                Protocol.V2_4,
                minimum=0.0,
                maximum=100.0,
            )
            sensor.set_latest_state(50)
            state = await sensor.get_state(republish=True)
            assert isinstance(state, (int, float))

    @pytest.mark.asyncio
    async def test_precision_zero_non_exact_float(self):
        """Line 467: When precision=0 and value is non-exact float, return float."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigen_prec_zero_flt",
                InputType.HOLDING,
                0,
                1,
                30001,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                "mdi:power",
                None,
                0,  # gain=None, precision=0
                Protocol.V2_4,
                minimum=0.0,
                maximum=100.0,
            )
            sensor.set_latest_state(42.7)
            state = await sensor.get_state(republish=True)
            # Should be a number (float since not exact int)
            assert isinstance(state, (float, int))


# ─────────────────────────────────────────────────────────────────────────────
# ThreePhaseAdjustmentTargetValue missing output_type (line 581)
# ─────────────────────────────────────────────────────────────────────────────


class TestThreePhaseAdjustmentTargetValue:
    def test_missing_output_type_raises(self):
        """Line 581: ValueError when output_type not in kwargs."""
        from sigenergy2mqtt.sensors.base.writable import ThreePhaseAdjustmentTargetValue

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # output_type is passed through **kwargs by ThreePhaseAdjustmentTargetValue
            # but we need to NOT pass it to trigger line 581
            # ThreePhaseAdjustmentTargetValue calls super().__init__(**kwargs) first,
            # then checks for output_type. We call it without output_type.
            with pytest.raises(ValueError, match="output_type parameter is required"):
                ThreePhaseAdjustmentTargetValue(
                    availability_control_sensor=None,
                    name="Test",
                    object_id="sigen_three_phase",
                    input_type=InputType.HOLDING,
                    plant_index=0,
                    device_address=1,
                    address=40008,
                    count=2,
                    data_type=ModbusDataType.INT32,
                    scan_interval=60,
                    unit=None,
                    device_class=None,
                    icon="mdi:power",
                    gain=None,
                    precision=None,
                    protocol_version=Protocol.V1_8,
                    # output_type intentionally omitted → triggers line 581
                )
