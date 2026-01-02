from sigenergy2mqtt.config.validation import check_log_level
from dataclasses import dataclass, field
from .validation import check_bool, check_host, check_int, check_string
import logging


@dataclass
class InfluxDBConfiguration:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8086
    database: str = "sigenergy"
    # v2 fields
    token: str = ""
    org: str = ""
    bucket: str = ""
    org: str = ""
    username: str = ""
    password: str = ""
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    log_level: int = logging.WARNING

    def configure(self, config: dict, override: bool = False) -> None:
        if isinstance(config, dict):
            if "enabled" in config:
                logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: influxdb.enabled = {config['enabled']}")
                self.enabled = check_bool(config["enabled"], "influxdb.enabled")
            if self.enabled:
                for k, v in config.items():
                    if k == "enabled":
                        continue
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: influxdb.{k} = {'******' if 'password' in k.lower() else v}")
                    match k:
                        case "host":
                            self.host = check_host(v, "influxdb.host")
                        case "port":
                            self.port = check_int(v, "influxdb.port", min=1, max=65535)
                        case "database":
                            self.database = check_string(str(v), "influxdb.database", allow_none=False, allow_empty=False)
                        case "token":
                            self.token = check_string(v, "influxdb.token", allow_none=True, allow_empty=True)
                        case "org":
                            self.org = check_string(v, "influxdb.org", allow_none=True, allow_empty=True)
                        case "bucket":
                            self.bucket = check_string(v, "influxdb.bucket", allow_none=True, allow_empty=True)
                        case "org":
                            self.org = check_string(str(v), "influxdb.org", allow_none=True, allow_empty=True)
                        case "username":
                            self.username = check_string(v, "influxdb.username", allow_none=True, allow_empty=True)
                        case "password":
                            self.password = check_string(v, "influxdb.password", allow_none=True, allow_empty=True)
                        case "include":
                            if isinstance(v, list):
                                self.include = [str(x) for x in v]
                            else:
                                raise ValueError("influxdb.include must be a list of sensor identifiers")
                        case "exclude":
                            if isinstance(v, list):
                                self.exclude = [str(x) for x in v]
                            else:
                                raise ValueError("influxdb.exclude must be a list of sensor identifiers")
                        case "log-level":
                            self.log_level = check_log_level(v, "influxdb.log-level")
                        case _:
                            if k != "enabled":
                                raise ValueError(f"influxdb configuration element contains unknown option '{k}'")
        else:
            raise ValueError("influxdb configuration element must contain options and their values")
