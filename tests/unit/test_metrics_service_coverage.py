from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.config import _swap_active_config
from sigenergy2mqtt.metrics.metrics_service import MetricsService


class TestMetricsServiceCoverage:
    @pytest.mark.asyncio
    async def test_init_without_influxdb(self):
        protocol = Protocol.V2_0
        # Use _swap_active_config to ensure influxdb is disabled
        with _swap_active_config(Config()) as cfg:
            cfg.influxdb.enabled = False

            service = MetricsService(protocol)

            # Check if InfluxDB sensors are NOT publishable
            sensor_keys = list(service.sensors.keys())
            assert not any("influxdb_" in k for k in sensor_keys if service.sensors[k].publishable)
            assert any("modbus_write_errors" in k for k in sensor_keys)

    @pytest.mark.asyncio
    async def test_init_with_influxdb_enabled(self):
        protocol = Protocol.V2_0
        with _swap_active_config(Config()) as cfg:
            cfg.home_assistant.unique_id_prefix = "test_prefix"
            cfg.influxdb.enabled = True

            service = MetricsService(protocol)

            sensor_keys = list(service.sensors.keys())
            assert any("influxdb_writes" in k for k in sensor_keys)
            assert any("modbus_write_errors" in k for k in sensor_keys)

    @pytest.mark.asyncio
    async def test_publish_updates(self):
        protocol = Protocol.V2_0
        with _swap_active_config(Config()) as cfg:
            cfg.home_assistant.unique_id_prefix = "test_prefix"
            cfg.influxdb.enabled = False

            service = MetricsService(protocol)

            modbus_client = MagicMock()
            mqtt_client = MagicMock()

            service.on_commencement(modbus_client, mqtt_client)
            mqtt_client.publish.assert_any_call("sigenergy2mqtt/status", "online", qos=0, retain=True)

            service.on_completion(modbus_client, mqtt_client)
            mqtt_client.publish.assert_any_call("sigenergy2mqtt/status", "offline", qos=0, retain=True)
