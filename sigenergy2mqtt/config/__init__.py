__all__ = ["Config", "SmartPortConfiguration", "ConsumptionSource", "OutputField", "StatusField", "VoltageSource", "initialize"]

import logging
import os
import sys

from . import cli, const
from .config import Config as _Config
from .config import active_config
from .pvoutput_config import ConsumptionSource, OutputField, StatusField, VoltageSource
from .smart_port_config import SmartPortConfiguration

# Export the Config class. It provides backward compatibility via ConfigMeta
# but also allows creating new instances.
Config = _Config


def initialize():
    """Explicitly initialize the configuration module.

    This performs side effects previously handled on import:
    - Logging setup
    - Folder creation
    - Stale file cleanup
    - CLI argument parsing and applying overrides
    """
    # 1. System-level initialization (logging, folders)
    persistent_path = _Config.system_initialize()
    active_config.persistent_state_path = persistent_path

    # 2. Parse CLI arguments
    args = cli.parse_args()

    if args.show_version:
        sys.exit(0)

    # 3. Apply CLI overrides to environment variables (for backward compatibility with how Config loads)
    _apply_cli_overrides(args)

    # 4. Initialize Config with the discovered path if needed (it already defaults to current folder)
    # The reload() call will pick up the environment variables we just set.

    # Check for config path
    try:
        config_path = os.getenv(const.SIGENERGY2MQTT_CONFIG)
        if config_path:
            filename = str(config_path).strip()
            if os.path.isfile(filename):
                active_config.load(filename)
            else:
                raise FileNotFoundError(f"Specified config file '{filename}' does not exist!")
        elif os.path.isfile("/etc/sigenergy2mqtt.yaml"):
            active_config.load("/etc/sigenergy2mqtt.yaml")
        elif os.path.isfile("/data/sigenergy2mqtt.yaml"):
            active_config.load("/data/sigenergy2mqtt.yaml")
        else:
            active_config.reload()
    except Exception as e:
        logging.critical(f"Error processing configuration: {e}")
        sys.exit(1)

    # Handle early exit flags
    if getattr(args, "clean", False):
        active_config.clean = True

    if getattr(args, "validate_only", False):
        try:
            active_config.validate()
            logging.info("Configuration validated successfully.")
            sys.exit(0)
        except Exception as e:
            logging.critical(f"Configuration validation failed: {e}")
            sys.exit(1)

    if getattr(args, "discovery_only", False):
        active_config.home_assistant.discovery_only = True


def _apply_cli_overrides(args):
    """Applies parsed CLI arguments to environment variables and Config instance."""
    # Special case for log level to set it early
    log_level_arg = getattr(args, const.SIGENERGY2MQTT_LOG_LEVEL, None)
    if log_level_arg:
        active_config.log_level = getattr(logging, log_level_arg)
        logging.getLogger("root").setLevel(active_config.log_level)
        logging.info(f"sigenergy2mqtt log-level changed to {log_level_arg}")

    for arg, value in vars(args).items():
        if arg in ["clean", "discovery_only", "validate_only", "show_version"]:
            continue

        # Handle boolean flags that should only be applied if true
        if (
            arg == const.SIGENERGY2MQTT_HASS_ENABLED
            or arg == const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX
            or arg == const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS
            or arg == const.SIGENERGY2MQTT_INFLUX_ENABLED
            or arg == const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING
            or arg == const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS
            or arg == const.SIGENERGY2MQTT_MQTT_ANONYMOUS
            or arg == const.SIGENERGY2MQTT_MQTT_TLS
            or arg == const.SIGENERGY2MQTT_MQTT_TLS_INSECURE
            or arg == const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK
            or arg == const.SIGENERGY2MQTT_NO_METRICS
            or arg == const.SIGENERGY2MQTT_PVOUTPUT_ENABLED
            or arg == const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS
            or arg == const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS
            or arg == const.SIGENERGY2MQTT_SMARTPORT_ENABLED
        ) and value not in ["true", "True", True, 1]:
            continue

        # Handle Modbus read-only special case
        if arg == const.SIGENERGY2MQTT_MODBUS_READ_ONLY:
            if value in ["true", "True", True, 1]:
                _Config.apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_ONLY, "true")
                _Config.apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_WRITE, "false")
                _Config.apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY, "false")
            continue

        if value is not None:
            if isinstance(value, list):
                _Config.apply_cli_to_env(arg, ",".join([str(x) for x in value]))
            else:
                _Config.apply_cli_to_env(arg, str(value))
