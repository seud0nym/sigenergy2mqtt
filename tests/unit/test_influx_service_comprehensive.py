import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

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
    Config.influxdb.include = []
    Config.influxdb.exclude = []
    Config.influxdb.write_timeout = 30.0
    Config.influxdb.read_timeout = 120.0
    Config.influxdb.batch_size = 100
    Config.influxdb.flush_interval = 1.0
    Config.influxdb.query_interval = 0.1
    Config.influxdb.max_retries = 3
    Config.influxdb.pool_connections = 100
    Config.influxdb.pool_maxsize = 100
    return Config.influxdb


def test_init_no_influx_config(logger):
    # This test intended to verify what happens if influxdb section is missing/None
    # But since __init__ now requires attributes, we should verify it handles missing optional config
    # OR if we want to test "enabled=False" (which is default)
    # If Config.influxdb is completely None, __init__ will crash.
    # But validation ensures Config.influxdb exists with defaults.
    # So we should test "not enabled".
    mock_config = MagicMock()
    mock_config.enabled = False
    # Defaults required for init to proceed past enabled check if logic allows?
    # InfluxService checks enabled first?
    # No, it sets defaults first.
    mock_config.max_retries = 3
    mock_config.pool_connections = 100
    mock_config.pool_maxsize = 100
    mock_config.batch_size = 100
    mock_config.flush_interval = 1.0
    mock_config.query_interval = 0.1

    with patch.object(Config, "influxdb", mock_config):
        svc = InfluxService(logger, plant_index=0)
        assert svc._writer_type is None


def test_init_influx_disabled(logger):
    Config.influxdb.enabled = False
    svc = InfluxService(logger, plant_index=0)
    assert svc._writer_type is None


@pytest.mark.asyncio
async def test_init_token_prefers_v2_http(logger, influx_config):
    influx_config.token = "mytoken"
    with patch("requests.Session.post") as mock_post:
        mock_post.side_effect = [
            MockResponse(204),  # v2 HTTP success
        ]
        svc = InfluxService(logger, plant_index=0)
        await svc._async_init()
        assert svc._writer_type == "v2_http"


@pytest.mark.asyncio
async def test_init_v2_http_success_no_token(logger, influx_config):
    # Even without token, if we can write to v2 api (e.g. no auth), we use it
    with patch("requests.Session.post") as mock_post:
        # First call might typically be v2 check in fallback
        mock_post.side_effect = [
            MockResponse(204),  # v2 HTTP success
        ]
        svc = InfluxService(logger, plant_index=0)
        await svc._async_init()
        assert svc._writer_type == "v2_http"


@pytest.mark.asyncio
async def test_init_v2_http_bucket_creation(logger, influx_config):
    influx_config.token = "mytoken"
    with patch("requests.Session.post") as mock_post, patch("requests.Session.get") as mock_get:
        mock_post.side_effect = [
            MockResponse(404),  # v2 write fail
            MockResponse(201),  # v2 bucket create success
            MockResponse(204),  # v2 write retry success
        ]
        mock_get.return_value = MockResponse(200, {"orgs": [{"id": "org123"}]})

        svc = InfluxService(logger, plant_index=0)
        await svc._async_init()
        assert svc._writer_type == "v2_http"


@pytest.mark.asyncio
async def test_init_v1_http_database_creation(logger, influx_config):
    influx_config.username = "user"
    with patch("requests.Session.post") as mock_post:
        mock_post.side_effect = [
            MockResponse(404, content=b"database not found"),  # v1 write fail
            MockResponse(200),  # database create success
            MockResponse(204),  # v1 write retry success
        ]

        svc = InfluxService(logger, plant_index=0)
        await svc._async_init()
        assert svc._writer_type == "v1_http"


@pytest.mark.asyncio
async def test_init_all_fail_returns_false(logger, influx_config):
    # Ensure even with token we fail if network fails
    influx_config.token = "tok"
    with patch("requests.Session.post", side_effect=Exception("all fail")):
        svc = InfluxService(logger, plant_index=0)
        success = await svc._async_init()
        assert success is False


def test_to_line_protocol(logger):
    svc = InfluxService(logger, plant_index=0)
    tags = {"t1": "v1", "t 2": "v 2"}
    fields = {"f1": 10, "f2": 10.5, "f3": "str val"}
    ts = 1234567890
    line = svc._to_line_protocol("meas name", tags, fields, ts)
    assert 'meas\\ name,t1=v1,t\\ 2=v\\ 2 f1=10i,f2=10.5,f3="str val" 1234567890000000000' in line


@pytest.mark.asyncio
async def test_write_line_http_fail(logger, influx_config):
    # Disable init so we can manually configure the writer for the test
    influx_config.enabled = False
    svc = InfluxService(logger, plant_index=0)
    svc._online = True  # Enable for write test

    # Manually configure writer
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"

    # Mock clean session post failure
    with patch.object(svc._session, "post", side_effect=Exception("write error")):
        with patch.object(logger, "error") as mock_logger_error:
            await svc._write_line("test line")
            await svc.flush_buffer()  # Force flush to trigger write
            # Log message contains exception detail and context
            found = any("InfluxDB write failed: write error" in c.args[0] for c in mock_logger_error.call_args_list)
            assert found


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
        assert res is False
        mock_warn.assert_called()


@pytest.mark.asyncio
async def test_handle_mqtt_exception_handling(logger):
    svc = InfluxService(logger, plant_index=0)
    svc._topic_cache["topic1"] = {"uom": "W", "object_id": "obj1", "unique_id": "uid1"}

    with patch.object(svc, "_to_line_protocol", side_effect=Exception("format error")):
        with patch.object(logger, "error") as mock_error:
            res = await svc.handle_mqtt(None, None, "100", "topic1", None)
            assert res is False
            assert "Failed to handle MQTT message" in mock_error.call_args[0][0]


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
        # The exception in s["object_id"] is caught and returns None, OR loop continues
        # If loop continues, topic is not in cache
        assert "topic_err" not in svc._topic_cache


@pytest.mark.asyncio
async def test_write_line_v2_http_and_v1_http(logger, influx_config):
    influx_config.enabled = False  # Disable init
    svc = InfluxService(logger, plant_index=0)
    svc._online = True

    # v2_http
    svc._writer_type = "v2_http"
    svc._write_url = "http://v2"
    with patch.object(svc._session, "post") as mock_post:
        mock_post.return_value = MockResponse(204)
        await svc._write_line("line2")
        await svc.flush_buffer()  # Force flush to trigger write
        mock_post.assert_called()

    # v1_http
    svc._writer_type = "v1_http"
    svc._write_url = "http://v1"
    with patch.object(svc._session, "post") as mock_post:
        mock_post.return_value = MockResponse(204)
        await svc._write_line("line1")
        await svc.flush_buffer()  # Force flush to trigger write
        mock_post.assert_called()


@pytest.mark.asyncio
async def test_init_v1_fallback_success(logger, influx_config):
    # official client check not needed now, so we simulate v2 fail and v1 success
    influx_config.token = "tok"
    influx_config.username = "user"

    # We expect:
    # 1. v2 check fails (e.g. 404 or connection error)
    # 2. v1 check succeeds
    with patch("requests.Session.post") as mock_post:
        # Side effects for calls:
        # Call 1: v2 check -> fail
        # Call 2: v1 check -> success
        mock_post.side_effect = [Exception("v2 conn fail"), MockResponse(204)]

        svc = InfluxService(logger, plant_index=0)
        await svc._async_init()
        assert svc._writer_type == "v1_http"


@pytest.mark.asyncio
async def test_schedule_starts_and_cancels_sync_task(logger):
    svc = InfluxService(logger, plant_index=0)
    # Manually simulate established connection
    svc._writer_type = "v2_http"

    # Mock sync_from_homeassistant to be a long running task
    async def mock_sync():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    with patch.object(svc, "sync_from_homeassistant", side_effect=mock_sync) as mock_method:
        tasks = svc.schedule(None, MagicMock())

        # Ensure online is True so loop runs (must be Future)
        fut = asyncio.Future()
        svc.online = fut

        # Launch the keep_running task
        task = asyncio.create_task(tasks[0])

        # Give it a moment to start the sync task
        await asyncio.sleep(0.1)

        # Verify sync was called
        mock_method.assert_called_once()

        # Stop everything
        svc.online = False
        await task  # This should finish and cancel the mock_sync

        # verifying it didn't hang is implicit success
