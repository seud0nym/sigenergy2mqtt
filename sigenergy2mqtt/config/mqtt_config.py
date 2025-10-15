from .validation import check_bool, check_host, check_int, check_log_level, check_port
from dataclasses import dataclass
import logging


@dataclass
class MqttConfiguration:
    broker: str = "127.0.0.1"
    port: int = 1883

    keepalive: int = 60

    tls: bool = False
    tls_insecure: bool = False  # Allow insecure TLS connections (not recommended)

    anonymous: bool = False
    username: str = None
    password: str = None

    log_level: int = logging.WARNING

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            if "tls" in config:
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: mqtt.tls = {config['tls']}")
                self.tls = check_bool(config["tls"], "mqtt.tls")
                if self.tls:
                    logging.debug("Applying new default of 8883 to mqtt.port because communication to broker over TLS/SSL is enabled")
                    self.port = 8883  # Default port for MQTT over TLS
            for field, value in config.items():
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: mqtt.{field} = {'******' if field == 'password' else value}")
                match field:
                    case "broker":
                        self.broker = check_host(value, f"mqtt.{field}")
                    case "port":
                        self.port = check_port(value, f"mqtt.{field}")
                    case "keepalive":
                        self.keepalive = check_int(value, f"mqtt.{field}", min=1)
                    case "anonymous":
                        self.anonymous = check_bool(value, f"mqtt.{field}")
                    case "username":
                        self.username = value
                    case "password":
                        self.password = value
                    case "log-level":
                        self.log_level = check_log_level(value, f"mqtt.{field}")
                    case "tls-insecure":
                        self.tls_insecure = check_bool(value, f"mqtt.{field}")
                    case _:
                        if field != "tls":
                            raise ValueError(f"mqtt configuration element contains unknown option '{field}'")
        else:
            raise ValueError("mqtt configuration element must contain options and their values")
