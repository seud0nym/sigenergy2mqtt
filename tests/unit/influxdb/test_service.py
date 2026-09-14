import asyncio
from unittest.mock import MagicMock, patch

import pytest
from urllib3.exceptions import MaxRetryError

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.base import _ShutdownAwareRetry
from sigenergy2mqtt.influxdb.service import InfluxService


def _bring_online(svc: InfluxService) -> asyncio.Future:
    """Bring a service online via the real ``online`` setter (not the ``_online`` backdoor).

    Exercises the same code path production code uses, so that the setter's
    bookkeeping (clearing the shutdown event, etc.) and the corresponding
    offline-transition logic (session close, task cancellation) are actually
    tested rather than bypassed.
    """
    future = asyncio.get_running_loop().create_future()
    svc.online = future
    return future


class DummyMqtt:
    def publish(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_influx_handle_mqtt_writes_line():
    logger = MagicMock()
    svc = InfluxService(plant_index=0)

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
        svc = InfluxService(plant_index=0)
        await svc.async_init()

        # Verify URL contains org parameter
        args, kwargs = mock_post.call_args
        assert "org=myorg" in args[0]
        assert svc._writer_type == "v2_http"
        assert "mybucket" in svc._write_url


@pytest.mark.asyncio
async def test_online_false_closes_session():
    """Setting online = False (via the real setter) must close the HTTP session."""
    svc = InfluxService(plant_index=0)
    _bring_online(svc)
    assert svc.online is True

    svc._session = MagicMock()
    svc.online = False

    svc._session.close.assert_called_once()
    assert svc.online is False


def test_shutdown_aware_retry_increment_raises_when_shutdown_signalled():
    """_ShutdownAwareRetry.increment() must raise MaxRetryError once shutdown is signalled."""
    retry = _ShutdownAwareRetry()
    retry._shutdown_event = asyncio.Event()
    retry._shutdown_event.set()

    with pytest.raises(MaxRetryError):
        retry.increment()


def test_init_connection_falls_back_to_tokenless_v1():
    """With no token and no username, _init_connection should reach the final tokenless v1 fallback."""
    svc = InfluxService(plant_index=0)
    config = {
        "host": "localhost",
        "port": 8086,
        "db": "mydb",
        "user": None,
        "pwd": None,
        "token": None,
        "org": None,
        "bucket": "mydb",
        "base": "http://localhost:8086",
        "auth": None,
    }
    test_line = b"state value=1"

    with (
        patch.object(svc, "get_config_values", return_value=config),
        patch.object(svc, "_try_v2_write", return_value=False) as mock_v2,
        patch.object(svc, "_try_v1_write", return_value=True) as mock_v1,
    ):
        svc._init_connection()  # should not raise

    # Neither the token'd v2 attempt nor the user'd v1 attempt should fire (both
    # config values are falsy); only the tokenless v2 probe and the final
    # tokenless v1 fallback should be attempted.
    mock_v2.assert_called_once_with(config["base"], config["bucket"], config["org"], None, test_line)
    mock_v1.assert_called_once_with(config["base"], config["db"], config["auth"], test_line)


@pytest.mark.asyncio
async def test_execute_write_returns_false_for_unrecognized_writer_type():
    """execute_write must return False (not raise) when _writer_type is None/unrecognized.

    This is the normal state immediately after async_init() succeeds with
    InfluxDB disabled: the service is online, but no writer has been configured.
    """
    svc = InfluxService(plant_index=0)
    _bring_online(svc)
    svc._writer_type = None

    result = await svc.execute_write(b"state value=1 123")

    assert result is False
