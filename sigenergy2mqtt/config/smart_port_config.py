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

    testing: bool = False

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                if override:
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: modbus.smart-port.module.{field} = {'******' if field == 'password' else value}")
                match field:
                    case "name":
                        self.name = check_module(value, f"modbus.smart-port.module.{field}")
                    case "host":
                        self.host = check_host(value, f"modbus.smart-port.module.{field}")
                    case "port":
                        self.port = check_port(value, f"modbus.smart-port.module.{field}")
                    case "username":
                        self.username = check_string(value, f"modbus.smart-port.module.{field}")
                    case "password":
                        self.password = check_string(value, f"modbus.smart-port.module.{field}")
                    case "pv-power":
                        self.pv_power = check_string(value, f"modbus.smart-port.module.{field}")
                    case _:
                        raise ValueError(f"modbus.smart-port.module.configuration element contains unknown option '{field}'")
        else:
            raise ValueError("modbus.smart-port.module.configuration elements must contain options and their values")

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
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: modbus.smart-port.mqtt.{field} = {value}")
                        match field:
                            case "topic":
                                topic.topic = check_string(value, f"modbus.smart-port.mqtt.{field}", allow_none=True, allow_empty=False)
                            case "gain":
                                topic.gain = check_int(value, f"modbus.smart-port.mqtt.{field}", allow_none=False, min=1)
                            case _:
                                raise ValueError(f"modbus.smart-port.mqtt {'override from env/cli' if override else 'configuration'} contains unknown option '{field}'")
                    if topic.topic and not topic.topic.isspace(): # Command line/Environment variable overrides can cause an empty topic
                        result.append(topic)
                else:
                    raise ValueError("modbus.smart-port.mqtt configuration elements must contain a list of topics and, optionally, their gains")
                return result
        else:
            raise ValueError("modbus.smart-port.mqtt configuration elements must contain a list of topics and, optionally, their gains")

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
                        logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: modbus.smart-port.enabled = {value}")
                        self.enabled = check_bool(value, f"modbus.smart-port.{field}")
                    case "module":
                        self.module.configure(value, override)
                    case "mqtt":
                        self.mqtt = TopicConfig.configure(value, override)
                    case _:
                        raise ValueError(f"modbus.smart-port configuration element contains unknown option '{field}'")
            if self.enabled and (not self.module.name or self.module.name.isspace()) and len(self.mqtt) == 0:
                raise ValueError("modbus.smart-port.enabled, but no module name or MQTT topics configured")
        else:
            raise ValueError("modbus.smart-port configuration elements must contain options and their values")
