import os
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from sigenergy2mqtt.config import _promote_cli_to_env, const


@patch.dict(os.environ, {}, clear=True)
def test_apply_influxdb_tuning_overrides():
    """Test that InfluxDB tuning CLI arguments are correctly applied to environment variables."""
    args = SimpleNamespace()

    # Set values for all tuning parameters
    setattr(args, const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT, 45.0)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT, 90.0)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE, 500)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL, 2.5)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL, 1.5)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES, 5)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS, 50)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE, 50)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE, 2000)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS, 8)

    _promote_cli_to_env(args)
    # Verify os.environ
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT] == "45.0"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT] == "90.0"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE] == "500"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL] == "2.5"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL] == "1.5"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES] == "5"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS] == "50"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE] == "50"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE] == "2000"
    assert os.environ[const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS] == "8"
