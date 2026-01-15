import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import DerivedSensor, InputType, NumericSensor, ObservableMixin, ReadOnlySensor, Sensor, SubstituteMixin


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
            sensor.set_latest_state(150.0)
            state = await sensor.get_state(republish=True)
            assert state == 100.0
