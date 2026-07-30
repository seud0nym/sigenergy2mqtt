"""Diagnostics web server configuration sub-model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sigenergy2mqtt.config.models._base import _SUB


class DiagnosticsConfig(BaseModel):
    """Configuration for the diagnostics web server.

    Defines the parameters used to control the built-in diagnostics web
    service, including the address and port on which it listens and the
    page refresh interval.
    """

    model_config = _SUB

    enabled: bool = Field(
        True,
    )
    """Set to False to disable diagnostics. Note: If running
    within Docker, this flag is ignored and treated as True."""

    host: str = Field(
        "127.0.0.1",
        alias="host",
    )
    """The address to which the diagnostics web server is to be bound."""

    port: int = Field(
        8502,
        alias="port",
        ge=1,
        le=65535,
    )
    """The diagnostics web server listening port."""

    refresh_interval: float = Field(
        5.0,
        alias="refresh-interval",
        gt=0.0,
    )
    """The diagnostics web page refresh interval in seconds."""
