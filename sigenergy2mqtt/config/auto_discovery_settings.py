"""Settings model for Modbus auto-discovery preflight configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import Field
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
