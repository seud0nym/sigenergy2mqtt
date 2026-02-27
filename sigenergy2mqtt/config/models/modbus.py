from __future__ import annotations

import dataclasses
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from sigenergy2mqtt.common import ScanIntervalDefault
from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.models.smart_port import SmartPortConfig
from sigenergy2mqtt.config.validators import validate_log_level


class RegisterAccess(BaseModel):
    model_config = _SUB

    no_remote_ems: bool = Field(False, alias="no-remote-ems")
    read_only: bool = Field(True, alias="read-only")
    read_write: bool = Field(True, alias="read-write")
    write_only: bool = Field(True, alias="write-only")


class ScanInterval(BaseModel):
    model_config = _SUB

    low: int = Field(ScanIntervalDefault.LOW, ge=1)
    medium: int = Field(ScanIntervalDefault.MEDIUM, ge=1)
    high: int = Field(ScanIntervalDefault.HIGH, ge=1)
    realtime: int = Field(ScanIntervalDefault.REALTIME, ge=1)


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
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)

        # ── Register access fields ───────────────────────────────────────────
        raw_reg = data.get("registers")
        if dataclasses.is_dataclass(raw_reg) and not isinstance(raw_reg, type):
            reg = dataclasses.asdict(raw_reg)
        elif isinstance(raw_reg, dict):
            reg = dict(raw_reg)
        else:
            reg = {}
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
        raw_si = data.get("scan_interval") or data.get("scan-interval")
        if dataclasses.is_dataclass(raw_si) and not isinstance(raw_si, type):
            si = dataclasses.asdict(raw_si)
        elif isinstance(raw_si, dict):
            si = dict(raw_si)
        else:
            si = {}
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
        """Default to inverter device ID 1 when nothing is specified."""
        if not self.inverters and not self.ac_chargers and not self.dc_chargers:
            self.inverters = [1]
        return self
