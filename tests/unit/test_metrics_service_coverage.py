from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.metrics.metrics_service import MetricsService


class TestMetricsServiceCoverage:
    @pytest.mark.asyncio
    async def test_init_without_influxdb(self):
        protocol = Protocol.V2_0
        # Mock Config to ensure influxdb is seemingly disabled or missing
        with patch("sigenergy2mqtt.metrics.metrics_service.Config") as MockConfig:
            MockConfig.influxdb.enabled = False

            service = MetricsService(protocol)

            # Check if InfluxDB sensors are NOT present
            # We can check the protected _sensors list key or try to iterate
            sensor_keys = list(service.sensors.keys())
            assert not any("influxdb_writes" in k for k in sensor_keys)
            assert any("modbus_write_errors" in k for k in sensor_keys)

    @pytest.mark.asyncio
    async def test_init_with_influxdb_enabled(self):
        protocol = Protocol.V2_0
        with patch("sigenergy2mqtt.metrics.metrics_service.Config") as MockConfig:
            MockConfig.home_assistant.unique_id_prefix = "test_prefix"
            MockConfig.influxdb.enabled = True

            service = MetricsService(protocol)

            sensor_keys = list(service.sensors.keys())
            assert any("influxdb_writes" in k for k in sensor_keys)
            assert any("modbus_write_errors" in k for k in sensor_keys)

    @pytest.mark.asyncio
    async def test_publish_updates(self):
        protocol = Protocol.V2_0
        with patch("sigenergy2mqtt.metrics.metrics_service.Config") as MockConfig:
            MockConfig.home_assistant.unique_id_prefix = "test_prefix"
            MockConfig.influxdb.enabled = False

            service = MetricsService(protocol)

            modbus_client = MagicMock()
            mqtt_client = MagicMock()

            # Mock super().publish_updates to avoid actual execution logic if needed,
            # but since Device.publish_updates is complex, we might just let it run if dependencies are mocked.
            # However, super().publish_updates might try to read from modbus.
            # Let's mock the internal _update_sensor or similar if we want deep isolation,
            # or just mock the super call.

            with patch("sigenergy2mqtt.metrics.metrics_service.Device.publish_updates", new_callable=AsyncMock) as mock_super_publish:
                await service.publish_updates(modbus_client, mqtt_client, "test_name")

                # Check if status messages were published
                mqtt_client.publish.assert_any_call("sigenergy2mqtt/status", "online", qos=0, retain=True)
                mqtt_client.publish.assert_any_call("sigenergy2mqtt/status", "offline", qos=0, retain=True)

                # Check if super was called
                mock_super_publish.assert_awaited()
