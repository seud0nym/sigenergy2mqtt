import time
import asyncio
from unittest.mock import MagicMock, patch
import pytest
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.metrics.metrics_sensors import (
    InfluxDBWrites,
    InfluxDBWriteErrors,
    InfluxDBWriteMax,
    InfluxDBWriteMean,
    InfluxDBQueries,
    InfluxDBQueryErrors,
    InfluxDBRetries,
    InfluxDBThroughput,
    ResetMetrics,
    MetricsSensor,
    Started,
    ModbusReadsPerSecond,
)
from sigenergy2mqtt.config import active_config

@pytest.fixture(autouse=True)
def mock_config():
    with patch("sigenergy2mqtt.config.active_config.home_assistant.unique_id_prefix", "sigen"), \
         patch("sigenergy2mqtt.config.active_config.home_assistant.entity_id_prefix", "sigenergy2mqtt"), \
         patch("sigenergy2mqtt.config.active_config.influxdb.enabled", True):
        yield

class TestMetricsSensorsExtended:
    @pytest.mark.asyncio
    async def test_metrics_sensor_debug_logging(self, caplog):
        sensor = MetricsSensor("name", "sigen_uid", "sigenergy2mqtt_test_object")
        sensor.debug_logging = True
        with caplog.at_level("DEBUG"):
            sensor.configure_mqtt_topics("device_id")
            assert "Configured MQTT topics" in caplog.text

    @pytest.mark.asyncio
    async def test_modbus_reads_per_second_zero_elapsed(self):
        sensor = ModbusReadsPerSecond()
        Metrics.sigenergy2mqtt_modbus_register_reads = 100
        Metrics._started = time.monotonic() + 10 # Future start
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0

    @pytest.mark.asyncio
    async def test_started_sensor_none(self):
        sensor = Started()
        Metrics.sigenergy2mqtt_started = None
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == ""

    @pytest.mark.asyncio
    async def test_influxdb_writes(self):
        sensor = InfluxDBWrites()
        Metrics.sigenergy2mqtt_influxdb_writes = 10
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 10
        assert sensor.publishable is True

    @pytest.mark.asyncio
    async def test_influxdb_write_errors(self):
        sensor = InfluxDBWriteErrors()
        Metrics.sigenergy2mqtt_influxdb_write_errors = 2
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 2

    @pytest.mark.asyncio
    async def test_influxdb_write_max(self):
        sensor = InfluxDBWriteMax()
        Metrics.sigenergy2mqtt_influxdb_write_max = 50.5
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 50.5

    @pytest.mark.asyncio
    async def test_influxdb_write_mean(self):
        sensor = InfluxDBWriteMean()
        Metrics.sigenergy2mqtt_influxdb_write_mean = 25.0
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 25.0

    @pytest.mark.asyncio
    async def test_influxdb_queries(self):
        sensor = InfluxDBQueries()
        Metrics.sigenergy2mqtt_influxdb_queries = 5
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 5

    @pytest.mark.asyncio
    async def test_influxdb_query_errors(self):
        sensor = InfluxDBQueryErrors()
        Metrics.sigenergy2mqtt_influxdb_query_errors = 1
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 1

    @pytest.mark.asyncio
    async def test_influxdb_retries(self):
        sensor = InfluxDBRetries()
        Metrics.sigenergy2mqtt_influxdb_retries = 3
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 3

    @pytest.mark.asyncio
    async def test_influxdb_throughput(self):
        sensor = InfluxDBThroughput()
        Metrics.sigenergy2mqtt_influxdb_batch_total = 1000
        Metrics._started = time.monotonic() - 10
        await sensor._update_internal_state()
        assert 90.0 <= sensor.latest_raw_state <= 110.0

    @pytest.mark.asyncio
    async def test_influxdb_throughput_zero_elapsed(self):
        sensor = InfluxDBThroughput()
        Metrics._started = time.monotonic() + 10
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 0.0

    @pytest.mark.asyncio
    async def test_mqtt_publish_failures(self):
        # Hit 97, 106-107
        sensor = InfluxDBWrites() # Wait, I should use MQTTPublishFailures
        from sigenergy2mqtt.metrics.metrics_sensors import MQTTPublishFailures
        sensor = MQTTPublishFailures()
        Metrics.sigenergy2mqtt_mqtt_publish_failures = 5
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 5

    @pytest.mark.asyncio
    async def test_mqtt_physical_publishes(self):
        # Hit 114, 124-125
        from sigenergy2mqtt.metrics.metrics_sensors import MQTTPhysicalPublishes
        sensor = MQTTPhysicalPublishes()
        Metrics.sigenergy2mqtt_mqtt_physical_publish_percentage = 99.9
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 99.9

class TestResetMetricsCoverage:

    def test_reset_metrics_init(self):
        sensor = ResetMetrics()
        assert sensor["name"] == "Reset Metrics"
        assert sensor.unique_id == "sigen_metrics_reset"

    def test_reset_metrics_configure_topics(self, caplog):
        sensor = ResetMetrics()
        sensor.debug_logging = True
        with caplog.at_level("DEBUG"):
            sensor.configure_mqtt_topics("dev1")
            assert "Configured MQTT topics" in caplog.text
        assert sensor[ "command_topic"] == "sigenergy2mqtt/metrics/metrics_reset/set"

    def test_reset_metrics_get_discovery(self, caplog):
        sensor = ResetMetrics()
        sensor.debug_logging = True
        with caplog.at_level("DEBUG"):
            discovery = sensor.get_discovery_components()
            assert "Discovered components" in caplog.text
        assert sensor.unique_id in discovery
        assert discovery[sensor.unique_id]["payload_press"] == "reset"

    def test_reset_metrics_publish_attributes(self):
        # Hit 669
        sensor = ResetMetrics()
        sensor.publish_attributes(None)


    @pytest.mark.asyncio
    async def test_reset_metrics_set_value_success(self):
        sensor = ResetMetrics()
        with patch.object(Metrics, "reset") as mock_reset:
            res = await sensor.set_value(None, None, "reset", "source", None)
            assert res is True
            mock_reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_metrics_set_value_ignored(self):
        sensor = ResetMetrics()
        res = await sensor.set_value(None, None, "wrong", "source", None)
        assert res is False

    @pytest.mark.asyncio
    async def test_reset_metrics_value_is_valid(self):
        sensor = ResetMetrics()
        assert await sensor.value_is_valid(None, "reset") is True
        assert await sensor.value_is_valid(None, "other") is False
