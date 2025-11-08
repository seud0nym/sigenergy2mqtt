from .validation import check_bool, check_int, check_log_level, check_string
from dataclasses import dataclass, field
from enum import StrEnum
import logging


class ConsumptionSource(StrEnum):
    CONSUMPTION = "consumption"
    IMPORTED = "imported"
    NET_OF_BATTERY = "net-of-battery"


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


class OutputField(StrEnum):
    GENERATION = "g"
    EXPORTS = "e"
    IMPORTS = "ip"
    PEAK_POWER = "pp"
    CONSUMPTION = "c"


@dataclass
class PVOutputConfiguration:
    enabled: bool = False

    consumption: str | None = None
    exports: bool = False
    imports: bool = False

    extended: dict[str, str] = field(
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

    testing: bool = False

    @property
    def consumption_enabled(self) -> bool:
        return self.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.IMPORTED, ConsumptionSource.NET_OF_BATTERY)

    def configure(self, config: dict, override: bool = False) -> None:
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
                            self.api_key = check_string(value, "pvoutput.api-key", allow_none=(not self.enabled), allow_empty=(not self.enabled), hex_chars_only=True)
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
                        case "interval-minutes":
                            logging.warning(
                                "The 'interval-minutes' option is deprecated and will be removed in a future version. The Status Interval is now determined from the settings on pvoutput.org."
                            )
                        case "log-level":
                            self.log_level = check_log_level(value, f"pvoutput.{field}")
                        case "output-hour":
                            self.output_hour = check_int(value, f"pvoutput.{field}", min=20, max=23, allowed=-1)
                        case "system-id":
                            self.system_id = check_string(str(value), f"pvoutput.{field}", allow_none=(not self.enabled), allow_empty=(not self.enabled))
                            if self.system_id == "testing":
                                self.testing = True
                                logging.warning(
                                    "PVOutput system-id is set to 'testing'. This is for testing purposes only and should not be used in production. PVOutput data will not be sent to the actual PVOutput service. Please set a valid system-id for production use."
                                )
                        case "temperature-topic":
                            self.temperature_topic = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                        case StatusField.V7.value | StatusField.V8.value | StatusField.V9.value | StatusField.V10.value | StatusField.V11.value | StatusField.V12.value:
                            self.extended[field] = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                        case "calc-debug-logging":
                            self.calc_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case "update-debug-logging":
                            self.update_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")
