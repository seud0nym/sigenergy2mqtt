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

    def configure(self, config: dict) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                for field, value in config.items():
                    match field:
                        case "broker":
                            self.broker = check_host(value, f"mqtt {field}")
                        case "port":
                            self.port = check_port(value, f"mqtt {field}")
                        case "anonymous":
                            self.anonymous = check_bool(value, f"mqtt {field}")
                        case "username":
                            self.username = value
                        case "password":
                            self.password = value
                        case "log-level":
                            self.log_level = check_log_level(value, f"mqtt {field}")
                        case _:
                            raise ValueError(f"mqtt configuration element contains unknown option '{field}'")
                if not self.anonymous:
                    if self.username is None:
                        raise ValueError("mqtt configuration does not contain the username and anonymous is not set to true")
                    if self.password is None:
                        raise ValueError("mqtt configuration does not contain the password and anonymous is not set to true")
        else:
            raise ValueError("mqtt configuration element must contain options and their values")
