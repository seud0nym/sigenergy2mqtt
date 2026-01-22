import time
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.metrics.metrics_sensors import (
    MetricsSensor,
    ModbusActiveLocks,
    ModbusCacheHits,
    ModbusReadErrors,
    ModbusReadMax,
    ModbusReadMean,
    ModbusReadMin,
    ModbusReadsPerSecond,
    ModbusWriteErrors,
    ModbusWriteMax,
    ModbusWriteMean,
    ModbusWriteMin,
    ProtocolPublished,
    ProtocolVersion,
    Started,
)


@pytest.fixture(autouse=True)
def mock_config():
    with patch("sigenergy2mqtt.config.Config.home_assistant.unique_id_prefix", "sigen"), patch("sigenergy2mqtt.config.Config.home_assistant.entity_id_prefix", "sigenergy2mqtt"):
        yield


class TestMetricsSensor:
    def test_init(self):
        sensor = MetricsSensor(name="Test Sensor", unique_id="sigen_test_id", object_id="sigenergy2mqtt_test_object", unit="test_unit", scan_interval=10)
        assert sensor["name"] == "Test Sensor"
        assert sensor["unique_id"] == "sigen_test_id"
        assert sensor["object_id"] == "sigenergy2mqtt_test_object"
        assert sensor["unit_of_measurement"] == "test_unit"
        assert sensor.scan_interval == 10
        assert sensor["enabled_by_default"] is True

    @pytest.mark.asyncio
    async def test_update_internal_state_raises_not_implemented(self):
        sensor = MetricsSensor("name", "sigen_uid", "sigenergy2mqtt_oid")
        with pytest.raises(NotImplementedError):
            await sensor._update_internal_state()

    def test_configure_mqtt_topics(self):
        sensor = MetricsSensor("name", "sigen_uid", "sigenergy2mqtt_test_object")
        base = sensor.configure_mqtt_topics("device_id")
        assert base == "sigenergy2mqtt/metrics"
        assert sensor["state_topic"] == "sigenergy2mqtt/metrics/test_object"
        assert sensor["availability_topic"] == "sigenergy2mqtt/status"

    def test_publish_attributes(self):
        sensor = MetricsSensor("name", "sigen_uid", "sigenergy2mqtt_oid")
        # Should do nothing
        sensor.publish_attributes(None)


class TestModbusCacheHits:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusCacheHits()
        Metrics.sigenergy2mqtt_modbus_cache_hit_percentage = 45.5
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 45.5


class TestModbusReadsPerSecond:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusReadsPerSecond()
        Metrics.sigenergy2mqtt_modbus_reads = 100
        Metrics._started = time.monotonic() - 10
        await sensor._update_internal_state()
        # Roughly 10 reads per second
        assert 9.0 <= sensor.latest_raw_state <= 11.0


class TestModbusReadErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusReadErrors()
        Metrics.sigenergy2mqtt_modbus_read_errors = 5
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 5


class TestModbusReadMax:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusReadMax()
        Metrics.sigenergy2mqtt_modbus_read_max = 123.456
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 123.456

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self):
        sensor = ModbusReadMax()
        Metrics.sigenergy2mqtt_modbus_read_max = float("inf")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0


class TestModbusReadMean:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusReadMean()
        Metrics.sigenergy2mqtt_modbus_read_mean = 50.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 50.0


class TestModbusReadMin:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusReadMin()
        Metrics.sigenergy2mqtt_modbus_read_min = 10.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 10.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self):
        sensor = ModbusReadMin()
        Metrics.sigenergy2mqtt_modbus_read_min = float("inf")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0


class TestModbusWriteErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusWriteErrors()
        Metrics.sigenergy2mqtt_modbus_write_errors = 3
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 3


class TestModbusWriteMax:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusWriteMax()
        Metrics.sigenergy2mqtt_modbus_write_max = 200.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 200.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self):
        sensor = ModbusWriteMax()
        Metrics.sigenergy2mqtt_modbus_write_max = float("inf")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0


class TestModbusWriteMean:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusWriteMean()
        Metrics.sigenergy2mqtt_modbus_write_mean = 100.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 100.0


class TestModbusWriteMin:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ModbusWriteMin()
        Metrics.sigenergy2mqtt_modbus_write_min = 1.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 1.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self):
        sensor = ModbusWriteMin()
        Metrics.sigenergy2mqtt_modbus_write_min = float("inf")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0


class TestModbusActiveLocks:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        with patch("sigenergy2mqtt.modbus.ModbusLockFactory.get_waiter_count", return_value=5):
            sensor = ModbusActiveLocks()
            await sensor._update_internal_state()
            assert sensor.latest_raw_state == 5


class TestStarted:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = Started()
        Metrics.sigenergy2mqtt_started = "2023-01-01T00:00:00"
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == "2023-01-01T00:00:00"


class TestProtocolVersion:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ProtocolVersion(Protocol.V1_8)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == str(Protocol.V1_8.value)


class TestProtocolPublished:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        with patch("sigenergy2mqtt.metrics.metrics_sensors.ProtocolApplies", return_value="2024-08-05"):
            sensor = ProtocolPublished()
            sensor.protocol_version = Protocol.V1_8
            await sensor._update_internal_state()
            assert sensor.latest_raw_state == "2024-08-05"
