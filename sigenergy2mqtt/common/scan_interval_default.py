from enum import IntEnum


class ScanIntervalDefault(IntEnum):
    REALTIME = 5
    HIGH = 10
    MEDIUM = 60
    LOW = 600
