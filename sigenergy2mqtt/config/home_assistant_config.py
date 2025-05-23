from .validation import check_bool, check_int, check_string
from dataclasses import dataclass
import logging


@dataclass
class HomeAssistantConfiguration:
    enabled: bool = False
    discovery_only: bool = False
    republish_discovery_interval: int = 0

    discovery_prefix: str = "homeassistant"
    entity_id_prefix: str = "sigen"
    unique_id_prefix: str = "sigen"
    device_name_prefix: str = ""

    enabled_by_default: bool = False

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "enabled":
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: home-assistant.{field} = {value}")
                        self.enabled = check_bool(value, f"home-assistant.{field}")
            if self.enabled:
                for field, value in config.items():
                    if field != "enabled":
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: home-assistant.{field} = {value}")
                    match field:
                        case "device-name-prefix":
                            self.device_name_prefix = check_string(value, f"home-assistant.{field}", allow_none=False, allow_empty=True)
                        case "discovery-only":
                            self.discovery_only = check_bool(value, f"home-assistant.{field}")
                        case "discovery-prefix":
                            self.discovery_prefix = check_string(value, f"home-assistant.{field}", allow_none=False, allow_empty=False)
                        case "entity-id-prefix":
                            self.entity_id_prefix = check_string(value, f"home-assistant.{field}", allow_none=False, allow_empty=False)
                        case "republish-discovery-interval":
                            self.republish_discovery_interval = check_int(value, f"home-assistant.{field}", min=0)
                        case "sensors-enabled-by-default":
                            self.enabled_by_default = check_bool(value, f"home-assistant.{field}")
                        case "unique-id-prefix":
                            self.unique_id_prefix = check_string(value, f"home-assistant.{field}", allow_none=False, allow_empty=False)
                        case _:
                            if field != "enabled":
                                raise ValueError(f"home-assistant.configuration element contains unknown option '{field}'")
        else:
            raise ValueError("home-assistant configuration element must contain options and their values")
