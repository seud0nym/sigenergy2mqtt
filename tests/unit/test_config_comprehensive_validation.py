import logging
from datetime import time

import pytest

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
from sigenergy2mqtt.config.modbus_config import ModbusConfiguration
from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration, Tariff, TariffType, TimePeriod


class TestConfigComprehensiveValidation:
    def test_mqtt_validation(self):
        mqtt = MqttConfiguration(broker="")
        with pytest.raises(ValueError, match="mqtt.broker must be provided"):
            mqtt.validate()

        mqtt.broker = "localhost"
        mqtt.anonymous = False
        mqtt.username = ""
        with pytest.raises(ValueError, match="mqtt.username must be provided"):
            mqtt.validate()

        mqtt.username = "user"
        mqtt.password = ""
        with pytest.raises(ValueError, match="mqtt.password must be provided"):
            mqtt.validate()

        mqtt.password = "pass"
        mqtt.validate()  # Should pass

    def test_device_validation(self):
        dev = ModbusConfiguration(host="")
        with pytest.raises(ValueError, match="modbus.host must be provided"):
            dev.validate()

        dev.host = "1.2.3.4"
        dev.validate()  # Should pass

    def test_ha_validation(self):
        ha = HomeAssistantConfiguration(enabled=True, discovery_prefix="")
        with pytest.raises(ValueError, match="home-assistant.discovery-prefix must be provided"):
            ha.validate()

        ha.discovery_prefix = "homeassistant"
        ha.entity_id_prefix = ""
        with pytest.raises(ValueError, match="home-assistant.entity-id-prefix must be provided"):
            ha.validate()

        ha.entity_id_prefix = "sigen"
        ha.unique_id_prefix = ""
        with pytest.raises(ValueError, match="home-assistant.unique-id-prefix must be provided"):
            ha.validate()

        ha.unique_id_prefix = "sigen"
        ha.validate()  # Should pass

    def test_pvoutput_validation(self):
        pv = PVOutputConfiguration(enabled=True, api_key="")
        with pytest.raises(ValueError, match="pvoutput.api-key must be provided"):
            pv.validate()

        pv.api_key = "123"
        pv.system_id = ""
        with pytest.raises(ValueError, match="pvoutput.system-id must be provided"):
            pv.validate()

        pv.system_id = "abc"
        # Test time periods
        period = TimePeriod(type=TariffType.PEAK, start=time(12, 0), end=time(11, 0))
        tariff = Tariff(periods=[period])
        pv.tariffs = [tariff]
        with pytest.raises(ValueError, match="pvoutput time period end time .* must be after start time"):
            pv.validate()

        period.end = time(13, 0)
        pv.validate()  # Should pass

    def test_config_global_validation(self):
        # Reset Config for testing
        Config.modbus = []
        with pytest.raises(ValueError, match="At least one Modbus device must be configured"):
            Config.validate()

        Config.modbus = [ModbusConfiguration(host="localhost")]
        Config.mqtt = MqttConfiguration(broker="localhost", anonymous=True)
        Config.home_assistant = HomeAssistantConfiguration(enabled=False)
        Config.pvoutput = PVOutputConfiguration(enabled=False)

        Config.validate()  # Should pass
