from .validation import check_bool, check_host, check_log_level, check_port
from dataclasses import dataclass
import logging


@dataclass
class MqttConfiguration:
    broker: str = "127.0.0.1"
    port: int = 1883

    anonymous: bool = False
    username: str = None
    password: str = None

    log_level: int = logging.WARNING

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: mqtt.{field} = {'******' if field == 'password' else value}")
                match field:
                    case "broker":
                        self.broker = check_host(value, f"mqtt.{field}")
                    case "port":
                        self.port = check_port(value, f"mqtt.{field}")
                    case "anonymous":
                        self.anonymous = check_bool(value, f"mqtt.{field}")
                    case "username":
                        self.username = value
                    case "password":
                        self.password = value
                    case "log-level":
                        self.log_level = check_log_level(value, f"mqtt.{field}")
                    case _:
                        raise ValueError(f"mqtt configuration element contains unknown option '{field}'")
        else:
            raise ValueError("mqtt configuration element must contain options and their values")
