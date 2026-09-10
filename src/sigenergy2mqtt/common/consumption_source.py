from enum import StrEnum


class ConsumptionSource(StrEnum):
    CONSUMPTION = "consumption"
    IMPORTED = "imported"
    NET_OF_BATTERY = "net-of-battery"
