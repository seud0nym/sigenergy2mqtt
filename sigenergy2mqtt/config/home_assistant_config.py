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
                        if override:
                            logging.debug(f"Applying 'home-assistant enabled state' override from env/cli ({value})")
                        self.enabled = check_bool(value, f"home-assistant {field}")
            if self.enabled:
                for field, value in config.items():
                    match field:
                        case "device-name-prefix":
                            if override:
                                logging.debug(f"Applying 'home-assistant device name prefix' override from env/cli ({value})")
                            self.device_name_prefix = check_string(value, f"home-assistant {field}", allow_none=False, allow_empty=True)
                        case "discovery-only":
                            if override:
                                logging.debug(f"Applying 'home-assistant discovery only' override from env/cli ({value})")
                            self.discovery_only = check_bool(value, f"home-assistant {field}")
                        case "discovery-prefix":
                            if override:
                                logging.debug(f"Applying 'home-assistant discovery prefix' override from env/cli ({value})")
                            self.discovery_prefix = check_string(value, f"home-assistant {field}", allow_none=False, allow_empty=False)
                        case "entity-id-prefix":
                            if override:
                                logging.debug(f"Applying 'home-assistant entity id prefix' override from env/cli ({value})")
                            self.entity_id_prefix = check_string(value, f"home-assistant {field}", allow_none=False, allow_empty=False)
                        case "republish-discovery-interval":
                            if override:
                                logging.debug(f"Applying 'home-assistant republish discovery interval' override from env/cli ({value})")
                            self.republish_discovery_interval = check_int(value, f"home-assistant {field}", min=0)
                        case "sensors-enabled-by-default":
                            if override:
                                logging.debug(f"Applying 'home-assistant sensors enabled by default' override from env/cli ({value})")
                            self.enabled_by_default = check_bool(value, f"home-assistant {field}")
                        case "unique-id-prefix":
                            if override:
                                logging.debug(f"Applying 'home-assistant unique id prefix' override from env/cli ({value})")
                            self.unique_id_prefix = check_string(value, f"home-assistant {field}", allow_none=False, allow_empty=False)
                        case _:
                            if field != "enabled":
                                raise ValueError(f"home-assistant configuration element contains unknown option '{field}'")
        else:
            raise ValueError("home-assistant configuration element must contain options and their values")
