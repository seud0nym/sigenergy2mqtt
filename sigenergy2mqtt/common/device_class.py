from enum import StrEnum


class DeviceClass(StrEnum):
    BATTERY = "battery"
    CURRENT = "current"
    ENERGY = "energy"
    ENUM = "enum"
    FREQUENCY = "frequency"
    POWER = "power"
    POWER_FACTOR = "power_factor"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"
    VOLTAGE = "voltage"
