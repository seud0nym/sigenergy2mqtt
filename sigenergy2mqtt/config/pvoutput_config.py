from .validation import check_bool, check_int, check_log_level, check_string
from dataclasses import dataclass
import logging


@dataclass
class PVOutputConfiguration:
    enabled: bool = False

    consumption: bool = False
    exports: bool = False
    peak_power: bool = False

    api_key: str = ""
    system_id: str = ""

    interval_minutes: int = 5
    
    output_hour: int = 23
 
    log_level: int = logging.CRITICAL

    def configure(self, config: dict) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "enabled":
                        self.enabled = check_bool(value, f"pvoutput {field}")
            if self.enabled:
                for field, value in config.items():
                    match field:
                        case "api-key":
                            self.api_key = value
                        case "consumption":
                            self.consumption = check_bool(value, f"pvoutput {field}")
                        case "exports":
                            self.exports = check_bool(value, f"pvoutput {field}")
                        case "interval-minutes":
                            self.interval_minutes = check_int(value, f"pvoutput {field}", min=5, max=60)
                        case "log-level":
                            self.log_level = check_log_level(value, f"pvoutput {field}")
                        case "peak-power":
                            self.peak_power = check_bool(value, f"pvoutput {field}")
                        case "system-id":
                            self.system_id = str(value)
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
                check_string(self.api_key, "pvoutput api-key", allow_none=False, allow_empty=False, hex_chars_only=True)
                check_string(self.system_id, "pvoutput system-id", allow_none=False, allow_empty=False)
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")
   