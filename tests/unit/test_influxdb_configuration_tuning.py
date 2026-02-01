from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.influxdb_config import InfluxDBConfiguration
from sigenergy2mqtt.influxdb.influx_service import InfluxService


def test_influxdb_config_tuning_defaults():
    cfg = InfluxDBConfiguration()
    assert cfg.write_timeout == 30.0
    assert cfg.read_timeout == 120.0
    assert cfg.batch_size == 100
    assert cfg.flush_interval == 1.0
    assert cfg.query_interval == 0.1
    assert cfg.max_retries == 3
    assert cfg.pool_connections == 100
    assert cfg.pool_maxsize == 100


def test_influxdb_config_tuning_parsing():
    cfg = InfluxDBConfiguration()
    config_dict = {
        "enabled": True,
        "token": "test_token",
        "org": "test_org",
        "write-timeout": "10.5",
        "read-timeout": "60.0",
        "batch-size": "50",
        "flush-interval": 2.0,
        "query-interval": "0.5",
        "max-retries": 5,
        "pool-connections": "20",
        "pool-maxsize": "30",
    }
    cfg.configure(config_dict)

    assert cfg.write_timeout == 10.5
    assert cfg.read_timeout == 60.0
    assert cfg.batch_size == 50
    assert cfg.flush_interval == 2.0
    assert cfg.query_interval == 0.5
    assert cfg.max_retries == 5
    assert cfg.pool_connections == 20
    assert cfg.pool_maxsize == 30


@pytest.mark.asyncio
async def test_influx_service_uses_config_values(monkeypatch):
    # Setup custom config
    Config.influxdb.batch_size = 50
    Config.influxdb.flush_interval = 2.0
    Config.influxdb.query_interval = 0.5
    Config.influxdb.max_retries = 2

    logger = MagicMock()
    svc = InfluxService(logger, plant_index=0)
    svc._online = True

    # Check attributes set in init
    assert svc._batch_size == 50
    assert svc._flush_interval == 2.0
    assert svc._query_interval == 0.5

    # Verify retry strategy logic uses config
    # We can inspect the adapter mounted to session
    adapter = svc._session.get_adapter("http://")
    assert adapter.max_retries.total == 2

    # Verify defaults used in methods (mocking _rate_limited_query to capture args)

    captured_args = {}

    async def mock_rate_limit(func, name, retries):
        captured_args["retries"] = retries
        return True, "ok"

    svc._rate_limited_query = mock_rate_limit
    Config.influxdb.read_timeout = 99.0
    Config.influxdb.max_retries = 5

    await svc._query_v2("base", "org", "tok", "q")
    assert captured_args["retries"] == 5

    # Verify write timeout logic
    # Mock asyncio.to_thread to check timeout arg
    captured_post = {}

    async def fake_to_thread(func, *args, **kwargs):
        captured_post["timeout"] = kwargs.get("timeout")
        return MagicMock(status_code=204)

    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)

    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"
    Config.influxdb.write_timeout = 45.0

    await svc._execute_write(b"data")
    assert captured_post["timeout"] == 45.0
