from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from sigenergy2mqtt.config.models._base import _SUB


class SmartPortMqttEntry(BaseModel):
    model_config = _SUB

    topic: Optional[str] = Field(None, alias="topic")
    gain: int = Field(1, alias="gain", ge=1)


class SmartPortModule(BaseModel):
    model_config = _SUB

    name: str = Field("", alias="name")
    host: str = Field("", alias="host")
    port: Optional[int] = Field(None, alias="port")
    username: str = Field("", alias="username")
    password: str = Field("", alias="password")
    pv_power: str = Field("", alias="pv-power")
    testing: bool = Field(False, alias="testing")


class SmartPortConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    module: SmartPortModule = Field(default_factory=SmartPortModule, alias="module")  # type: ignore[reportCallIssue]
    mqtt: list[SmartPortMqttEntry] = Field(default_factory=list, alias="mqtt")

    @model_validator(mode="after")
    def check_enabled(self) -> "SmartPortConfig":
        if self.enabled:
            if not self.module.name and not self.mqtt:
                raise ValueError("modbus.smart-port.enabled, but no module name or MQTT topics configured")
        return self
