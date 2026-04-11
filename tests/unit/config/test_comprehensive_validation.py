"""Comprehensive validation tests for pydantic config models."""

import pytest
from pydantic import ValidationError

from sigenergy2mqtt.config.settings import (
    HomeAssistantConfig,
    ModbusConfig,
    MqttConfig,
    PvOutputConfig,
    Settings,
)


class TestConfigComprehensiveValidation:
    def test_mqtt_validation_empty_broker(self):
        """MqttConfig itself does not raise on empty broker, but Settings cross-validates."""
        config = MqttConfig(broker="")
        assert config.broker == ""

    def test_mqtt_validation_non_anonymous_requires_username(self):
        with pytest.raises(ValidationError, match="mqtt.username must be provided"):
            MqttConfig(broker="localhost", anonymous=False, username="", password="pass")

    def test_mqtt_validation_non_anonymous_requires_password(self):
        with pytest.raises(ValidationError, match="mqtt.password must be provided"):
            MqttConfig(broker="localhost", anonymous=False, username="user", password="")

    def test_mqtt_validation_passes(self):
        config = MqttConfig(broker="localhost", anonymous=False, username="user", password="pass")
        assert config.broker == "localhost"
        assert config.username == "user"

    def test_device_validation_empty_host(self):
        with pytest.raises(ValidationError, match="modbus entry must have a host"):
            ModbusConfig(host="")

    def test_device_validation_passes(self):
        config = ModbusConfig(host="1.2.3.4")
        assert config.host == "1.2.3.4"

    def test_ha_validation_enabled_empty_discovery_prefix(self):
        with pytest.raises(ValidationError, match="home-assistant.discovery-prefix must be provided"):
            HomeAssistantConfig(enabled=True, discovery_prefix="")

    def test_ha_validation_enabled_empty_entity_id_prefix(self):
        with pytest.raises(ValidationError, match="home-assistant.entity-id-prefix must be provided"):
            HomeAssistantConfig(enabled=True, entity_id_prefix="")

    def test_ha_validation_enabled_empty_unique_id_prefix(self):
        with pytest.raises(ValidationError, match="home-assistant.unique-id-prefix must be provided"):
            HomeAssistantConfig(enabled=True, unique_id_prefix="")

    def test_ha_validation_passes(self):
        config = HomeAssistantConfig(enabled=True, discovery_prefix="homeassistant", entity_id_prefix="sigen", unique_id_prefix="sigen")
        assert config.enabled is True
        assert config.discovery_prefix == "homeassistant"

    def test_pvoutput_validation_enabled_empty_api_key(self):
        with pytest.raises(ValidationError, match="pvoutput.api-key must be provided"):
            PvOutputConfig(enabled=True, api_key="", system_id="123")

    def test_pvoutput_validation_enabled_empty_system_id(self):
        with pytest.raises(ValidationError, match="pvoutput.system-id must be provided"):
            PvOutputConfig(enabled=True, api_key="1a2b3c", system_id="")

    def test_pvoutput_validation_time_period_end_before_start(self):
        period_dict = {"type": "peak", "start": "12:00", "end": "11:00"}
        tariff_dict = {"plan": "test", "periods": [period_dict]}
        with pytest.raises(ValidationError, match="pvoutput time period end time .* must be after start time"):
            PvOutputConfig(enabled=True, api_key="1a2b3c", system_id="123", **{"time-periods": [tariff_dict]})

    def test_pvoutput_validation_passes(self):
        period_dict = {"type": "peak", "start": "12:00", "end": "13:00"}
        tariff_dict = {"plan": "test", "periods": [period_dict]}
        config = PvOutputConfig(enabled=True, api_key="1a2b3c", system_id="123", **{"time-periods": [tariff_dict]})
        assert config.enabled is True
        assert len(config.tariffs) == 1

    def test_settings_no_modbus_raises(self):
        """Settings cross-model validation requires at least one Modbus device."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError, match="At least one Modbus device must be configured"):
                Settings(modbus=[])
