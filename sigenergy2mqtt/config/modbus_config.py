from .smart_port_config import SmartPortConfig
from .validation import check_bool, check_host, check_int, check_int_list, check_log_level, check_port
from dataclasses import dataclass, field
from typing import List
import logging


@dataclass
class RegisterAccess:
    no_remote_ems: bool = False
    read_only: bool = True
    read_write: bool = True
    write_only: bool = True


@dataclass
class ScanInterval:
    realtime: int = 5
    high: int = 10
    medium: int = 60
    low: int = 600


@dataclass
class DeviceConfig:
    host: str = ""
    port: int = 502

    ac_chargers: List[int] = field(default_factory=list)
    dc_chargers: List[int] = field(default_factory=list)
    inverters: List[int] = field(default_factory=list)

    log_level: int = logging.WARNING

    registers = RegisterAccess()
    scan_interval = ScanInterval()

    smartport = SmartPortConfig()

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            for field, value in config.items():
                if field != "smart-port":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: modbus.{field} = {value}")
                match field:
                    case "host":
                        self.host = check_host(value, f"modbus.{field}")
                    case "port":
                        self.port = check_port(value, f"modbus.{field}")
                    case "log-level":
                        self.log_level = check_log_level(value, f"modbus.{field}")
                    case "no-remote-ems":
                        self.registers.no_remote_ems = check_bool(value, f"modbus.{field}")
                    case "read-only":
                        self.registers.read_only = check_bool(value, f"modbus.{field}")
                    case "read-write":
                        self.registers.read_write = check_bool(value, f"modbus.{field}")
                    case "write-only":
                        self.registers.write_only = check_bool(value, f"modbus.{field}")
                    case "ac-chargers":
                        self.ac_chargers = check_int_list(value, f"modbus.{field}")
                    case "dc-chargers":
                        self.dc_chargers = check_int_list(value, f"modbus.{field}")
                    case "inverters":
                        self.inverters = check_int_list(value, f"modbus.{field}")
                    case "smart-port":
                        self.smartport.configure(value, override)
                    case "scan-interval-low":
                        self.scan_interval.low = check_int(value, f"modbus.{field}", min=300)
                    case "scan-interval-medium":
                        self.scan_interval.medium = check_int(value, f"modbus.{field}", min=30)
                    case "scan-interval-high":
                        self.scan_interval.high = check_int(value, f"modbus.{field}", min=5)
                    case "scan-interval-realtime":
                        self.scan_interval.realtime = check_int(value, f"modbus.{field}", min=1)
                    case _:
                        raise ValueError(f"modbus device configuration element contains unknown option '{field}'")
            if len(self.inverters) == 0:
                self.inverters.append(1)
        else:
            raise ValueError("modbus device configuration elements must contain options and their values")
