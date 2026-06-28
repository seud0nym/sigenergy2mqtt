"""Health check configuration sub-model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from sigenergy2mqtt.config.models._base import _SUB


class HealthCheckConfig(BaseModel):
    """Configuration for service health checks.

    Defines the parameters used to check the health state of the service,
    and determine whether a restart should be triggered.
    """

    model_config = _SUB

    enabled: bool = Field(
        True,
    )
    """Set to False to disable health checks and auto-restart. Note: If running
    within Docker, this flag is ignored and treated as True for publishing purposes,
    but automatic restarts are always disabled."""

    interval: int = Field(
        30,
        ge=1,
    )
    """Interval in seconds at which the health check runs."""

    timeout: int = Field(
        5,
        ge=1,
    )
    """Timeout in seconds for checking health states."""

    start_period: int = Field(
        45,
        alias="start-period",
        ge=0,
    )
    """Initial start period in seconds during which health check failures do not count towards retries."""

    retries: int = Field(
        3,
        ge=1,
    )
    """Number of consecutive health check failures allowed before a restart is requested."""
