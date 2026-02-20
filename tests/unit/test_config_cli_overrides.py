import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sigenergy2mqtt.config import _promote_cli_to_env, const


@patch.dict(os.environ, {}, clear=True)
def test_apply_cli_overrides_boolean_flags():
    """Test that boolean flags are only applied if true."""
    # Create mock args with mixed true/false/none values for boolean flags
    # Use SimpleNamespace to act like a real args object
    args = SimpleNamespace()

    # 1. Flags that should be ignored (False, None, "false")
    setattr(args, const.SIGENERGY2MQTT_HASS_ENABLED, False)
    setattr(args, const.SIGENERGY2MQTT_INFLUX_ENABLED, None)
    setattr(args, const.SIGENERGY2MQTT_MQTT_TLS, "false")

    # Explicitly set log level to None so it is skipped
    # (setattr is fine on SimpleNamespace)
    setattr(args, const.SIGENERGY2MQTT_LOG_LEVEL, None)

    # 2. Flags that should be applied (True, 1, "true")
    setattr(args, const.SIGENERGY2MQTT_PVOUTPUT_ENABLED, True)
    # WARNING: Do NOT set SmartPort enabled here if you can't satisfy its config requirements in teardown,
    # OR rely on patch.dict(os.environ) to clean it up (which we do now).
    setattr(args, const.SIGENERGY2MQTT_SMARTPORT_ENABLED, "true")

    # 3. Non-boolean flags (should always be applied if not None)
    setattr(args, "some_other_arg", "some_value")

    with patch("sigenergy2mqtt.config.config.auto_discovery_scan", new_callable=AsyncMock, return_value=[]):
        _promote_cli_to_env(args)

        # Verify ignored flags were NOT set in os.environ
        assert const.SIGENERGY2MQTT_HASS_ENABLED not in os.environ
        assert const.SIGENERGY2MQTT_INFLUX_ENABLED not in os.environ
        assert const.SIGENERGY2MQTT_MQTT_TLS not in os.environ

        # Verify applied flags WERE set in os.environ
        assert os.environ[const.SIGENERGY2MQTT_PVOUTPUT_ENABLED] == "True"
        assert os.environ[const.SIGENERGY2MQTT_SMARTPORT_ENABLED] == "true"
        assert os.environ["some_other_arg"] == "some_value"


@patch.dict(os.environ, {}, clear=True)
def test_apply_cli_overrides_repeated_interval():
    """Test that repeated_state_publish_interval is correctly applied."""
    args = SimpleNamespace()
    setattr(args, const.SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL, 10)
    setattr(args, const.SIGENERGY2MQTT_LOG_LEVEL, None)

    with patch("sigenergy2mqtt.config.config.auto_discovery_scan", new_callable=AsyncMock, return_value=[]):
        _promote_cli_to_env(args)
        assert os.environ[const.SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL] == "10"
