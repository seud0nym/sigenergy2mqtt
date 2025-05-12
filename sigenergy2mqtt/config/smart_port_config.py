from .validation import check_bool, check_host, check_int, check_module, check_port, check_string
from dataclasses import dataclass, field
from typing import Self
import logging


@dataclass
class ModuleConfig:
    name: str = ""
    host: str = ""
    port: int = None
    username: str = ""
    password: str = ""
    pv_power: str = ""

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "name":
                        if override:
                            logging.debug(f"Applying 'modbus smart-port module name' override from env/cli ({value})")
                        self.name = check_module(value, f"modbus smart-port module {field}")
                    case "host":
                        if override: 
                            logging.debug(f"Applying 'modbus smart-port module host' override from env/cli ({value})")
                        self.host = check_host(value, f"modbus smart-port module {field}")
                    case "port":
                        if override:
                            logging.debug(f"Applying 'modbus smart-port module port' override from env/cli ({value})")
                        self.port = check_port(value, f"modbus smart-port module {field}")
                    case "username":
                        if override:
                            logging.debug(f"Applying 'modbus smart-port module username' override from env/cli ({value})")
                        self.username = check_string(value, f"modbus smart-port module {field}")
                    case "password":
                        if override:
                            logging.debug("Applying 'modbus smart-port module password' override from env/cli (******)")
                        self.password = check_string(value, f"modbus smart-port module {field}")
                    case "pv-power":
                        if override:
                            logging.debug(f"Applying 'modbus smart-port module pv-power' override from env/cli ({value})")
                        self.pv_power = check_string(value, f"modbus smart-port module {field}")
                    case _:
                        raise ValueError(f"modbus smart-port module configuration element contains unknown option '{field}'")
        else:
            raise ValueError("modbus smart-port module configuration elements must contain options and their values")

@dataclass
class TopicConfig:
    topic: str = ""
    gain: int = 1

    @classmethod
    def configure(self, topics: list, override: bool = False) -> list[Self]:
        result: list[Self] = []
        if isinstance(topics, list):
            for config in topics:
                if isinstance(config, dict):
                    topic = TopicConfig()
                    for field, value in config.items():
                        match field:
                            case "topic":
                                if override:
                                    logging.debug(f"Applying 'modbus smart-port mqtt topic' override from env/cli ({value})")
                                topic.topic = check_string(value, f"modbus smart-port mqtt {field}", allow_none=False, allow_empty=False)
                            case "gain":
                                if override:
                                    logging.debug(f"Applying 'modbus smart-port mqtt gain' override from env/cli ({value})")
                                topic.gain = check_int(value, f"modbus smart-port mqtt {field}", allow_none=False, min=1)
                            case _:
                                raise ValueError(f"modbus smart-port mqtt topic configuration element contains unknown option '{field}'")
                    if topic.topic and not topic.topic.isspace(): # Command line/Environment variable overrides can cause an empty topic
                        result.append(topic)
                    result.append(topic)
                else:
                    raise ValueError("modbus smart-port mqtt configuration elements must contain a list of topics and, optionally, their gains")
                return result
            else:
                raise ValueError("modbus smart-port mqtt configuration elements must contain a list of topics and, optionally, their gains")
        else:
            raise ValueError("modbus configuration mqtt element must contain a list of Sigenergy hosts")

@dataclass
class SmartPortConfig:
    enabled: bool = False
    module: ModuleConfig = field(default_factory=ModuleConfig)
    mqtt: list[TopicConfig] = field(default_factory=list)

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "enabled":
                        if override:
                            logging.debug(f"Applying 'modbus smart-port enabled state' override from env/cli ({value})")
                        self.enabled = check_bool(value, f"modbus smart-port {field}")
                    case "module":
                        self.module.configure(value, override)
                    case "mqtt":
                        self.mqtt = TopicConfig.configure(value, override)
                    case _:
                        raise ValueError(f"modbus smart-port configuration element contains unknown option '{field}'")
            if self.enabled and (not self.module.name or self.module.name.isspace()) and len(self.mqtt) == 0:
                raise ValueError("modbus smart-port enabled, but no module name or MQTT topics configured")
        else:
            raise ValueError("modbus smart-port configuration elements must contain options and their values")
