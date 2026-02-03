import logging
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sigenergy2mqtt.config import Config, _apply_cli_overrides, const


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

    # Mock Config.apply_cli_to_env to verify calls
    # Patch the _Config class alias directly in the module where _apply_cli_overrides is defined
    with patch("sigenergy2mqtt.config._Config") as mock_config_class:
        mock_apply = mock_config_class.apply_cli_to_env

        _apply_cli_overrides(args)

        # Verify calls
        called_args = [call.args[0] for call in mock_apply.call_args_list]

        # Verify ignored flags were NOT called
        assert const.SIGENERGY2MQTT_HASS_ENABLED not in called_args, f"{const.SIGENERGY2MQTT_HASS_ENABLED} should be ignored"
        assert const.SIGENERGY2MQTT_INFLUX_ENABLED not in called_args, f"{const.SIGENERGY2MQTT_INFLUX_ENABLED} should be ignored"
        assert const.SIGENERGY2MQTT_MQTT_TLS not in called_args, f"{const.SIGENERGY2MQTT_MQTT_TLS} should be ignored"

        # Verify applied flags WERE called
        mock_apply.assert_any_call(const.SIGENERGY2MQTT_PVOUTPUT_ENABLED, "True")
        mock_apply.assert_any_call(const.SIGENERGY2MQTT_SMARTPORT_ENABLED, "true")
        mock_apply.assert_any_call("some_other_arg", "some_value")
