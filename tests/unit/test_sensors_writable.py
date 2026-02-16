import asyncio
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Imported here (no hacks needed for mqtt any more)
from sigenergy2mqtt.common import Protocol  # noqa: E402
from sigenergy2mqtt.modbus import ModbusClient  # noqa: E402
from sigenergy2mqtt.sensors.base import InputType, NumericSensor, SelectSensor, Sensor, SwitchSensor, WriteOnlySensor  # noqa: E402


@pytest.fixture(autouse=True)
def mock_config_all():
    with patch("sigenergy2mqtt.sensors.base.Config") as mock_config:
        mock_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_config.home_assistant.enabled = True
        mock_config.sensor_overrides = {}
        mock_config.persistent_state_path = "."
        yield mock_config


@pytest.fixture(autouse=True)
def mock_metrics():
    with patch("sigenergy2mqtt.sensors.base.Metrics") as mock:
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

    # Default behaviour for convert_to_registers: try to return a list with the value if it's int-like
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


class TestWritableSensorMixin:
    @pytest.mark.asyncio
    async def test_write_registers_single_uint16(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigenergy_test", 0, 1, 30001, Protocol.V2_4)
            mock_mqtt = MagicMock()

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor._write_registers(mock_modbus, 100, mock_mqtt)

            assert result is True
            mock_modbus.write_register.assert_called_once_with(30001, 100, device_id=1, no_response_expected=False)
            assert sensor.force_publish is True

    @pytest.mark.asyncio
    async def test_write_registers_multiple_registers(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(None, "Test", "sigenergy_test", InputType.HOLDING, 0, 1, 30001, 2, ModbusClient.DATATYPE.UINT32, 10, "U", None, None, "mdi:power", 1.0, 2, Protocol.V2_4)

            mock_mqtt = MagicMock()
            # Disable side_effect to use return_value
            mock_modbus.convert_to_registers.side_effect = None
            mock_modbus.convert_to_registers.return_value = [1234, 5678]

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_registers.return_value = mock_rr

            result = await sensor._write_registers(mock_modbus, 123.45, mock_mqtt)

            assert result is True
            mock_modbus.write_registers.assert_called_once_with(30001, [1234, 5678], device_id=1, no_response_expected=False)


    @pytest.mark.asyncio
    async def test_write_registers_error_response(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigenergy_test", 0, 1, 30001, Protocol.V2_4)

            mock_rr = MagicMock()
            mock_rr.isError.return_value = True
            mock_rr.exception_code = 1
            mock_modbus.write_register.return_value = mock_rr

            with pytest.raises(Exception, match="0x01 ILLEGAL FUNCTION"):
                await sensor._write_registers(mock_modbus, 1, MagicMock())
            assert sensor.force_publish is True

    @pytest.mark.asyncio
    async def test_write_registers_timeout(self, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigenergy_test", 0, 1, 30001, Protocol.V2_4)

            with patch("sigenergy2mqtt.sensors.base.ModbusLockFactory.get") as mock_lock_factory_get:
                mock_lock = MagicMock()

                @asynccontextmanager
                async def mock_lock_cm(timeout=None):
                    raise asyncio.TimeoutError()
                    yield

                mock_lock.lock.side_effect = mock_lock_cm
                mock_lock_factory_get.return_value = mock_lock

                result = await sensor._write_registers(mock_modbus, 1, MagicMock())
                assert result is False
                assert sensor.force_publish is True

    @pytest.mark.asyncio
    async def test_write_registers_cancelled(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigenergy_test", 0, 1, 30001, Protocol.V2_4)
            mock_modbus.write_register.side_effect = asyncio.CancelledError()

            result = await sensor._write_registers(mock_modbus, 1, MagicMock())
            assert result is False
            assert sensor.force_publish is True


class TestWriteOnlySensorLogic:
    @pytest.mark.asyncio
    async def test_write_only_sensor_set_value(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = WriteOnlySensor("Test", "sigenergy_test", 0, 1, 30001, Protocol.V2_4, payload_on="on", payload_off="off", value_on=1, value_off=0)
            sensor.configure_mqtt_topics("test_device")

            mock_mqtt = MagicMock()
            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, mock_mqtt, "on", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30001, 1, device_id=1, no_response_expected=False)


class TestNumericSensorWritable:
    @pytest.mark.asyncio
    async def test_numeric_sensor_set_value_with_gain(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None, "Test", "sigenergy_test", InputType.HOLDING, 0, 1, 30100, 1, ModbusClient.DATATYPE.UINT16, 10, "W", None, None, "mdi:power", 10.0, 0, Protocol.V2_4, minimum=0, maximum=1000
            )
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, MagicMock(), 50.0, cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30100, 500, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_numeric_sensor_set_value_none_and_invalid(self, mock_lock_factory, mock_modbus, caplog):
        """NumericSensor should ignore None and reject non-numeric input with a warning."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigenergy_test2",
                InputType.HOLDING,
                0,
                1,
                30101,
                1,
                ModbusClient.DATATYPE.UINT16,
                10,
                "W",
                None,
                None,
                "mdi:power",
                1.0,
                0,
                Protocol.V2_4,
                minimum=0,
                maximum=100,
            )
            sensor.configure_mqtt_topics("test_device")

            # None is ignored
            caplog.clear()
            result = await sensor.set_value(mock_modbus, MagicMock(), None, cast(str, sensor["command_topic"]), MagicMock())
            assert result is False
            assert any("Ignored attempt to set value to *None*" in rec.message for rec in caplog.records)

            # Non-numeric logs a warning and returns False
            caplog.clear()
            result = await sensor.set_value(mock_modbus, MagicMock(), "abc", cast(str, sensor["command_topic"]), MagicMock())
            assert result is False
            assert any("Attempt to set value to 'abc' FAILED" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_numeric_set_value_with_string_and_gain(self, mock_lock_factory, mock_modbus):
        """NumericSensor should accept numeric strings and apply gain before writing."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Test",
                "sigenergy_test3",
                InputType.HOLDING,
                0,
                1,
                30102,
                1,
                ModbusClient.DATATYPE.UINT16,
                10,
                "W",
                None,
                None,
                "mdi:power",
                10.0,
                0,
                Protocol.V2_4,
                minimum=0,
                maximum=1000,
            )
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, MagicMock(), "5", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            # 5 * gain(10) == 50
            mock_modbus.write_register.assert_called_with(30102, 50, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_numeric_get_state_raw_clamp_with_gain(self):
        """When raw=True and value is out-of-range the raw return should include gain."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(None, "NumRaw", "sigenergy_numraw", InputType.HOLDING, 0, 1, 30103, 1, ModbusClient.DATATYPE.UINT16, 10, "W", None, None, "mdi:power", 2.0, 1, Protocol.V2_4, minimum=10.0, maximum=100.0)

            with patch("sigenergy2mqtt.sensors.base.ReadWriteSensor.get_state", new_callable=AsyncMock) as mock_super:
                # value below min -> should return min * gain when raw=True
                mock_super.return_value = 5.0
                val = await sensor.get_state(raw=True)
                assert val == 10.0 * 2.0


class TestSelectSensorWritable:
    @pytest.mark.asyncio
    async def test_select_sensor_set_value_index(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            options = ["Off", "On", "Auto"]
            sensor = SelectSensor(None, "Test", "sigenergy_test", 0, 1, 30200, 10, options, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, MagicMock(), "Auto", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30200, 2, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_select_sensor_set_value_index_string_and_invalid(self, mock_lock_factory, mock_modbus, caplog):
        """SelectSensor should accept numeric index strings and reject invalid values."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            options = ["Off", "On", "Auto"]
            sensor = SelectSensor(None, "Test", "sigenergy_test", 0, 1, 30201, 10, options, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            # Index as string should work
            result = await sensor.set_value(mock_modbus, MagicMock(), "1", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30201, 1, device_id=1, no_response_expected=False)

            # Integer index should also work
            result = await sensor.set_value(mock_modbus, MagicMock(), 0, cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30201, 0, device_id=1, no_response_expected=False)

            # Invalid option should be rejected and log an error
            caplog.clear()
            result = await sensor.set_value(mock_modbus, MagicMock(), "InvalidOption", cast(str, sensor["command_topic"]), MagicMock())
            assert result is False
            assert any("invalid value" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_select_sensor_translated_option_and_empty_option(self, mock_lock_factory, mock_modbus):
        """Covers translated-option matching and empty-option handling."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            options = ["Off", "", "Auto"]
            sensor = SelectSensor(None, "Test", "sigenergy_test_trans", 0, 1, 30202, 10, options, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            # Empty option should be treated as unknown when reading
            with patch("sigenergy2mqtt.sensors.base.ReadWriteSensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 1
                assert await sensor.get_state() == "Unknown Mode: 1"

            # Translated option matching path in _get_option_index
            with patch("sigenergy2mqtt.sensors.base._t", side_effect=lambda key, default, debugging=False: f"T:{default}"):
                mock_rr = MagicMock()
                mock_rr.isError.return_value = False
                mock_modbus.write_register.return_value = mock_rr

                # 'T:Auto' is the translated option for index 2
                result = await sensor.set_value(mock_modbus, MagicMock(), "T:Auto", cast(str, sensor["command_topic"]), MagicMock())
                assert result is True
                mock_modbus.write_register.assert_called_with(30202, 2, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_select_accepts_float_index_string_and_is_case_sensitive(self, mock_lock_factory, mock_modbus, caplog):
        """SelectSensor should accept numeric float-strings (e.g. '1.0') and reject case-mismatched option strings."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            options = ["Off", "On", "Auto"]
            sensor = SelectSensor(None, "Test", "sigenergy_test_case", 0, 1, 30203, 10, options, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            # numeric float-string index should be accepted
            result = await sensor.set_value(mock_modbus, MagicMock(), "1.0", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30203, 1, device_id=1, no_response_expected=False)

            # case-sensitive option matching: 'auto' should be rejected
            caplog.clear()
            res2 = await sensor.set_value(mock_modbus, MagicMock(), "auto", cast(str, sensor["command_topic"]), MagicMock())
            assert res2 is False
            assert any("invalid value" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_switch_accepts_boolean_values(self, mock_lock_factory, mock_modbus):
        """SwitchSensor should accept True/False and write 1/0 respectively."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = SwitchSensor(None, "Test", "sigenergy_switch_bool", 0, 1, 30302, 10, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            res_true = await sensor.set_value(mock_modbus, MagicMock(), True, cast(str, sensor["command_topic"]), MagicMock())
            assert res_true is True
            mock_modbus.write_register.assert_called_with(30302, 1, device_id=1, no_response_expected=False)

            res_false = await sensor.set_value(mock_modbus, MagicMock(), False, cast(str, sensor["command_topic"]), MagicMock())
            assert res_false is True
            mock_modbus.write_register.assert_called_with(30302, 0, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_numeric_set_value_decimal_string_precision_zero(self, mock_lock_factory, mock_modbus):
        """NumericSensor should accept decimal strings and (with precision=0) write the integer part."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(None, "Test", "sigenergy_num_decimal", InputType.HOLDING, 0, 1, 30104, 1, ModbusClient.DATATYPE.UINT16, 10, "W", None, None, "mdi:power", 1.0, 0, Protocol.V2_4, minimum=0, maximum=1000)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, MagicMock(), "3.9", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            # 3.9 should be converted to int(3.9) == 3 before writing
            mock_modbus.write_register.assert_called_with(30104, 3.0, device_id=1, no_response_expected=False)

class TestSwitchSensorWritable:
    @pytest.mark.asyncio
    async def test_switch_sensor_set_value(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = SwitchSensor(None, "Test", "sigenergy_test", 0, 1, 30300, 10, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            result = await sensor.set_value(mock_modbus, MagicMock(), 1, cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30300, 1, device_id=1, no_response_expected=False)

    @pytest.mark.asyncio
    async def test_switch_sensor_set_value_string_and_bad(self, mock_lock_factory, mock_modbus, caplog):
        """SwitchSensor should accept numeric strings but raise on non-numeric input."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = SwitchSensor(None, "Test", "sigenergy_test2", 0, 1, 30301, 10, Protocol.V2_4)
            sensor.configure_mqtt_topics("test_device")

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_register.return_value = mock_rr

            # Numeric string works
            result = await sensor.set_value(mock_modbus, MagicMock(), "1", cast(str, sensor["command_topic"]), MagicMock())
            assert result is True
            mock_modbus.write_register.assert_called_with(30301, 1, device_id=1, no_response_expected=False)

            # Non-numeric should raise ValueError and log
            caplog.clear()
            with pytest.raises(ValueError):
                await sensor.set_value(mock_modbus, MagicMock(), "bad", cast(str, sensor["command_topic"]), MagicMock())
            assert any("value_is_valid check of value 'bad' FAILED" in rec.message for rec in caplog.records)
