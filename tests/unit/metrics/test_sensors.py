import time
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.sensors.metrics import (
    MetricsSensor,
    ModbusActiveLocks,
    ModbusCacheHits,
    ModbusPhysicalReads,
    ModbusReadErrors,
    ModbusReadMax,
    ModbusReadMean,
    ModbusReadMin,
    ModbusReadsPerSecond,
    ModbusSkippedErrors,
    ModbusWriteErrors,
    ModbusWriteMax,
    ModbusWriteMean,
    ModbusWriteMin,
    ProtocolPublished,
    ProtocolVersionSensor,
    Started,
    StateStoreLoads,
    StateStoreSaveErrors,
    StateStoreSaveMax,
    StateStoreSaveMean,
    StateStoreSaveMin,
    StateStoreSaves,
)


@pytest.fixture(autouse=True)
def mock_config():
    with patch("sigenergy2mqtt.config.active_config.home_assistant.unique_id_prefix", "sigen"), patch("sigenergy2mqtt.config.active_config.home_assistant.entity_id_prefix", "sigenergy2mqtt"):
        yield


class TestMetricsSensor:
    def test_init(self):
        sensor = MetricsSensor(attribute=None, name="Test Sensor", unique_id="sigen_test_id", object_id="sigenergy2mqtt_test_object", unit="test_unit", scan_interval=10)
        assert sensor["name"] == "Test Sensor"
        assert sensor["unique_id"] == "sigen_test_id"
        assert sensor["object_id"] == "sigenergy2mqtt_test_object"
        assert sensor["unit_of_measurement"] == "test_unit"
        assert sensor.scan_interval == 10
        assert sensor["enabled_by_default"] is True
        assert sensor._attribute is None

    @pytest.mark.asyncio
    async def test_update_internal_state_raises_not_implemented(self):
        sensor = MetricsSensor(None, "name", "sigen_uid", "sigenergy2mqtt_oid")
        with pytest.raises(NotImplementedError):
            await sensor._update_internal_state()

    def test_configure_mqtt_topics(self):
        sensor = MetricsSensor(None, "name", "sigen_uid", "sigenergy2mqtt_test_object")
        base = sensor.configure_mqtt_topics("device_id")
        assert base == "sigenergy2mqtt/metrics/test_object"
        assert sensor["state_topic"] == "sigenergy2mqtt/metrics/test_object"
        assert sensor["availability_topic"] == "sigenergy2mqtt/status"

    def test_publish_attributes(self):
        sensor = MetricsSensor(None, "name", "sigen_uid", "sigenergy2mqtt_oid")
        # Should do nothing
        sensor.publish_attributes(None)


class TestModbusCacheHits:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusCacheHits()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_cache_hit_percentage", 45.5)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 45.5


class TestModbusPhysicalReads:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusPhysicalReads()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_physical_read_percentage", 12.34)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 12.34


class TestModbusReadsPerSecond:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusReadsPerSecond()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_reads", 100)
        monkeypatch.setattr(Metrics, "_started", time.monotonic() - 10)
        await sensor._update_internal_state()
        # Roughly 10 reads per second
        assert 9.0 <= sensor.latest_raw_state <= 11.0


class TestModbusReadErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusReadErrors()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_errors", 5)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 5


class TestModbusReadMax:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusReadMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_max", 123.456)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 123.456

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = ModbusReadMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_max", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestModbusReadMean:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusReadMean()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_mean", 50.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 50.0


class TestModbusReadMin:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusReadMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_min", 10.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 10.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = ModbusReadMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_read_min", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestModbusWriteErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusWriteErrors()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_errors", 3)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 3


class TestModbusWriteMax:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusWriteMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_max", 200.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 200.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = ModbusWriteMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_max", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestModbusWriteMean:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusWriteMean()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_mean", 100.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 100.0


class TestModbusWriteMin:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusWriteMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_min", 1.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 1.0

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = ModbusWriteMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_write_min", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestModbusActiveLocks:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        with patch("sigenergy2mqtt.modbus.ModbusLockFactory.get_waiter_count", return_value=5):
            sensor = ModbusActiveLocks()
            await sensor._update_internal_state()
            assert sensor.latest_raw_state == 5


class TestStarted:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = Started()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_started", "2023-01-01T00:00:00")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == "2023-01-01T00:00:00"


class TestProtocolVersionSensor:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        sensor = ProtocolVersionSensor(ProtocolVersion.V1_8)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == str(ProtocolVersion.V1_8.value)


class TestProtocolPublished:
    @pytest.mark.asyncio
    async def test_update_internal_state(self):
        with patch("sigenergy2mqtt.sensors.metrics.ProtocolApplies", return_value="2024-08-05"):
            sensor = ProtocolPublished(ProtocolVersion.V1_8)
            await sensor._update_internal_state()
            assert sensor.latest_raw_state == "2024-08-05"


class TestModbusSkippedErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = ModbusSkippedErrors()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_modbus_skipped_errors", 7)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 7


class TestStateStoreSaves:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreSaves()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_saves", 42)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 42


class TestStateStoreSaveErrors:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreSaveErrors()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_errors", 3)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 3


class TestStateStoreSaveMax:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreSaveMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_max", 150.5)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 150.5

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = StateStoreSaveMax()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_max", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestStateStoreSaveMean:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreSaveMean()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_mean", 45.0)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 45.0


class TestStateStoreSaveMin:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreSaveMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_min", 12.5)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 12.5

    @pytest.mark.asyncio
    async def test_update_internal_state_inf(self, monkeypatch):
        sensor = StateStoreSaveMin()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_save_min", float("inf"))
        assert await sensor._update_internal_state() is False
        assert sensor.latest_raw_state is None


class TestStateStoreLoads:
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch):
        sensor = StateStoreLoads()
        monkeypatch.setattr(Metrics, "sigenergy2mqtt_state_store_loads", 100)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == 100


from sigenergy2mqtt.sensors.metrics import (
    CloudAuthErrors,
    CloudAvailable,
    CloudConnected,
    CloudConnectionAttempts,
    CloudConnectionErrors,
    CloudConnectionMax,
    CloudConnectionMean,
    CloudConnectionMin,
    CloudConnections,
    CloudConnectionTotal,
    CloudQueries,
    CloudQueryErrors,
    CloudQueryMax,
    CloudQueryMean,
    CloudQueryMin,
    CloudQueryTotal,
    CloudRateLimits,
    CloudReconnections,
)


class TestCloudMetricsSensors:
    @pytest.mark.parametrize(
        ("sensor_cls", "attribute", "test_value"),
        [
            (CloudQueries, "sigenergy2mqtt_cloud_queries", 10),
            (CloudQueryTotal, "sigenergy2mqtt_cloud_query_total", 50.5),
            (CloudQueryMax, "sigenergy2mqtt_cloud_query_max", 100.0),
            (CloudQueryMean, "sigenergy2mqtt_cloud_query_mean", 20.0),
            (CloudQueryMin, "sigenergy2mqtt_cloud_query_min", 1.0),
            (CloudQueryErrors, "sigenergy2mqtt_cloud_query_errors", 2),
            (CloudConnections, "sigenergy2mqtt_cloud_connections", 5),
            (CloudConnectionErrors, "sigenergy2mqtt_cloud_connection_errors", 1),
            (CloudConnectionAttempts, "sigenergy2mqtt_cloud_connection_attempts", 6),
            (CloudConnectionTotal, "sigenergy2mqtt_cloud_connection_total", 500.0),
            (CloudConnectionMax, "sigenergy2mqtt_cloud_connection_max", 200.0),
            (CloudConnectionMean, "sigenergy2mqtt_cloud_connection_mean", 100.0),
            (CloudConnectionMin, "sigenergy2mqtt_cloud_connection_min", 50.0),
            (CloudReconnections, "sigenergy2mqtt_cloud_reconnections", 3),
            (CloudRateLimits, "sigenergy2mqtt_cloud_rate_limits", 4),
            (CloudAuthErrors, "sigenergy2mqtt_cloud_auth_errors", 1),
            (CloudConnected, "sigenergy2mqtt_cloud_connected", True),
            (CloudAvailable, "sigenergy2mqtt_cloud_available", False),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_internal_state(self, monkeypatch, sensor_cls, attribute, test_value):
        sensor = sensor_cls()
        monkeypatch.setattr(Metrics, attribute, test_value)
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == test_value

    @pytest.mark.parametrize(
        "sensor_cls",
        [
            CloudQueries,
            CloudQueryTotal,
            CloudQueryMax,
            CloudQueryMean,
            CloudQueryMin,
            CloudQueryErrors,
            CloudConnections,
            CloudConnectionErrors,
            CloudConnectionAttempts,
            CloudConnectionTotal,
            CloudConnectionMax,
            CloudConnectionMean,
            CloudConnectionMin,
            CloudReconnections,
            CloudRateLimits,
            CloudAuthErrors,
            CloudConnected,
            CloudAvailable,
        ],
    )
    def test_cloud_sensors_publishable(self, monkeypatch, sensor_cls):
        from sigenergy2mqtt.config import active_config

        monkeypatch.setattr(active_config.cloud, "username", "test", raising=False)
        monkeypatch.setattr(active_config.cloud, "password", "test", raising=False)
        monkeypatch.setattr(active_config.cloud, "region", "eu", raising=False)
        monkeypatch.setattr(active_config.cloud, "accept_unofficial_api_risk", True, raising=False)

        sensor = sensor_cls()
        assert sensor.publishable is True

        monkeypatch.setattr(active_config.cloud, "accept_unofficial_api_risk", False, raising=False)
        sensor = sensor_cls()
        assert sensor.publishable is False
