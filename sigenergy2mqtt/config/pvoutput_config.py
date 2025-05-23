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

    interval_minutes: int = 5
    
    output_hour: int = 21
 
    log_level: int = logging.WARNING

    testing: bool = False

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "enabled":
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: pvoutput.enabled = {value}")
                        self.enabled = check_bool(value, f"pvoutput.{field}")
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
                            self.interval_minutes = check_int(value, f"pvoutput.{field}", min=5, max=15)
                        case "log-level":
                            self.log_level = check_log_level(value, f"pvoutput.{field}")
                        case "output-hour":
                            self.output_hour = check_int(value, f"pvoutput.{field}", min=20, max=23)
                        case "peak-power":
                            self.peak_power = check_bool(value, f"pvoutput.{field}")
                        case "system-id":
                            self.system_id = check_string(str(value), "pvoutput.system-id", allow_none=(not self.enabled), allow_empty=(not self.enabled))
                        case "testing":
                            self.testing = check_bool(value, f"pvoutput.{field}")
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")
   