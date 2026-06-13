"""Settings model for Modbus auto-discovery preflight configuration."""

from __future__ import annotations

import ipaddress
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AutoDiscoverySettings(BaseSettings):
    """Parse only the settings required to decide and execute auto-discovery."""

    model_config = SettingsConfigDict(populate_by_name=True)

    yaml_file_arg: Optional[str] = Field(None, exclude=True)

    modbus_port: int = Field(502, alias="modbus-port")
    modbus_auto_discovery: Optional[str] = Field(None, alias="modbus-auto-discovery")
    modbus_auto_discovery_timeout: float = Field(0.25, alias="modbus-auto-discovery-timeout")
    modbus_auto_discovery_ping_timeout: float = Field(0.5, alias="modbus-auto-discovery-ping-timeout")
    modbus_auto_discovery_retries: int = Field(0, alias="modbus-auto-discovery-retries")
    modbus_auto_discovery_networks: list[str] = Field(default_factory=list, alias="modbus-auto-discovery-networks")
    modbus_auto_discovery_exclude: list[str] = Field(default_factory=lambda: ["PID", "PSS"], alias="modbus-auto-discovery-exclude")
    modbus_auto_discovery_max_device_id: int = Field(10, alias="modbus-auto-discovery-max-device-id")

    @field_validator("modbus_auto_discovery_networks", mode="before")
    @classmethod
    def validate_networks(cls, v: list[str] | str | None) -> list[str]:
        """Validate that each entry is a valid IPv4 network in CIDR notation."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [x.strip() for x in v.split(",") if x.strip()]
        validated: list[str] = []
        for entry in v:
            try:
                network = ipaddress.IPv4Network(entry, strict=False)
                validated.append(str(network))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid IPv4 CIDR network '{entry}': {e}")
        return validated

    @field_validator("modbus_auto_discovery_exclude", mode="before")
    @classmethod
    def validate_excludes(cls, v: list[str] | str | None) -> list[str]:
        """Validate that each entry is a valid device class name."""
        if v is None:
            return ["PID", "PSS"]  # defaults
        if isinstance(v, str):
            v = [x.strip() for x in v.split(",") if x.strip()]
        validated: list[str] = []
        for entry in v:
            if entry in ["ACCharger", "DCCharger", "PID", "PSS"]:
                validated.append(entry)
            else:
                raise ValueError(f"Invalid Device class name '{entry}'")
        return validated

    @field_validator("modbus_auto_discovery_max_device_id", mode="before")
    @classmethod
    def validate_max_device_id(cls, v: int | str | None) -> int:
        """Validate that the max device ID is a positive integer."""
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError("modbus-auto-discovery-max-device-id must be a positive integer")
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ValueError("modbus-auto-discovery-max-device-id must be a positive integer")
        if v > 246:
            raise ValueError("modbus-auto-discovery-max-device-id must be less than or equal to 246")
        return v
