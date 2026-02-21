"""
Runtime configuration for sigenergy2mqtt.

Configuration is loaded from a YAML file and optionally overridden by environment
variables.  The single global instance :data:`active_config` is the authoritative
source of truth at runtime.  All other modules should read from this instance rather
than constructing their own.

Typical startup sequence::

    found_path = active_config.system_initialize()
    active_config.persistent_state_path = found_path
    active_config.load(config_filename)
    active_config.validate()

For testing, use :func:`_swap_active_config` to temporarily replace the global::

    with _swap_active_config(Config()) as cfg:
        cfg.load("test_fixture.yaml")
        cfg.validate()
        ...
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from ruamel.yaml import YAML

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import ConsumptionMethod

from . import const, version
from .auto_discovery import scan as auto_discovery_scan
from .home_assistant_config import HomeAssistantConfiguration
from .influxdb_config import InfluxDBConfiguration
from .modbus_config import ModbusConfiguration
from .mqtt_config import MqttConfiguration
from .pvoutput_config import ConsumptionSource, PVOutputConfiguration, VoltageSource
from .validation import check_bool, check_float, check_host, check_int, check_int_list, check_log_level, check_port, check_string, check_string_list


class ConfigurationError(Exception):
    """Raised when the configuration is invalid or cannot be loaded."""


class Config:
    """Holds the complete runtime configuration for sigenergy2mqtt.

    Instances are initialised with sensible defaults via :meth:`_apply_defaults`.
    Configuration is then layered in two passes:

    1. A YAML file loaded by :meth:`load` / :meth:`reload`.
    2. Environment variable overrides applied on top.

    The global singleton :data:`active_config` is the instance used at runtime.
    Direct instantiation is supported for testing via :func:`_swap_active_config`.
    """

    origin: dict[str, str]

    clean: bool
    consumption: ConsumptionMethod
    ems_mode_check: bool
    log_level: int
    metrics_enabled: bool

    language: str

    repeated_state_publish_interval: int

    sanity_check_default_kw: float
    sanity_check_failures_increment: bool

    modbus: list[ModbusConfiguration]
    home_assistant: HomeAssistantConfiguration
    influxdb: InfluxDBConfiguration
    mqtt: MqttConfiguration
    pvoutput: PVOutputConfiguration

    sensor_debug_logging: bool
    sensor_overrides: dict[str, dict[str, bool | int | float | str | list[int] | Any | None]]

    persistent_state_path: Path

    _source: str | None

    def _apply_defaults(self, reset_infrastructure: bool = True):
        """Reset every attribute to its default value.

        Called by :meth:`__init__` and at the start of every :meth:`reload` so that
        a reload always starts from a clean slate rather than accumulating stale state.

        Args:
            reset_infrastructure: If True, resets fields that define the config source
                and persistence (e.g. _source, persistent_state_path).
        """
        self.origin = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}

        self.clean = False
        self.consumption = ConsumptionMethod.TOTAL
        self.ems_mode_check = True
        self.log_level = logging.WARNING
        self.metrics_enabled = True

        self.language = i18n.get_default_language()

        self.repeated_state_publish_interval = 0

        self.sanity_check_default_kw = 500.0
        self.sanity_check_failures_increment = False

        self.modbus = []
        self.home_assistant = HomeAssistantConfiguration()
        self.influxdb = InfluxDBConfiguration()
        self.mqtt = MqttConfiguration()
        self.pvoutput = PVOutputConfiguration()

        self.sensor_debug_logging = False
        self.sensor_overrides = {}

        if reset_infrastructure:
            self._source = None
            self.persistent_state_path = Path(".")

    def __init__(self):
        self._apply_defaults()

    def reset(self):
        """Reset all configuration to defaults, discarding any loaded state.

        Equivalent to constructing a fresh ``Config()`` instance.  Useful in tests
        that share a config object across multiple cases.
        """
        self._apply_defaults()

    def validate(self) -> None:
        """Validate the current configuration, raising on the first error found.

        Checks that at least one Modbus device is configured, then delegates to the
        ``validate()`` method of each sub-configuration object (Modbus devices, MQTT,
        Home Assistant, PVOutput).

        Additionally enforces consistency between ``ems_mode_check`` and the per-device
        register settings: when EMS mode checking is disabled the device must be
        configured for full read/write access without the remote EMS restriction.

        Raises:
            ValueError: If any validation rule is violated.
        """
        if len(self.modbus) == 0:
            raise ValueError("At least one Modbus device must be configured")

        for device in self.modbus:
            device.validate()

            if not self.ems_mode_check:
                if device.registers.no_remote_ems:
                    raise ValueError("When ems_mode_check is disabled, no_remote_ems must be False")
                if not device.registers.read_write:
                    raise ValueError("When ems_mode_check is disabled, read_write must be True")

        self.mqtt.validate()
        self.home_assistant.validate()
        self.pvoutput.validate()

    def get_modbus_log_level(self) -> int:
        """Return the minimum log level across all configured Modbus devices.

        This is used to set the log level of the underlying Modbus library so that
        debug output is shown whenever any device is configured for debug logging.
        Returns ``logging.WARNING`` when no devices are configured.
        """
        if not self.modbus:
            return logging.WARNING
        return min(device.log_level for device in self.modbus)

    def set_modbus_log_level(self, level: int) -> None:
        """Set the log level on every configured Modbus device.

        Args:
            level: A ``logging`` module level constant (e.g. ``logging.DEBUG``).
        """
        for device in self.modbus:
            device.log_level = level

    def load(self, filename: str) -> None:
        """Load configuration from a YAML file and apply environment variable overrides.

        Records *filename* as the configuration source and delegates to :meth:`reload`.
        Subsequent calls to :meth:`reload` will re-read the same file.

        Args:
            filename: Path to the YAML configuration file.
        """
        logging.info(f"Loading configuration from {filename}...")
        self._source = filename
        self.reload()

    def _log_applying(self, name: str, value: Any, override: bool) -> None:
        """Emit a debug log line describing a configuration value being applied.

        Args:
            name: The configuration key name.
            value: The value being applied (logged as-is; callers should redact secrets
                before passing them here).
            override: If ``True``, the log message indicates an env/cli override;
                otherwise it indicates a value from the YAML file.
        """
        source = "override from env/cli" if override else "configuration"
        logging.debug(f"Applying {source}: {name} = {value}")

    def _process_env_key(self, key: str, value: str, overrides: dict[str, Any], auto_discovered: Any):
        """Validate and store a single environment variable into the *overrides* dict.

        This is called for every ``SIGENERGY2MQTT_*`` environment variable found by
        :meth:`_load_from_env`.  Each recognised key is validated and written into the
        appropriate nested location in *overrides*.  Unknown keys produce a warning.
        Keys related to auto-discovery are silently skipped here because they are
        consumed directly in :meth:`reload`.

        Args:
            key: The environment variable name.
            value: The raw string value of the environment variable.
            overrides: The mutable overrides dict that will be passed to
                :meth:`_configure` after all env vars have been processed.
            auto_discovered: The list of auto-discovered device dicts, or ``None``.
                Some env vars (e.g. log level, read/write mode) are propagated to
                auto-discovered devices as well as stored in *overrides*.
        """
        match key:
            case const.SIGENERGY2MQTT_CONSUMPTION:
                overrides["consumption"] = ConsumptionMethod(
                    check_string(
                        value,
                        key,
                        ConsumptionMethod.CALCULATED.value,
                        ConsumptionMethod.TOTAL.value,
                        ConsumptionMethod.GENERAL.value,
                        allow_empty=False,
                        allow_none=False,
                    )
                )
            case const.SIGENERGY2MQTT_DEBUG_SENSOR:
                overrides["sensor-overrides"][check_string(value, key, allow_empty=False, allow_none=False)] = {"debug-logging": True}
                overrides["log-level"] = logging.DEBUG
            case const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX:
                overrides["home-assistant"]["device-name-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX:
                overrides["home-assistant"]["discovery-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX:
                overrides["home-assistant"]["edit-pct-box"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_HASS_ENABLED:
                overrides["home-assistant"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX:
                overrides["home-assistant"]["entity-id-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX:
                overrides["home-assistant"]["unique-id-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS:
                overrides["home-assistant"]["use-simplified-topics"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_BUCKET:
                overrides["influxdb"]["bucket"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_DATABASE:
                overrides["influxdb"]["database"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT:
                overrides["influxdb"]["default-measurement"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY:
                overrides["influxdb"]["load-hass-history"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_ENABLED:
                overrides["influxdb"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_EXCLUDE:
                overrides["influxdb"]["exclude"] = check_string_list(value, key)
            case const.SIGENERGY2MQTT_INFLUX_HOST:
                overrides["influxdb"]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_INFLUX_INCLUDE:
                overrides["influxdb"]["include"] = check_string_list(value, key)
            case const.SIGENERGY2MQTT_INFLUX_LOG_LEVEL:
                overrides["influxdb"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_INFLUX_ORG:
                overrides["influxdb"]["org"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_PASSWORD:
                overrides["influxdb"]["password"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_PORT:
                overrides["influxdb"]["port"] = check_int(value, key, min=1, max=65535)
            case const.SIGENERGY2MQTT_INFLUX_TOKEN:
                overrides["influxdb"]["token"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_USERNAME:
                overrides["influxdb"]["username"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT:
                overrides["influxdb"]["write-timeout"] = check_float(value, key, min=0.1)
            case const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT:
                overrides["influxdb"]["read-timeout"] = check_float(value, key, min=0.1)
            case const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE:
                overrides["influxdb"]["batch-size"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL:
                overrides["influxdb"]["flush-interval"] = check_float(value, key, min=0.1)
            case const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL:
                overrides["influxdb"]["query-interval"] = check_float(value, key, min=0.0)
            case const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES:
                overrides["influxdb"]["max-retries"] = check_int(value, key, min=0)
            case const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS:
                overrides["influxdb"]["pool-connections"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE:
                overrides["influxdb"]["pool-maxsize"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE:
                overrides["influxdb"]["sync-chunk-size"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS:
                overrides["influxdb"]["max-sync-workers"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_LANGUAGE:
                try:
                    overrides["language"] = check_string(value, key, *i18n.get_available_translations(), allow_empty=False, allow_none=False)
                except ValueError:
                    default = i18n.get_default_language()
                    logging.warning(f"Invalid language '{value}' for {key}, falling back to '{default}'")
                    overrides["language"] = default
            case const.SIGENERGY2MQTT_LOG_LEVEL:
                overrides["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID:
                overrides["modbus"][0]["ac-chargers"] = check_int_list(value, key)
            case (
                const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES
            ):
                pass  # Handled in reload()
            case const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID:
                overrides["modbus"][0]["dc-chargers"] = check_int_list(value, key)
            case const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING:
                overrides["modbus"][0]["disable-chunking"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MODBUS_HOST:
                overrides["modbus"][0]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID:
                overrides["modbus"][0]["inverters"] = check_int_list(value, key)
            case const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL:
                overrides["modbus"][0]["log-level"] = check_log_level(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["log-level"] = overrides["modbus"][0]["log-level"]
            case const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS:
                overrides["modbus"][0]["no-remote-ems"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["no-remote-ems"] = overrides["modbus"][0]["no-remote-ems"]
            case const.SIGENERGY2MQTT_MODBUS_PORT:
                overrides["modbus"][0]["port"] = check_port(value, key)
            case const.SIGENERGY2MQTT_MODBUS_READ_ONLY:
                overrides["modbus"][0]["read-only"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["read-only"] = overrides["modbus"][0]["read-only"]
            case const.SIGENERGY2MQTT_MODBUS_READ_WRITE:
                overrides["modbus"][0]["read-write"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["read-write"] = overrides["modbus"][0]["read-write"]
            case const.SIGENERGY2MQTT_MODBUS_RETRIES:
                overrides["modbus"][0]["retries"] = check_int(value, key, min=0)
            case const.SIGENERGY2MQTT_MODBUS_TIMEOUT:
                overrides["modbus"][0]["timeout"] = check_float(value, key, min=0.25)
            case const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY:
                overrides["modbus"][0]["write-only"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["write-only"] = overrides["modbus"][0]["write-only"]
            case const.SIGENERGY2MQTT_MQTT_ANONYMOUS:
                overrides["mqtt"]["anonymous"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_BROKER:
                overrides["mqtt"]["broker"] = check_host(value, key)
            case const.SIGENERGY2MQTT_MQTT_KEEPALIVE:
                overrides["mqtt"]["keepalive"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_MQTT_LOG_LEVEL:
                overrides["mqtt"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_MQTT_PASSWORD:
                overrides["mqtt"]["password"] = value
            case const.SIGENERGY2MQTT_MQTT_PORT:
                overrides["mqtt"]["port"] = check_port(value, key)
            case const.SIGENERGY2MQTT_MQTT_TLS:
                overrides["mqtt"]["tls"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_TLS_INSECURE:
                overrides["mqtt"]["tls-insecure"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_TRANSPORT:
                overrides["mqtt"]["transport"] = check_string(value, key, "tcp", "websockets", allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_MQTT_USERNAME:
                overrides["mqtt"]["username"] = value
            case const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK:
                overrides["no-ems-mode-check"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_NO_METRICS:
                overrides["no-metrics"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_API_KEY:
                overrides["pvoutput"]["api-key"] = check_string(value, key, allow_none=False, allow_empty=False, hex_chars_only=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING:
                overrides["pvoutput"]["calc-debug-logging"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION:
                overrides["pvoutput"]["consumption"] = check_string(
                    value,
                    key,
                    "false",
                    "true",
                    ConsumptionSource.CONSUMPTION.value,
                    ConsumptionSource.IMPORTED.value,
                    ConsumptionSource.NET_OF_BATTERY.value,
                    allow_empty=False,
                    allow_none=False,
                )
            case const.SIGENERGY2MQTT_PVOUTPUT_ENABLED:
                overrides["pvoutput"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS:
                overrides["pvoutput"]["exports"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10:
                overrides["pvoutput"]["v10"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11:
                overrides["pvoutput"]["v11"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12:
                overrides["pvoutput"]["v12"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7:
                overrides["pvoutput"]["v7"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8:
                overrides["pvoutput"]["v8"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9:
                overrides["pvoutput"]["v9"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS:
                overrides["pvoutput"]["imports"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL:
                overrides["pvoutput"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR:
                overrides["pvoutput"]["output-hour"] = check_int(value, key, min=-1, max=23)
            case const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON:
                overrides["pvoutput"]["time-periods"] = json.loads(value)
            case const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID:
                overrides["pvoutput"]["system-id"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC:
                overrides["pvoutput"]["temperature-topic"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING:
                overrides["pvoutput"]["update-debug-logging"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE:
                overrides["pvoutput"]["voltage"] = check_string(value, key, *[v.value for v in VoltageSource])
            case const.SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL:
                overrides["repeated-state-publish-interval"] = check_int(value, key, allow_none=False)
            case const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW:
                overrides["sanity-check-default-kw"] = check_float(value, key, allow_none=False, min=0)
            case const.SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT:
                overrides["sanity-check-failures-increment"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH:
                overrides["modbus"][0]["scan-interval-high"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-high"]:
                            device["scan-interval-high"] = overrides["modbus"][0]["scan-interval-high"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW:
                overrides["modbus"][0]["scan-interval-low"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-low"]:
                            device["scan-interval-low"] = overrides["modbus"][0]["scan-interval-low"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM:
                overrides["modbus"][0]["scan-interval-medium"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-medium"]:
                            device["scan-interval-medium"] = overrides["modbus"][0]["scan-interval-medium"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME:
                overrides["modbus"][0]["scan-interval-realtime"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-realtime"]:
                            device["scan-interval-realtime"] = overrides["modbus"][0]["scan-interval-realtime"]
            case const.SIGENERGY2MQTT_SMARTPORT_ENABLED:
                overrides["modbus"][0]["smart-port"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_SMARTPORT_HOST:
                overrides["modbus"][0]["smart-port"]["module"]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME:
                overrides["modbus"][0]["smart-port"]["module"]["name"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN:
                overrides["modbus"][0]["smart-port"]["mqtt"][0]["gain"] = check_int(value, key, allow_none=True, min=1)
            case const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC:
                overrides["modbus"][0]["smart-port"]["mqtt"][0]["topic"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_PASSWORD:
                overrides["modbus"][0]["smart-port"]["module"]["password"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_PV_POWER:
                overrides["modbus"][0]["smart-port"]["module"]["pv-power"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_USERNAME:
                overrides["modbus"][0]["smart-port"]["module"]["username"] = value
            case _:
                logging.warning(f"UNKNOWN env/cli override: {key} = {'******' if 'PASSWORD' in key or 'API_KEY' in key else value}")

    def _load_from_env(self, overrides: dict[str, Any], auto_discovered: Any = None):
        """Scan environment variables and populate *overrides* with validated values.

        Iterates over all environment variables whose names start with
        ``SIGENERGY2MQTT_`` (excluding ``SIGENERGY2MQTT_CONFIG``) and delegates each
        one to :meth:`_process_env_key`.  Values that are ``None`` or the literal
        string ``"None"`` are skipped.

        Args:
            overrides: The mutable overrides dict to populate.
            auto_discovered: The list of auto-discovered device dicts, or ``None``,
                passed through to :meth:`_process_env_key`.

        Raises:
            ConfigurationError: Wrapping any exception raised by :meth:`_process_env_key`,
                with the offending key name included in the message.
        """
        for key, value in os.environ.items():
            if key.startswith("SIGENERGY2MQTT_") and key != "SIGENERGY2MQTT_CONFIG" and value is not None and value != "None":
                logging.debug(f"Found env/cli override: {key} = {'[REDACTED]' if 'PASSWORD' in key or 'API_KEY' in key else value}")
                try:
                    self._process_env_key(key, value, overrides, auto_discovered)
                except Exception as e:
                    raise ConfigurationError(f"Error processing override '{key}'") from e

    def _apply_auto_discovery(self, auto_discovered: Any):
        """Merge auto-discovered Modbus devices into :attr:`modbus`.

        For each device returned by the auto-discovery scan:

        - If an existing :class:`ModbusConfiguration` matches the discovered host/port
          (or has a blank host acting as a wildcard), the existing entry is updated with
          the discovered device IDs.
        - Otherwise a new :class:`ModbusConfiguration` is appended to :attr:`modbus`.

        Args:
            auto_discovered: A list of device dicts as returned by the auto-discovery
                scan, each containing at least ``host`` and ``port`` keys.  Non-list
                values are silently ignored.
        """
        if not isinstance(auto_discovered, list):
            return
        for device in auto_discovered:
            updated = False
            for defined in self.modbus:
                if (defined.host == device.get("host") or defined.host == "") and defined.port == device.get("port"):
                    if defined.host == "":
                        defined.host = device.get("host", "")
                        defined.port = device.get("port", 502)
                        logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                    else:
                        logging.info(f"Auto-discovered found configured Modbus device: {device.get('host')}:{device.get('port')}, updating with discovered device IDs")
                    defined.configure(device, override=True, auto_discovered=True)
                    updated = True
                    break
            if not updated:
                logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                new_device = ModbusConfiguration()
                new_device.configure(device, override=True, auto_discovered=True)
                self.modbus.append(new_device)

    def _configure(self, data: dict, override: bool = False) -> None:
        """Apply a dictionary of configuration values to this instance.

        Used for both the primary YAML load and the env/cli override pass.  Each
        top-level key in *data* is matched and its value is validated and assigned to
        the appropriate attribute or sub-configuration object.

        Args:
            data: A mapping of configuration keys to values.  Must be a ``dict``;
                passing any other type raises ``ValueError`` immediately.
            override: If ``True``, debug log messages will indicate the values are
                env/cli overrides rather than primary configuration.

        Raises:
            ValueError: If *data* is not a dict, if a key is unrecognised, or if any
                value fails validation.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Configuration data must be a mapping, got {type(data).__name__}")
        for name, value in data.items():
            match name:
                case "consumption":
                    self._log_applying(name, value, override)
                    self.consumption = ConsumptionMethod(
                        check_string(
                            value,
                            name,
                            ConsumptionMethod.CALCULATED.value,
                            ConsumptionMethod.TOTAL.value,
                            ConsumptionMethod.GENERAL.value,
                            allow_empty=False,
                            allow_none=False,
                        )
                    )
                case "language":
                    self._log_applying(name, value, override)
                    try:
                        self.language = check_string(value, name, *i18n.get_available_translations(), allow_empty=False, allow_none=False)
                    except ValueError:
                        default = i18n.get_default_language()
                        logging.warning(f"Invalid language '{value}' for {name}, falling back to '{default}'")
                        self.language = default
                case "home-assistant":
                    self.home_assistant.configure(value, override)
                case "log-level":
                    self._log_applying(name, value, override)
                    self.log_level = check_log_level(value, name)
                case "mqtt":
                    self.mqtt.configure(value, override)
                case "modbus":
                    if not isinstance(value, list):
                        raise ValueError("modbus configuration element must contain a list of Sigenergy hosts")
                    for index, config in enumerate(value):
                        if isinstance(config, dict):
                            if len(self.modbus) <= index:
                                device = ModbusConfiguration()
                                self.modbus.append(device)
                            else:
                                device = self.modbus[index]
                            device.configure(config, override)
                case "no-ems-mode-check":
                    self._log_applying(name, value, override)
                    self.ems_mode_check = not check_bool(value, name)
                case "no-metrics":
                    self._log_applying(name, value, override)
                    self.metrics_enabled = not check_bool(value, name)
                case "pvoutput":
                    self.pvoutput.configure(value, override)
                case "influxdb":
                    self.influxdb.configure(value, override)
                case "repeated-state-publish-interval":
                    self._log_applying(name, value, override)
                    self.repeated_state_publish_interval = check_int(value, name, allow_none=False)
                case "sanity-check-default-kw":
                    self._log_applying(name, value, override)
                    self.sanity_check_default_kw = check_float(value, name, allow_none=False, min=0)
                case "sanity-check-failures-increment":
                    self._log_applying(name, value, override)
                    self.sanity_check_failures_increment = check_bool(value, name)
                case "sensor-debug-logging":
                    self._log_applying(name, value, override)
                    self.sensor_debug_logging = check_bool(value, name)
                case "sensor-overrides":
                    if value is None:
                        pass
                    elif not isinstance(value, dict):
                        raise ValueError("sensor-overrides configuration elements must contain a list of class names, each followed by options and their values")
                    else:
                        for sensor, settings in value.items():
                            self.sensor_overrides[sensor] = {}
                            for p, v in settings.items():
                                logging.debug(f"Applying configuration sensor-overrides: {sensor}.{p} = {v}")
                                ctx = f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -"
                                match p:
                                    case "debug-logging":
                                        self.sensor_overrides[sensor][p] = check_bool(v, ctx)
                                    case "gain":
                                        self.sensor_overrides[sensor][p] = check_int(v, ctx, allow_none=True, min=1)
                                    case "icon":
                                        self.sensor_overrides[sensor][p] = check_string(v, ctx, allow_none=False, starts_with="mdi:")
                                    case "max-failures":
                                        self.sensor_overrides[sensor][p] = check_int(v, ctx, allow_none=True, min=1)
                                    case "max-failures-retry-interval":
                                        self.sensor_overrides[sensor][p] = check_int(v, ctx, allow_none=False, min=0)
                                    case "precision":
                                        self.sensor_overrides[sensor][p] = check_int(v, ctx, allow_none=False, min=0, max=6)
                                    case "publishable":
                                        self.sensor_overrides[sensor][p] = check_bool(v, ctx)
                                    case "publish-raw":
                                        self.sensor_overrides[sensor][p] = check_bool(v, ctx)
                                    case "scan-interval":
                                        self.sensor_overrides[sensor][p] = check_int(v, ctx, allow_none=False, min=1)
                                    case "sanity-check-max-value":
                                        self.sensor_overrides[sensor][p] = check_float(v, ctx, allow_none=False)
                                    case "sanity-check-min-value":
                                        self.sensor_overrides[sensor][p] = check_float(v, ctx, allow_none=False)
                                    case "sanity-check-delta":
                                        self.sensor_overrides[sensor][p] = check_bool(v, ctx)
                                    case "unit-of-measurement":
                                        self.sensor_overrides[sensor][p] = check_string(v, ctx, allow_none=False)
                                    case _:
                                        raise ValueError(f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} - property is not known or not overridable")
                case _:
                    raise ValueError(f"Configuration contains unknown element '{name}'")

    def reload(self) -> None:
        """Reload configuration from the YAML source file and re-apply all overrides.

        The full load sequence on every call:

        1. Reset all attributes to defaults via :meth:`_apply_defaults`.
        2. If a source file was set by :meth:`load`, parse and apply it.
        3. Run Modbus auto-discovery if requested (``force``) or not yet cached
           (``once``), writing results to a YAML cache file for subsequent runs.
        4. Apply environment variable overrides on top.
        5. Load the i18n translation for the resolved language.
        6. Merge auto-discovered devices into :attr:`modbus`.

        Raises:
            ConfigurationError: If an environment variable override cannot be processed.
            OSError: If the YAML source file or auto-discovery cache cannot be read or
                written.
        """
        self._apply_defaults(reset_infrastructure=False)

        overrides: dict[str, Any] = {
            "home-assistant": {},
            "mqtt": {},
            "modbus": [{"smart-port": {"mqtt": [{}], "module": {}}}],
            "influxdb": {},
            "pvoutput": {},
            "sensor-overrides": {},
        }

        if self._source:
            _yaml = YAML(typ="safe", pure=True)
            with open(self._source, "r") as f:
                data = _yaml.load(f)
            if data:
                self._configure(data)
            else:
                logging.warning(f"Ignored configuration file {self._source} because it contains no keys?")

        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(self.persistent_state_path, "auto-discovery.yaml")
        auto_discovered = None

        if auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file()):
            port = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, "502"))
            ping_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, "0.5"))
            modbus_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, "0.25"))
            modbus_retries = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, "0"))
            logging.info(f"Auto-discovery required, scanning for Sigenergy devices ({port=} {ping_timeout=} {modbus_timeout=} {modbus_retries=})...")
            auto_discovered = self._run_auto_discovery(port, ping_timeout, modbus_timeout, modbus_retries)
            if len(auto_discovered) > 0:
                with open(auto_discovery_cache, "w") as f:
                    _yaml = YAML(typ="safe", pure=True)
                    _yaml.dump(auto_discovered, f)
        elif auto_discovery == "once" and auto_discovery_cache.is_file():
            logging.info("Auto-discovery already completed, using cached results.")
            with open(auto_discovery_cache, "r") as f:
                auto_discovered = YAML(typ="safe", pure=True).load(f)

        self._load_from_env(overrides, auto_discovered)
        self._configure(overrides, True)

        i18n.load(self.language)

        if auto_discovered:
            self._apply_auto_discovery(auto_discovered)

    def _run_auto_discovery(self, port: int, ping_timeout: float, modbus_timeout: float, modbus_retries: int, timeout: float = 120.0) -> list:
        """Execute the async auto-discovery scan, handling event loop edge cases.

        If no event loop is running, uses asyncio.run(). If called from within
        already-running async code (e.g. during a reload triggered by a signal
        handler), submits the coroutine to the running loop via
        run_coroutine_threadsafe and waits up to *timeout* seconds.

        Args:
            port: The Modbus TCP port to scan.
            ping_timeout: Seconds to wait for an ICMP ping response.
            modbus_timeout: Seconds to wait for a Modbus TCP response.
            modbus_retries: Number of Modbus connection retries per host.
            timeout: Maximum seconds to wait when submitting to a running loop.

        Returns:
            A list of discovered device dicts, or an empty list on failure.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            # Normal case: no event loop running, asyncio.run() is safe.
            try:
                return asyncio.run(auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries))
            except Exception:
                logging.exception("Auto-discovery failed")
                return []

        # A loop is already running (e.g. called from a signal handler or sync
        # code invoked from async context). Submit to the running loop from this
        # thread and wait with a finite timeout to avoid hanging indefinitely.
        try:
            future = asyncio.run_coroutine_threadsafe(auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries), loop)
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()  # pyrefly: ignore - future is always bound before .result() raises.
            logging.error("Auto-discovery timed out after %.1fs", timeout)
            return []
        except Exception:
            logging.exception("Auto-discovery failed when submitting to running loop")
            return []

    def version(self) -> str:
        """Return the current sigenergy2mqtt version string."""
        return version.__version__

    @classmethod
    def system_initialize(cls):
        """Perform one-time system-level initialisation before configuration is loaded.

        This classmethod should be called once at application startup, before
        constructing or loading any :class:`Config` instance.  It:

        1. Configures the root logger with an appropriate format (TTY, Docker, or
           plain syslog-style) via :func:`_setup_logging`.
        2. Logs the application and Python version.
        3. Enforces the minimum Python version requirement (3.12+).
        4. Locates or creates the persistent state directory via
           :func:`_create_persistent_state_path`.
        5. Removes stale state files older than 7 days via :func:`_clean_stale_files`.

        Returns:
            The resolved :class:`~pathlib.Path` to the persistent state directory.

        Raises:
            ConfigurationError: If the Python version requirement is not met, or if no
                writable directory can be found for persistent state storage.
        """
        _setup_logging()

        logger = logging.getLogger("root")
        logger.info(f"Release {version.__version__} (Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")

        min_version = (3, 12)
        if sys.version_info < min_version:
            raise ConfigurationError(f"Python {min_version[0]}.{min_version[1]} or higher is required!")

        found_path = _create_persistent_state_path()
        _clean_stale_files(found_path)
        return found_path


def _setup_logging() -> None:
    """Configure the root logger with a format appropriate to the runtime environment.

    Three formats are used:

    - **TTY**: includes timestamp and ``sigenergy2mqtt:`` prefix — for interactive use.
    - **Docker**: includes timestamp but no prefix — for structured container log collectors.
    - **Other**: no timestamp — for init systems (systemd, etc.) that add their own.
    """
    if os.isatty(sys.stdout.fileno()):
        fmt = "{asctime} {levelname:<8} sigenergy2mqtt:{module:.<15.15}{lineno:04d} {message}"
    else:
        cgroup = Path("/proc/self/cgroup")
        in_docker = Path("/.dockerenv").is_file() or (cgroup.is_file() and "docker" in cgroup.read_text())
        fmt = "{asctime} {levelname:<8} {module:.<15.15}{lineno:04d} {message}" if in_docker else "{levelname:<8} {module:.<15.15}{lineno:04d} {message}"
    logging.basicConfig(format=fmt, level=logging.INFO, style="{")


def _create_persistent_state_path() -> Path:
    """Find a writable base directory and create the ``sigenergy2mqtt`` subdirectory.

    Candidate base directories are tried in order: ``/data/``, ``/var/lib/``, the
    current user's home directory, and ``/tmp/``.  The first writable candidate is
    used.

    Returns:
        The resolved absolute :class:`~pathlib.Path` of the persistent state directory.

    Raises:
        ConfigurationError: If none of the candidate directories are writable.
    """
    candidates = ["/data/", "/var/lib/", str(Path.home()), "/tmp/"]
    for base in candidates:
        if os.path.isdir(base) and os.access(base, os.W_OK):
            path = Path(base, "sigenergy2mqtt")
            if not path.is_dir():
                logging.info(f"Persistent state folder '{path}' created")
                path.mkdir()
            else:
                logging.debug(f"Persistent state folder '{path}' already exists")
            return path.resolve()
    raise ConfigurationError("Unable to create persistent state folder!")


def _clean_stale_files(path: Path) -> None:
    """Remove files from *path* that have not been modified in the last 7 days.

    The following files are always retained regardless of age:

    - ``".current-version"``
    - Files with the suffix ``.yaml``, ``.publishable``, or ``.token``

    Args:
        path: The directory to clean.  Only regular files are considered;
            subdirectories are ignored.
    """
    threshold_time = time.time() - (7 * 86400)
    _keep_suffixes = {".yaml", ".publishable", ".token"}
    _keep_names = {".current-version"}
    for file in path.iterdir():
        if not file.is_file():
            continue
        stat = file.stat()
        if stat.st_mtime < threshold_time and file.name not in _keep_names and file.suffix not in _keep_suffixes:
            try:
                file.unlink()
                logging.info(f"Removed stale state file: {file} (last modified: {time.ctime(stat.st_mtime)})")
            except (PermissionError, OSError) as e:
                logging.error(f"Failed to remove stale state file: {file} ({e})")


class _ConfigProxy:
    """A proxy for the active Config instance that allows it to be swapped.

    This ensures that internal modules which do 'from sigenergy2mqtt.config import active_config'
    continue to refer to the same proxy object even when the underlying Config is replaced
    by _swap_active_config.
    """

    def __init__(self, config: Config):
        # Use super().__setattr__ to avoid recursion
        super().__setattr__("_config", config)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._config, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_config":
            super().__setattr__(name, value)
        else:
            setattr(self._config, name, value)

    def __delattr__(self, name: str) -> None:
        if name == "_config":
            super().__delattr__(name)
        else:
            delattr(self._config, name)

    def __repr__(self) -> str:
        return f"<ConfigProxy for {self._config!r}>"

    def __dir__(self):
        return dir(self._config)


@contextmanager
def _swap_active_config(new_config: Config) -> Generator[Config, None, None]:
    """Context manager that temporarily replaces the global :data:`active_config`.

    Intended for use in tests that need to load a fixture configuration without
    affecting the global singleton used by production code.  The original
    ``active_config`` is restored when the context exits, even if an exception is
    raised.

    Args:
        new_config: The :class:`Config` instance to install as the active config.

    Yields:
        *new_config*, so callers can use ``as`` to receive it::

            with _swap_active_config(Config()) as cfg:
                cfg.load("test_fixture.yaml")
                ...
    """
    global active_config
    if isinstance(active_config, _ConfigProxy):
        old = active_config._config
        active_config._config = new_config
        try:
            yield new_config
        finally:
            active_config._config = old
    else:
        # Fallback for when active_config is not proxied (e.g. during some edge cases in tests)
        old = active_config
        active_config = new_config
        try:
            yield new_config
        finally:
            active_config = old


# Global singleton — the authoritative configuration instance at runtime.
active_config = _ConfigProxy(Config())
