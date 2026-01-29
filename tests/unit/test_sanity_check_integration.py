from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.base import InputType, NumericSensor, SelectSensor
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass
from sigenergy2mqtt.sensors.sanity_check import SanityCheckException


class TestSanityCheckIntegration:
    @pytest.fixture
    def mock_mqtt_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_modbus_client(self):
        client = MagicMock()
        client.connected = True
        client.read_holding_registers = AsyncMock()
        client.read_input_registers = AsyncMock()
        return client

    def test_numeric_sensor_sanity_check_initialization(self):
        # NumericSensor with min/max having gain applied
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test Sensor",
            object_id="sigen_test_sensor",
            input_type=InputType.HOLDING,
            plant_index=1,
            device_address=200,
            address=30001,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit="W",
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:test",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
            minimum=5.0,  # Display value
            maximum=20.0,  # Display value
        )

        # Raw min should be 5.0 * 10 = 50
        # Raw max should be 20.0 * 10 = 200
        assert sensor.sanity_check.min_raw == 50
        assert sensor.sanity_check.max_raw == 200

    def test_select_sensor_sanity_check_initialization(self):
        options = ["A", "B", "C"]
        sensor = SelectSensor(
            availability_control_sensor=None,
            name="Test Select",
            object_id="sigen_test_select",
            plant_index=1,
            device_address=200,
            address=30002,
            scan_interval=60,
            options=options,
            protocol_version=Protocol.V1_8,
        )

        # Raw values are indices 0, 1, 2
        assert sensor.sanity_check.min_raw == 0
        assert sensor.sanity_check.max_raw == 2

    @pytest.mark.asyncio
    async def test_sensor_publish_sanity_failure_increment(self, mock_mqtt_client, mock_modbus_client):
        # Config.sanity_check_failures_increment = True by default
        Config.sanity_check_failures_increment = True

        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test Fail",
            object_id="sigen_test_fail",
            input_type=InputType.HOLDING,
            plant_index=1,
            device_address=200,
            address=30003,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit="W",
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:test",
            gain=1,
            precision=1,
            protocol_version=Protocol.V1_8,
            minimum=10,
            maximum=20,
        )

        # Mock get_state to return value outside range via sanity_check.is_sane (which is called in set_state)
        # However, Sensor.get_state calls modbus read -> _update_internal_state -> set_latest_state -> set_state -> sanity.is_sane
        # We can mock modbus read to return invalid raw value.

        # Raw value 5 (below min 10)
        mock_rr = MagicMock()
        mock_rr.registers = [5]
        mock_rr.isError.return_value = False
        mock_modbus_client.read_holding_registers.return_value = mock_rr
        mock_modbus_client.convert_from_registers.return_value = 5

        await sensor.publish(mock_mqtt_client, mock_modbus_client)

        # Should have incremented failures
        assert sensor._failures == 1

        # Now try with config set to False
        Config.sanity_check_failures_increment = False
        sensor._failures = 0

        await sensor.publish(mock_mqtt_client, mock_modbus_client)

        # Should NOT increment failures
        assert sensor._failures == 0

        # Reset config
        Config.sanity_check_failures_increment = True

    @pytest.mark.asyncio
    async def test_numeric_sensor_sanity_check_enforcement(self):
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test Enf",
            object_id="sigen_test_enf",
            input_type=InputType.HOLDING,
            plant_index=1,
            device_address=200,
            address=30004,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit="W",
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:test",
            gain=1,
            precision=1,
            protocol_version=Protocol.V1_8,
            minimum=10,
            maximum=20,
        )

        # Valid update
        sensor.set_state(15)
        assert sensor._states[-1][1] == 15

        # Invalid update: SanityCheckException
        # Note: set_state usually catches nothing, but it calls sanity.is_sane which raises SanityCheckException
        # In actual flow, exceptions are caught in publish. Here we test set_state directly.

        with pytest.raises(SanityCheckException):
            sensor.set_state(5)

        with pytest.raises(SanityCheckException):
            sensor.set_state(25)
