from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from sigenergy2mqtt.config.models._base import _SUB


class HomeAssistantConfig(BaseModel):
    model_config = _SUB

    enabled: bool = Field(False, alias="enabled")
    device_name_prefix: str = Field("", alias="device-name-prefix")
    discovery_prefix: str = Field("homeassistant", alias="discovery-prefix")
    entity_id_prefix: str = Field("sigen", alias="entity-id-prefix")
    unique_id_prefix: str = Field("sigen", alias="unique-id-prefix")
    use_sigenergy_local_modbus_naming: bool = Field(False, alias="use-sigenergy-local-modbus-naming")
    use_simplified_topics: bool = Field(False, alias="use-simplified-topics")
    edit_percentage_with_box: bool = Field(False, alias="edit-pct-box")
    discovery_only: bool = Field(False, alias="discovery-only")
    republish_discovery_interval: int = Field(0, alias="republish-discovery-interval", ge=0)
    enabled_by_default: bool = Field(False, alias="sensors-enabled-by-default")

    @model_validator(mode="after")
    def check_required_when_enabled(self) -> "HomeAssistantConfig":
        if self.enabled:
            if not self.discovery_prefix:
                raise ValueError("home-assistant.discovery-prefix must be provided")
            if not self.entity_id_prefix:
                raise ValueError("home-assistant.entity-id-prefix must be provided")
            if not self.unique_id_prefix:
                raise ValueError("home-assistant.unique-id-prefix must be provided")
        return self

    @model_validator(mode="after")
    def check_use_sigenergy_local_modbus_naming(self) -> "HomeAssistantConfig":
        if self.use_sigenergy_local_modbus_naming and self.entity_id_prefix != "sigen":
            from sigenergy2mqtt.config.config import ConfigurationError
            raise ConfigurationError("home-assistant.entity-id-prefix must be 'sigen' (default) when use-sigenergy-local-modbus-naming is true")
        return self
