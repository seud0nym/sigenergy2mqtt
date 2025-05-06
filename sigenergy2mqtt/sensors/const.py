from enum import StrEnum
from typing import Final

PERCENTAGE: Final = "%"


class DeviceClass(StrEnum):
    BATTERY = "battery"
    CURRENT = "current"
    ENERGY = "energy"
    FREQUENCY = "frequency"
    POWER = "power"
    POWER_FACTOR = "power_factor"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"
    VOLTAGE = "voltage"


class InputType(StrEnum):
    HOLDING = "holding"
    INPUT = "input"


class StateClass(StrEnum):
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


class UnitOfApparentPower(StrEnum):
    """Apparent power units."""

    VOLT_AMPERE = "VA"
    KILOVOLT_AMPERE = "kVA"


class UnitOfElectricCurrent(StrEnum):
    """Electric current units."""

    MILLIAMPERE = "mA"
    AMPERE = "A"


class UnitOfElectricPotential(StrEnum):
    """Electric potential units."""

    MICROVOLT = "µV"
    MILLIVOLT = "mV"
    VOLT = "V"
    KILOVOLT = "kV"
    MEGAVOLT = "MV"


class UnitOfEnergy(StrEnum):
    """Energy units."""

    JOULE = "J"
    KILO_JOULE = "kJ"
    MEGA_JOULE = "MJ"
    GIGA_JOULE = "GJ"
    MILLIWATT_HOUR = "mWh"
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"
    MEGA_WATT_HOUR = "MWh"
    GIGA_WATT_HOUR = "GWh"
    TERA_WATT_HOUR = "TWh"
    CALORIE = "cal"
    KILO_CALORIE = "kcal"
    MEGA_CALORIE = "Mcal"
    GIGA_CALORIE = "Gcal"


class UnitOfFrequency(StrEnum):
    """Frequency units."""

    HERTZ = "Hz"
    KILOHERTZ = "kHz"
    MEGAHERTZ = "MHz"
    GIGAHERTZ = "GHz"


class UnitOfPower(StrEnum):
    """Power units."""

    MILLIWATT = "mW"
    WATT = "W"
    KILO_WATT = "kW"
    MEGA_WATT = "MW"
    GIGA_WATT = "GW"
    TERA_WATT = "TW"
    BTU_PER_HOUR = "BTU/h"


class UnitOfReactivePower(StrEnum):
    """Reactive power units."""

    VOLT_AMPERE_REACTIVE = "var"
    KILO_VOLT_AMPERE_REACTIVE = "kvar"


class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class UnitOfTime(StrEnum):
    """Time units."""

    MICROSECONDS = "μs"
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    WEEKS = "w"
    MONTHS = "m"
    YEARS = "y"
