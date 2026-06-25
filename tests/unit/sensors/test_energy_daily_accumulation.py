import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, StateClass, UnitOfEnergy
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.persistence import Category
from sigenergy2mqtt.sensors.base import ReadOnlySensor, Sensor
from sigenergy2mqtt.sensors.base.accumulation import EnergyDailyAccumulationSensor


@pytest.fixture(autouse=True)
def mock_state_store():
    with patch("sigenergy2mqtt.sensors.base.accumulation.state_store") as mock:
        mock.load_sync.return_value = None
        yield mock


@pytest.fixture(autouse=True)
def sigen_config():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    with _swap_active_config(cfg):
        yield cfg


@pytest.fixture
def source_sensor():
    source = MagicMock(spec=ReadOnlySensor)
    source.unique_id = "sigen_test_source_uid"
    source.object_id = "sigen_test_source_oid"
    source.data_type = ModbusDataType.UINT32
    source.unit = UnitOfEnergy.KILO_WATT_HOUR
    source.device_class = DeviceClass.ENERGY
    source.state_class = StateClass.TOTAL_INCREASING
    source.__getitem__.return_value = "mdi:flash"
    source.gain = 1.0
    source.precision = 2
    return source


class TestEnergyDailyAccumulationSensor:
    def test_init(self, source_sensor):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )
            assert sensor._state_at_midnight is None
            assert sensor._midnight_persistence_key == "sigen_test_source_uid.atmidnight"

    def test_on_added_to_device_loads_midnight_state(self, source_sensor, mock_state_store):
        mock_state_store.load_sync.return_value = "100.5"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            sensor.on_added_to_device()

            mock_state_store.load_sync.assert_any_call(Category.SENSOR, "sigen_test_source_uid.atmidnight", stale_after=timedelta(hours=24))
            assert sensor._state_at_midnight == 100.5

    def test_load_midnight_state_invalid(self, source_sensor, mock_state_store):
        mock_state_store.load_sync.return_value = "invalid"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            sensor._load_midnight_state()
            assert sensor._state_at_midnight is None
            mock_state_store.delete_sync.assert_called_with(Category.SENSOR, "sigen_test_source_uid.atmidnight")

    def test_load_midnight_state_negative(self, source_sensor, mock_state_store):
        mock_state_store.load_sync.return_value = "-10.0"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            sensor._load_midnight_state()
            assert sensor._state_at_midnight is None
            mock_state_store.delete_sync.assert_called_with(Category.SENSOR, "sigen_test_source_uid.atmidnight")

    @pytest.mark.asyncio
    async def test_update_state_at_midnight(self, source_sensor, mock_state_store):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            await sensor._update_state_at_midnight(150.0)
            assert sensor._state_at_midnight == 150.0
            mock_state_store.save_sync.assert_called_with(Category.SENSOR, "sigen_test_source_uid.atmidnight", "150.0")

    @pytest.mark.asyncio
    async def test_notify(self, source_sensor):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            source_sensor.latest_raw_state = 300.0

            mock_mqtt_client = MagicMock()
            mock_handler = MagicMock()

            result = await sensor.notify(None, mock_mqtt_client, 50.0, sensor._reset_topic, mock_handler)

            assert result is True
            assert sensor._state_now == 50.0
            # midnight state = source_raw - new_state = 300.0 - 50.0 = 250.0
            assert sensor._state_at_midnight == 250.0
            assert sensor.latest_raw_state == 50.0

    @pytest.mark.asyncio
    async def test_publish_updates_midnight_state(self, source_sensor):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            source_sensor.latest_raw_state = 200.0

            mock_mqtt_client = MagicMock()

            sensor.configure_mqtt_topics("test_device")

            # Since _state_at_midnight is None, publish should set it to latest_raw
            await sensor.publish(mock_mqtt_client, None)

            assert sensor._state_at_midnight == 200.0

    def test_set_source_values_day_change(self, source_sensor):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            source_sensor.latest_raw_state = 100.0
            source_sensor.state_count = 2

            # Yesterday
            t1 = time.mktime(time.strptime("2026-05-13 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Today
            t2 = time.mktime(time.strptime("2026-05-14 00:01:00", "%Y-%m-%d %H:%M:%S"))

            source_sensor.previous_time = t1
            source_sensor.latest_time = t2

            with patch.object(sensor, "run_persistence_coroutine", side_effect=lambda coro: coro.close()):
                sensor.update_from_source_sensor(source_sensor)

            assert sensor._state_at_midnight == 100.0
            assert sensor._state_now == 0.0

    def test_set_source_values_normal(self, source_sensor):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = EnergyDailyAccumulationSensor(
                name="Daily Energy",
                unique_id="sigen_daily_uid",
                object_id="sigen_daily_oid",
                source=source_sensor,
            )

            # Initially set midnight state
            source_sensor.state_count = 1
            source_sensor.latest_raw_state = 50.0
            sensor.update_from_source_sensor(source_sensor)

            assert sensor._state_at_midnight == 50.0
            assert sensor._state_now == 0.0

            # Normal increase
            source_sensor.latest_raw_state = 70.0
            source_sensor.state_count = 2
            t1 = time.mktime(time.strptime("2026-05-14 10:00:00", "%Y-%m-%d %H:%M:%S"))
            t2 = time.mktime(time.strptime("2026-05-14 10:05:00", "%Y-%m-%d %H:%M:%S"))
            source_sensor.previous_time = t1
            source_sensor.latest_time = t2

            sensor.update_from_source_sensor(source_sensor)

            assert sensor._state_at_midnight == 50.0
            assert sensor._state_now == 20.0
