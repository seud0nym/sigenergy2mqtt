import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any, Final, cast

from .validation import check_bool, check_date, check_int, check_log_level, check_string, check_time


class ConsumptionSource(StrEnum):
    CONSUMPTION = "consumption"
    IMPORTED = "imported"
    NET_OF_BATTERY = "net-of-battery"


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


class TariffType(StrEnum):
    OFF_PEAK = "off-peak"
    PEAK = "peak"
    SHOULDER = "shoulder"
    HIGH_SHOULDER = "high-shoulder"


class VoltageSource(StrEnum):
    PHASE_A = "phase-a"
    PHASE_B = "phase-b"
    PHASE_C = "phase-c"
    L_N_AVG = "l/n-avg"  # line to neutral average
    L_L_AVG = "l/l-avg"  # line to line average
    PV = "pv"  # average across PV strings


@dataclass
class TimePeriod:
    type: TariffType
    start: time
    end: time
    days: list[str] = field(default_factory=list)


@dataclass
class Tariff:
    plan: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    default: TariffType = TariffType.SHOULDER
    periods: list[TimePeriod] = field(default_factory=list)


WEEKDAYS: Final = ("Mon", "Tue", "Wed", "Thu", "Fri")
WEEKENDS: Final = ("Sat", "Sun")


@dataclass
class PVOutputConfiguration:
    enabled: bool = False

    consumption: str | None = None
    exports: bool = False
    imports: bool = False

    tariffs: list[Tariff] = field(default_factory=list)

    extended: dict[StatusField, str] = field(
        default_factory=lambda: {
            StatusField.V7: "",
            StatusField.V8: "",
            StatusField.V9: "",
            StatusField.V10: "",
            StatusField.V11: "",
            StatusField.V12: "",
        }
    )

    api_key: str = ""
    system_id: str = ""

    output_hour: int = 23

    log_level: int = logging.WARNING
    calc_debug_logging: bool = False
    update_debug_logging: bool = False

    temperature_topic: str = ""
    voltage: VoltageSource = VoltageSource.L_N_AVG

    testing: bool = False
    started = datetime.now().timestamp()

    @property
    def consumption_enabled(self) -> bool:
        return self.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.IMPORTED, ConsumptionSource.NET_OF_BATTERY)

    @property
    def current_time_period(self) -> tuple[OutputField | None, OutputField]:
        export_type = None  # No export default if completely unmatched, because total exports is always reported, but time periods may not be defined
        import_type = OutputField.IMPORT_PEAK  # Import default prior to introduction of time periods was peak
        if self.tariffs:
            now_date_time = datetime.now()
            today = now_date_time.date()
            now = now_date_time.time()
            dow = now_date_time.strftime("%a")  # 'Mon', 'Tue', etc.
            for tariff in self.tariffs:
                if (tariff.from_date is None or tariff.from_date <= today) and (tariff.to_date is None or tariff.to_date >= today):
                    for period in tariff.periods:
                        if "All" in period.days or dow in period.days or ("Weekdays" in period.days and dow in WEEKDAYS) or ("Weekends" in period.days and dow in WEEKENDS):
                            if period.start <= now < period.end:
                                if self.calc_debug_logging:
                                    logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) and time matched '{period.type}' ({period.start}-{period.end}) on {dow}")
                                export_type, import_type = self._type_to_output_fields(period.type)
                                break
                    else:
                        if self.calc_debug_logging:
                            logging.debug(f"Current date matched '{tariff.plan}' ({tariff.from_date} to {tariff.to_date}) but no time matched so using default '{tariff.default}'")
                        export_type, import_type = self._type_to_output_fields(tariff.default)  # Set the default types if date matched but time outside of defined periods
        return (export_type, import_type)

    def _type_to_output_fields(self, type: TariffType) -> tuple[OutputField, OutputField]:
        match type:
            case TariffType.OFF_PEAK:
                export_type = OutputField.EXPORT_OFF_PEAK
                import_type = OutputField.IMPORT_OFF_PEAK
            case TariffType.PEAK:
                export_type = OutputField.EXPORT_PEAK
                import_type = OutputField.IMPORT_PEAK
            case TariffType.SHOULDER:
                export_type = OutputField.EXPORT_SHOULDER
                import_type = OutputField.IMPORT_SHOULDER
            case TariffType.HIGH_SHOULDER:
                export_type = OutputField.EXPORT_HIGH_SHOULDER
                import_type = OutputField.IMPORT_HIGH_SHOULDER
            case _:
                raise ValueError(f"Invalid tariff type: {type}")
        return (export_type, import_type)

    def configure(self, config: Any, override: bool = False) -> None:
        if isinstance(config, dict):
            if "enabled" in config:
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: pvoutput.enabled = {config['enabled']}")
                self.enabled = check_bool(config["enabled"], "pvoutput.enabled")
            if self.enabled:
                for field, value in config.items():
                    if field != "enabled":
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: pvoutput.{field} = {'******' if field == 'api-key' else value}")
                    match field:
                        case "api-key":
                            validated = check_string(value, "pvoutput.api-key", allow_none=(not self.enabled), allow_empty=(not self.enabled), hex_chars_only=True)
                            self.api_key = validated if validated and isinstance(validated, str) else ""
                        case "consumption":
                            match value:
                                case False | "false":
                                    self.consumption = None
                                case True | "true" | ConsumptionSource.CONSUMPTION.value:
                                    self.consumption = ConsumptionSource.CONSUMPTION
                                case ConsumptionSource.IMPORTED.value:
                                    self.consumption = ConsumptionSource.IMPORTED
                                case ConsumptionSource.NET_OF_BATTERY.value:
                                    self.consumption = ConsumptionSource.NET_OF_BATTERY
                                case _:
                                    raise ValueError(
                                        f"pvoutput.consumption must be 'true', 'false', '{ConsumptionSource.CONSUMPTION.value}', '{ConsumptionSource.IMPORTED.value}', or '{ConsumptionSource.NET_OF_BATTERY.value}', got '{value}'"
                                    )
                        case "exports":
                            self.exports = check_bool(value, f"pvoutput.{field}")
                        case "imports":
                            self.imports = check_bool(value, f"pvoutput.{field}")
                        case "log-level":
                            self.log_level = check_log_level(value, f"pvoutput.{field}")
                        case "output-hour":
                            validated = check_int(value, f"pvoutput.{field}", min=20, max=23, allowed=-1)
                            if validated and isinstance(validated, int):
                                self.output_hour = validated
                        case "system-id":
                            validated = check_string(str(value), f"pvoutput.{field}", allow_none=(not self.enabled), allow_empty=(not self.enabled))
                            if validated and isinstance(validated, str):
                                self.system_id = validated
                                if self.system_id == "testing":
                                    self.testing = True
                                    logging.warning(
                                        "PVOutput system-id is set to 'testing'. This is for testing purposes only and should not be used in production. PVOutput data will not be sent to the actual PVOutput service. Please set a valid system-id for production use."
                                    )
                        case "temperature-topic":
                            validated = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                            if validated and isinstance(validated, str):
                                self.temperature_topic = validated
                        case "voltage":
                            self.voltage = VoltageSource(cast(str, check_string(value, f"pvoutput.{field}", *[v.value for v in VoltageSource], allow_empty=False, allow_none=False)))
                        case StatusField.V7.value | StatusField.V8.value | StatusField.V9.value | StatusField.V10.value | StatusField.V11.value | StatusField.V12.value:
                            validated = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                            if validated and isinstance(validated, str):
                                self.extended[field] = validated
                        case "calc-debug-logging":
                            self.calc_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case "update-debug-logging":
                            self.update_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case "time-periods":
                            if isinstance(value, list):
                                tariffs: list[Tariff] = []
                                index = 0
                                for tariff in value:
                                    if isinstance(tariff, dict):
                                        plan: str | None = None
                                        from_date: date = datetime.min.date()
                                        to_date: date = datetime.max.date()
                                        default: TariffType = TariffType.SHOULDER
                                        periods: list[TimePeriod] | None = None
                                        for key in tariff.keys():
                                            if key not in ("plan", "from-date", "to-date", "default", "periods"):
                                                raise ValueError(f"pvoutput.time-periods[{index}] contains unknown option '{key}'")
                                            match key:
                                                case "plan":
                                                    plan = check_string(tariff[key], f"pvoutput.time-periods[{index}].{key}", allow_none=True, allow_empty=True)
                                                case "from-date":
                                                    from_date = check_date(tariff[key], f"pvoutput.time-periods[{index}].{key}")
                                                case "to-date":
                                                    to_date = check_date(tariff[key], f"pvoutput.time-periods[{index}].{key}")
                                                case "default":
                                                    default = TariffType(
                                                        cast(
                                                            str,
                                                            check_string(
                                                                tariff[key], f"pvoutput.time-periods[{index}].{key}", "off-peak", "peak", "shoulder", "high-shoulder", allow_empty=False, allow_none=False
                                                            ),
                                                        )
                                                    )
                                                case "periods":
                                                    periods = self._parse_time_periods(tariff[key])
                                        if periods is None:
                                            raise ValueError(f"pvoutput.time-periods[{index}] must contain a 'periods' element")
                                        else:
                                            tariffs.append(Tariff(plan=f"Unknown-{index}" if plan is None else plan, from_date=from_date, to_date=to_date, default=default, periods=periods))
                                        index += 1
                                self.tariffs = sorted(tariffs, key=lambda t: (t.from_date or datetime.min, t.to_date or datetime.max), reverse=True)
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")

    def _parse_time_periods(self, value: list[dict[str, str]]) -> list[TimePeriod]:
        periods: list[TimePeriod] = []
        if isinstance(value, list):
            index = 0
            for period in value:
                if isinstance(period, dict):
                    if "type" in period and "start" in period and "end" in period:
                        type: TariffType = TariffType(
                            cast(str, check_string(period["type"], f"pvoutput.time-periods[{index}].type", "off-peak", "peak", "shoulder", "high-shoulder", allow_empty=False, allow_none=False))
                        )
                        start: time = check_time(period["start"], f"pvoutput.time-periods[{index}].start")
                        end: time = check_time(period["end"], f"pvoutput.time-periods[{index}].end")
                        days: list[str] = []
                        if "days" in period:
                            if isinstance(period["days"], list):
                                for day in period["days"]:
                                    validated = check_string(
                                        day.capitalize(),
                                        f"pvoutput.time-periods[{period['type']}:{period['start']}-{period['end']}].days",
                                        "Mon",
                                        "Tue",
                                        "Wed",
                                        "Thu",
                                        "Fri",
                                        "Sat",
                                        "Sun",
                                        "Weekdays",
                                        "Weekends",
                                        "All",
                                    )
                                    if validated and isinstance(validated, str):
                                        days.append(validated)
                            else:
                                raise ValueError(f"pvoutput.time-periods.periods[{index}].days must be a list of days, or Weekdays, Weekends, or All")
                        else:
                            days.append("All")
                        periods.append(TimePeriod(type=type, start=start, end=end, days=days))
                    else:
                        raise ValueError(f"pvoutput.time-periods.periods[{index}] must contain 'type', 'start', and 'end' elements")
                else:
                    raise ValueError(f"pvoutput.time-periods.periods[{index}] must be a time period definition")
                index += 1
            return periods
        else:
            raise ValueError("pvoutput time-periods.periods configuration element must contain a list of time period definitions")
