from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from sigenergy2mqtt.common import (
    ConsumptionSource,
    StatusField,
    Tariff,
    TariffType,
    VoltageSource,
)
from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.validation import check_date, check_string
from sigenergy2mqtt.config.validators import parse_time_periods, validate_log_level


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
            else:
                ext[key] = ""
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

    @field_validator("system_id", mode="before")
    @classmethod
    def validate_system_id(cls, v: Any) -> str:
        if not v:
            return ""
        v = str(v)
        if v != "testing" and not v.isnumeric():
            raise ValueError("pvoutput.system-id must be numeric or 'testing'")
        return v

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
    def parse_time_periods_field(cls, v: Any) -> list:
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
            plan = check_string(
                tariff_dict.get("plan"),
                f"pvoutput.time-periods[{index}].plan",
                allow_none=True,
                allow_empty=True,
            )
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
            periods = parse_time_periods(tariff_dict["periods"], index)
            tariffs.append(
                Tariff(
                    plan=f"Unknown-{index}" if plan is None else plan,
                    from_date=from_dt,
                    to_date=to_dt,
                    default=default,
                    periods=periods,
                )
            )
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

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def consumption_enabled(self) -> bool:
        return self.consumption in (
            ConsumptionSource.CONSUMPTION,
            ConsumptionSource.IMPORTED,
            ConsumptionSource.NET_OF_BATTERY,
        )
