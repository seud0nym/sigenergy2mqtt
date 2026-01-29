import logging
import secrets
import string
from dataclasses import dataclass
from typing import Literal, cast

from .validation import check_bool, check_host, check_int, check_log_level, check_port, check_string

TRANSPORTS = Literal["tcp", "websockets"]


@dataclass
class MqttConfiguration:
    broker: str = "127.0.0.1"
    port: int = 1883
    transport: Literal["tcp", "websockets"] = "tcp"

    keepalive: int = 60
    retry_delay: int = 30

    tls: bool = False
    tls_insecure: bool = False  # Allow insecure TLS connections (not recommended)

    anonymous: bool = False
    username: str | None = None
    password: str | None = None

    client_id_prefix: str = f"sigenergy2mqtt_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))}"

    log_level: int = logging.WARNING

    def validate(self) -> None:
        if not self.broker:
            raise ValueError("mqtt.broker must be provided")
        if not self.anonymous:
            if not self.username:
                raise ValueError("mqtt.username must be provided when anonymous is false")
            if not self.password:
                raise ValueError("mqtt.password must be provided when anonymous is false")

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
                        self.keepalive = cast(int, check_int(value, f"mqtt.{field}", min=1))
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
                    case "transport":
                        self.transport = cast(TRANSPORTS, check_string(value, f"mqtt.{field}", "tcp", "websockets", allow_none=False, allow_empty=False))
                    case _:
                        if field != "tls":
                            raise ValueError(f"mqtt configuration element contains unknown option '{field}'")
        else:
            raise ValueError("mqtt configuration element must contain options and their values")
