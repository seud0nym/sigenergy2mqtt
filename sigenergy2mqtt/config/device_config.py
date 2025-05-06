from .smart_port_config import SmartPortConfig
from .validation import check_bool, check_host, check_int_list, check_log_level, check_port
from dataclasses import dataclass, field
from typing import List
import logging



@dataclass
class RegisterAccess:
    read_only: bool = True
    read_write: bool = True
    write_only: bool = True

@dataclass
class DeviceConfig:
    host: str = ""
    port: int = 502

    ac_chargers: List[int] = field(default_factory=list)
    dc_chargers: List[int] = field(default_factory=list)
    inverters: List[int] = field(default_factory=list)

    log_level: int = logging.WARNING

    registers = RegisterAccess()

    smartport = SmartPortConfig()

    def configure(self, config: dict) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                match field:
                    case "host":
                        self.host = check_host(value, f"modbus {field}")
                    case "port":
                        self.port = check_port(value, f"modbus {field}")
                    case "log-level":
                        self.log_level = check_log_level(value, f"modbus {field}")
                    case "read-only":
                        self.registers.read_only = check_bool(value, f"modbus {field}")
                    case "read-write":
                        self.registers.read_write = check_bool(value, f"modbus {field}")
                    case "write-only":
                        self.registers.write_only = check_bool(value, f"modbus {field}")
                    case "ac-chargers":
                        self.ac_chargers = check_int_list(value, f"modbus {field}")
                    case "dc-chargers":
                        self.dc_chargers = check_int_list(value, f"modbus {field}")
                    case "inverters":
                        self.inverters = check_int_list(value, f"modbus {field}")
                    case "smart-port":
                        self.smartport.configure(value)
                    case _:
                        raise ValueError(f"modbus device configuration element contains unknown option '{field}'")
            if len(self.ac_chargers) > 0:
                if (len(self.inverters) > 0 or len(self.dc_chargers) > 0):
                    raise ValueError("modbus host with ac-chargers configured cannot contain configuration for dc-chargers or inverters")
            elif len(self.inverters) == 0:
                self.inverters.append(1)
        else:
            raise ValueError("modbus device configuration elements must contain options and their values")
