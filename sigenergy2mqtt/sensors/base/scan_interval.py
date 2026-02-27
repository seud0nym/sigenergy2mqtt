"""Scan interval tier definitions."""

from enum import StrEnum

from sigenergy2mqtt.common import ScanIntervalDefault
from sigenergy2mqtt.config import active_config


class ScanIntervalTier(StrEnum):
    REALTIME = "realtime"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScanInterval:
    """Helper to get scan interval for a given plant and tier."""

    @staticmethod
    def _get(plant_index: int, tier: ScanIntervalTier) -> int:
        if 0 <= plant_index < len(active_config.modbus):
            return getattr(active_config.modbus[plant_index].scan_interval, tier.value)
        return getattr(ScanIntervalDefault, tier.name)

    @staticmethod
    def low(plant_index: int) -> int:
        return ScanInterval._get(plant_index, ScanIntervalTier.LOW)

    @staticmethod
    def medium(plant_index: int) -> int:
        return ScanInterval._get(plant_index, ScanIntervalTier.MEDIUM)

    @staticmethod
    def high(plant_index: int) -> int:
        return ScanInterval._get(plant_index, ScanIntervalTier.HIGH)

    @staticmethod
    def realtime(plant_index: int) -> int:
        return ScanInterval._get(plant_index, ScanIntervalTier.REALTIME)
