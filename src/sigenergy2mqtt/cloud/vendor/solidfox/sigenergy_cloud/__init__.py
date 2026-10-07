"""Owned async client for the Sigenergy Cloud app API."""

from .app_version import MYSIGEN_APP_VERSION
from .client import UNLIMITED_POWER_KW, SigenergyCloudClient, is_unlimited_power
from .errors import (
    SigenergyCloudAPIError,
    SigenergyCloudAuthError,
    SigenergyCloudError,
    SigenergyCloudRateLimitError,
    SigenergyCloudTokenExpiredError,
)
from .models import (
    BatteryLevelSettings,
    InstantManualControl,
    InstantManualMode,
    PeakShavingSchedule,
    PeakShavingSlot,
)

__all__ = [
    "MYSIGEN_APP_VERSION",
    "UNLIMITED_POWER_KW",
    "BatteryLevelSettings",
    "InstantManualControl",
    "InstantManualMode",
    "PeakShavingSchedule",
    "PeakShavingSlot",
    "SigenergyCloudAPIError",
    "SigenergyCloudAuthError",
    "SigenergyCloudClient",
    "SigenergyCloudError",
    "SigenergyCloudRateLimitError",
    "SigenergyCloudTokenExpiredError",
    "is_unlimited_power",
]
