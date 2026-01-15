import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import (
    AvailabilityMixin,
    InputType,
    NumericSensor,
    SelectSensor,
    Sensor,
    SwitchSensor,
    WritableSensorMixin,
    WriteOnlySensor,
)
from sigenergy2mqtt.sensors.plant_read_write import (
    MaxChargingLimit,
    MaxDischargingLimit,
    PVMaxPowerLimit,
    RemoteEMSControlMode,
    RemoteEMSLimit,
)


class ConcreteWritableSensor(WritableSensorMixin, Sensor):
    async def _update_internal_state(self, **kwargs):
        return True


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.config.Config") as mock:
        mock.home_assistant.entity_id_prefix = "sigen"
        mock.home_assistant.unique_id_prefix = "sigen"
        mock.home_assistant.discovery_prefix = "homeassistant"
        mock.home_assistant.enabled = True
        mock.home_assistant.use_simplified_topics = False
        mock.home_assistant.edit_percentage_with_box = False
        mock.home_assistant.enabled_by_default = True
        mock.sensor_overrides = {}
        mock.clean = False
        mock.persistent_state_path = "/tmp"
        mock.ems_mode_check = True
        mock.modbus = [MagicMock()]
        mock.modbus[0].scan_interval.medium = 60
        mock.modbus[0].scan_interval.high = 10
        # Patch where it's imported in sensors
        with patch("sigenergy2mqtt.sensors.base.Config", mock), patch("sigenergy2mqtt.sensors.plant_read_write.Config", mock):
            yield mock


class TestValueIsValidBase:
    @pytest.mark.asyncio
    async def test_writable_sensor_mixin_default(self, mock_config):
        sensor = ConcreteWritableSensor(
            name="Test",
            unique_id="sigen_test",
            object_id="sigen_test",
            unit="W",
            device_class=None,
            state_class=None,
            icon="mdi:test",
            gain=1.0,
            precision=2,
            protocol_version=Protocol.V1_8,
            data_type=ModbusDataType.UINT16,
            input_type=InputType.HOLDING,
            plant_index=0,
            device_address=247,
            address=40000,
            count=1,
        )
        assert await sensor.value_is_valid(None, 123) is True

    @pytest.mark.asyncio
    async def test_write_only_sensor(self, mock_config):
        sensor = WriteOnlySensor(
            # WriteOnlySensor __init__ provides the MSM args
            name="Test",
            object_id="sigen_test",
            plant_index=0,
            device_address=247,
            address=40000,
            protocol_version=Protocol.V1_8,
            value_off=0,
            value_on=1,
        )
        assert await sensor.value_is_valid(None, 0) is True
        assert await sensor.value_is_valid(None, 1) is True
        assert await sensor.value_is_valid(None, 2) is False

    @pytest.mark.asyncio
    async def test_numeric_sensor_float_range(self, mock_config):
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigen_test",
            input_type=InputType.HOLDING,
            plant_index=0,
            device_address=247,
            address=40001,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=60,
            unit="W",
            device_class=None,
            state_class=None,
            icon="mdi:test",
            gain=1.0,
            precision=1,
            protocol_version=Protocol.V1_8,
            minimum=0.0,
            maximum=100.0,
        )
        assert await sensor.value_is_valid(None, 50) is True
        assert await sensor.value_is_valid(None, 0) is True
        assert await sensor.value_is_valid(None, 100) is True
        assert await sensor.value_is_valid(None, -1) is False
        assert await sensor.value_is_valid(None, 101) is False
        assert await sensor.value_is_valid(None, "abc") is False

    @pytest.mark.asyncio
    async def test_numeric_sensor_tuple_range(self, mock_config):
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigen_test",
            input_type=InputType.HOLDING,
            plant_index=0,
            device_address=247,
            address=40001,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=60,
            unit="W",
            device_class=None,
            state_class=None,
            icon="mdi:test",
            gain=1.0,
            precision=1,
            protocol_version=Protocol.V1_8,
            minimum=(-10.0, -5.0),
            maximum=(5.0, 10.0),
        )
        # min range is -10 to -5, max range is 5 to 10
        assert await sensor.value_is_valid(None, -7) is True
        assert await sensor.value_is_valid(None, 7) is True
        assert await sensor.value_is_valid(None, -11) is False
        assert await sensor.value_is_valid(None, -4) is False
        assert await sensor.value_is_valid(None, 4) is False
        assert await sensor.value_is_valid(None, 11) is False

    @pytest.mark.asyncio
    async def test_select_sensor(self, mock_config):
        sensor = SelectSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigen_test",
            plant_index=0,
            device_address=247,
            address=40001,
            scan_interval=60,
            options=["A", "B", "C"],
            protocol_version=Protocol.V1_8,
        )
        assert await sensor.value_is_valid(None, "A") is True
        assert await sensor.value_is_valid(None, "B") is True
        assert await sensor.value_is_valid(None, "1") is True  # Index as string
        assert await sensor.value_is_valid(None, 1) is True  # Index as int
        assert await sensor.value_is_valid(None, "D") is False
        assert await sensor.value_is_valid(None, "3") is False

    @pytest.mark.asyncio
    async def test_switch_sensor(self, mock_config):
        sensor = SwitchSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigen_test",
            plant_index=0,
            device_address=247,
            address=40001,
            scan_interval=60,
            protocol_version=Protocol.V1_8,
        )
        assert await sensor.value_is_valid(None, 0) is True
        assert await sensor.value_is_valid(None, 1) is True
        assert await sensor.value_is_valid(None, 2) is False


class TestValueIsValidPlant:
    @pytest.mark.asyncio
    async def test_remote_ems_control_mode(self, mock_config):
        mock_avail = MagicMock(spec=AvailabilityMixin)
        mock_avail.get_state = AsyncMock(return_value=1)
        mock_avail.name = "Remote EMS"

        sensor = RemoteEMSControlMode(plant_index=0, remote_ems=mock_avail)
        assert await sensor.value_is_valid(None, 1) is True

        mock_avail.get_state.return_value = 0
        assert await sensor.value_is_valid(None, 1) is False

    @pytest.mark.asyncio
    async def test_remote_ems_limit(self, mock_config):
        mock_avail = MagicMock(spec=AvailabilityMixin)
        mock_avail.latest_raw_state = 1
        mock_avail.name = "Remote EMS"
        mock_mode = MagicMock(spec=RemoteEMSControlMode)

        sensor = RemoteEMSLimit(
            availability_control_sensor=mock_avail,
            remote_ems_mode=mock_mode,
            charging=True,
            discharging=True,
            name="Limit",
            object_id="sigen_limit",
            plant_index=0,
            address=40032,
            icon="mdi:test",
            maximum=10.0,
            protocol_version=Protocol.V1_8,
        )
        assert await sensor.value_is_valid(None, 5) is True

        mock_avail.latest_raw_state = 0
        assert await sensor.value_is_valid(None, 5) is False

    @pytest.mark.asyncio
    async def test_max_charging_limit(self, mock_config):
        mock_avail = MagicMock(spec=AvailabilityMixin)
        mock_avail.latest_raw_state = 1
        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.latest_raw_state = 3  # Command Charging

        sensor = MaxChargingLimit(plant_index=0, remote_ems=mock_avail, remote_ems_mode=mock_mode, rated_charging_power=10.0)
        assert await sensor.value_is_valid(None, 5) is True

        mock_mode.latest_raw_state = 1  # Normal
        assert await sensor.value_is_valid(None, 5) is False

        mock_config.ems_mode_check = False
        assert await sensor.value_is_valid(None, 5) is True

    @pytest.mark.asyncio
    async def test_max_discharging_limit(self, mock_config):
        mock_avail = MagicMock(spec=AvailabilityMixin)
        mock_avail.latest_raw_state = 1
        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.latest_raw_state = 5  # Command Discharging

        sensor = MaxDischargingLimit(plant_index=0, remote_ems=mock_avail, remote_ems_mode=mock_mode, rated_discharging_power=10.0)
        assert await sensor.value_is_valid(None, 5) is True

        mock_mode.latest_raw_state = 1  # Normal
        assert await sensor.value_is_valid(None, 5) is False

    @pytest.mark.asyncio
    async def test_pv_max_power_limit(self, mock_config):
        mock_avail = MagicMock(spec=AvailabilityMixin)
        mock_avail.latest_raw_state = 1
        mock_mode = MagicMock(spec=RemoteEMSControlMode)
        mock_mode.latest_raw_state = 3  # Command Charging

        sensor = PVMaxPowerLimit(plant_index=0, remote_ems=mock_avail, remote_ems_mode=mock_mode)
        assert await sensor.value_is_valid(None, 5) is True

        mock_mode.latest_raw_state = 1  # Normal
        assert await sensor.value_is_valid(None, 5) is False
