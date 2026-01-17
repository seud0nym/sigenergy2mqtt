import asyncio
import sys
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock circular dependencies before importing sensors.base
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

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
            sensor = NumericSensor(None, "Test", "sigenergy_test", InputType.HOLDING, 0, 1, 30001, 2, ModbusClient.DATATYPE.FLOAT32, 10, "U", None, None, "mdi:power", 1.0, 2, Protocol.V2_4)

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
    async def test_write_registers_string(self, mock_lock_factory, mock_modbus):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(None, "Test", "sigenergy_test", InputType.HOLDING, 0, 1, 30001, 4, ModbusClient.DATATYPE.STRING, 10, "U", None, None, "mdi:power", 1.0, 2, Protocol.V2_4)

            mock_mqtt = MagicMock()
            # Disable side_effect to use return_value
            mock_modbus.convert_to_registers.side_effect = None
            mock_modbus.convert_to_registers.return_value = [0x4142, 0x4344]

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_modbus.write_registers.return_value = mock_rr

            result = await sensor._write_registers(mock_modbus, "ABCD", mock_mqtt)

            assert result is True
            mock_modbus.write_registers.assert_called_once_with(30001, [0x4142, 0x4344], device_id=1, no_response_expected=False)

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
