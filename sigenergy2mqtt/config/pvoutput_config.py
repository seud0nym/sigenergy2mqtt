from .validation import check_bool, check_int, check_log_level, check_string
from dataclasses import dataclass
import logging


@dataclass
class PVOutputConfiguration:
    enabled: bool = False

    consumption: bool = False
    exports: bool = False
    peak_power: bool = True

    api_key: str = ""
    system_id: str = ""

    output_hour: int = 21

    log_level: int = logging.WARNING
    update_debug_logging: bool = False

    temperature_topic: str = ""

    testing: bool = False

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            if "enabled" in config:
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: pvoutput.enabled = {config['enabled']}")
                self.enabled = check_bool(config['enabled'], "pvoutput.enabled")
            if self.enabled:
                for field, value in config.items():
                    if field != "enabled":
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: pvoutput.{field} = {'******' if field == 'api-key' else value}")
                    match field:
                        case "api-key":
                            self.api_key = check_string(value, "pvoutput.api-key", allow_none=(not self.enabled), allow_empty=(not self.enabled), hex_chars_only=True)
                        case "consumption":
                            self.consumption = check_bool(value, f"pvoutput.{field}")
                        case "exports":
                            self.exports = check_bool(value, f"pvoutput.{field}")
                        case "interval-minutes":
                            logging.warning(
                                "The 'interval-minutes' option is deprecated and will be removed in a future version. The Status Interval is now determined from the settings on pvoutput.org."
                            )
                        case "log-level":
                            self.log_level = check_log_level(value, f"pvoutput.{field}")
                        case "output-hour":
                            self.output_hour = check_int(value, f"pvoutput.{field}", min=0 if self.testing else 20, max=23)
                        case "peak-power":
                            self.peak_power = check_bool(value, f"pvoutput.{field}")
                        case "system-id":
                            self.system_id = check_string(str(value), f"pvoutput.{field}", allow_none=(not self.enabled), allow_empty=(not self.enabled))
                            if self.system_id == "testing":
                                self.testing = True
                                logging.warning(
                                    "PVOutput system-id is set to 'testing'. This is for testing purposes only and should not be used in production. PVOutput data will not be sent to the actual PVOutput service. Please set a valid system-id for production use."
                                )
                        case "temperature-topic":
                            self.temperature_topic = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                        case "update-debug-logging":
                            self.update_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")
