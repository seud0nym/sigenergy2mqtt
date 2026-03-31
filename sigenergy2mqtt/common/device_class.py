from enum import StrEnum
from typing import Optional

from .units import (
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)

# Source: https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/const.py#L91


class DeviceClass(StrEnum):
    """Device class for sensors."""

    # Non-numerical device classes
    DATE = "date"
    """Date.

    Unit of measurement: `None`

    ISO8601 format: https://en.wikipedia.org/wiki/ISO_8601
    """

    ENUM = "enum"
    """Enumeration.

    Provides a fixed list of options the state of the sensor can be in.

    Unit of measurement: `None`
    """

    TIMESTAMP = "timestamp"
    """Timestamp.

    Unit of measurement: `None`

    ISO8601 format: https://en.wikipedia.org/wiki/ISO_8601
    """

    # Numerical device classes, these should be aligned with NumberDeviceClass
    ABSOLUTE_HUMIDITY = "absolute_humidity"
    """Absolute humidity.

    Unit of measurement: `g/m³`, `mg/m³`
    """

    APPARENT_POWER = "apparent_power"
    """Apparent power.

    Unit of measurement: `mVA`, `VA`, `kVA`
    """

    AQI = "aqi"
    """Air Quality Index.

    Unit of measurement: `None`
    """

    AREA = "area"
    """Area

    Unit of measurement: `UnitOfArea` units
    """

    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"
    """Atmospheric pressure.

    Unit of measurement: `UnitOfPressure` units
    """

    BATTERY = "battery"
    """Percentage of battery that is left.

    Unit of measurement: `%`
    """

    BLOOD_GLUCOSE_CONCENTRATION = "blood_glucose_concentration"
    """Blood glucose concentration.

    Unit of measurement: `mg/dL`, `mmol/L`
    """

    CO = "carbon_monoxide"
    """Carbon Monoxide gas concentration.

    Unit of measurement: `ppb` (parts per billion), `ppm` (parts per million), `mg/m³`, `μg/m³`
    """

    CO2 = "carbon_dioxide"
    """Carbon Dioxide gas concentration.

    Unit of measurement: `ppm` (parts per million)
    """

    CONDUCTIVITY = "conductivity"
    """Conductivity.

    Unit of measurement: `S/cm`, `mS/cm`, `μS/cm`
    """

    CURRENT = "current"
    """Current.

    Unit of measurement: `A`, `mA`
    """

    DATA_RATE = "data_rate"
    """Data rate.

    Unit of measurement: UnitOfDataRate
    """

    DATA_SIZE = "data_size"
    """Data size.

    Unit of measurement: UnitOfInformation
    """

    DISTANCE = "distance"
    """Generic distance.

    Unit of measurement: `LENGTH_*` units
    - SI /metric: `mm`, `cm`, `m`, `km`
    - USCS / imperial: `in`, `ft`, `yd`, `mi`
    """

    DURATION = "duration"
    """Fixed duration.

    Unit of measurement: `d`, `h`, `min`, `s`, `ms`, `μs`
    """

    ENERGY = "energy"
    """Energy.

    Use this device class for sensors measuring energy consumption, for example
    electric energy consumption.
    Unit of measurement: `J`, `kJ`, `MJ`, `GJ`, `mWh`, `Wh`, `kWh`, `MWh`, `GWh`, `TWh`, `cal`, `kcal`, `Mcal`, `Gcal`
    """

    ENERGY_DISTANCE = "energy_distance"
    """Energy distance.

    Use this device class for sensors measuring energy by distance, for example the amount
    of electric energy consumed by an electric car.

    Unit of measurement: `kWh/100km`, `Wh/km`, `mi/kWh`, `km/kWh`
    """

    ENERGY_STORAGE = "energy_storage"
    """Stored energy.

    Use this device class for sensors measuring stored energy, for example the amount
    of electric energy currently stored in a battery or the capacity of a battery.

    Unit of measurement: `J`, `kJ`, `MJ`, `GJ`, `mWh`, `Wh`, `kWh`, `MWh`, `GWh`, `TWh`, `cal`, `kcal`, `Mcal`, `Gcal`
    """

    FREQUENCY = "frequency"
    """Frequency.

    Unit of measurement: `Hz`, `kHz`, `MHz`, `GHz`
    """

    GAS = "gas"
    """Gas.

    Unit of measurement:
    - SI / metric: `L`, `m³`
    - USCS / imperial: `ft³`, `CCF`, `MCF`
    """

    HUMIDITY = "humidity"
    """Relative humidity.

    Unit of measurement: `%`
    """

    ILLUMINANCE = "illuminance"
    """Illuminance.

    Unit of measurement: `lx`
    """

    IRRADIANCE = "irradiance"
    """Irradiance.

    Unit of measurement:
    - SI / metric: `W/m²`
    - USCS / imperial: `BTU/(h⋅ft²)`
    """

    MOISTURE = "moisture"
    """Moisture.

    Unit of measurement: `%`
    """

    MONETARY = "monetary"
    """Amount of money.

    Unit of measurement: ISO4217 currency code

    See https://en.wikipedia.org/wiki/ISO_4217#Active_codes for active codes
    """

    NITROGEN_DIOXIDE = "nitrogen_dioxide"
    """Amount of NO2.

    Unit of measurement: `ppb` (parts per billion), `ppm` (parts per million), `μg/m³`
    """

    NITROGEN_MONOXIDE = "nitrogen_monoxide"
    """Amount of NO.

    Unit of measurement: `ppb` (parts per billion), `μg/m³`
    """

    NITROUS_OXIDE = "nitrous_oxide"
    """Amount of N2O.

    Unit of measurement: `μg/m³`
    """

    OZONE = "ozone"
    """Amount of O3.

    Unit of measurement: `ppb` (parts per billion), `ppm` (parts per million), `μg/m³`
    """

    PH = "ph"
    """Potential hydrogen (acidity/alkalinity).

    Unit of measurement: Unitless
    """

    PM1 = "pm1"
    """Particulate matter <= 1 μm.

    Unit of measurement: `μg/m³`
    """

    PM10 = "pm10"
    """Particulate matter <= 10 μm.

    Unit of measurement: `μg/m³`
    """

    PM25 = "pm25"
    """Particulate matter <= 2.5 μm.

    Unit of measurement: `μg/m³`
    """

    PM4 = "pm4"
    """Particulate matter <= 4 μm.

    Unit of measurement: `μg/m³`
    """

    POWER_FACTOR = "power_factor"
    """Power factor.

    Unit of measurement: `%`, `None`
    """

    POWER = "power"
    """Power.

    Unit of measurement: `mW`, `W`, `kW`, `MW`, `GW`, `TW`, `BTU/h`
    """

    PRECIPITATION = "precipitation"
    """Accumulated precipitation.

    Unit of measurement: UnitOfPrecipitationDepth
    - SI / metric: `cm`, `mm`
    - USCS / imperial: `in`
    """

    PRECIPITATION_INTENSITY = "precipitation_intensity"
    """Precipitation intensity.

    Unit of measurement: UnitOfVolumetricFlux
    - SI /metric: `mm/d`, `mm/h`
    - USCS / imperial: `in/d`, `in/h`
    """

    PRESSURE = "pressure"
    """Pressure.

    Unit of measurement:
    - `mbar`, `cbar`, `bar`
    - `mPa`, `Pa`, `hPa`, `kPa`
    - `inHg`
    - `psi`
    - `inH₂O`
    """

    REACTIVE_ENERGY = "reactive_energy"
    """Reactive energy.

    Unit of measurement: `varh`, `kvarh`
    """

    REACTIVE_POWER = "reactive_power"
    """Reactive power.

    Unit of measurement: `mvar`, `var`, `kvar`
    """

    SIGNAL_STRENGTH = "signal_strength"
    """Signal strength.

    Unit of measurement: `dB`, `dBm`
    """

    SOUND_PRESSURE = "sound_pressure"
    """Sound pressure.

    Unit of measurement: `dB`, `dBA`
    """

    SPEED = "speed"
    """Generic speed.

    Unit of measurement: `SPEED_*` units or `UnitOfVolumetricFlux`
    - SI /metric: `mm/d`, `mm/h`, `m/s`, `km/h`, `mm/s`
    - USCS / imperial: `in/d`, `in/h`, `in/s`, `ft/s`, `mph`
    - Nautical: `kn`
    - Beaufort: `Beaufort`
    """

    SULPHUR_DIOXIDE = "sulphur_dioxide"
    """Amount of SO2.

    Unit of measurement: `ppb` (parts per billion), `μg/m³`
    """

    TEMPERATURE = "temperature"
    """Temperature.

    Unit of measurement: `°C`, `°F`, `K`
    """

    TEMPERATURE_DELTA = "temperature_delta"
    """Difference of temperatures - Temperature range.

    Unit of measurement: `°C`, `°F`, `K`
    """

    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"
    """Amount of VOC.

    Unit of measurement: `μg/m³`, `mg/m³`
    """

    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"
    """Ratio of VOC.

    Unit of measurement: `ppm`, `ppb`
    """

    VOLTAGE = "voltage"
    """Voltage.

    Unit of measurement: `V`, `mV`, `μV`, `kV`, `MV`
    """

    VOLUME = "volume"
    """Generic volume.

    Unit of measurement: `VOLUME_*` units
    - SI / metric: `mL`, `L`, `m³`
    - USCS / imperial: `ft³`, `CCF`, `MCF`, `fl. oz.`, `gal` (warning: volumes expressed in
    USCS/imperial units are currently assumed to be US volumes)
    """

    VOLUME_STORAGE = "volume_storage"
    """Generic stored volume.

    Use this device class for sensors measuring stored volume, for example the amount
    of fuel in a fuel tank.

    Unit of measurement: `VOLUME_*` units
    - SI / metric: `mL`, `L`, `m³`
    - USCS / imperial: `ft³`, `CCF`, `MCF`, `fl. oz.`, `gal` (warning: volumes expressed in
    USCS/imperial units are currently assumed to be US volumes)
    """

    VOLUME_FLOW_RATE = "volume_flow_rate"
    """Generic flow rate

    Unit of measurement: UnitOfVolumeFlowRate
    - SI / metric: `m³/h`, `m³/min`, `m³/s`, `L/h`, `L/min`, `L/s`, `mL/s`
    - USCS / imperial: `ft³/min`, `gal/min`, `gal/d`
    """

    WATER = "water"
    """Water.

    Unit of measurement:
    - SI / metric: `m³`, `L`
    - USCS / imperial: `ft³`, `CCF`, `MCF`, `gal` (warning: volumes expressed in
    USCS/imperial units are currently assumed to be US volumes)
    """

    WEIGHT = "weight"
    """Generic weight, represents a measurement of an object's mass.

    Weight is used instead of mass to fit with every day language.

    Unit of measurement: `MASS_*` units
    - SI / metric: `μg`, `mg`, `g`, `kg`
    - USCS / imperial: `oz`, `lb`
    """

    WIND_DIRECTION = "wind_direction"
    """Wind direction.

    Unit of measurement: `°`
    """

    WIND_SPEED = "wind_speed"
    """Wind speed.

    Unit of measurement: `SPEED_*` units
    - SI /metric: `m/s`, `km/h`
    - USCS / imperial: `ft/s`, `mph`
    - Nautical: `kn`
    - Beaufort: `Beaufort`
    """

    @staticmethod
    def is_valid_unit(device_class: "DeviceClass", unit: Optional[StrEnum] | str) -> bool:
        """Return True if unit is a valid unit of measurement for the given device class.

        Args:
            device_class: The DeviceClass to check against.
            unit: A StrEnum unit value, or None for device classes that take no unit.

        Returns:
            True if the unit is valid for the device class, False otherwise.

        Notes:
            MONETARY accepts any string unit (open ISO4217 set), so always returns True
            for that device class regardless of the unit value.
        """
        valid = _DEVICE_CLASS_UNITS[device_class]
        if valid is None:
            # None sentinel: this device class accepts any unit string (e.g. MONETARY).
            return True
        unit_value: str | None = unit.value if isinstance(unit, StrEnum) else unit
        return unit_value in valid


NON_NUMERIC_DEVICE_CLASSES = {
    DeviceClass.DATE,
    DeviceClass.ENUM,
    DeviceClass.TIMESTAMP,
}


# ---------------------------------------------------------------------------
# Valid units mapping
# ---------------------------------------------------------------------------
# Each entry maps a DeviceClass to the set of accepted unit strings.
#
# Convention:
#   frozenset  – membership is checked; None inside the set means "no unit".
#   None       – open/unbounded set; any unit string is accepted.
#
# When adding a new DeviceClass:
#   1. Add a frozenset of its documented unit strings, preferring frozenset(UnitOfXxx)
#      over hardcoded strings wherever a matching enum exists in units.py.
#   2. Include Python None in the frozenset wherever the docstring lists `None`
#      as a valid unit of measurement.
#   3. If the unit set is unbounded (e.g. currency codes), use None as the dict value.
#
# Entries marked "no enum in units.py" use hardcoded strings because no
# corresponding StrEnum has been defined yet. Add the import and switch to
# frozenset(UnitOfXxx) once the enum exists.
# ---------------------------------------------------------------------------

_ENERGY_UNITS: frozenset[str | None] = frozenset(UnitOfEnergy)

_VOLUME_UNITS: frozenset[str | None] = frozenset(
    {
        "mL",
        "L",
        "m³",
        "ft³",
        "CCF",
        "MCF",
        "fl. oz.",
        "gal",
    }
)

_SPEED_UNITS: frozenset[str | None] = frozenset(
    {
        "mm/d",
        "mm/h",
        "m/s",
        "km/h",
        "mm/s",  # SI / metric
        "in/d",
        "in/h",
        "in/s",
        "ft/s",
        "mph",  # USCS / imperial
        "kn",  # Nautical
        "Beaufort",  # Beaufort scale
    }
)

_DEVICE_CLASS_UNITS: dict[DeviceClass, frozenset[str | None] | None] = {
    # --- Non-numerical (unit is always None) ---
    DeviceClass.DATE: frozenset({None}),
    DeviceClass.ENUM: frozenset({None}),
    DeviceClass.TIMESTAMP: frozenset({None}),
    # --- Numerical ---
    DeviceClass.ABSOLUTE_HUMIDITY: frozenset({"g/m³", "mg/m³"}),
    # mVA is not yet in UnitOfApparentPower — supplemented manually.
    DeviceClass.APPARENT_POWER: frozenset(UnitOfApparentPower) | frozenset({"mVA"}),
    DeviceClass.AQI: frozenset({None}),
    # No UnitOfArea in units.py yet — hardcoded strings.
    DeviceClass.AREA: frozenset(
        {
            "m²",
            "cm²",
            "km²",
            "in²",
            "ft²",
            "yd²",
            "mi²",
            "ac",
            "ha",
        }
    ),
    # No UnitOfPressure in units.py yet — hardcoded strings.
    DeviceClass.ATMOSPHERIC_PRESSURE: frozenset(
        {
            "mbar",
            "cbar",
            "bar",
            "mPa",
            "Pa",
            "hPa",
            "kPa",
            "inHg",
            "psi",
            "inH₂O",
        }
    ),
    DeviceClass.BATTERY: frozenset({PERCENTAGE}),
    DeviceClass.BLOOD_GLUCOSE_CONCENTRATION: frozenset({"mg/dL", "mmol/L"}),
    DeviceClass.CO: frozenset({"ppb", "ppm", "mg/m³", "μg/m³"}),
    DeviceClass.CO2: frozenset({"ppm"}),
    DeviceClass.CONDUCTIVITY: frozenset({"S/cm", "mS/cm", "μS/cm"}),
    DeviceClass.CURRENT: frozenset(UnitOfElectricCurrent),
    # No UnitOfDataRate in units.py yet — hardcoded strings.
    DeviceClass.DATA_RATE: frozenset(
        {
            "bit/s",
            "kbit/s",
            "Mbit/s",
            "Gbit/s",
            "B/s",
            "kB/s",
            "MB/s",
            "GB/s",
        }
    ),
    # No UnitOfInformation in units.py yet — hardcoded strings.
    DeviceClass.DATA_SIZE: frozenset(
        {
            "bit",
            "kbit",
            "Mbit",
            "Gbit",
            "B",
            "kB",
            "MB",
            "GB",
            "TB",
            "PB",
            "EB",
            "ZB",
            "YB",
        }
    ),
    DeviceClass.DISTANCE: frozenset(
        {
            "mm",
            "cm",
            "m",
            "km",  # SI / metric
            "in",
            "ft",
            "yd",
            "mi",  # USCS / imperial
        }
    ),
    DeviceClass.DURATION: frozenset(UnitOfTime),
    DeviceClass.ENERGY: _ENERGY_UNITS,
    DeviceClass.ENERGY_DISTANCE: frozenset({"kWh/100km", "Wh/km", "mi/kWh", "km/kWh"}),
    DeviceClass.ENERGY_STORAGE: _ENERGY_UNITS,
    DeviceClass.FREQUENCY: frozenset(UnitOfFrequency),
    DeviceClass.GAS: frozenset({"L", "m³", "ft³", "CCF", "MCF"}),
    DeviceClass.HUMIDITY: frozenset({PERCENTAGE}),
    DeviceClass.ILLUMINANCE: frozenset({"lx"}),
    DeviceClass.IRRADIANCE: frozenset({"W/m²", "BTU/(h⋅ft²)"}),
    DeviceClass.MOISTURE: frozenset({PERCENTAGE}),
    # ISO4217 is an open set of currency codes — accept any string.
    DeviceClass.MONETARY: None,
    DeviceClass.NITROGEN_DIOXIDE: frozenset({"ppb", "ppm", "μg/m³"}),
    DeviceClass.NITROGEN_MONOXIDE: frozenset({"ppb", "μg/m³"}),
    DeviceClass.NITROUS_OXIDE: frozenset({"μg/m³"}),
    DeviceClass.OZONE: frozenset({"ppb", "ppm", "μg/m³"}),
    DeviceClass.PH: frozenset({None}),
    DeviceClass.PM1: frozenset({"μg/m³"}),
    DeviceClass.PM10: frozenset({"μg/m³"}),
    DeviceClass.PM25: frozenset({"μg/m³"}),
    DeviceClass.PM4: frozenset({"μg/m³"}),
    DeviceClass.POWER_FACTOR: frozenset({PERCENTAGE, None}),
    DeviceClass.POWER: frozenset(UnitOfPower),
    DeviceClass.PRECIPITATION: frozenset({"cm", "mm", "in"}),
    DeviceClass.PRECIPITATION_INTENSITY: frozenset({"mm/d", "mm/h", "in/d", "in/h"}),
    # No UnitOfPressure in units.py yet — hardcoded strings.
    DeviceClass.PRESSURE: frozenset(
        {
            "mbar",
            "cbar",
            "bar",
            "mPa",
            "Pa",
            "hPa",
            "kPa",
            "inHg",
            "psi",
            "inH₂O",
        }
    ),
    # No UnitOfReactiveEnergy in units.py yet — hardcoded strings.
    DeviceClass.REACTIVE_ENERGY: frozenset({"varh", "kvarh"}),
    # mvar is not yet in UnitOfReactivePower — supplemented manually.
    DeviceClass.REACTIVE_POWER: frozenset(UnitOfReactivePower) | frozenset({"mvar"}),
    DeviceClass.SIGNAL_STRENGTH: frozenset({"dB", "dBm"}),
    DeviceClass.SOUND_PRESSURE: frozenset({"dB", "dBA"}),
    DeviceClass.SPEED: _SPEED_UNITS,
    DeviceClass.SULPHUR_DIOXIDE: frozenset({"ppb", "μg/m³"}),
    DeviceClass.TEMPERATURE: frozenset(UnitOfTemperature),
    DeviceClass.TEMPERATURE_DELTA: frozenset(UnitOfTemperature),
    DeviceClass.VOLATILE_ORGANIC_COMPOUNDS: frozenset({"μg/m³", "mg/m³"}),
    DeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS: frozenset({"ppm", "ppb"}),
    DeviceClass.VOLTAGE: frozenset(UnitOfElectricPotential),
    DeviceClass.VOLUME: _VOLUME_UNITS,
    DeviceClass.VOLUME_STORAGE: _VOLUME_UNITS,
    # No UnitOfVolumeFlowRate in units.py yet — hardcoded strings.
    DeviceClass.VOLUME_FLOW_RATE: frozenset(
        {
            "m³/h",
            "m³/min",
            "m³/s",
            "L/h",
            "L/min",
            "L/s",
            "mL/s",
            "ft³/min",
            "gal/min",
            "gal/d",
        }
    ),
    DeviceClass.WATER: frozenset({"m³", "L", "ft³", "CCF", "MCF", "gal"}),
    DeviceClass.WEIGHT: frozenset(
        {
            "μg",
            "mg",
            "g",
            "kg",  # SI / metric
            "oz",
            "lb",  # USCS / imperial
        }
    ),
    DeviceClass.WIND_DIRECTION: frozenset({"°"}),
    DeviceClass.WIND_SPEED: frozenset(
        {
            "m/s",
            "km/h",  # SI / metric
            "ft/s",
            "mph",  # USCS / imperial
            "kn",  # Nautical
            "Beaufort",  # Beaufort scale
        }
    ),
}
