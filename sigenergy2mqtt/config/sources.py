"""
Custom pydantic-settings sources.

Three sources are registered, in priority order:
  1. EnvSettingsSource                  — SIGENERGY2MQTT_* environment variables
  2. RuamelYamlSettingsSource           — main YAML config file
  3. AutoDiscoveryYamlSettingsSource    — auto-discovery output YAML
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from sigenergy2mqtt.config import const
from sigenergy2mqtt.config.coerce import _bool, _float, _int, _int_list, _invert_bool, _set, _str_list

# ---------------------------------------------------------------------------
# YAML sources
# ---------------------------------------------------------------------------


class RuamelYamlSettingsSource(PydanticBaseSettingsSource):
    """
    Loads settings from a YAML file using ruamel.yaml.

    File path resolution order:
      1. SIGENERGY2MQTT_CONFIG environment variable
      2. yaml_file kwarg passed at construction
      3. 'sigenergy2mqtt.yaml' in the current working directory
    """

    def __init__(self, settings_cls: type[BaseSettings], yaml_file: str | Path | None = None):
        super().__init__(settings_cls)
        self._yaml_file = yaml_file

    def _resolve_yaml_path(self) -> Path | None:
        path = os.environ.get(const.SIGENERGY2MQTT_CONFIG) or self._yaml_file or "sigenergy2mqtt.yaml"
        p = Path(path)
        return p if p.exists() else None

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        path = self._resolve_yaml_path()
        if path is None:
            return {}
        from ruamel.yaml import YAML

        yaml = YAML()
        with open(path, "r") as f:
            data = yaml.load(f)
        return dict(data) if data else {}


class AutoDiscoveryYamlSettingsSource(PydanticBaseSettingsSource):
    """
    Loads the modbus device list produced by auto-discovery.

    The discovery file contains either a bare list or a dict with a 'modbus' key.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        discovery_yaml: str | Path | None = None,
    ):
        super().__init__(settings_cls)
        self._discovery_yaml = Path(discovery_yaml) if discovery_yaml else None

    def _load(self) -> list[dict[str, Any]]:
        if self._discovery_yaml is None or not self._discovery_yaml.exists():
            return []
        from ruamel.yaml import YAML

        yaml = YAML()
        with open(self._discovery_yaml, "r") as f:
            data = yaml.load(f)
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "modbus" in data:
            return data["modbus"]
        return []

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        devices = self._load()
        return {"discovery_modbus": devices} if devices else {}


# ---------------------------------------------------------------------------
# Environment variable source
# ---------------------------------------------------------------------------


class EnvSettingsSource(PydanticBaseSettingsSource):
    """
    Maps SIGENERGY2MQTT_* environment variables onto the nested Settings model
    using the typed constants from const.py as the canonical key names.
    """

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:  # noqa: C901
        g = os.environ.get
        result: dict[str, Any] = {}

        # ── Top-level ────────────────────────────────────────────────────────
        _set(result, "log_level", g(const.SIGENERGY2MQTT_LOG_LEVEL))
        _set(result, "language", g(const.SIGENERGY2MQTT_LANGUAGE))
        _set(result, "consumption", g(const.SIGENERGY2MQTT_CONSUMPTION))
        _set(result, "repeated_state_publish_interval", _int(g(const.SIGENERGY2MQTT_REPEATED_STATE_PUBLISH_INTERVAL)))
        _set(result, "sanity_check_default_kw", _float(g(const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW)))
        _set(result, "sanity_check_failures_increment", _bool(g(const.SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT)))
        _set(result, "ems_mode_check", _invert_bool(g(const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK)))
        _set(result, "metrics_enabled", _invert_bool(g(const.SIGENERGY2MQTT_NO_METRICS)))
        _set(result, "sensor_debug_logging", _bool(g(const.SIGENERGY2MQTT_DEBUG_SENSOR)))

        debug_sensor_name = g(const.SIGENERGY2MQTT_DEBUG_SENSOR)
        if debug_sensor_name and debug_sensor_name.lower() not in ("none", ""):
            overrides = result.get("sensor_overrides", {})
            overrides[debug_sensor_name] = {"debug-logging": True}
            result["sensor_overrides"] = overrides
            result["log_level"] = logging.DEBUG

        # ── Home Assistant ───────────────────────────────────────────────────
        hass: dict[str, Any] = {}
        _set(hass, "enabled", _bool(g(const.SIGENERGY2MQTT_HASS_ENABLED)))
        _set(hass, "device_name_prefix", g(const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX))
        _set(hass, "discovery_prefix", g(const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX))
        _set(hass, "entity_id_prefix", g(const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX))
        _set(hass, "unique_id_prefix", g(const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX))
        _set(hass, "sigenergy_local_modbus_naming", _bool(g(const.SIGENERGY2MQTT_HASS_SIGENERGY_LOCAL_MODBUS_NAMING)))
        _set(hass, "use_simplified_topics", _bool(g(const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS)))
        _set(hass, "edit_percentage_with_box", _bool(g(const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX)))
        if hass:
            result["home_assistant"] = hass

        # ── MQTT ─────────────────────────────────────────────────────────────
        mqtt: dict[str, Any] = {}
        _set(mqtt, "broker", g(const.SIGENERGY2MQTT_MQTT_BROKER))
        _set(mqtt, "port", _int(g(const.SIGENERGY2MQTT_MQTT_PORT)))
        _set(mqtt, "keepalive", _int(g(const.SIGENERGY2MQTT_MQTT_KEEPALIVE)))
        _set(mqtt, "tls", _bool(g(const.SIGENERGY2MQTT_MQTT_TLS)))
        _set(mqtt, "tls_insecure", _bool(g(const.SIGENERGY2MQTT_MQTT_TLS_INSECURE)))
        _set(mqtt, "transport", g(const.SIGENERGY2MQTT_MQTT_TRANSPORT))
        _set(mqtt, "anonymous", _bool(g(const.SIGENERGY2MQTT_MQTT_ANONYMOUS)))
        _set(mqtt, "username", g(const.SIGENERGY2MQTT_MQTT_USERNAME))
        _set(mqtt, "password", g(const.SIGENERGY2MQTT_MQTT_PASSWORD))
        _set(mqtt, "log_level", g(const.SIGENERGY2MQTT_MQTT_LOG_LEVEL))
        if mqtt:
            result["mqtt"] = mqtt

        # ── Modbus ───────────────────────────────────────────────────────────
        modbus: dict[str, Any] = {}
        _set(modbus, "host", g(const.SIGENERGY2MQTT_MODBUS_HOST))
        _set(modbus, "port", _int(g(const.SIGENERGY2MQTT_MODBUS_PORT)))
        _set(modbus, "timeout", _float(g(const.SIGENERGY2MQTT_MODBUS_TIMEOUT)))
        _set(modbus, "retries", _int(g(const.SIGENERGY2MQTT_MODBUS_RETRIES)))
        _set(modbus, "disable_chunking", _bool(g(const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING)))
        _set(modbus, "log_level", g(const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL))
        _set(modbus, "read_only", _bool(g(const.SIGENERGY2MQTT_MODBUS_READ_ONLY)))
        _set(modbus, "read_write", _bool(g(const.SIGENERGY2MQTT_MODBUS_READ_WRITE)))
        _set(modbus, "write_only", _bool(g(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY)))
        _set(modbus, "no_remote_ems", _bool(g(const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS)))
        _set(modbus, "inverters", _int_list(g(const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID)))
        _set(modbus, "ac_chargers", _int_list(g(const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID)))
        _set(modbus, "dc_chargers", _int_list(g(const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID)))
        _set(modbus, "scan_interval_low", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW)))
        _set(modbus, "scan_interval_medium", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM)))
        _set(modbus, "scan_interval_high", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH)))
        _set(modbus, "scan_interval_realtime", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME)))

        # Smart-port
        sp: dict[str, Any] = {}
        _set(sp, "enabled", _bool(g(const.SIGENERGY2MQTT_SMARTPORT_ENABLED)))
        sp_mod: dict[str, Any] = {}
        _set(sp_mod, "name", g(const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME))
        _set(sp_mod, "host", g(const.SIGENERGY2MQTT_SMARTPORT_HOST))
        _set(sp_mod, "username", g(const.SIGENERGY2MQTT_SMARTPORT_USERNAME))
        _set(sp_mod, "password", g(const.SIGENERGY2MQTT_SMARTPORT_PASSWORD))
        _set(sp_mod, "pv_power", g(const.SIGENERGY2MQTT_SMARTPORT_PV_POWER))
        if sp_mod:
            sp["module"] = sp_mod
        sp_mqtt: dict[str, Any] = {}
        _set(sp_mqtt, "topic", g(const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC))
        _set(sp_mqtt, "gain", _int(g(const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN)))
        if sp_mqtt:
            sp["mqtt"] = [sp_mqtt]
        if sp:
            modbus["smartport"] = sp

        if modbus:
            result["modbus_env_override"] = modbus

        # ── PVOutput ─────────────────────────────────────────────────────────
        pvo: dict[str, Any] = {}
        _set(pvo, "enabled", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_ENABLED)))
        _set(pvo, "api_key", g(const.SIGENERGY2MQTT_PVOUTPUT_API_KEY))
        _set(pvo, "system_id", g(const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID))
        _set(pvo, "consumption", g(const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION))
        _set(pvo, "exports", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS)))
        _set(pvo, "imports", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS)))
        _set(pvo, "output_hour", _int(g(const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR)))
        _set(pvo, "temperature_topic", g(const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC))
        _set(pvo, "voltage", g(const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE))
        _set(pvo, "v7", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7))
        _set(pvo, "v8", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8))
        _set(pvo, "v9", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9))
        _set(pvo, "v10", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10))
        _set(pvo, "v11", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11))
        _set(pvo, "v12", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12))
        _set(pvo, "log_level", g(const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL))
        _set(pvo, "calc_debug_logging", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING)))
        _set(pvo, "update_debug_logging", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING)))
        periods_json = g(const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON)
        if periods_json:
            pvo["time-periods"] = json.loads(periods_json)
        if pvo:
            result["pvoutput"] = pvo

        # ── InfluxDB ─────────────────────────────────────────────────────────
        influx: dict[str, Any] = {}
        _set(influx, "enabled", _bool(g(const.SIGENERGY2MQTT_INFLUX_ENABLED)))
        _set(influx, "host", g(const.SIGENERGY2MQTT_INFLUX_HOST))
        _set(influx, "port", _int(g(const.SIGENERGY2MQTT_INFLUX_PORT)))
        _set(influx, "username", g(const.SIGENERGY2MQTT_INFLUX_USERNAME))
        _set(influx, "password", g(const.SIGENERGY2MQTT_INFLUX_PASSWORD))
        _set(influx, "database", g(const.SIGENERGY2MQTT_INFLUX_DATABASE))
        _set(influx, "org", g(const.SIGENERGY2MQTT_INFLUX_ORG))
        _set(influx, "token", g(const.SIGENERGY2MQTT_INFLUX_TOKEN))
        _set(influx, "bucket", g(const.SIGENERGY2MQTT_INFLUX_BUCKET))
        _set(influx, "default_measurement", g(const.SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT))
        _set(influx, "load_hass_history", _bool(g(const.SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY)))
        _set(influx, "include", _str_list(g(const.SIGENERGY2MQTT_INFLUX_INCLUDE)))
        _set(influx, "exclude", _str_list(g(const.SIGENERGY2MQTT_INFLUX_EXCLUDE)))
        _set(influx, "log_level", g(const.SIGENERGY2MQTT_INFLUX_LOG_LEVEL))
        _set(influx, "write_timeout", _float(g(const.SIGENERGY2MQTT_INFLUX_WRITE_TIMEOUT)))
        _set(influx, "read_timeout", _float(g(const.SIGENERGY2MQTT_INFLUX_READ_TIMEOUT)))
        _set(influx, "batch_size", _int(g(const.SIGENERGY2MQTT_INFLUX_BATCH_SIZE)))
        _set(influx, "flush_interval", _float(g(const.SIGENERGY2MQTT_INFLUX_FLUSH_INTERVAL)))
        _set(influx, "query_interval", _float(g(const.SIGENERGY2MQTT_INFLUX_QUERY_INTERVAL)))
        _set(influx, "max_retries", _int(g(const.SIGENERGY2MQTT_INFLUX_MAX_RETRIES)))
        _set(influx, "pool_connections", _int(g(const.SIGENERGY2MQTT_INFLUX_POOL_CONNECTIONS)))
        _set(influx, "pool_maxsize", _int(g(const.SIGENERGY2MQTT_INFLUX_POOL_MAXSIZE)))
        _set(influx, "sync_chunk_size", _int(g(const.SIGENERGY2MQTT_INFLUX_SYNC_CHUNK_SIZE)))
        _set(influx, "max_sync_workers", _int(g(const.SIGENERGY2MQTT_INFLUX_MAX_SYNC_WORKERS)))
        if influx:
            result["influxdb"] = influx

        return result


def _auto_discovery_env_values(getenv: Any, include_modbus_port: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    _set(result, "modbus_auto_discovery", getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY))
    _set(result, "modbus_auto_discovery_timeout", _float(getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT)))
    _set(result, "modbus_auto_discovery_ping_timeout", _float(getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT)))
    _set(result, "modbus_auto_discovery_retries", _int(getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES)))
    if include_modbus_port:
        _set(result, "modbus_port", _int(getenv(const.SIGENERGY2MQTT_MODBUS_PORT)))
    return result


class AutoDiscoveryEnvSettingsSource(PydanticBaseSettingsSource):
    """Maps only auto-discovery related SIGENERGY2MQTT_* variables."""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return _auto_discovery_env_values(os.environ.get, include_modbus_port=True)
