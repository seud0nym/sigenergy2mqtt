"""
sigenergy2mqtt configuration via pydantic-settings.

Priority (highest → lowest):
  1. Environment variables  (SIGENERGY2MQTT_*)
  2. YAML config file       (path set by SIGENERGY2MQTT_CONFIG, default: sigenergy2mqtt.yaml)
  3. Auto-discovery YAML    (produced by auto-discovery; merged by host into modbus list)
  4. Defaults in this file

Usage:
    from settings import Settings
    cfg = Settings()

    cfg.mqtt.broker
    cfg.home_assistant.enabled
    cfg.modbus[0].host
    cfg.modbus[0].registers.read_only
    cfg.modbus[0].scan_interval.low
    cfg.modbus[0].smartport.enabled
    cfg.pvoutput.tariffs
    cfg.influxdb.host
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, InitSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import WEEKDAYS, WEEKENDS, ConsumptionMethod, ConsumptionSource, OutputField, StatusField, Tariff, TariffType, TimePeriod, VoltageSource

from . import const
from .validation import check_bool, check_date, check_float, check_int, check_string, check_time

# ---------------------------------------------------------------------------
# Helper: every sub-model accepts both alias (YAML kebab key) and field name
# ---------------------------------------------------------------------------
_SUB = ConfigDict(populate_by_name=True)

# Modbus env-var keys that are propagated to ALL devices (including auto-discovered)
_PROPAGATABLE_MODBUS_KEYS: Final = frozenset(
    {
        "log_level",
        "no_remote_ems",
        "read_only",
        "read_write",
        "write_only",
        "scan_interval_low",
        "scan_interval_medium",
        "scan_interval_high",
        "scan_interval_realtime",
    }
)


# ---------------------------------------------------------------------------
# Shared field validators
# ---------------------------------------------------------------------------


def validate_log_level(v: str | int) -> int:
    """Accept a level name (e.g. "WARNING") or int and return the int level."""
    if isinstance(v, int):
        return v
    level = logging.getLevelNamesMapping().get(v.upper())
    if level is None:
        valid = ", ".join(logging.getLevelNamesMapping().keys())
        raise ValueError(f"invalid log level {v!r}, must be one of: {valid}")
    return level


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class HomeAssistantConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    device_name_prefix: str = Field("", alias="device-name-prefix")
    discovery_prefix: str = Field("homeassistant", alias="discovery-prefix")
    entity_id_prefix: str = Field("sigen", alias="entity-id-prefix")
    unique_id_prefix: str = Field("sigen", alias="unique-id-prefix")
    use_simplified_topics: bool = Field(False, alias="use-simplified-topics")
    edit_percentage_with_box: bool = Field(False, alias="edit-pct-box")
    discovery_only: bool = Field(False, alias="discovery-only")
    republish_discovery_interval: int = Field(0, alias="republish-discovery-interval", ge=0)
    enabled_by_default: bool = Field(False, alias="sensors-enabled-by-default")

    @model_validator(mode="after")
    def check_required_when_enabled(self) -> "HomeAssistantConfig":
        if self.enabled:
            if not self.discovery_prefix:
                raise ValueError("home-assistant.discovery-prefix must be provided")
            if not self.entity_id_prefix:
                raise ValueError("home-assistant.entity-id-prefix must be provided")
            if not self.unique_id_prefix:
                raise ValueError("home-assistant.unique-id-prefix must be provided")
        return self


class MqttConfig(BaseModel):
    model_config = _SUB

    broker: str = Field("127.0.0.1", alias="broker")
    port: int = Field(1883, alias="port", ge=1, le=65535)
    keepalive: int = Field(60, alias="keepalive", ge=1)
    retry_delay: int = Field(30)
    tls: bool = Field(False, alias="tls")
    tls_insecure: bool = Field(False, alias="tls-insecure")
    transport: str = Field("tcp", alias="transport", pattern=r"^(tcp|websockets)$")
    anonymous: bool = Field(True, alias="anonymous")
    username: Optional[str] = Field(None, alias="username")
    password: Optional[str] = Field(None, alias="password")
    client_id_prefix: str = Field(default_factory=lambda: f"sigenergy2mqtt_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))}")
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)

    @model_validator(mode="after")
    def apply_tls_port_default(self) -> "MqttConfig":
        """When TLS is enabled and the port is still the plain default, switch to 8883."""
        if self.tls and self.port == 1883:
            self.port = 8883
        return self

    @model_validator(mode="after")
    def check_auth(self) -> "MqttConfig":
        if not self.anonymous:
            if not self.username:
                raise ValueError("mqtt.username must be provided when mqtt.anonymous is false")
            if not self.password:
                raise ValueError("mqtt.password must be provided when mqtt.anonymous is false")
        return self


class SmartPortMqttEntry(BaseModel):
    model_config = _SUB

    topic: Optional[str] = Field(None, alias="topic")
    gain: int = Field(1, alias="gain", ge=1)


class SmartPortModule(BaseModel):
    model_config = _SUB

    name: str = Field("", alias="name")
    host: str = Field("", alias="host")
    port: Optional[int] = Field(None, alias="port")
    username: str = Field("", alias="username")
    password: str = Field("", alias="password")
    pv_power: str = Field("", alias="pv-power")
    testing: bool = Field(False, alias="testing")


class SmartPortConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    module: SmartPortModule = Field(default_factory=SmartPortModule, alias="module")  # type: ignore[reportCallIssue]
    mqtt: list[SmartPortMqttEntry] = Field(default_factory=list, alias="mqtt")

    @model_validator(mode="after")
    def check_enabled(self) -> "SmartPortConfig":
        if self.enabled and not self.module.name and not self.mqtt:
            raise ValueError("modbus.smart-port.enabled, but no module name or MQTT topics configured")
        return self


class RegisterAccess(BaseModel):
    """Mirrors the RegisterAccess dataclass; nested inside ModbusConfig."""

    model_config = _SUB

    no_remote_ems: bool = Field(False, alias="no-remote-ems")
    read_only: bool = Field(True, alias="read-only")
    read_write: bool = Field(True, alias="read-write")
    write_only: bool = Field(True, alias="write-only")


class ScanInterval(BaseModel):
    """Mirrors the ScanInterval dataclass; nested inside ModbusConfig."""

    model_config = _SUB

    low: int = Field(600, ge=1)
    medium: int = Field(60, ge=1)
    high: int = Field(10, ge=1)
    realtime: int = Field(5, ge=1)


class ModbusConfig(BaseModel):
    model_config = _SUB

    host: str = Field("", alias="host")
    port: int = Field(502, alias="port", ge=1, le=65535)
    timeout: float = Field(1.0, alias="timeout", ge=0.25)
    retries: int = Field(3, alias="retries", ge=0)
    disable_chunking: bool = Field(False, alias="disable-chunking")
    inverters: list[int] = Field(default_factory=list, alias="inverters")
    ac_chargers: list[int] = Field(default_factory=list, alias="ac-chargers")
    dc_chargers: list[int] = Field(default_factory=list, alias="dc-chargers")
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)
    registers: RegisterAccess = Field(default_factory=RegisterAccess, alias="registers")  # type: ignore[reportCallIssue]
    scan_interval: ScanInterval = Field(default_factory=ScanInterval, alias="scan-interval")  # type: ignore[reportCallIssue]
    smartport: SmartPortConfig = Field(default_factory=SmartPortConfig, alias="smart-port")  # type: ignore[reportCallIssue]

    @model_validator(mode="before")
    @classmethod
    def reshape_flat_fields(cls, data: Any) -> Any:
        """
        Lift flat YAML/env register and scan-interval keys into their nested sub-models.

        The YAML spec has these as peer keys of host/port at the device level; pydantic
        expects them under 'registers' and 'scan_interval' respectively.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)  # shallow copy to avoid mutating caller's dict

        # ── Register access fields ───────────────────────────────────────────
        reg = dict(data.get("registers") or {})
        for src, dst in (
            ("no-remote-ems", "no-remote-ems"),
            ("no_remote_ems", "no_remote_ems"),
            ("read-only", "read-only"),
            ("read_only", "read_only"),
            ("read-write", "read-write"),
            ("read_write", "read_write"),
            ("write-only", "write-only"),
            ("write_only", "write_only"),
        ):
            if src in data:
                reg[dst] = data.pop(src)
        if reg:
            data["registers"] = reg

        # ── Scan interval fields ─────────────────────────────────────────────
        si = dict(data.get("scan_interval") or data.get("scan-interval") or {})
        for src, dst in (
            ("scan-interval-low", "low"),
            ("scan_interval_low", "low"),
            ("scan-interval-medium", "medium"),
            ("scan_interval_medium", "medium"),
            ("scan-interval-high", "high"),
            ("scan_interval_high", "high"),
            ("scan-interval-realtime", "realtime"),
            ("scan_interval_realtime", "realtime"),
        ):
            if src in data:
                si[dst] = data.pop(src)
        if si:
            data["scan_interval"] = si

        return data

    @model_validator(mode="after")
    def check_host_set(self) -> "ModbusConfig":
        if not self.host:
            raise ValueError("modbus entry must have a host")
        return self

    @model_validator(mode="after")
    def default_inverters(self) -> "ModbusConfig":
        """Match existing behaviour: default to inverter device ID 1 when nothing specified."""
        if not self.inverters and not self.ac_chargers and not self.dc_chargers:
            self.inverters = [1]
        return self


class PvOutputConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    api_key: str = Field("", alias="api-key")
    system_id: str = Field("", alias="system-id")
    testing: bool = Field(False)
    consumption: Optional[str] = Field(None, alias="consumption")
    exports: bool = Field(False, alias="exports")
    imports: bool = Field(False, alias="imports")
    output_hour: int = Field(23, alias="output-hour")
    temperature_topic: str = Field("", alias="temperature-topic")
    voltage: VoltageSource = Field(VoltageSource.L_N_AVG, alias="voltage")
    # v7-v12 are stored in the 'extended' dict keyed by StatusField value strings
    extended: dict[str, str] = Field(
        default_factory=lambda: {
            sf.value: ""
            for sf in (
                StatusField.V7,
                StatusField.V8,
                StatusField.V9,
                StatusField.V10,
                StatusField.V11,
                StatusField.V12,
            )
        },
        alias="extended",
    )
    log_level: int = Field(logging.CRITICAL, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)
    calc_debug_logging: bool = Field(False, alias="calc-debug-logging")
    update_debug_logging: bool = Field(False, alias="update-debug-logging")
    # tariffs is the parsed form of the YAML 'time-periods' list
    tariffs: list[Any] = Field(default_factory=list, alias="time-periods")

    started: float = Field(default=0.0, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def reshape_extended_fields(cls, data: Any) -> Any:
        """Move flat v7-v12 YAML keys into the 'extended' sub-dict."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        ext = dict(data.get("extended") or {})
        for key in ("v7", "v8", "v9", "v10", "v11", "v12"):
            if key in data:
                ext[key] = data.pop(key)
        if ext:
            data["extended"] = ext
        return data

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Any) -> str:
        if v and isinstance(v, str):
            try:
                int(v, 16)
            except ValueError:
                raise ValueError("pvoutput.api-key must only contain hexadecimal characters")
        return v or ""

    @field_validator("consumption", mode="before")
    @classmethod
    def validate_consumption(cls, v: Any) -> Optional[str]:
        if v is None or v is False or v == "false":
            return None
        if v is True or v == "true" or v == ConsumptionSource.CONSUMPTION.value:
            return ConsumptionSource.CONSUMPTION
        try:
            return ConsumptionSource(v)
        except ValueError:
            valid = ", ".join(s.value for s in ConsumptionSource)
            raise ValueError(f"pvoutput.consumption must be false, true, {valid}")

    @field_validator("output_hour", mode="before")
    @classmethod
    def validate_output_hour(cls, v: Any) -> int:
        v = int(v)
        if v == -1:
            return v
        if not (20 <= v <= 23):
            raise ValueError("pvoutput.output-hour must be -1 or between 20 and 23")
        return v

    @field_validator("voltage", mode="before")
    @classmethod
    def validate_voltage(cls, v: Any) -> VoltageSource:
        if isinstance(v, VoltageSource):
            return v
        try:
            return VoltageSource(v)
        except ValueError:
            valid = ", ".join(s.value for s in VoltageSource)
            raise ValueError(f"pvoutput.voltage must be one of: {valid}")

    @field_validator("tariffs", mode="before")
    @classmethod
    def parse_time_periods(cls, v: Any) -> list:
        """Parse the raw YAML 'time-periods' list[dict] into list[Tariff]."""
        if not v or not isinstance(v, list):
            return []
        tariffs: list[Tariff] = []
        for index, tariff_dict in enumerate(v):
            if not isinstance(tariff_dict, dict):
                raise ValueError(f"pvoutput.time-periods[{index}] must be a time period definition")
            for key in tariff_dict:
                if key not in ("plan", "from-date", "to-date", "default", "periods"):
                    raise ValueError(f"pvoutput.time-periods[{index}] contains unknown option '{key}'")
            plan = check_string(tariff_dict.get("plan"), f"pvoutput.time-periods[{index}].plan", allow_none=True, allow_empty=True)
            from_dt = check_date(tariff_dict["from-date"], f"pvoutput.time-periods[{index}].from-date") if "from-date" in tariff_dict else None
            to_dt = check_date(tariff_dict["to-date"], f"pvoutput.time-periods[{index}].to-date") if "to-date" in tariff_dict else None
            default = TariffType(
                check_string(
                    tariff_dict.get("default", TariffType.SHOULDER.value),
                    f"pvoutput.time-periods[{index}].default",
                    "off-peak",
                    "peak",
                    "shoulder",
                    "high-shoulder",
                    allow_empty=False,
                    allow_none=False,
                )
            )
            if "periods" not in tariff_dict:
                raise ValueError(f"pvoutput.time-periods[{index}] must contain a 'periods' element")
            periods = _parse_time_periods(tariff_dict["periods"], index)
            tariffs.append(
                Tariff(
                    plan=f"Unknown-{index}" if plan is None else plan,
                    from_date=from_dt,
                    to_date=to_dt,
                    default=default,
                    periods=periods,
                )
            )
        # Sort newest-first, matching existing behaviour

        return sorted(
            tariffs,
            key=lambda t: (t.from_date or datetime.min.date(), t.to_date or datetime.max.date()),
            reverse=True,
        )

    @model_validator(mode="after")
    def set_testing_flag(self) -> "PvOutputConfig":
        if self.system_id == "testing":
            self.testing = True
            logging.warning("PVOutput system-id is set to 'testing'. PVOutput data will not be sent to the actual PVOutput service.")
        return self

    @model_validator(mode="after")
    def check_required_when_enabled(self) -> "PvOutputConfig":
        if self.enabled:
            if not self.api_key:
                raise ValueError("pvoutput.api-key must be provided when enabled")
            if not self.system_id:
                raise ValueError("pvoutput.system-id must be provided when enabled")
            for tariff in self.tariffs:
                for period in tariff.periods:
                    if period.end <= period.start:
                        raise ValueError(f"pvoutput time period end time ({period.end}) must be after start time ({period.start})")
        return self

    @property
    def consumption_enabled(self) -> bool:
        return self.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.IMPORTED, ConsumptionSource.NET_OF_BATTERY)

    def _type_to_output_fields(self, type: TariffType) -> tuple[OutputField, OutputField]:
        match type:
            case TariffType.OFF_PEAK:
                export_type = OutputField.EXPORT_OFF_PEAK
                import_type = OutputField.IMPORT_OFF_PEAK
            case TariffType.PEAK:
                export_type = OutputField.EXPORT_PEAK
                import_type = OutputField.IMPORT_PEAK
            case TariffType.SHOULDER:
                export_type = OutputField.EXPORT_SHOULDER
                import_type = OutputField.IMPORT_SHOULDER
            case TariffType.HIGH_SHOULDER:
                export_type = OutputField.EXPORT_HIGH_SHOULDER
                import_type = OutputField.IMPORT_HIGH_SHOULDER
            case _:
                raise ValueError(f"Invalid tariff type: {type}")
        return (export_type, import_type)

    @property
    def current_time_period(self) -> tuple[OutputField | None, OutputField]:
        export_type = None  # No export default if completely unmatched, because total exports is always reported, but time periods may not be defined
        import_type = OutputField.IMPORT_PEAK  # Import default prior to introduction of time periods was peak
        if self.tariffs:
            now_date_time = datetime.now()
            today = now_date_time.date()
            now = now_date_time.time()
            dow = now_date_time.strftime("%a")  # 'Mon', 'Tue', etc.
            for tariff in self.tariffs:
                if (tariff.from_date is None or tariff.from_date <= today) and (tariff.to_date is None or tariff.to_date >= today):
                    for period in tariff.periods:
                        if "All" in period.days or dow in period.days or ("Weekdays" in period.days and dow in WEEKDAYS) or ("Weekends" in period.days and dow in WEEKENDS):
                            if period.start <= now < period.end:
                                if self.calc_debug_logging:
                                    logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) and time matched '{period.type}' ({period.start}-{period.end}) on {dow}")
                                export_type, import_type = self._type_to_output_fields(period.type)
                                break
                    else:
                        if self.calc_debug_logging:
                            logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) but no time matched so using default '{tariff.default}'")
                        export_type, import_type = self._type_to_output_fields(tariff.default)  # Set the default types if date matched but time outside of defined periods
        return (export_type, import_type)


def _parse_time_periods(value: list, tariff_index: int) -> list[TimePeriod]:
    """Parse a raw list of period dicts into list[TimePeriod]."""
    if not isinstance(value, list):
        raise ValueError("pvoutput time-periods.periods configuration element must contain a list of time period definitions")
    periods: list[TimePeriod] = []
    for i, period in enumerate(value):
        if not isinstance(period, dict):
            raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}] must be a time period definition")
        if not all(k in period for k in ("type", "start", "end")):
            raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}] must contain 'type', 'start', and 'end' elements")
        ptype = TariffType(
            check_string(
                period["type"],
                f"pvoutput.time-periods[{tariff_index}].periods[{i}].type",
                "off-peak",
                "peak",
                "shoulder",
                "high-shoulder",
                allow_empty=False,
                allow_none=False,
            )
        )
        start = check_time(period["start"], f"pvoutput.time-periods[{tariff_index}].periods[{i}].start")
        end = check_time(period["end"], f"pvoutput.time-periods[{tariff_index}].periods[{i}].end")
        days: list[str] = []
        if "days" in period:
            if not isinstance(period["days"], list):
                raise ValueError(f"pvoutput.time-periods[{tariff_index}].periods[{i}].days must be a list of days")
            for day in period["days"]:
                validated = check_string(
                    day.capitalize(),
                    f"pvoutput.time-periods[{tariff_index}].periods[{i}].days",
                    "Mon",
                    "Tue",
                    "Wed",
                    "Thu",
                    "Fri",
                    "Sat",
                    "Sun",
                    "Weekdays",
                    "Weekends",
                    "All",
                )
                if validated:
                    days.append(validated)
        else:
            days.append("All")
        periods.append(TimePeriod(type=ptype, start=start, end=end, days=days))
    return periods


class InfluxDbConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    host: str = Field("127.0.0.1", alias="host")
    port: int = Field(8086, alias="port", ge=1, le=65535)
    username: str = Field("", alias="username")
    password: str = Field("", alias="password")
    database: str = Field("sigenergy", alias="database")
    org: str = Field("", alias="org")
    token: str = Field("", alias="token")
    bucket: str = Field("", alias="bucket")
    default_measurement: str = Field("state", alias="default-measurement", min_length=1)
    load_hass_history: bool = Field(False, alias="load-hass-history")
    include: list[str] = Field(default_factory=list, alias="include")
    exclude: list[str] = Field(default_factory=list, alias="exclude")
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)
    write_timeout: float = Field(30.0, alias="write-timeout", ge=0.1)
    read_timeout: float = Field(120.0, alias="read-timeout", ge=0.1)
    batch_size: int = Field(100, alias="batch-size", ge=1)
    flush_interval: float = Field(1.0, alias="flush-interval", ge=0.1)
    query_interval: float = Field(0.5, alias="query-interval", ge=0.0)
    max_retries: int = Field(3, alias="max-retries", ge=0)
    pool_connections: int = Field(100, alias="pool-connections", ge=1)
    pool_maxsize: int = Field(100, alias="pool-maxsize", ge=1)
    sync_chunk_size: int = Field(1000, alias="sync-chunk-size", ge=1)
    max_sync_workers: int = Field(4, alias="max-sync-workers", ge=1)

    @model_validator(mode="after")
    def check_credentials(self) -> "InfluxDbConfig":
        if not self.enabled:
            return self
        # Lone password with no username → treat as token (v2 API)
        if self.password and not self.username and not self.token:
            self.token = self.password
            self.password = ""
        has_v2 = bool(self.token and self.org)
        has_v1 = bool(self.username and self.password)
        if not has_v2 and not has_v1:
            raise ValueError("influxdb configuration requires either v2 credentials (token and org) or v1 credentials (username and password)")
        return self


# ---------------------------------------------------------------------------
# Sensor overrides validation
# ---------------------------------------------------------------------------

_SENSOR_OVERRIDE_VALIDATORS: dict[str, Any] = {
    "debug-logging": lambda v, ctx: check_bool(v, ctx),
    "gain": lambda v, ctx: check_int(v, ctx, allow_none=True, min=1),
    "icon": lambda v, ctx: check_string(v, ctx, allow_none=False, starts_with="mdi:"),
    "max-failures": lambda v, ctx: check_int(v, ctx, allow_none=True, min=1),
    "max-failures-retry-interval": lambda v, ctx: check_int(v, ctx, allow_none=False, min=0),
    "precision": lambda v, ctx: check_int(v, ctx, allow_none=False, min=0, max=6),
    "publishable": lambda v, ctx: check_bool(v, ctx),
    "publish-raw": lambda v, ctx: check_bool(v, ctx),
    "scan-interval": lambda v, ctx: check_int(v, ctx, allow_none=False, min=1),
    "sanity-check-max-value": lambda v, ctx: check_float(v, ctx, allow_none=False),
    "sanity-check-min-value": lambda v, ctx: check_float(v, ctx, allow_none=False),
    "sanity-check-delta": lambda v, ctx: check_bool(v, ctx),
    "unit-of-measurement": lambda v, ctx: check_string(v, ctx, allow_none=False),
}


def validate_sensor_overrides(raw: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Validate every sensor override entry, mirroring Config._configure sensor-overrides."""
    result: dict[str, dict[str, Any]] = {}
    for sensor, settings in raw.items():
        validated: dict[str, Any] = {}
        for prop, val in settings.items():
            ctx = f"Error processing configuration sensor-overrides: {sensor}.{prop} = {val} -"
            if prop not in _SENSOR_OVERRIDE_VALIDATORS:
                raise ValueError(f"Error processing configuration sensor-overrides: {sensor}.{prop} = {val} - property is not known or not overridable")
            validated[prop] = _SENSOR_OVERRIDE_VALIDATORS[prop](val, ctx)
        result[sensor] = validated
    return result


# ---------------------------------------------------------------------------
# Modbus list merge and override helpers
# ---------------------------------------------------------------------------


def _merge_modbus_by_host_port(
    base: list[dict[str, Any]],  # discovery devices
    overlay: list[dict[str, Any]],  # YAML-configured devices
) -> list[dict[str, Any]]:
    """
    Merge discovery and YAML-config modbus lists.

    For each YAML entry:
    - Blank host acts as a wildcard matching the first discovery device with the same port.
    - A named host matches an exact discovery device (host + port).
    - No match → kept as a standalone entry.

    YAML config wins over discovery for all keys it provides.
    Discovery contributes device IDs (inverters, ac-chargers, dc-chargers) and host when the
    YAML entry had a blank host wildcard.
    """
    # Index discovery devices by "host:port"
    disc_map: dict[str, dict[str, Any]] = {}
    for entry in base:
        key = f"{entry.get('host', '')}:{entry.get('port', 502)}"
        disc_map[key] = dict(entry)

    result: dict[str, dict[str, Any]] = {}

    for entry in overlay:
        host = entry.get("host", "")
        port = entry.get("port", 502)

        if not host:
            # Wildcard: find first discovery device with matching port
            matched_key = next(
                (k for k, d in disc_map.items() if d.get("port", 502) == port),
                None,
            )
            if matched_key:
                disc = disc_map.pop(matched_key)
                merged = {**disc, **{k: v for k, v in entry.items() if v or v == 0}}
                merged["host"] = disc["host"]  # take host from discovery
                result[f"{merged['host']}:{port}"] = merged
            else:
                result[f":{port}"] = dict(entry)
        else:
            key = f"{host}:{port}"
            if key in disc_map:
                disc = disc_map.pop(key)
                # YAML wins; bring device IDs from discovery when YAML didn't set them
                merged = dict(disc)
                merged.update({k: v for k, v in entry.items() if k not in ("inverters", "ac-chargers", "dc-chargers", "ac_chargers", "dc_chargers") or v})
                result[key] = merged
            else:
                result[key] = dict(entry)

    # Append any remaining discovery-only devices
    for key, disc in disc_map.items():
        if key not in result:
            result[key] = disc

    return list(result.values())


def _apply_modbus_env_override(
    modbus_list: list[ModbusConfig],
    override: dict[str, Any],
) -> list[ModbusConfig]:
    """
    Apply a flat env-var override dict to one modbus entry.

    Targets the entry whose host matches SIGENERGY2MQTT_MODBUS_HOST, or index 0.
    If the list is empty and a host is set, bootstrap a new entry from the override.
    """
    if not override:
        return modbus_list

    target_host = override.get("host")

    if not modbus_list:
        return [ModbusConfig(**override)]

    idx = 0
    if target_host:
        for i, m in enumerate(modbus_list):
            if m.host == target_host:
                idx = i
                break

    base = modbus_list[idx].model_dump(by_alias=False)
    # Flatten nested registers/scan_interval back out so reshape_flat_fields can re-nest them
    regs = base.pop("registers", {})
    si = base.pop("scan_interval", {})
    base.update({f"no_{k}" if k == "remote_ems" else k: v for k, v in regs.items()})
    base.update({f"scan_interval_{k}": v for k, v in si.items()})
    base.update(override)

    result = list(modbus_list)
    result[idx] = ModbusConfig(**base)
    return result


def _propagate_to_all_devices(
    modbus_list: list[ModbusConfig],
    override: dict[str, Any],
) -> list[ModbusConfig]:
    """Apply propagatable env-var keys (log level, register access, scan intervals) to every device."""
    propagatable = {k: v for k, v in override.items() if k in _PROPAGATABLE_MODBUS_KEYS}
    if not propagatable:
        return modbus_list

    result: list[ModbusConfig] = []
    for device in modbus_list:
        base = device.model_dump(by_alias=False)
        regs = base.pop("registers", {})
        si = base.pop("scan_interval", {})
        base.update({f"no_{k}" if k == "remote_ems" else k: v for k, v in regs.items()})
        base.update({f"scan_interval_{k}": v for k, v in si.items()})
        base.update(propagatable)
        result.append(ModbusConfig(**base))
    return result


# ---------------------------------------------------------------------------
# Custom settings sources
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
    Loads the modbus device list produced by auto-discovery and passes it to
    Settings.model_post_init for host-matched merging with the main config.

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


class EnvSettingsSource(PydanticBaseSettingsSource):
    """
    Maps SIGENERGY2MQTT_* environment variables onto the nested Settings model
    using the typed constants from const.py as the canonical key names.
    """

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
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

        # SIGENERGY2MQTT_DEBUG_SENSOR takes a sensor *name*, not a boolean.
        # Inject it into sensor_overrides and force log level to DEBUG.
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

        # ── Modbus (env vars configure a single device) ──────────────────────
        modbus: dict[str, Any] = {}
        _set(modbus, "host", g(const.SIGENERGY2MQTT_MODBUS_HOST))
        _set(modbus, "port", _int(g(const.SIGENERGY2MQTT_MODBUS_PORT)))
        _set(modbus, "timeout", _float(g(const.SIGENERGY2MQTT_MODBUS_TIMEOUT)))
        _set(modbus, "retries", _int(g(const.SIGENERGY2MQTT_MODBUS_RETRIES)))
        _set(modbus, "disable_chunking", _bool(g(const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING)))
        _set(modbus, "log_level", g(const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL))
        # Register access — stored flat; reshape_flat_fields nests them
        _set(modbus, "read_only", _bool(g(const.SIGENERGY2MQTT_MODBUS_READ_ONLY)))
        _set(modbus, "read_write", _bool(g(const.SIGENERGY2MQTT_MODBUS_READ_WRITE)))
        _set(modbus, "write_only", _bool(g(const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY)))
        _set(modbus, "no_remote_ems", _bool(g(const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS)))
        _set(modbus, "inverters", _int_list(g(const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID)))
        _set(modbus, "ac_chargers", _int_list(g(const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID)))
        _set(modbus, "dc_chargers", _int_list(g(const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID)))
        # Scan intervals — stored flat; reshape_flat_fields nests them
        _set(modbus, "scan_interval_low", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW)))
        _set(modbus, "scan_interval_medium", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM)))
        _set(modbus, "scan_interval_high", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH)))
        _set(modbus, "scan_interval_realtime", _int(g(const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME)))

        # Auto-discovery control
        _set(result, "modbus_auto_discovery", g(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY))
        _set(result, "modbus_auto_discovery_timeout", _float(g(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT)))
        _set(result, "modbus_auto_discovery_ping_timeout", _float(g(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT)))
        _set(result, "modbus_auto_discovery_retries", _int(g(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES)))

        # Smart-port (applies to the first/targeted modbus device)
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
        # v7-v12 go into extended; reshape_extended_fields handles extraction
        _set(pvo, "v7", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7))
        _set(pvo, "v8", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8))
        _set(pvo, "v9", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9))
        _set(pvo, "v10", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10))
        _set(pvo, "v11", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11))
        _set(pvo, "v12", g(const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12))
        _set(pvo, "log_level", g(const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL))
        _set(pvo, "calc_debug_logging", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING)))
        _set(pvo, "update_debug_logging", _bool(g(const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING)))
        # PERIODS_JSON is a JSON string encoding the full time-periods list
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


# ---------------------------------------------------------------------------
# Tiny helpers (None-safe coercions used by EnvSettingsSource)
# ---------------------------------------------------------------------------


def _set(d: dict, key: str, val: Any) -> None:
    """Write to dict only if val is not None."""
    if val is not None:
        d[key] = val


def _bool(v: str | None) -> bool | None:
    if v is None:
        return None
    return v.strip().lower() in ("1", "true", "yes", "on", "y")


def _invert_bool(v: str | None) -> bool | None:
    """Parse boolean env var and invert it (for no-* flags stored as positive attributes)."""
    result = _bool(v)
    return None if result is None else not result


def _int(v: str | None) -> int | None:
    return int(v) if v is not None else None


def _float(v: str | None) -> float | None:
    return float(v) if v is not None else None


def _int_list(v: str | None) -> list[int] | None:
    """'1,2,3' → [1, 2, 3]"""
    if v is None:
        return None
    return [int(x.strip()) for x in v.split(",") if x.strip()]


def _str_list(v: str | None) -> list[str] | None:
    """'a,b,c' → ['a', 'b', 'c']"""
    if v is None:
        return None
    return [x.strip() for x in v.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# Root settings model
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """
    Root configuration.  Instantiate once at startup:

        cfg = Settings()

        # With a pre-run auto-discovery result file:
        cfg = Settings(_discovery_yaml="auto-discovery.yaml")

    Field names and types are designed to match the existing Config class
    (excluding persistent_state_path and _source).

    Priority (highest → lowest):
      env vars → YAML config file → auto-discovery YAML → defaults
    """

    model_config = SettingsConfigDict(populate_by_name=True)

    # ── Internal args ────────────────────────────────────────────────────────
    yaml_file_arg: Optional[str] = Field(None, exclude=True)
    discovery_yaml_arg: Optional[str | Path] = Field(None, exclude=True)

    # ── Top-level scalars ────────────────────────────────────────────────────
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)
    language: str = Field("en", alias="language")
    consumption: ConsumptionMethod = Field(ConsumptionMethod.TOTAL, alias="consumption")
    repeated_state_publish_interval: int = Field(0, alias="repeated-state-publish-interval")
    sanity_check_default_kw: float = Field(500.0, alias="sanity-check-default-kw", ge=0)
    sanity_check_failures_increment: bool = Field(False, alias="sanity-check-failures-increment")
    # Stored as positive flag; YAML/env key is no-ems-mode-check (inverted)
    ems_mode_check: bool = Field(True, alias="ems-mode-check")
    # Stored as positive flag; YAML/env key is no-metrics (inverted)
    metrics_enabled: bool = Field(True, alias="metrics-enabled")
    sensor_debug_logging: bool = Field(False, alias="sensor-debug-logging")

    # ── Auto-discovery control ───────────────────────────────────────────────
    modbus_auto_discovery: Optional[str] = Field(None, alias="modbus-auto-discovery")
    modbus_auto_discovery_timeout: Optional[float] = Field(None, alias="modbus-auto-discovery-timeout")
    modbus_auto_discovery_ping_timeout: Optional[float] = Field(None, alias="modbus-auto-discovery-ping-timeout")
    modbus_auto_discovery_retries: Optional[int] = Field(None, alias="modbus-auto-discovery-retries")

    # ── Sub-configs ──────────────────────────────────────────────────────────
    home_assistant: HomeAssistantConfig = Field(default_factory=HomeAssistantConfig, alias="home-assistant")  # type: ignore[reportCallIssue]
    mqtt: MqttConfig = Field(default_factory=MqttConfig)  # type: ignore[reportCallIssue]
    pvoutput: PvOutputConfig = Field(default_factory=PvOutputConfig)  # type: ignore[reportCallIssue]
    influxdb: InfluxDbConfig = Field(default_factory=InfluxDbConfig)  # type: ignore[reportCallIssue]
    modbus: list[ModbusConfig] = Field(default_factory=list)

    # sensor-overrides: arbitrary sensor keys → validated override dicts
    sensor_overrides: dict[str, Any] = Field(default_factory=dict, alias="sensor-overrides")

    # ── Private side-channels (set by custom sources, consumed in post_init) ─
    modbus_env_override: dict[str, Any] = Field(default_factory=dict, exclude=True)
    discovery_modbus: list[dict[str, Any]] = Field(default_factory=list, exclude=True)

    @field_validator("consumption", mode="before")
    @classmethod
    def validate_consumption(cls, v: Any) -> ConsumptionMethod:
        if isinstance(v, ConsumptionMethod):
            return v
        try:
            return ConsumptionMethod(v)
        except ValueError:
            valid = ", ".join(m.value for m in ConsumptionMethod)
            raise ValueError(f"consumption must be one of: {valid}")

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if i18n:
            available = i18n.get_available_translations()
            if v not in available:
                default = i18n.get_default_language()
                logging.warning(f"Invalid language '{v}', falling back to '{default}'")
                return default
        return v

    @field_validator("ems_mode_check", mode="before")
    @classmethod
    def invert_no_ems_mode_check(cls, v: Any) -> bool:
        """YAML key is 'no-ems-mode-check'; stored as the inverse ems_mode_check."""
        if isinstance(v, bool):
            return v
        # If it arrived as the raw no-ems-mode-check value (True = disable checking)
        # the inversion is already done by _invert_bool in EnvSettingsSource.
        # From YAML it arrives as-is so we need to invert.
        return not _bool(str(v))

    @field_validator("metrics_enabled", mode="before")
    @classmethod
    def invert_no_metrics(cls, v: Any) -> bool:
        """YAML key is 'no-metrics'; stored as the inverse metrics_enabled."""
        if isinstance(v, bool):
            return v
        return not _bool(str(v))

    @field_validator("sensor_overrides", mode="before")
    @classmethod
    def validate_sensor_overrides_field(cls, v: Any) -> dict:
        if not v:
            return {}
        if not isinstance(v, dict):
            raise ValueError("sensor-overrides must contain a list of class names")
        return validate_sensor_overrides(v)

    def model_post_init(self, __context: Any) -> None:
        discovery = self.discovery_modbus
        env_override = self.modbus_env_override

        # ── Step 1: merge discovery into YAML config ─────────────────────────
        if discovery:
            yaml_dicts = [m.model_dump(by_alias=False) for m in self.modbus]
            merged_dicts = _merge_modbus_by_host_port(base=discovery, overlay=yaml_dicts)
            self.modbus = [ModbusConfig(**d) for d in merged_dicts]

        # ── Step 2: apply targeted env override to one device ────────────────
        if env_override:
            self.modbus = _apply_modbus_env_override(self.modbus, env_override)

        # ── Step 3: propagate broadcast env vars to ALL devices ──────────────
        if env_override:
            self.modbus = _propagate_to_all_devices(self.modbus, env_override)

        # ── Cross-model validation ────────────────────────────────────────────
        if not self.modbus:
            raise ValueError("At least one Modbus device must be configured")

        if not self.ems_mode_check:
            for device in self.modbus:
                if device.registers.no_remote_ems:
                    raise ValueError("When ems_mode_check is disabled, no_remote_ems must be False")
                if not device.registers.read_write:
                    raise ValueError("When ems_mode_check is disabled, read_write must be True")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file = None
        discovery_yaml = None
        if isinstance(init_settings, InitSettingsSource):
            yaml_file = init_settings.init_kwargs.get("yaml_file_arg")
            discovery_yaml = init_settings.init_kwargs.get("discovery_yaml_arg")

        return (
            EnvSettingsSource(settings_cls),  # 1. env vars
            RuamelYamlSettingsSource(settings_cls, yaml_file),  # 2. config YAML
            AutoDiscoveryYamlSettingsSource(settings_cls, discovery_yaml),  # 3. discovery YAML
            init_settings,  # 4. programmatic
        )


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json as _json

    cfg = Settings()  # type: ignore[reportCallIssue]
    print(_json.dumps(cfg.model_dump(), indent=2, default=str))
