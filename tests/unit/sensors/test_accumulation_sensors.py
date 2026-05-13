from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, StateClass
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import ResettableAccumulationSensor, Sensor


@pytest.fixture(autouse=True)
def mock_state_store():
    with patch("sigenergy2mqtt.sensors.base.accumulation.state_store") as mock:
        mock.load_sync.return_value = None
        yield mock


class TestAccumulationLogic:
    @pytest.mark.asyncio
    async def test_riemann_sum_accumulation(self):
        """Test the basic Riemann sum (trapezoidal) accumulation logic."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"
        source.log_identity = "source"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ResettableAccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            # Initial state should be 0.0
            assert sensor._current_total == 0.0

            # First reading (needs at least 2 for trapezoidal rule)
            source.latest_interval = None
            source.state_count = 1
            sensor.set_source_values(source)
            assert sensor._current_total == 0.0

            # Second reading
            # Interval = 3600s (1 hour)
            # Power: 10W -> 20W
            # Avg Power = 15W
            # Energy = 15W * 1h = 15Wh = 0.015kWh (if gain=1.0 and unit is kWh? wait, gain applies to raw values)
            # Actually, the logic is: increase = 0.5 * (prev + curr) * interval_hours
            # If source is in Watts and we want kWh, we need to handle units/gain correctly.
            # In the code: increase = 0.5 * (previous + current) * interval_hours
            # new_total = self._current_total + increase

            source.latest_interval = 3600.0
            source.state_count = 2
            source.previous_raw_state = 10.0
            source.latest_raw_state = 20.0

            # Mock persistence to avoid background thread issues
            with patch.object(sensor, "run_persistence_coroutine", side_effect=lambda coro: coro.close()):
                result = sensor.set_source_values(source)
                assert result is True
                # 0.5 * (10 + 20) * 1.0 = 15.0
                assert sensor._current_total == 15.0
                assert sensor.latest_raw_state == 15.0

    @pytest.mark.asyncio
    async def test_negative_power_ignored(self):
        """Test that negative power readings are treated as zero."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ResettableAccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            source.latest_interval = 3600.0
            source.state_count = 2
            source.previous_raw_state = -10.0
            source.latest_raw_state = -20.0

            with patch.object(sensor, "run_persistence_coroutine", side_effect=lambda coro: coro.close()):
                sensor.set_source_values(source)
                # 0.5 * (0 + 0) * 1.0 = 0.0
                assert sensor._current_total == 0.0

    @pytest.mark.asyncio
    async def test_reset_functionality(self):
        """Test that the sensor can be reset via MQTT notify."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ResettableAccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            sensor._current_total = 50.0

            # Mocking MQTT handler and client
            mock_handler = MagicMock()
            mock_mqtt_client = MagicMock()

            # Reset to 10.0
            # notify(self, modbus_client, mqtt_client, value, source, handler)
            result = await sensor.notify(None, mock_mqtt_client, 10.0, sensor._reset_topic, mock_handler)

            assert result is True
            assert sensor._current_total == 10.0
            assert sensor.latest_raw_state == 10.0
            assert sensor.force_publish is True

    @pytest.mark.asyncio
    async def test_persistence_loading(self, mock_state_store):
        """Test that the sensor loads its state from persistence on init."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"

        mock_state_store.load_sync.return_value = "123.45"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ResettableAccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            assert sensor._current_total == 123.45
            assert sensor.latest_raw_state == 123.45


class TestAccumulationSensor:
    @pytest.mark.asyncio
    async def test_accumulation_sensor_no_reset_topic(self):
        """Test that AccumulationSensor doesn't have reset capability."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.sensors.base import AccumulationSensor

            sensor = AccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            assert not hasattr(sensor, "_reset_topic")
            assert "reset" not in sensor.get_discovery_components()

            # Should not be observable
            from sigenergy2mqtt.sensors.base.mixins import ObservableMixin

            assert not isinstance(sensor, ObservableMixin)

    @pytest.mark.asyncio
    async def test_accumulation_sensor_logic(self):
        """Test accumulation logic in the base AccumulationSensor."""
        source = MagicMock(spec=Sensor)
        source.unique_id = "source_uid"

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.sensors.base import AccumulationSensor

            sensor = AccumulationSensor(
                name="Accumulator",
                unique_id="sigen_accumulator_uid",
                object_id="sigen_accumulator_oid",
                source=source,
                data_type=ModbusDataType.UINT32,
                unit="kWh",
                device_class=DeviceClass.ENERGY,
                state_class=StateClass.TOTAL_INCREASING,
                icon="mdi:battery",
                gain=1.0,
                precision=2,
            )

            source.latest_interval = 3600.0
            source.state_count = 2
            source.previous_raw_state = 10.0
            source.latest_raw_state = 20.0

            with patch.object(sensor, "run_persistence_coroutine", side_effect=lambda coro: coro.close()):
                sensor.set_source_values(source)
                assert sensor._current_total == 15.0
                assert sensor.latest_raw_state == 15.0
