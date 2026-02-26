from dataclasses import dataclass, field
from datetime import time

from .tariff_type import TariffType


@dataclass
class TimePeriod:
    type: TariffType
    start: time
    end: time
    days: list[str] = field(default_factory=list)
