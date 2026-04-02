"""
Root settings model.

Priority (highest → lowest):
  1. Environment variables  (SIGENERGY2MQTT_*)
  2. YAML config file       (path set by SIGENERGY2MQTT_CONFIG, default: sigenergy2mqtt.yaml)
  3. Auto-discovery YAML    (produced by auto-discovery; merged by host into modbus list)
  4. Defaults in sub-models
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, InitSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import WEEKDAYS, WEEKENDS, ConsumptionMethod, OutputField, TariffType
from sigenergy2mqtt.config.coerce import _bool
from sigenergy2mqtt.config.merge import (
    apply_modbus_env_override,
    merge_modbus_by_host_port,
    propagate_to_all_devices,
)
from sigenergy2mqtt.config.models import (
    HomeAssistantConfig,
    InfluxDbConfig,
    ModbusConfig,
    MqttConfig,
    PvOutputConfig,
)
from sigenergy2mqtt.config.sources import (
    AutoDiscoveryYamlSettingsSource,
    EnvSettingsSource,
    RuamelYamlSettingsSource,
)
from sigenergy2mqtt.config.validators import validate_log_level, validate_sensor_overrides

# ---------------------------------------------------------------------------
# PvOutputConfig methods that use datetime.now() must live here so that
# tests can patch 'sigenergy2mqtt.config.settings.datetime'.
# ---------------------------------------------------------------------------


def _pvoutput_type_to_output_fields(self: "PvOutputConfig", type: TariffType) -> tuple[OutputField, OutputField]:
    match type:
        case TariffType.OFF_PEAK:
            return OutputField.EXPORT_OFF_PEAK, OutputField.IMPORT_OFF_PEAK
        case TariffType.PEAK:
            return OutputField.EXPORT_PEAK, OutputField.IMPORT_PEAK
        case TariffType.SHOULDER:
            return OutputField.EXPORT_SHOULDER, OutputField.IMPORT_SHOULDER
        case TariffType.HIGH_SHOULDER:
            return OutputField.EXPORT_HIGH_SHOULDER, OutputField.IMPORT_HIGH_SHOULDER
        case _:
            raise ValueError(f"Invalid tariff type: {type}")


def _pvoutput_current_time_period(self: "PvOutputConfig") -> tuple[OutputField | None, OutputField]:
    export_type = None
    import_type = OutputField.IMPORT_PEAK
    if self.tariffs:
        now_date_time = datetime.now()
        today = now_date_time.date()
        now = now_date_time.time()
        dow = now_date_time.strftime("%a")
        for tariff in self.tariffs:
            if (tariff.from_date is None or tariff.from_date <= today) and (tariff.to_date is None or tariff.to_date >= today):
                for period in tariff.periods:
                    if "All" in period.days or dow in period.days or ("Weekdays" in period.days and dow in WEEKDAYS) or ("Weekends" in period.days and dow in WEEKENDS):
                        if period.start <= now < period.end:
                            if self.log_level <= logging.DEBUG and self.calc_debug_logging:
                                logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) and time matched '{period.type}' ({period.start}-{period.end}) on {dow}")
                            export_type, import_type = _pvoutput_type_to_output_fields(self, period.type)
                            break
                else:
                    if self.log_level <= logging.DEBUG and self.calc_debug_logging:
                        logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) but no time matched so using default '{tariff.default}'")
                    export_type, import_type = _pvoutput_type_to_output_fields(self, tariff.default)
    return (export_type, import_type)


PvOutputConfig._type_to_output_fields = _pvoutput_type_to_output_fields  # type: ignore[attr-defined]
PvOutputConfig.current_time_period = property(_pvoutput_current_time_period)  # type: ignore[attr-defined]


class Settings(BaseSettings):
    """
    Root configuration.  Instantiate once at startup:

        cfg = Settings()

        # With a pre-run auto-discovery result file:
        cfg = Settings(_discovery_yaml="auto-discovery.yaml")
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
    ems_mode_check: bool = Field(True, alias="ems-mode-check")
    metrics_enabled: bool = Field(True, alias="metrics-enabled")
    sensor_debug_logging: bool = Field(False, alias="sensor-debug-logging")

    # ── Sub-configs ──────────────────────────────────────────────────────────
    home_assistant: HomeAssistantConfig = Field(default_factory=HomeAssistantConfig, alias="home-assistant")  # type: ignore[reportCallIssue]
    mqtt: MqttConfig = Field(default_factory=MqttConfig)  # type: ignore[reportCallIssue]
    pvoutput: PvOutputConfig = Field(default_factory=PvOutputConfig)  # type: ignore[reportCallIssue]
    influxdb: InfluxDbConfig = Field(default_factory=InfluxDbConfig)  # type: ignore[reportCallIssue]
    modbus: list[ModbusConfig] = Field(default_factory=list)

    sensor_overrides: dict[str, Any] = Field(default_factory=dict, alias="sensor-overrides")

    # ── Private side-channels (set by custom sources, consumed in post_init) ─
    modbus_env_override: dict[str, Any] = Field(default_factory=dict, exclude=True)
    discovery_modbus: list[dict[str, Any]] = Field(default_factory=list, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def handle_negated_flags(cls, data: Any) -> Any:
        """
        Merge negated flags and kebab-case aliases into primary fields
        to avoid 'extra_forbidden' errors.
        """
        if not isinstance(data, dict):
            return data

        # 1. Merge negated YAML/kebab keys to their positive snake_case field names
        negated_mapping = {
            "no-ems-mode-check": "ems_mode_check",
            "no_ems_mode_check": "ems_mode_check",
            "no-metrics": "metrics_enabled",
            "no_metrics": "metrics_enabled",
        }
        for negated_key, positive_field in negated_mapping.items():
            if negated_key in data:
                val = data.pop(negated_key)
                if val is not None:
                    if positive_field not in data:
                        bool_val = _bool(str(val)) if isinstance(val, str) else bool(val)
                        data[positive_field] = not bool_val

        # 2. Merge YAML/kebab keys into their snake_case field names
        for field_name, field_info in cls.model_fields.items():
            alias = field_info.alias
            if alias and alias != field_name and alias in data:
                val_alias = data.pop(alias)
                if field_name not in data:
                    data[field_name] = val_alias
                elif isinstance(val_alias, dict) and isinstance(data[field_name], dict):
                    data[field_name] = {**data[field_name], **val_alias}

        return data

    # ── Field validators ─────────────────────────────────────────────────────

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
        if isinstance(v, bool):
            return v
        return not _bool(str(v))

    @field_validator("metrics_enabled", mode="before")
    @classmethod
    def invert_no_metrics(cls, v: Any) -> bool:
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

    # ── Post-init orchestration ───────────────────────────────────────────────

    def model_post_init(self, __context: Any) -> None:
        discovery = self.discovery_modbus
        env_override = self.modbus_env_override

        # Step 1: merge discovery into YAML config
        if discovery:
            yaml_dicts = [m.model_dump(by_alias=False) for m in self.modbus]
            merged_dicts = merge_modbus_by_host_port(base=discovery, overlay=yaml_dicts)
            self.modbus = [ModbusConfig(**d) for d in merged_dicts]

        # Step 2: apply targeted env override to one device
        if env_override:
            self.modbus = apply_modbus_env_override(self.modbus, env_override)

        # Step 3: propagate broadcast env vars to ALL devices
        if env_override:
            self.modbus = propagate_to_all_devices(self.modbus, env_override)

        # Sync root logger to the resolved log level
        logging.getLogger().setLevel(self.log_level)

        # Cross-model validation
        if not self.modbus:
            raise ValueError("At least one Modbus device must be configured")

        if not self.ems_mode_check:
            for device in self.modbus:
                if device.registers.no_remote_ems:
                    raise ValueError("When ems_mode_check is disabled, no_remote_ems must be False")
                if not device.registers.read_write:
                    raise ValueError("When ems_mode_check is disabled, read_write must be True")

    # ── Source customisation ──────────────────────────────────────────────────

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
