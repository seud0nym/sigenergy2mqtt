"""Owned async client for the Sigenergy Cloud app API."""

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
