from __future__ import annotations

import logging
import secrets
import string
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from sigenergy2mqtt.config.models._base import _SUB
from sigenergy2mqtt.config.validators import validate_log_level


class MqttConfig(BaseModel):
    model_config = _SUB

    broker: str = Field("127.0.0.1", alias="broker")
    port: int = Field(1883, alias="port", ge=1, le=65535)
    keepalive: int = Field(60, alias="keepalive", ge=1)
    retry_delay: int = Field(30)
    tls: bool = Field(False, alias="tls")
    tls_insecure: bool = Field(False, alias="tls-insecure")
    transport: str = Field("tcp", alias="transport", pattern=r"^(tcp|websockets)$")
    anonymous: bool = Field(False, alias="anonymous")
    username: Optional[str] = Field(None, alias="username")
    password: Optional[str] = Field(None, alias="password")
    client_id_prefix: str = Field(
        default_factory=lambda: (
            f"sigenergy2mqtt_"
            f"{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))}"
        )
    )
    log_level: int = Field(logging.WARNING, alias="log-level")
    _validate_log_level = field_validator("log_level", mode="before")(validate_log_level)

    @model_validator(mode="after")
    def apply_tls_port_default(self) -> "MqttConfig":
        """When TLS is enabled and the port is still the plain default, switch to 8883."""
        if self.tls and self.port == 1883:
            self.port = 8883
        return self

    @model_validator(mode="after")
    def check_auth(self) -> "MqttConfig":
        if not self.anonymous:
            fields_set = getattr(self, "model_fields_set", set())
            explicit_auth_config = any(field in fields_set for field in ("anonymous", "username", "password"))

            # Allow the bare model defaults (anonymous=False with no username/password)
            # so default object construction remains possible. Any explicit auth-related
            # configuration still requires both username and password.
            if explicit_auth_config or self.username is not None or self.password is not None:
                if not self.username:
                    raise ValueError("mqtt.username must be provided when mqtt.anonymous is false")
                if not self.password:
                    raise ValueError("mqtt.password must be provided when mqtt.anonymous is false")
        return self
