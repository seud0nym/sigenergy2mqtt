"""Tests for pydantic config sub-model objects."""

import logging
from datetime import time

import pytest
from pydantic import ValidationError

from sigenergy2mqtt.common.consumption_source import ConsumptionSource
from sigenergy2mqtt.common.tariff_type import TariffType
from sigenergy2mqtt.common.voltage_source import VoltageSource
from sigenergy2mqtt.config.models import HomeAssistantConfig, ModbusConfig, MqttConfig, PvOutputConfig, SmartPortConfig, SmartPortModule, SmartPortMqttEntry


class TestHomeAssistantConfig:
    def test_default_values(self):
        config = HomeAssistantConfig()
        assert config.enabled is False
        assert config.discovery_prefix == "homeassistant"
        assert config.entity_id_prefix == "sigen"
        assert config.unique_id_prefix == "sigen"

    def test_enabled(self):
        config = HomeAssistantConfig(enabled=True)
        assert config.enabled is True

    def test_all_fields(self):
        config = HomeAssistantConfig(
            enabled=True,
            device_name_prefix="MyHome",
            discovery_prefix="ha",
            edit_percentage_with_box=True,
            entity_id_prefix="test_sigen",
            republish_discovery_interval=300,
            enabled_by_default=True,
            unique_id_prefix="test_unique",
            use_simplified_topics=True,
        )
        assert config.device_name_prefix == "MyHome"
        assert config.discovery_only is False
        assert config.discovery_prefix == "ha"
        assert config.edit_percentage_with_box is True
        assert config.entity_id_prefix == "test_sigen"
        assert config.republish_discovery_interval == 300
        assert config.enabled_by_default is True
        assert config.unique_id_prefix == "test_unique"
        assert config.use_simplified_topics is True

    def test_alias_keys(self):
        """Fields can also be set via their YAML alias names."""
        config = HomeAssistantConfig(
            **{
                "enabled": True,
                "device-name-prefix": "MyHome",
                "discovery-prefix": "ha",
                "edit-pct-box": True,
                "entity-id-prefix": "test_sigen",
                "republish-discovery-interval": 300,
                "sensors-enabled-by-default": True,
                "unique-id-prefix": "test_unique",
                "use-simplified-topics": True,
            }
        )
        assert config.device_name_prefix == "MyHome"
        assert config.discovery_prefix == "ha"
        assert config.edit_percentage_with_box is True
        assert config.entity_id_prefix == "test_sigen"
        assert config.republish_discovery_interval == 300
        assert config.enabled_by_default is True
        assert config.unique_id_prefix == "test_unique"
        assert config.use_simplified_topics is True

    def test_false_values(self):
        """Test that False values are properly set."""
        config = HomeAssistantConfig(
            enabled=True,
            edit_percentage_with_box=False,
            enabled_by_default=False,
            use_simplified_topics=False,
        )
        assert config.enabled is True
        assert config.discovery_only is False
        assert config.edit_percentage_with_box is False
        assert config.enabled_by_default is False
        assert config.use_simplified_topics is False


class TestMqttConfig:
    def test_default_values(self):
        config = MqttConfig()
        assert config.broker == "127.0.0.1"
        assert config.port == 1883
        assert config.tls is False

    def test_broker_port(self):
        config = MqttConfig(broker="192.168.1.100", port=1884)
        assert config.broker == "192.168.1.100"
        assert config.port == 1884

    def test_tls_changes_default_port(self):
        config = MqttConfig(tls=True)
        assert config.tls is True
        assert config.port == 8883

    def test_tls_with_explicit_port(self):
        config = MqttConfig(tls=True, port=1234)
        assert config.tls is True
        assert config.port == 1234

    def test_all_fields(self):
        config = MqttConfig(
            keepalive=120,
            anonymous=True,
            username="user",
            password="pass",
            log_level="DEBUG",
            tls_insecure=True,
        )
        assert config.keepalive == 120
        assert config.anonymous is True
        assert config.username == "user"
        assert config.password == "pass"
        assert config.log_level == logging.DEBUG
        assert config.tls_insecure is True

    def test_false_values(self):
        config = MqttConfig(tls=False, anonymous=True, tls_insecure=False)
        assert config.tls is False
        assert config.anonymous is True
        assert config.tls_insecure is False


class TestPvOutputConfig:
    def test_default_values(self):
        config = PvOutputConfig()
        assert config.enabled is False
        assert config.consumption is None
        assert config.voltage == VoltageSource.L_N_AVG

    def test_consumption_source_values(self):
        config = PvOutputConfig(consumption=ConsumptionSource.CONSUMPTION.value)
        assert config.consumption == ConsumptionSource.CONSUMPTION

        config = PvOutputConfig(consumption=ConsumptionSource.IMPORTED.value)
        assert config.consumption == ConsumptionSource.IMPORTED

        config = PvOutputConfig(consumption="net-of-battery")
        assert config.consumption == ConsumptionSource.NET_OF_BATTERY

    def test_basic_fields(self):
        config = PvOutputConfig(
            enabled=True,
            api_key="ABCDEF1234567890ABCDEF1234567890",
            system_id="12345",
            consumption="imported",
            exports=True,
            imports=True,
            output_hour=22,
            temperature_topic="home/temp",
            voltage="pv",
        )
        assert config.api_key == "ABCDEF1234567890ABCDEF1234567890"
        assert config.system_id == "12345"
        assert config.consumption == ConsumptionSource.IMPORTED
        assert config.exports is True
        assert config.imports is True
        assert config.output_hour == 22
        assert config.temperature_topic == "home/temp"
        assert config.voltage == VoltageSource.PV

    def test_testing_system_id(self):
        config = PvOutputConfig(enabled=True, api_key="1a2b3c", system_id="testing")
        assert config.testing is True

    def test_false_values(self):
        config = PvOutputConfig(
            enabled=True,
            api_key="ABCDEF1234567890ABCDEF1234567890",
            system_id="12345",
            exports=False,
            imports=False,
            calc_debug_logging=False,
            update_debug_logging=False,
        )
        assert config.enabled is True
        assert config.exports is False
        assert config.imports is False
        assert config.calc_debug_logging is False
        assert config.update_debug_logging is False

    def test_time_periods(self):
        period_dict = {"type": "peak", "start": "08:00", "end": "20:00", "days": ["Mon", "Tue"]}
        tariff_dict = {"plan": "My Plan", "default": "off-peak", "periods": [period_dict]}
        config = PvOutputConfig(
            enabled=True,
            api_key="1a2b3c",
            system_id="abc",
            **{"time-periods": [tariff_dict]},
        )
        assert len(config.tariffs) == 1
        tariff = config.tariffs[0]
        assert tariff.plan == "My Plan"
        assert tariff.default == TariffType.OFF_PEAK
        assert len(tariff.periods) == 1
        assert tariff.periods[0].type == TariffType.PEAK
        assert tariff.periods[0].start == time(8, 0)
        assert tariff.periods[0].end == time(20, 0)
        assert tariff.periods[0].days == ["Mon", "Tue"]


class TestSmartPortConfig:
    def test_default_values(self):
        config = SmartPortConfig()
        assert config.enabled is False
        assert isinstance(config.module, SmartPortModule)
        assert config.mqtt == []

    def test_module(self):
        config = SmartPortConfig(
            enabled=True,
            module=SmartPortModule(
                name="enphase",
                host="1.2.3.4",
                port=80,
                username="admin",
                password="password",
                pv_power="envoy/production/inverters",
            ),
        )
        assert config.enabled is True
        assert config.module.name == "enphase"
        assert config.module.host == "1.2.3.4"
        assert config.module.port == 80
        assert config.module.username == "admin"
        assert config.module.password == "password"
        assert config.module.pv_power == "envoy/production/inverters"

    def test_mqtt_topics(self):
        config = SmartPortConfig(
            enabled=True,
            module=SmartPortModule(name="enphase"),
            mqtt=[
                SmartPortMqttEntry(topic="topic/1", gain=1),
                SmartPortMqttEntry(topic="topic/2", gain=10),
            ],
        )
        assert len(config.mqtt) == 2
        assert config.mqtt[0].topic == "topic/1"
        assert config.mqtt[1].topic == "topic/2"

    def test_invalid_enabled_combination(self):
        with pytest.raises(ValidationError, match="no module name or MQTT topics configured"):
            SmartPortConfig(enabled=True)


class TestModbusConfig:
    def test_default_values(self):
        config = ModbusConfig(host="localhost")
        assert config.port == 502
        assert config.retries == 3
        assert config.timeout == 1.0

    def test_basic_fields(self):
        config = ModbusConfig(
            host="192.168.1.50",
            port=503,
            retries=5,
            timeout=2.0,
            disable_chunking=True,
            log_level="INFO",
        )
        assert config.host == "192.168.1.50"
        assert config.port == 503
        assert config.retries == 5
        assert config.timeout == 2.0
        assert config.disable_chunking is True
        assert config.log_level == logging.INFO

    def test_registers_and_intervals(self):
        config = ModbusConfig(
            host="localhost",
            **{
                "no-remote-ems": True,
                "read-only": False,
                "read-write": False,
                "write-only": False,
                "scan-interval-low": 1200,
                "scan-interval-medium": 120,
                "scan-interval-high": 20,
                "scan-interval-realtime": 2,
            },
        )
        assert config.registers.no_remote_ems is True
        assert config.registers.read_only is False
        assert config.registers.read_write is False
        assert config.registers.write_only is False
        assert config.scan_interval.low == 1200
        assert config.scan_interval.medium == 120
        assert config.scan_interval.high == 20
        assert config.scan_interval.realtime == 2

    def test_device_lists(self):
        config = ModbusConfig(host="localhost", inverters=[1, 2, 3], ac_chargers=[10], dc_chargers=[20, 21])
        assert config.inverters == [1, 2, 3]
        assert config.ac_chargers == [10]
        assert config.dc_chargers == [20, 21]

    def test_default_inverter(self):
        """Should default to [1] if no devices specified."""
        config = ModbusConfig(host="localhost")
        assert config.inverters == [1]

    def test_boolean_toggles(self):
        config = ModbusConfig(
            host="localhost",
            disable_chunking=True,
            **{
                "no-remote-ems": True,
                "read-only": True,
                "read-write": True,
                "write-only": True,
            },
        )
        assert config.disable_chunking is True
        assert config.registers.no_remote_ems is True
        assert config.registers.read_only is True
        assert config.registers.read_write is True
        assert config.registers.write_only is True
