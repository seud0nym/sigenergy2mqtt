from enum import IntEnum


class Constants(IntEnum):
    PLANT_DEVICE_ADDRESS = 247
    THREE_PHASE_OUTPUT_TYPE = 2  # L1/L2/L3/N
    UINT32_MAX = 4294967295


class ScanIntervalDefault(IntEnum):
    REALTIME = 5
    HIGH = 10
    MEDIUM = 60
    LOW = 600
