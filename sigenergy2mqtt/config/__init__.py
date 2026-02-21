"""sigenergy2mqtt configuration package."""

__all__ = ["Config", "ConfigurationError", "ConsumptionSource", "initialize", "OutputField", "SmartPortConfiguration", "StatusField", "VoltageSource", "_swap_active_config"]

import logging
import os

from . import cli, const
from .config import Config, ConfigurationError, _swap_active_config, active_config
from .pvoutput_config import ConsumptionSource, OutputField, StatusField, VoltageSource
from .smart_port_config import SmartPortConfiguration

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_cli_to_env(variable: str, value: str | list[str]) -> None:
    """
    Set an environment variable from a CLI argument.
    """
    os.environ[variable] = ",".join(str(x) for x in value) if isinstance(value, list) else str(value)
    logging.debug(f"Environment variable '{variable}' set from CLI: value='{'[REDACTED]' if 'PASSWORD' in os.environ[variable] or 'API_KEY' in os.environ[variable] else os.environ[variable]}'")


def _is_arg_explicitly_set(value) -> bool:
    """
    Return True only when an argparse value was explicitly supplied on the
    command line.

    argparse stores False for unset boolean flags and None for omitted
    optional arguments — neither should override a config value.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value is True
    if isinstance(value, str) and value.lower() in ("false", ""):
        return False
    return True


def _promote_cli_to_env(args) -> None:
    """
    Copy explicitly-set CLI arguments into environment variables, unless an
    environment variable for that key is already present.

    This makes CLI and ENV identical from the perspective of the config
    loader: both arrive as env vars, ENV wins over CLI by virtue of already
    being set, and config file values are the fallback.

    The Modbus read-only flag is a special case: enabling it must atomically
    disable the two mutually-exclusive flags to keep the environment
    consistent before the config loader runs.
    """
    skip = {"clean", "discovery_only", "validate_only", "show_version"}

    for arg, value in vars(args).items():
        if arg in skip:
            continue

        if not _is_arg_explicitly_set(value):
            logging.debug(f"CLI arg {arg!r} not explicitly set, skipping")
            continue

        if os.getenv(arg):
            logging.debug(f"CLI arg {arg!r} superseded by environment variable, skipping")
            continue

        if arg == const.SIGENERGY2MQTT_MODBUS_READ_ONLY and value in (True, 1, "true", "True"):
            _apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_ONLY, "true")
            _apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_READ_WRITE, "false")
            _apply_cli_to_env(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY, "false")
            continue

        _apply_cli_to_env(arg, value)


def _discover_config_file() -> str | None:
    """
    Return the path of the first config file to load, or None to fall back
    to environment-variable / default-value initialisation.

    Search order:
      1. $SIGENERGY2MQTT_CONFIG environment variable
      2. /etc/sigenergy2mqtt.yaml
      3. /data/sigenergy2mqtt.yaml  (common in container environments)
    """
    env_path = os.getenv(const.SIGENERGY2MQTT_CONFIG, "").strip()
    if env_path:
        if not os.path.isfile(env_path):
            raise ConfigurationError(f"Specified config file {env_path!r} does not exist.")
        return env_path

    for candidate in ("/etc/sigenergy2mqtt.yaml", "/data/sigenergy2mqtt.yaml"):
        if os.path.isfile(candidate):
            return candidate

    return None


def _load_config() -> None:
    """Load active_config from a discovered file, or fall back to env-var / defaults."""
    path = _discover_config_file()
    if path:
        logging.debug("Loading configuration from %s", path)
        active_config.load(path)
    else:
        logging.debug("No config file found; using environment variables and defaults.")
        active_config.reload()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def initialize(args=None) -> bool:
    """
    Initialise the configuration module.

    Returns:
        False if early exit required, otherwise True
    """
    # 1. System setup
    persistent_path = active_config.system_initialize()
    active_config.persistent_state_path = persistent_path

    # 2. Parse CLI
    parsed_args = cli.parse_args(args)

    if parsed_args.show_version:
        return False  # Caller handles sys.exit if appropriate

    # 3. CLI → env (ENV already set takes priority, no duplicate processing logic)
    _promote_cli_to_env(parsed_args)

    # Apply log level immediately from env so subsequent logging is correct.
    log_level_name = os.getenv(const.SIGENERGY2MQTT_LOG_LEVEL)
    if log_level_name:
        level = getattr(logging, log_level_name, None)
        if level is None:
            raise ConfigurationError(f"Unknown log level: {log_level_name!r}")
        active_config.log_level = level
        logging.getLogger().setLevel(level)
        logging.info("sigenergy2mqtt log-level changed to %s", log_level_name)

    # 4. Load config
    try:
        _load_config()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"Error processing configuration: {exc}") from exc

    # 5. Early-exit flags
    if getattr(parsed_args, "clean", False):
        active_config.clean = True

    if getattr(parsed_args, "validate_only", False):
        active_config.validate()  # raises on failure; caller logs + exits
        return False

    if getattr(parsed_args, "discovery_only", False):
        active_config.home_assistant.discovery_only = True

    return True
