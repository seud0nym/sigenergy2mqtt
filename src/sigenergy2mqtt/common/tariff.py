from dataclasses import dataclass, field
from datetime import date

from .tariff_type import TariffType
from .time_period import TimePeriod


@dataclass
class Tariff:
    plan: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    default: TariffType = TariffType.SHOULDER
    periods: list[TimePeriod] = field(default_factory=list)
