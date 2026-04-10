"""Persistence configuration sub-model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sigenergy2mqtt.config.models._base import _SUB


class PersistenceConfig(BaseModel):
    """Configuration for the state persistence layer.

    Controls whether MQTT retained messages are used as a redundant
    backing store alongside the local disk-based state files.
    """

    model_config = _SUB

    mqtt_redundancy: bool = Field(
        True,
        alias="mqtt-redundancy",
    )
    """Set to False to disable MQTT retained message backup for state persistence."""

    mqtt_state_prefix: str = Field(
        "sigenergy2mqtt/_state",
        alias="mqtt-state-prefix",
    )
    """MQTT topic prefix for all persisted state messages."""

    disk_primary: bool = Field(
        True,
        alias="disk-primary",
    )
    """When True (default), disk is tried first on load; MQTT is used as fallback.
    Set to False to prefer MQTT over disk."""

    cache_warmup_timeout: float = Field(
        10.0,
        alias="cache-warmup-timeout",
        ge=1.0,
        le=60.0,
    )
    """Maximum seconds to wait for MQTT retained state during startup cache warming.
    The sentinel-based mechanism normally completes in milliseconds; this timeout
    is a safety limit for degraded broker conditions."""

    sync_timeout: float = Field(
        5.0,
        alias="sync-timeout",
        ge=0.1,
        le=30.0,
    )
    """Timeout in seconds for synchronous persistence operations when called from a non-asyncio thread."""
