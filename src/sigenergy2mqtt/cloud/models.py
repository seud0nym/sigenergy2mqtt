"""Domain objects shared by battery-control backends."""

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum


class InstantControlMode(StrEnum):
    CHARGE = "charge"
    DISCHARGE = "discharge"
    HOLD = "hold"
    SELF_CONSUMPTION = "self_consumption"


class ControlFeature(StrEnum):
    POWER_LIMIT = "power_limit"
    SOURCE_PRIORITY = "source_priority"
    SCHEDULING = "scheduling"
    BATCH_COMMANDS = "batch_commands"


@dataclass(frozen=True, slots=True)
class Capabilities:
    features: frozenset[ControlFeature]
    min_duration: timedelta
    max_duration: timedelta
    max_batch_size: int = 1

    def supports(self, feature: ControlFeature) -> bool:
        return feature in self.features


@dataclass(frozen=True, slots=True)
class InstantOverrideCommand:
    mode: InstantControlMode
    duration: timedelta
    power_kw: float | None = None
    charge_priority: str | None = None
    discharge_priority: str | None = None
    starts_at: float | None = None


@dataclass(frozen=True, slots=True)
class InstantControlStatus:
    enabled: bool
    mode: InstantControlMode | None
    ends_at: float | None
