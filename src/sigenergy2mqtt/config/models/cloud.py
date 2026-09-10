"""Sigenergy Cloud configuration sub-model."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from sigenergy_cloud import regions

from sigenergy2mqtt.common import ScanIntervalDefault
from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.validators import validate_log_level

if "aus" not in regions.REGION_BASE_URLS:
    # The 0.1.6 library only ships eu/cn/apac/us, so register Australia ourselves.
    # Trailing slash is required — the client appends paths directly.
    regions.REGION_BASE_URLS["aus"] = "https://api-aus.sigencloud.com/"


class CloudConfig(BaseModel):
    """Configuration for the Sigenergy Cloud service.

    Defines the parameters used to control the cloud integration.
    """

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Accept a region (e.g. "eu") and validate it."""
        v = v.strip()
        if not v:
            return ""
        if v not in regions.REGION_BASE_URLS:
            valid = ", ".join(regions.REGION_BASE_URLS.keys())
            raise ValueError(f"invalid region {v!r}, must be one of: {valid}")
        return v

    @model_validator(mode="after")
    def check_all_required_fields_provided(self) -> CloudConfig:
        fields = (self.username.strip(), self.password.strip(), self.region.strip())
        if all(not f for f in fields):  # if none are provided, normalise to empty strings
            self.username = self.password = self.region = ""
            return self
        if any(not f for f in fields):  # if some are provided and some are missing
            missing = [name for name, value in zip(("username", "password", "region"), fields) if not value]
            raise ValueError(f"missing required field(s): {', '.join(missing)}")
        return self

    model_config = _SUB

    username: str = Field("", alias="username")
    """The username for the Sigenergy Cloud service."""

    password: str = Field("", alias="password")
    """The password for the Sigenergy Cloud service."""

    region: str = Field("", alias="region")
    """The region to which the Sigenergy Cloud service belongs."""

    log_level: int = Field(logging.WARNING, alias="log-level")
    """Cloud subsystem log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)"""
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)

    scan_interval: int = Field(ScanIntervalDefault.CLOUD, ge=10)
    """The scan interval in seconds for retrieving cloud data. Default is 30 (seconds), and the minimum value is 10."""

    @computed_field(exclude_if=lambda _: True)
    @property
    def enabled(self) -> bool:
        """Return True if the cloud service is enabled (all required fields are provided)."""
        return bool(self.username.strip() and self.password.strip() and self.region.strip())
