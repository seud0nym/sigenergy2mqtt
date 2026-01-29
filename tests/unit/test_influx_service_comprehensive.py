import asyncio
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from influxdb_client.client.influxdb_client import InfluxDBClient

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.influx_service import InfluxService


class MockResponse:
    def __init__(self, status_code, json_data=None, content=b""):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self):
        return self._json_data


@pytest.fixture
def logger():
    return logging.getLogger("test_influx")


@pytest.fixture
def influx_config():
    Config.influxdb.enabled = True
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "mydb"
    Config.influxdb.username = None
    Config.influxdb.password = None
    Config.influxdb.token = None
    Config.influxdb.org = "myorg"
    Config.influxdb.bucket = "mybucket"
    Config.influxdb.include = []
    Config.influxdb.exclude = []
    return Config.influxdb


def test_init_no_influx_config(logger):
    with patch.object(Config, "influxdb", None):
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type is None


def test_init_influx_disabled(logger):
    Config.influxdb.enabled = False
    svc = InfluxService(logger, plant_index=0)
    assert svc._writer_type is None


def test_init_official_client_success(logger, influx_config):
    influx_config.token = "mytoken"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient") as mock_client:
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "client"
        mock_client.assert_called_once()


def test_init_official_client_failure_fallback_v1(logger, influx_config):
    influx_config.token = "mytoken"
    influx_config.username = "user"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("fail")), patch("requests.Session.post") as mock_post:
        mock_post.return_value = MockResponse(204)
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "v1_http"


def test_init_v2_http_success(logger, influx_config):
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("no client")), patch("requests.Session.post") as mock_post:
        # First call to /write (v1 fallback tries this or v2)
        # Actually it tries v2 first if user is not set
        mock_post.side_effect = [
            MockResponse(204),  # v2 HTTP success
        ]
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "v2_http"


def test_init_v2_http_bucket_creation(logger, influx_config):
    influx_config.token = "mytoken"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("no client")), patch("requests.Session.post") as mock_post, patch("requests.Session.get") as mock_get:
        mock_post.side_effect = [
            MockResponse(404),  # v2 write fail
            MockResponse(201),  # v2 bucket create success
            MockResponse(204),  # v2 write retry success
        ]
        mock_get.return_value = MockResponse(200, {"orgs": [{"id": "org123"}]})

        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "v2_http"


def test_init_v1_http_database_creation(logger, influx_config):
    influx_config.username = "user"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("no client")), patch("requests.Session.post") as mock_post:
        mock_post.side_effect = [
            MockResponse(404, content=b"database not found"),  # v1 write fail
            MockResponse(200),  # database create success
            MockResponse(204),  # v1 write retry success
        ]

        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "v1_http"


def test_init_all_fail_raises_runtime_error(logger, influx_config):
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=Exception("no client")), patch("requests.Session.post", side_effect=Exception("all fail")):
        with pytest.raises(RuntimeError, match="InfluxDB initialization failed"):
            InfluxService(logger, plant_index=0)


def test_to_line_protocol(logger):
    svc = InfluxService(logger, plant_index=0)
    tags = {"t1": "v1", "t 2": "v 2"}
    fields = {"f1": 10, "f2": 10.5, "f3": "str val"}
    ts = 1234567890
    line = svc._to_line_protocol("meas name", tags, fields, ts)
    assert 'meas\\ name,t1=v1,t\\ 2=v\\ 2 f1=10i,f2=10.5,f3="str val" 1234567890000000000' in line


def test_write_line_client_fail(logger, influx_config):
    influx_config.token = "mytoken"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient") as mock_client:
        svc = InfluxService(logger, plant_index=0)
        # The service calls _writer_obj.write_api(...)
        mock_write_api = MagicMock()
        svc._writer_obj.write_api.return_value = mock_write_api
        mock_write_api.write.side_effect = Exception("write error")

        with patch.object(logger, "error") as mock_logger_error:
            svc._write_line("test line")
            # Multiple errors logged, check if any match
            mock_logger_error.assert_any_call("InfluxDB write failed: write error")


@pytest.mark.asyncio
async def test_handle_mqtt_numeric_and_string(logger):
    svc = InfluxService(logger, plant_index=0)
    svc._topic_cache["topic1"] = {"uom": "W", "object_id": "obj1", "unique_id": "uid1"}
    svc._writer_type = "v1_http"

    with patch.object(svc, "_write_line") as mock_write:
        # Numeric payload
        await svc.handle_mqtt(None, None, "100.5", "topic1", None)
        assert "value=100.5" in mock_write.call_args[0][0]

        # String payload
        await svc.handle_mqtt(None, None, "status_ok", "topic1", None)
        assert 'value_str="status_ok"' in mock_write.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_mqtt_cache_miss(logger):
    svc = InfluxService(logger, plant_index=0)
    # Disable init as we don't have config here and it might fail if we had it
    with patch.object(logger, "warning") as mock_warn:
        res = await svc.handle_mqtt(None, None, "100", "unknown_topic", None)
        assert res is True
        mock_warn.assert_called()


@pytest.mark.asyncio
async def test_handle_mqtt_exception_handling(logger):
    svc = InfluxService(logger, plant_index=0)
    svc._topic_cache["topic1"] = {"uom": "W", "object_id": "obj1", "unique_id": "uid1"}

    with patch.object(svc, "_to_line_protocol", side_effect=Exception("format error")):
        with patch.object(logger, "error") as mock_error:
            res = await svc.handle_mqtt(None, None, "100", "topic1", None)
            assert res is False
            assert "Failed to handle mqtt message" in mock_error.call_args[0][0]


def test_subscribe_comprehensive(logger):
    svc = InfluxService(logger, plant_index=0)

    mock_sensor = MagicMock()
    mock_sensor.publishable = True
    mock_sensor.state_topic = "topic1"
    mock_sensor.unique_id = "uid1"
    mock_sensor.device_class = MagicMock(value="power")
    mock_sensor.__getitem__.side_effect = lambda k: "obj1" if k == "object_id" else None

    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {"s1": mock_sensor}

    with patch("sigenergy2mqtt.devices.device.DeviceRegistry.get", return_value=[mock_device]):
        mqtt_handler = MagicMock()
        svc.subscribe(None, mqtt_handler)
        assert "topic1" in svc._topic_cache
        mqtt_handler.register.assert_called_with(None, "topic1", svc.handle_mqtt)


@pytest.mark.asyncio
async def test_schedule_lifecycle(logger):
    svc = InfluxService(logger, plant_index=0)
    tasks = svc.schedule(None, None)
    assert len(tasks) == 1

    # Run the task briefly then stop it
    fut = asyncio.Future()
    svc.online = fut
    task = asyncio.create_task(tasks[0])
    await asyncio.sleep(0.1)
    svc.online = False
    await task

    # Check that it reached completion
    # (no explicit assert needed if it doesn't hang)


def test_empty_methods(logger):
    svc = InfluxService(logger, plant_index=0)
    svc.publish_availability(None, None)
    svc.publish_discovery(None)


def test_subscribe_edge_cases(logger):
    svc = InfluxService(logger, plant_index=0)

    # Case 1: No devices
    with patch("sigenergy2mqtt.devices.device.DeviceRegistry.get", return_value=None):
        svc.subscribe(None, MagicMock())
        # Cache hit skip check
        assert svc._topic_cache == {}

    # Case 2: Not publishable sensor
    mock_sensor = MagicMock()
    mock_sensor.publishable = False
    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {"s1": mock_sensor}
    with patch("sigenergy2mqtt.devices.device.DeviceRegistry.get", return_value=[mock_device]):
        svc.subscribe(None, MagicMock())
        assert svc._topic_cache == {}

    # Case 3: Sensor object_id exception
    mock_sensor = MagicMock()
    mock_sensor.publishable = True
    mock_sensor.state_topic = "topic_err"
    mock_sensor.unique_id = "uid_err"
    mock_sensor.device_class = None
    mock_sensor.data_type = MagicMock()
    mock_sensor.data_type.name = "INT16"

    def raise_err(k):
        if k == "unit_of_measurement":
            return "W"
        raise Exception("err")

    mock_sensor.__getitem__.side_effect = raise_err
    mock_device.get_all_sensors.return_value = {"s_err": mock_sensor}
    with patch("sigenergy2mqtt.devices.device.DeviceRegistry.get", return_value=[mock_device]):
        svc.subscribe(None, MagicMock())
        # The exception in s["object_id"] is caught and returns None
        assert svc._topic_cache["topic_err"]["object_id"] is None


@pytest.mark.asyncio
async def test_handle_mqtt_cache_miss_formatting(logger, influx_config):
    influx_config.enabled = False  # Disable init
    svc = InfluxService(logger, plant_index=0)
    svc._writer_type = "v1_http"
    with patch.object(svc, "_write_line") as mock_write:
        # Cache miss, should still write with topic-based measurement
        await svc.handle_mqtt(None, None, "123.5", "some/topic", None)
        # Check if call was made
        mock_write.assert_called()
        line = mock_write.call_args[0][0]
        assert "some_topic" in line
        assert "value=123.5" in line


def test_write_line_v2_http_and_v1_http(logger, influx_config):
    influx_config.enabled = False  # Disable init
    svc = InfluxService(logger, plant_index=0)

    # v2_http
    svc._writer_type = "v2_http"
    svc._write_url = "http://v2"
    with patch.object(svc._session, "post") as mock_post:
        mock_post.return_value = MockResponse(204)
        svc._write_line("line2")
        mock_post.assert_called()

    # v1_http
    svc._writer_type = "v1_http"
    svc._write_url = "http://v1"
    with patch.object(svc._session, "post") as mock_post:
        mock_post.return_value = MockResponse(204)
        svc._write_line("line1")
        mock_post.assert_called()


def test_init_v1_fallback_and_errors(logger, influx_config):
    # official client fail, v1 success
    influx_config.token = "tok"
    influx_config.username = "user"
    with patch("sigenergy2mqtt.influxdb.influx_service.InfluxDBClient", side_effect=[Exception("no client"), Exception("no client")]), patch("requests.Session.post") as mock_post:
        mock_post.return_value = MockResponse(204)
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type == "v1_http"
