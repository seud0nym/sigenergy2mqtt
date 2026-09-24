"""Sigenergy Cloud configuration sub-model."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import regions
from sigenergy2mqtt.common import ScanIntervalDefault
from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.validators import validate_log_level


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
        if v not in (*regions.REGION_BASE_URLS, "testing"):
            valid = ", ".join((*regions.REGION_BASE_URLS.keys(), "testing"))
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

    testing_url: str = Field("", alias="testing-url", exclude=True)
    """Base URL for the integration-test cloud service."""

    @field_validator("testing_url")
    @classmethod
    def validate_testing_url(cls, value: str) -> str:
        """Validate the optional HTTP(S) testing endpoint base URL."""
        value = value.strip()
        if not value:
            return ""
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("testing URL must be a valid http/https URL") from exc
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("testing URL must use the http or https scheme")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("testing URL must not contain credentials, a query, or a fragment")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("testing URL port must be between 1 and 65535")
        if not value.endswith("/"):
            raise ValueError("testing URL must end with '/'")
        return value

    log_level: int = Field(logging.INFO, alias="log-level")
    """Cloud subsystem log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)"""
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)

    scan_interval: int = Field(ScanIntervalDefault.CLOUD, ge=10, alias="scan-interval")
    """The scan interval in seconds for retrieving cloud data. Default is 30 (seconds), and the minimum value is 10."""

    accept_unofficial_api_risk: bool = Field(False, alias="accept-unofficial-api-risk")
    """Explicit opt-in required because this backend uses an unpublished API."""

    @computed_field(exclude_if=lambda _: True)
    @property
    def enabled(self) -> bool:
        """Return True if the cloud service is enabled (all required fields are provided)."""
        return bool(self.username.strip() and self.password.strip() and self.region.strip())
