import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import (
    DerivedSensor,
    InputType,
    ModbusSensorMixin,
    NumericSensor,
    ObservableMixin,
    ReadOnlySensor,
    ResettableAccumulationSensor,
    RunningStateSensor,
    Sensor,
    SubstituteMixin,
    SwitchSensor,
)


class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return True


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.sensors.base.Config") as mock:
        mock.home_assistant.entity_id_prefix = "sigenergy"
        mock.home_assistant.unique_id_prefix = "sigenergy"
        mock.home_assistant.discovery_prefix = "homeassistant"
        mock.home_assistant.enabled = True
        mock.home_assistant.use_simplified_topics = False
        mock.home_assistant.edit_percentage_with_box = False
        mock.home_assistant.enabled_by_default = True
        mock.sensor_overrides = {}
        mock.clean = False
        mock.persistent_state_path = "/tmp"
        yield mock


class TestBaseCoverage:
    def test_apply_sensor_overrides_regex(self, mock_config):
        mock_config.sensor_overrides = {"Concr.*": {"gain": 10.0, "precision": 3}}
        sensor = ConcreteSensor(
            name="Test", unique_id="sigenergy_test", object_id="sigenergy_test", unit="W", device_class=None, state_class=None, icon="mdi:test", gain=1.0, precision=2, protocol_version=Protocol.V1_8
        )
        sensor.apply_sensor_overrides(None)
        assert sensor.gain == 10.0
        assert sensor.precision == 3

    def test_get_discovery_components_basic(self, mock_config):
        sensor = ConcreteSensor(
            name="Test", unique_id="sigenergy_test", object_id="sigenergy_test", unit="W", device_class=None, state_class=None, icon="mdi:test", gain=1.0, precision=2, protocol_version=Protocol.V1_8
        )
        components = sensor.get_discovery_components()
        assert "sigenergy_test" in components
        assert components["sigenergy_test"]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_publish_not_publishable(self, mock_config):
        sensor = ReadOnlySensor(
            name="Test",
            object_id="sigenergy_test",
            input_type=InputType.INPUT,
            plant_index=0,
            device_address=1,
            address=30000,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=10,
            unit="V",
            device_class=None,
            state_class=None,
            icon="mdi:meter",
            gain=1.0,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        sensor.publishable = False
        mqtt_client = MagicMock()
        modbus_client = MagicMock()
        published = await sensor.publish(mqtt_client, modbus_client)
        assert published is False
        mqtt_client.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_numeric_sensor_precision_zero(self, mock_config):
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigenergy_test",
            input_type=InputType.INPUT,
            plant_index=0,
            device_address=1,
            address=30000,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=10,
            unit="V",
            device_class=None,
            state_class=None,
            icon="mdi:meter",
            gain=1.0,
            precision=0,
            protocol_version=Protocol.V1_8,
            maximum=200.0,
        )
        with patch.object(NumericSensor, "_update_internal_state", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True
            sensor.set_latest_state(123.7)
            state = await sensor.get_state(republish=True)
            assert state == 124
            assert isinstance(state, int)

    @pytest.mark.asyncio
    async def test_numeric_sensor_max_adjustment(self, mock_config):
        sensor = NumericSensor(
            availability_control_sensor=None,
            name="Test",
            object_id="sigenergy_test",
            input_type=InputType.INPUT,
            plant_index=0,
            device_address=1,
            address=30000,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=10,
            unit="V",
            device_class=None,
            state_class=None,
            icon="mdi:meter",
            gain=1.0,
            precision=1,
            protocol_version=Protocol.V1_8,
            maximum=100.0,
        )
        with patch.object(NumericSensor, "_update_internal_state", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True

            from sigenergy2mqtt.sensors.sanity_check import SanityCheckException

            with pytest.raises(SanityCheckException):
                sensor.set_latest_state(150.0)


class TestModbusSensorMixinErrorHandling:
    class DummyModbus(ModbusSensorMixin, Sensor):
        async def _update_internal_state(self, **kw):
            return True

    def test_check_register_response_none(self):
        sensor = self.DummyModbus(
            InputType.HOLDING,
            0,
            1,
            30001,
            1,
            name="N",
            unique_id="sigenergy_u",
            object_id="sigenergy_o",
            unit="U",
            device_class=None,
            state_class=None,
            icon="mdi:i",
            gain=1.0,
            precision=0,
            protocol_version=Protocol.V2_4,
        )
        assert sensor._check_register_response(None, "test") is False

    def test_check_register_response_errors(self):
        sensor = self.DummyModbus(
            InputType.HOLDING,
            0,
            1,
            30001,
            1,
            name="N",
            unique_id="sigenergy_u",
            object_id="sigenergy_o",
            unit="U",
            device_class=None,
            state_class=None,
            icon="mdi:i",
            gain=1.0,
            precision=0,
            protocol_version=Protocol.V2_4,
        )
        resp = MagicMock()
        resp.isError.return_value = True
        resp.exception_code = 1
        with pytest.raises(Exception, match="0x01 ILLEGAL FUNCTION"):
            sensor._check_register_response(resp, "test")


class TestAccumulationSensorPersistence:
    @pytest.mark.asyncio
    async def test_resettable_persistence_load_save(self, tmp_path):
        from sigenergy2mqtt.sensors.const import DeviceClass, StateClass

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src"
        with patch("sigenergy2mqtt.sensors.base.Config.persistent_state_path", str(tmp_path)):
            sensor = ResettableAccumulationSensor(
                "Acc",
                "sigenergy_acc_uid",
                "sigenergy_acc_obj",
                source,
                ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
            )
            await sensor._persist_current_total(123.45)

            sensor2 = ResettableAccumulationSensor(
                "Acc2",
                "sigenergy_acc_uid",
                "sigenergy_acc_obj",
                source,
                ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
            )
            assert sensor2._current_total == 123.45

    def test_resettable_discovery_components(self):
        from sigenergy2mqtt.sensors.const import DeviceClass, StateClass

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src"
        sensor = ResettableAccumulationSensor(
            "Acc",
            "sigenergy_acc_uid",
            "sigenergy_acc_obj",
            source,
            ModbusDataType.UINT32,
            unit="kWh",
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:flash",
            gain=1.0,
            precision=2,
        )
        comps = sensor.get_discovery_components()
        assert "sigenergy_acc_uid" in comps
        assert "unique_id" in comps["sigenergy_acc_uid"]


class TestSpecializedSensors:
    def test_switch_sensor_logic(self):
        from sigenergy2mqtt.sensors.base import SwitchSensor

        # availability_control_sensor, name, object_id, plant_index, device_address, address, scan_interval, protocol_version
        s = SwitchSensor(None, "Switch", "sigenergy_sw", 0, 1, 30005, 10, Protocol.V2_4)
        assert s.state2raw(1) == 1
        assert s.state2raw("1") == 1

    @pytest.mark.asyncio
    async def test_numeric_sensor_logic(self):
        from sigenergy2mqtt.sensors.base import NumericSensor
        from sigenergy2mqtt.sensors.const import DeviceClass, StateClass

        s = NumericSensor(
            None, "Num", "sigenergy_n", InputType.HOLDING, 0, 1, 30006, 1, ModbusDataType.UINT16, 10, "W", DeviceClass.POWER, StateClass.MEASUREMENT, "mdi:p", 1.0, 2, Protocol.V2_4, minimum=0, maximum=100
        )
        assert await s.value_is_valid(None, 50) is True
        assert await s.value_is_valid(None, 150) is False

    @pytest.mark.asyncio
    async def test_running_state_sensor(self):
        from sigenergy2mqtt.sensors.base import RunningStateSensor

        # name, object_id, plant_index, device_address, address, protocol_version
        s = RunningStateSensor("State", "sigenergy_state", 0, 1, 30007, Protocol.V2_4)
        client = AsyncMock()
        client.read_input_registers.return_value = MagicMock(isError=lambda: False, registers=[2])
        # Use MagicMock for synchronous method to avoid coroutine issues
        client.convert_from_registers = MagicMock(return_value=2)
        assert await s._update_internal_state(modbus_client=client) is True
        assert await s.get_state(modbus_client=client) == "Fault"
