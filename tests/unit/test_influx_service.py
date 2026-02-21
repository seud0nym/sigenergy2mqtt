from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.influx_service import InfluxService


class DummyMqtt:
    def publish(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_influx_handle_mqtt_writes_line():
    logger = MagicMock()
    svc = InfluxService(logger, plant_index=0)

    # Create a fake sensor
    class FakeSensor:
        def __init__(self):
            self._data = {"object_id": "sensor.test_1", "unique_id": "uid_test_1", "unit_of_measurement": "W"}
            self.state_topic = "sigenergy2mqtt/sensor.test_1/state"
            self.publishable = True

        def __getitem__(self, key):
            return self._data[key]

        @property
        def unique_id(self):
            return self._data["unique_id"]

    fake_sensor = FakeSensor()

    # Pre-populate the service topic cache
    svc._topic_cache[fake_sensor.state_topic] = {"uom": fake_sensor["unit_of_measurement"], "object_id": fake_sensor["object_id"], "unique_id": fake_sensor.unique_id}

    wrote = {}

    async def fake_write(line):
        wrote["line"] = line

    svc.write_line = fake_write
    await svc.handle_mqtt(None, None, "123.45", "sigenergy2mqtt/sensor.test_1/state", None)

    # Check if write was called with correct value
    assert "value" in wrote["line"] or "123.45" in wrote["line"]


@pytest.mark.asyncio
async def test_influx_org_propagation():
    """Test that org parameter is correctly propagated to v2 HTTP endpoint."""
    logger = MagicMock()
    active_config.influxdb.enabled = True
    active_config.influxdb.host = "localhost"
    active_config.influxdb.port = 8086
    active_config.influxdb.database = "mydb"
    active_config.influxdb.org = "myorg"
    active_config.influxdb.token = "mytoken"
    active_config.influxdb.bucket = "mybucket"
    active_config.influxdb.username = None
    active_config.influxdb.password = None

    # Test v2 HTTP path with org parameter
    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 204
        svc = InfluxService(logger, plant_index=0)
        await svc.async_init()

        # Verify URL contains org parameter
        args, kwargs = mock_post.call_args
        assert "org=myorg" in args[0]
        assert svc._writer_type == "v2_http"
        assert "mybucket" in svc._write_url
