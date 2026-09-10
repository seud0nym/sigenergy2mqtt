from enum import IntEnum


class Constants(IntEnum):
    MAX_MODBUS_REGISTERS_PER_REQUEST = 124  # Protocol 6.1.1/6.1.2
    PLANT_DEVICE_ADDRESS = 247
    THREE_PHASE_OUTPUT_TYPE = 2  # L1/L2/L3/N
    UINT32_MAX = 4294967295
