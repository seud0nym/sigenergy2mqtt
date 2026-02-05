import os
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from sigenergy2mqtt.config import _apply_cli_overrides, const


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

    # Patch the _Config class alias directly in the module where _apply_cli_overrides is defined
    with patch("sigenergy2mqtt.config._Config") as mock_config_class:
        mock_apply = mock_config_class.apply_cli_to_env

        _apply_cli_overrides(args)

        # Verify calls
        expected_calls = [
            call(const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT, "45.0"),
            call(const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT, "90.0"),
            call(const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE, "500"),
            call(const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL, "2.5"),
            call(const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL, "1.5"),
            call(const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES, "5"),
            call(const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS, "50"),
            call(const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE, "50"),
            call(const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE, "2000"),
            call(const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS, "8"),
        ]

        # Check each expected call
        for expected in expected_calls:
            mock_apply.assert_any_call(*expected.args)
