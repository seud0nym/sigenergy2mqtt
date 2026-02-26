from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator, model_validator

from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.validators import validate_log_level


class InfluxDbConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    host: str = Field("127.0.0.1", alias="host")
    port: int = Field(8086, alias="port", ge=1, le=65535)
    username: str = Field("", alias="username")
    password: str = Field("", alias="password")
    database: str = Field("sigenergy", alias="database")
    org: str = Field("", alias="org")
    token: str = Field("", alias="token")
    bucket: str = Field("", alias="bucket")
    default_measurement: str = Field("state", alias="default-measurement", min_length=1)
    load_hass_history: bool = Field(False, alias="load-hass-history")
    include: list[str] = Field(default_factory=list, alias="include")
    exclude: list[str] = Field(default_factory=list, alias="exclude")
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)
    write_timeout: float = Field(30.0, alias="write-timeout", ge=0.1)
    read_timeout: float = Field(120.0, alias="read-timeout", ge=0.1)
    batch_size: int = Field(100, alias="batch-size", ge=1)
    flush_interval: float = Field(1.0, alias="flush-interval", ge=0.1)
    query_interval: float = Field(0.5, alias="query-interval", ge=0.0)
    max_retries: int = Field(3, alias="max-retries", ge=0)
    pool_connections: int = Field(100, alias="pool-connections", ge=1)
    pool_maxsize: int = Field(100, alias="pool-maxsize", ge=1)
    sync_chunk_size: int = Field(1000, alias="sync-chunk-size", ge=1)
    max_sync_workers: int = Field(4, alias="max-sync-workers", ge=1)

    @model_validator(mode="after")
    def check_credentials(self) -> "InfluxDbConfig":
        if not self.enabled:
            return self
        # Lone password with no username → treat as token (v2 API)
        if self.password and not self.username and not self.token:
            self.token = self.password
            self.password = ""
        has_v2 = bool(self.token and self.org)
        has_v1 = bool(self.username and self.password)
        if not has_v2 and not has_v1:
            raise ValueError(
                "influxdb configuration requires either v2 credentials (token and org) "
                "or v1 credentials (username and password)"
            )
        return self
