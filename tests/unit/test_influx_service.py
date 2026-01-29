from unittest.mock import ANY, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.influx_service import InfluxService


class DummyMqtt:
    def publish(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_influx_handle_mqtt_includes_excludes(tmp_path):
    logger = MagicMock()
    svc = InfluxService(logger, plant_index=0)

    # Create a fake sensor
    class FakeSensor:
        def __init__(self):
            self._data = {"object_id": "sensor.test_1", "unique_id": "uid_test_1", "unit_of_measurement": "W"}
            self.state_topic = "sigenergy2mqtt/sensor.test_1/state"
            self.raw_state_topic = "sigenergy2mqtt/sensor.test_1/raw"
            self.publishable = True

        def __getitem__(self, key):
            return self._data[key]

        @property
        def unique_id(self):
            return self._data["unique_id"]

    fake_sensor = FakeSensor()

    # Patch DeviceRegistry to return a device containing the fake sensor
    fake_device = MagicMock()
    fake_device.get_all_sensors.return_value = {"uid_test_1": fake_sensor}

    with patch("sigenergy2mqtt.devices.device.DeviceRegistry.get", return_value=(fake_device,)):
        # Pre-populate the service topic cache to avoid scanning registry (service now ignores cache misses)
        svc._topic_cache[fake_sensor.state_topic] = {"uom": fake_sensor["unit_of_measurement"], "object_id": fake_sensor["object_id"], "unique_id": fake_sensor.unique_id}
        # No include/exclude -> should write (we patch _write_line to capture)
        wrote = {}

        def fake_write(line):
            wrote["line"] = line

        svc._write_line = fake_write
        await svc.handle_mqtt(None, None, "123.45", "sigenergy2mqtt/sensor.test_1/state", None)
        assert "value" in wrote["line"] or "123.45" in wrote["line"]

        # Exclude the sensor -> should skip
        Config.influxdb.exclude = ["test_1"]
        wrote.clear()
        await svc.handle_mqtt(None, None, "123.45", "sigenergy2mqtt/sensor.test_1/state", None)
        assert wrote == {}

        # Include list that doesn't match -> skip
        Config.influxdb.exclude = []
        Config.influxdb.include = ["other"]
        wrote.clear()
        await svc.handle_mqtt(None, None, "123.45", "sigenergy2mqtt/sensor.test_1/state", None)
        assert wrote == {}

        # Matching include -> write
        Config.influxdb.include = ["test_1"]
        wrote.clear()
        await svc.handle_mqtt(None, None, "123.45", "sigenergy2mqtt/sensor.test_1/state", None)
        assert "line" in wrote


@pytest.mark.asyncio
async def test_influx_org_propagation():
    logger = MagicMock()
    Config.influxdb.enabled = True
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "mydb"
    Config.influxdb.org = "myorg"
    Config.influxdb.password = "token"

    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient") as mock_client:
        mock_write_api = MagicMock()
        mock_client.return_value.write_api.return_value = mock_write_api

        # Test propagation in _init_connection (official client path)
        svc = InfluxService(logger, plant_index=0)

        # Verify InfluxDBClient was initialized with correct URL
        mock_client.assert_called_with(url="http://localhost:8086", token="token")

        # Verify write was called with correct org
        mock_write_api.write.assert_called_with(bucket="mydb", org="myorg", record=ANY)
        assert svc._writer_obj_org == "myorg"

    # Test v2 HTTP path
    Config.influxdb.org = "http-org"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("no client")):
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value.status_code = 204
            svc = InfluxService(logger, plant_index=0)

            # Verify URL contains org parameter
            args, kwargs = mock_post.call_args
            assert "org=http-org" in args[0]
            assert svc._writer_type == "v2_http"
