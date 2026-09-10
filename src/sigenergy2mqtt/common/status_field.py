from enum import StrEnum


class StatusField(StrEnum):
    BATTERY_POWER = "b1"
    BATTERY_SOC = "b2"
    BATTERY_CAPACITY = "b3"
    BATTERY_CHARGED = "b4"
    BATTERY_DISCHARGED = "b5"
    BATTERY_STATE = "b6"
    GENERATION_ENERGY = "v1"
    GENERATION_POWER = "v2"
    CONSUMPTION_ENERGY = "v3"
    CONSUMPTION_POWER = "v4"
    TEMPERATURE = "v5"
    VOLTAGE = "v6"
    V7 = "v7"
    V8 = "v8"
    V9 = "v9"
    V10 = "v10"
    V11 = "v11"
    V12 = "v12"
