import logging
from dataclasses import dataclass, field
from typing import cast

from sigenergy2mqtt.config.validation import check_log_level

from .validation import check_bool, check_float, check_host, check_int, check_string


@dataclass
class InfluxDBConfiguration:
    enabled: bool = False

    host: str = "127.0.0.1"
    port: int = 8086
    database: str = "sigenergy"

    default_measurement: str = "state"

    load_hass_history: bool = False

    # v2 fields
    token: str = ""
    org: str = ""
    bucket: str = ""
    username: str = ""
    password: str = ""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    write_timeout: float = 30.0
    read_timeout: float = 120.0
    batch_size: int = 100
    flush_interval: float = 1.0
    query_interval: float = 0.5
    max_retries: int = 3
    pool_connections: int = 100
    pool_maxsize: int = 100
    sync_chunk_size: int = 1000
    max_sync_workers: int = 4

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
                            self.port = cast(int, check_int(v, "influxdb.port", min=1, max=65535))
                        case "database":
                            self.database = cast(str, check_string(str(v), "influxdb.database", allow_none=False, allow_empty=False))
                        case "token":
                            self.token = "" if v is None else cast(str, check_string(v, "influxdb.token", allow_none=True, allow_empty=True))
                        case "org":
                            self.org = "" if v is None else cast(str, check_string(v, "influxdb.org", allow_none=True, allow_empty=True))
                        case "bucket":
                            self.bucket = "" if v is None else cast(str, check_string(v, "influxdb.bucket", allow_none=True, allow_empty=True))
                        case "username":
                            self.username = "" if v is None else cast(str, check_string(v, "influxdb.username", allow_none=True, allow_empty=True))
                        case "password":
                            self.password = "" if v is None else cast(str, check_string(v, "influxdb.password", allow_none=True, allow_empty=True))
                        case "default-measurement":
                            self.default_measurement = cast(str, check_string(str(v), "influxdb.default-measurement", allow_none=False, allow_empty=False))
                        case "load-hass-history":
                            self.load_hass_history = check_bool(v, "influxdb.load-hass-history")
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
                        case "write-timeout":
                            self.write_timeout = cast(float, check_float(v, "influxdb.write-timeout", min=0.1))
                        case "read-timeout":
                            self.read_timeout = cast(float, check_float(v, "influxdb.read-timeout", min=0.1))
                        case "batch-size":
                            self.batch_size = cast(int, check_int(v, "influxdb.batch-size", min=1))
                        case "flush-interval":
                            self.flush_interval = cast(float, check_float(v, "influxdb.flush-interval", min=0.1))
                        case "query-interval":
                            self.query_interval = cast(float, check_float(v, "influxdb.query-interval", min=0.0))
                        case "max-retries":
                            self.max_retries = cast(int, check_int(v, "influxdb.max-retries", min=0))
                        case "pool-connections":
                            self.pool_connections = cast(int, check_int(v, "influxdb.pool-connections", min=1))
                        case "pool-maxsize":
                            self.pool_maxsize = cast(int, check_int(v, "influxdb.pool-maxsize", min=1))
                        case "sync-chunk-size":
                            self.sync_chunk_size = cast(int, check_int(v, "influxdb.sync-chunk-size", min=1))
                        case "max-sync-workers":
                            self.max_sync_workers = cast(int, check_int(v, "influxdb.max-sync-workers", min=1))
                        case _:
                            if k != "enabled":
                                raise ValueError(f"influxdb configuration element contains unknown option '{k}'")
                # Validate that a valid combination of credentials is supplied
                # If password is provided without username or token, treat password as token
                if self.password and not self.username and not self.token:
                    self.token = self.password
                    self.password = ""
                has_v2_credentials = bool(self.token and self.org)
                has_v1_credentials = bool(self.username and self.password)
                if not has_v2_credentials and not has_v1_credentials:
                    raise ValueError("influxdb configuration requires either v2 credentials (token and org) or v1 credentials (username and password)")
        else:
            raise ValueError("influxdb configuration element must contain options and their values")
