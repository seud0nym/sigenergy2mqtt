from enum import StrEnum


class OutputField(StrEnum):
    GENERATION = "g"
    EXPORTS = "e"
    EXPORT_PEAK = "ep"
    EXPORT_OFF_PEAK = "eo"
    EXPORT_SHOULDER = "es"
    EXPORT_HIGH_SHOULDER = "eh"
    IMPORTS = ""
    IMPORT_PEAK = "ip"
    IMPORT_OFF_PEAK = "io"
    IMPORT_SHOULDER = "is"
    IMPORT_HIGH_SHOULDER = "ih"
    PEAK_POWER = "pp"
    CONSUMPTION = "c"
