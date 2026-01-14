import asyncio
import datetime
import sys
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

from pymodbus.client import AsyncModbusTcpClient as ModbusClient  # noqa: E402

from sigenergy2mqtt.config import Protocol  # noqa: E402
from sigenergy2mqtt.sensors.base import (  # noqa: E402
    EnergyDailyAccumulationSensor,
    EnergyLifetimeAccumulationSensor,
    InputType,
    ModbusSensorMixin,
    NumericSensor,
    ReadOnlySensor,
    SelectSensor,
    Sensor,
    TimestampSensor,
)
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass  # noqa: E402

# Mock Metrics and MetricsService to avoid background thread issues
mock_metrics = MagicMock()
mock_metrics.modbus_read = AsyncMock()
mock_metrics.modbus_write = AsyncMock()
sys.modules["sigenergy2mqtt.metrics.metrics"] = mock_metrics


@pytest.fixture(autouse=True)
def mock_config_all():
    with patch("sigenergy2mqtt.sensors.base.Config") as mock_config:
        mock_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_config.home_assistant.enabled = True
        mock_config.sensor_overrides = {}
        mock_config.persistent_state_path = "."
        mock_config.devices = []
        yield mock_config


class TestModbusSensor:
    def test_modbus_sensor_init_validation(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # Invalid device address
            with pytest.raises(AssertionError, match="Invalid device address"):
                ModbusSensorMixin(
                    InputType.HOLDING,
                    0,
                    0,
                    30000,
                    1,
                    name="N",
                    unique_id="sigenergy_o",
                    object_id="sigenergy_o",
                    unit="U",
                    device_class=None,
                    state_class=None,
                    icon="mdi:power",
                    gain=1.0,
                    precision=0,
                    protocol_version=Protocol.V2_4,
                )
            # Invalid address
            with pytest.raises(AssertionError, match="Invalid address"):
                ModbusSensorMixin(
                    InputType.HOLDING,
                    0,
                    1,
                    29999,
                    1,
                    name="N",
                    unique_id="sigenergy_o",
                    object_id="sigenergy_o",
                    unit="U",
                    device_class=None,
                    state_class=None,
                    icon="mdi:power",
                    gain=1.0,
                    precision=0,
                    protocol_version=Protocol.V2_4,
                )


class TestReadOnlySensor:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = ReadOnlySensor(
                name="Test RO",
                object_id="sigenergy_test_ro",
                input_type=InputType.HOLDING,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusClient.DATATYPE.UINT16,
                scan_interval=10,
                unit="W",
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )

            mock_modbus = AsyncMock()
            mock_modbus.convert_from_registers = MagicMock(return_value=123)

            mock_rr = MagicMock()
            mock_rr.isError.return_value = False
            mock_rr.registers = [123]
            mock_modbus.read_holding_registers.return_value = mock_rr

            result = await sensor._update_internal_state(modbus_client=mock_modbus)

            assert result is True
            assert sensor.latest_raw_state == 123


class TestTimestampSensor:
    @pytest.mark.asyncio
    async def test_get_state_timestamp(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TimestampSensor("TS", "sigenergy_ts", InputType.INPUT, 0, 1, 30005, 10, Protocol.V2_4)

            ts = 1700000000  # 2023-11-14 22:13:20 UTC
            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super_get:
                mock_super_get.return_value = ts

                state = await sensor.get_state()
                expected_dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()
                assert state == expected_dt

    def test_state2raw_timestamp(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = TimestampSensor("TS", "sigenergy_ts", InputType.INPUT, 0, 1, 30005, 10, Protocol.V2_4)
            iso_str = "2023-11-14T22:13:20+00:00"
            raw = sensor.state2raw(iso_str)
            assert raw == 1700000000


class TestNumericSensor:
    @pytest.mark.asyncio
    async def test_numeric_sensor_validation(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            sensor = NumericSensor(
                None,
                "Num",
                "sigenergy_num",
                InputType.HOLDING,
                0,
                1,
                30100,
                1,
                ModbusClient.DATATYPE.UINT16,
                10,
                "W",
                DeviceClass.POWER,
                StateClass.MEASUREMENT,
                "mdi:power",
                1.0,
                2,
                Protocol.V2_4,
                minimum=0,
                maximum=100,
            )

            assert await sensor.value_is_valid(None, 50) is True
            assert await sensor.value_is_valid(None, -1) is False
            assert await sensor.value_is_valid(None, 101) is False


class TestSelectSensor:
    @pytest.mark.asyncio
    async def test_select_sensor_logic(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            options = ["A", "B", "C"]
            sensor = SelectSensor(None, "Sel", "sigenergy_sel", 0, 1, 30200, 10, options, Protocol.V2_4)

            with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_super_get:
                mock_super_get.return_value = 1
                assert await sensor.get_state() == "B"

            assert await sensor.value_is_valid(None, "B") is True
            assert await sensor.value_is_valid(None, "D") is False


class TestEnergyAccumulationSensors:
    @pytest.mark.asyncio
    async def test_energy_lifetime_accumulation(self, tmp_path):
        with patch("sigenergy2mqtt.sensors.base.Config.persistent_state_path", str(tmp_path)):
            source = MagicMock(spec=Sensor)
            source.unique_id = "source_uid"

            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                sensor = EnergyLifetimeAccumulationSensor("Lifetime", "sigenergy_lifetime", "sigenergy_lifetime", source)

                sensor._current_total = 100.0
                values = [(1000.0, 10.0), (1100.0, 20.0)]
                source.latest_interval = 100.0

                with patch("asyncio.run_coroutine_threadsafe"):
                    sensor._persist_current_total = AsyncMock()
                    result = sensor.set_source_values(source, values)
                    assert result is True
                    assert pytest.approx(sensor._current_total) == 100.4166666

    @pytest.mark.asyncio
    async def test_energy_daily_accumulation_midnight(self, tmp_path):
        with patch("sigenergy2mqtt.sensors.base.Config.persistent_state_path", str(tmp_path)):
            source = ReadOnlySensor(
                "Source", "sigenergy_source", InputType.HOLDING, 0, 1, 30001, 1, ModbusClient.DATATYPE.UINT32, 10, "kWh", DeviceClass.ENERGY, StateClass.TOTAL_INCREASING, "mdi:energy", 1.0, 2, Protocol.V2_4
            )

            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                time_day1 = 1000000.0
                time_day2 = 1100000.0

                sensor = EnergyDailyAccumulationSensor("Daily", "sigenergy_daily", "sigenergy_daily", source)
                sensor._state_at_midnight = 1000.0

                values = [(time_day1, 1100.0), (time_day2, 1105.0)]

                mock_t1 = MagicMock()
                mock_t1.tm_year, mock_t1.tm_mon, mock_t1.tm_mday = 2023, 11, 14
                mock_t2 = MagicMock()
                mock_t2.tm_year, mock_t2.tm_mon, mock_t2.tm_mday = 2023, 11, 15

                def mock_localtime(t):
                    if t == time_day1:
                        return mock_t1
                    return mock_t2

                def mock_run_coro(coro, loop):
                    asyncio.create_task(coro)
                    return MagicMock()

                with patch("sigenergy2mqtt.sensors.base.time.localtime", side_effect=mock_localtime):
                    with patch("asyncio.run_coroutine_threadsafe", side_effect=mock_run_coro):
                        sensor.set_source_values(source, values)
                        await asyncio.sleep(0.1)
                        assert sensor._state_at_midnight == 1105.0
                        # Call again to verify state_now recalculation
                        sensor.set_source_values(source, [values[-1]])
                        assert sensor._state_now == 0.0
