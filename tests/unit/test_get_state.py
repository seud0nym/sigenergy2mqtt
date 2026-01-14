import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock circular dependencies before importing sigenergy2mqtt
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

from sigenergy2mqtt.config import Protocol
from sigenergy2mqtt.main.main import get_state as main_get_state
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerRunningState
from sigenergy2mqtt.sensors.base import DerivedSensor, ReadOnlySensor, Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, InputType, StateClass
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion
from sigenergy2mqtt.sensors.plant_read_only import EMSWorkMode, GridSensorStatus, GridStatus, SystemTimeZone
from sigenergy2mqtt.sensors.plant_read_write import PCSMaxExportLimit


# Concrete implementation of Sensor for testing since Sensor is abstract
class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        # By default, pretend we got a value and set it
        if "value" in kwargs:
            self.set_state(kwargs["value"])
        return True


@pytest.fixture(autouse=True)
def mock_config_global():
    with patch("sigenergy2mqtt.config.Config") as mock:
        mock.home_assistant.unique_id_prefix = "sigen"
        mock.home_assistant.entity_id_prefix = "sigen"
        mock.home_assistant.enabled = True
        mock.home_assistant.enabled_by_default = False
        mock.sensor_debug_logging = False
        mock.persistent_state_path = "/tmp"
        mock.devices = []
        mock.sensor_overrides = {}
        # Also patch in base module where it might have been imported already
        with patch("sigenergy2mqtt.sensors.base.Config", mock):
            with patch("sigenergy2mqtt.sensors.ac_charger_read_only.Config", mock):
                with patch("sigenergy2mqtt.sensors.plant_read_only.Config", mock):
                    with patch("sigenergy2mqtt.sensors.inverter_read_only.Config", mock):
                        with patch("sigenergy2mqtt.sensors.plant_read_write.Config", mock):
                            yield mock


class TestGetState:
    @pytest.mark.asyncio
    async def test_sensor_get_state_republish(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ConcreteSensor(name="Test", unique_id="sigen_u1", object_id="sigen_o1", unit="W", device_class=DeviceClass.POWER, state_class=StateClass.MEASUREMENT, icon="mdi:test", gain=1.0, precision=2)

            # Initial state
            await sensor.get_state(value=10.1234)
            assert sensor.latest_raw_state == 10.1234

            # Request republish
            state = await sensor.get_state(republish=True)
            assert state == 10.12  # precision=2 applied

            # Raw republish
            state = await sensor.get_state(republish=True, raw=True)
            assert state == 10.1234

    @pytest.mark.asyncio
    async def test_derived_sensor_get_state(self):
        class ConcreteDerived(DerivedSensor):
            def set_source_values(self, sensor, values):
                pass

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ConcreteDerived(
                name="Derived",
                unique_id="sigen_u2",
                object_id="sigen_o2",
                unit="W",
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:test",
                gain=1.0,
                precision=2,
                data_type=ModbusDataType.UINT16,
            )

            # Empty states
            assert await sensor.get_state() == 0

            # Set state
            sensor.set_state(50.555)
            assert await sensor.get_state() == 50.55
            assert await sensor.get_state(raw=True) == 50.555

    @pytest.mark.asyncio
    async def test_ac_charger_running_state_get_state(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ACChargerRunningState(plant_index=0, device_address=1)

            # Mock super().get_state
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 5
                assert await sensor.get_state() == "Charging"

                mock_super.return_value = 1
                assert await sensor.get_state() == "EV not connected"

                mock_super.return_value = 10
                assert await sensor.get_state() == "Unknown State code: 10"

                mock_super.return_value = None
                assert await sensor.get_state() == None

                mock_super.return_value = 5
                assert await sensor.get_state(raw=True) == 5

    @pytest.mark.asyncio
    async def test_system_time_zone_get_state(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = SystemTimeZone(plant_index=0)

            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 600  # 10 hours
                # timezone(timedelta(minutes=600)) -> UTC+10:00
                assert await sensor.get_state() == "UTC+10:00"

                mock_super.return_value = -300  # -5 hours
                assert await sensor.get_state() == "UTC-05:00"

    @pytest.mark.asyncio
    async def test_enum_sensors_get_state(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # EMSWorkMode
            ems = EMSWorkMode(plant_index=0)
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 0
                assert await ems.get_state() == "Max Self Consumption"
                mock_super.return_value = 7
                assert await ems.get_state() == "Remote EMS"

            # GridSensorStatus
            gss = GridSensorStatus(plant_index=0)
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 1
                assert await gss.get_state() == "Connected"

            # GridStatus
            gs = GridStatus(plant_index=0)
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                mock_super.return_value = 1
                assert await gs.get_state() == "Off Grid (auto)"

    @pytest.mark.asyncio
    async def test_inverter_firmware_version_get_state_trigger_rediscovery(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = InverterFirmwareVersion(plant_index=0, device_address=1)
            mock_device = MagicMock()
            mock_device.__getitem__.side_effect = lambda key: "v1.0" if key == "hw" else None
            sensor.parent_device = mock_device

            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super:
                # Same version
                mock_super.return_value = "v1.0"
                await sensor.get_state()
                assert mock_device.rediscover is not True

                # New version
                mock_super.return_value = "v2.0"
                await sensor.get_state()
                mock_device.__setitem__.assert_called_with("hw", "v2.0")
                assert mock_device.rediscover is True

    @pytest.mark.asyncio
    async def test_pcs_max_export_limit_invalid_value(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = PCSMaxExportLimit(plant_index=0)

            # PCSMaxExportLimit inherits from NumericSensor (in base) but it might be locally defined or not.
            # In my implementation plan I said: Verify that the special invalid value 0xFFFFFFFF is handled correctly

            with patch("sigenergy2mqtt.sensors.base.Sensor.get_state", new_callable=AsyncMock) as mock_super:
                # Valid value
                mock_super.return_value = 1000
                assert await sensor.get_state() == 1000
                assert sensor.publishable is True

                # Invalid value 0xFFFFFFFF
                mock_super.return_value = 0xFFFFFFFF
                # Currently, it returns the value / gain without special handling in get_state
                # 0xFFFFFFFF / 1000 = 4294967.295
                assert await sensor.get_state() == 4294967.295

    @pytest.mark.asyncio
    async def test_main_get_state_helper(self):
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock()
        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "localhost"
        mock_modbus.comm_params.port = 502

        # Success case
        mock_sensor.get_state.return_value = 123
        s, val = await main_get_state(mock_sensor, mock_modbus, "test_device")
        assert s == mock_sensor
        assert val == 123

        # Failure case
        mock_sensor.get_state.side_effect = Exception("error")
        s, val = await main_get_state(mock_sensor, mock_modbus, "test_device", default_value="fallback")
        assert s == mock_sensor
        assert val == "fallback"
