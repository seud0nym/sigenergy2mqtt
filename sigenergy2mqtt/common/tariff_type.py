from enum import StrEnum


class TariffType(StrEnum):
    OFF_PEAK = "off-peak"
    PEAK = "peak"
    SHOULDER = "shoulder"
    HIGH_SHOULDER = "high-shoulder"
