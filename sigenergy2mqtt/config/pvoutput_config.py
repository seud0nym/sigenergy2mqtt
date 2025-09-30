from .validation import check_bool, check_int, check_log_level, check_string
from dataclasses import dataclass, field
import logging


@dataclass
class PVOutputConfiguration:
    enabled: bool = False

    consumption: str | None = None
    exports: bool = True
    imports: bool = True

    extended: dict[str, str] = field(
        default_factory=lambda: {
            "v7": "",
            "v8": "",
            "v9": "",
            "v10": "",
            "v11": "",
            "v12": "",
        }
    )

    api_key: str = ""
    system_id: str = ""

    output_hour: int = 23

    log_level: int = logging.WARNING
    update_debug_logging: bool = False

    temperature_topic: str = ""

    testing: bool = False

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
                                case True | "true" | "consumption":
                                    self.consumption = "consumption"
                                case "imported":
                                    self.consumption = "imported"
                                case _:
                                    raise ValueError(f"pvoutput.consumption must be 'true', 'false', 'consumption', or 'imports', got '{value}'")
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
                        case "v7" | "v8" | "v9" | "v10" | "v11" | "v12":
                            self.extended[field] = check_string(value, f"pvoutput.{field}", allow_none=True, allow_empty=True)
                        case "update-debug-logging":
                            self.update_debug_logging = check_bool(value, f"pvoutput.{field}")
                        case _:
                            if field != "enabled":
                                raise ValueError(f"pvoutput configuration element contains unknown option '{field}'")
        else:
            raise ValueError("pvoutput configuration element must contain options and their values")
