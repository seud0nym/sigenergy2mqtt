import pytest
from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration, ConsumptionSource, VoltageSource, TariffType, OutputField
from datetime import time
import logging
from sigenergy2mqtt.config.smart_port_config import SmartPortConfig, ModuleConfig, TopicConfig  # noqa: F401
from sigenergy2mqtt.config.modbus_config import DeviceConfig


class TestHomeAssistantConfiguration:
    def test_default_values(self):
        config = HomeAssistantConfiguration()
        assert config.enabled is False
        assert config.discovery_prefix == "homeassistant"
        assert config.entity_id_prefix == "sigen"
        assert config.unique_id_prefix == "sigen"

    def test_configure_enabled(self):
        config = HomeAssistantConfiguration()
        config.configure({"enabled": True})
        assert config.enabled is True

    def test_configure_all_fields(self):
        config = HomeAssistantConfiguration()
        config.configure(
            {
                "enabled": True,
                "device-name-prefix": "MyHome",
                "discovery-only": True,
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
        assert config.discovery_only is True
        assert config.discovery_prefix == "ha"
        assert config.edit_percentage_with_box is True
        assert config.entity_id_prefix == "test_sigen"
        assert config.republish_discovery_interval == 300
        assert config.enabled_by_default is True
        assert config.unique_id_prefix == "test_unique"
        assert config.use_simplified_topics is True

    def test_configure_unknown_option(self):
        config = HomeAssistantConfiguration()
        with pytest.raises(ValueError, match="unknown option 'unknown'"):
            config.configure({"enabled": True, "unknown": "value"})

    def test_configure_not_dict(self):
        config = HomeAssistantConfiguration()
        with pytest.raises(ValueError, match="must contain options and their values"):
            config.configure("not a dict")


class TestMqttConfiguration:
    def test_default_values(self):
        config = MqttConfiguration()
        assert config.broker == "127.0.0.1"
        assert config.port == 1883
        assert config.tls is False

    def test_configure_broker_port(self):
        config = MqttConfiguration()
        config.configure({"broker": "192.168.1.100", "port": 1884})
        assert config.broker == "192.168.1.100"
        assert config.port == 1884

    def test_configure_tls_changes_default_port(self):
        config = MqttConfiguration()
        config.configure({"tls": True})
        assert config.tls is True
        assert config.port == 8883

    def test_configure_tls_with_explicit_port(self):
        config = MqttConfiguration()
        config.configure({"tls": True, "port": 1234})
        assert config.tls is True
        assert config.port == 1234

    def test_configure_all_fields(self):
        config = MqttConfiguration()
        config.configure({"keepalive": 120, "anonymous": True, "username": "user", "password": "pass", "log-level": "DEBUG", "tls-insecure": True})
        assert config.keepalive == 120
        assert config.anonymous is True
        assert config.username == "user"
        assert config.password == "pass"
        assert config.log_level == logging.DEBUG
        assert config.tls_insecure is True


class TestPVOutputConfiguration:
    def test_default_values(self):
        config = PVOutputConfiguration()
        assert config.enabled is False
        assert config.consumption is None
        assert config.voltage == VoltageSource.L_N_AVG

    def test_consumption_enabled_property(self):
        config = PVOutputConfiguration()
        assert config.consumption_enabled is False

        config.consumption = ConsumptionSource.CONSUMPTION
        assert config.consumption_enabled is True

        config.consumption = ConsumptionSource.IMPORTED
        assert config.consumption_enabled is True

        config.consumption = ConsumptionSource.NET_OF_BATTERY
        assert config.consumption_enabled is True

        config.consumption = "invalid"
        assert config.consumption_enabled is False

    def test_configure_basic_fields(self):
        config = PVOutputConfiguration()
        config.configure(
            {
                "enabled": True,
                "api-key": "ABCDEF1234567890ABCDEF1234567890",
                "system-id": "12345",
                "consumption": "imported",
                "exports": True,
                "imports": True,
                "output-hour": 22,
                "temperature-topic": "home/temp",
                "voltage": "pv",
            }
        )
        assert config.api_key == "ABCDEF1234567890ABCDEF1234567890"
        assert config.system_id == "12345"
        assert config.consumption == ConsumptionSource.IMPORTED
        assert config.exports is True
        assert config.imports is True
        assert config.output_hour == 22
        assert config.temperature_topic == "home/temp"
        assert config.voltage == VoltageSource.PV

    def test_configure_testing_system_id(self):
        config = PVOutputConfiguration()
        config.configure({"enabled": True, "system-id": "testing"})
        assert config.testing is True

    def test_type_to_output_fields(self):
        config = PVOutputConfiguration()

        e, i = config._type_to_output_fields(TariffType.OFF_PEAK)
        assert e == OutputField.EXPORT_OFF_PEAK
        assert i == OutputField.IMPORT_OFF_PEAK

        e, i = config._type_to_output_fields(TariffType.PEAK)
        assert e == OutputField.EXPORT_PEAK
        assert i == OutputField.IMPORT_PEAK

    def test_configure_time_periods(self):
        config = PVOutputConfiguration()
        config.configure({"enabled": True, "time-periods": [{"plan": "My Plan", "default": "off-peak", "periods": [{"type": "peak", "start": "08:00", "end": "20:00", "days": ["Mon", "Tue"]}]}]})
        assert len(config.tariffs) == 1
        tariff = config.tariffs[0]
        assert tariff.plan == "My Plan"
        assert tariff.default == "off-peak"
        assert len(tariff.periods) == 1
        assert tariff.periods[0].type == "peak"
        assert tariff.periods[0].start == time(8, 0)
        assert tariff.periods[0].end == time(20, 0)
        assert tariff.periods[0].days == ["Mon", "Tue"]

    def test_current_time_period(self):
        config = PVOutputConfiguration()
        # Mocking datetime.now is hard, but we can test the logic by providing tariffs
        # and letting it match against actual current time, or just verify it handles empty tariffs
        e, i = config.current_time_period
        assert e is None
        assert i == OutputField.IMPORT_PEAK


class TestSmartPortConfiguration:
    def test_default_values(self):
        config = SmartPortConfig()
        assert config.enabled is False
        assert isinstance(config.module, ModuleConfig)
        assert config.mqtt == []

    def test_configure_module(self):
        config = SmartPortConfig()
        config.configure({"enabled": True, "module": {"name": "enphase", "host": "1.2.3.4", "port": 80, "username": "admin", "password": "password", "pv-power": "envoy/production/inverters"}})
        assert config.enabled is True
        assert config.module.name == "enphase"
        assert config.module.host == "1.2.3.4"
        assert config.module.port == 80
        assert config.module.username == "admin"
        assert config.module.password == "password"
        assert config.module.pv_power == "envoy/production/inverters"

    def test_configure_mqtt_topics(self):
        config = SmartPortConfig()
        # This test will likely expose the bug where it only returns the first topic
        config.configure({"enabled": True, "module": {"name": "enphase"}, "mqtt": [{"topic": "topic/1", "gain": 1}, {"topic": "topic/2", "gain": 10}]})
        assert len(config.mqtt) == 2
        assert config.mqtt[0].topic == "topic/1"
        assert config.mqtt[1].topic == "topic/2"

    def test_configure_invalid_enabled_combination(self):
        config = SmartPortConfig()
        with pytest.raises(ValueError, match="no module name or MQTT topics configured"):
            config.configure({"enabled": True})


class TestDeviceConfig:
    def test_default_values(self):
        config = DeviceConfig()
        assert config.host == ""
        assert config.port == 502
        assert config.retries == 3
        assert config.timeout == 1.0

    def test_configure_basic_fields(self):
        config = DeviceConfig()
        config.configure({"host": "192.168.1.50", "port": 503, "retries": 5, "timeout": 2.0, "disable-chunking": True, "log-level": "INFO"})
        assert config.host == "192.168.1.50"
        assert config.port == 503
        assert config.retries == 5
        assert config.timeout == 2.0
        assert config.disable_chunking is True
        assert config.log_level == logging.INFO

    def test_configure_registers_and_intervals(self):
        config = DeviceConfig()
        config.configure(
            {"no-remote-ems": True, "read-only": False, "read-write": False, "write-only": False, "scan-interval-low": 1200, "scan-interval-medium": 120, "scan-interval-high": 20, "scan-interval-realtime": 2}
        )
        assert config.registers.no_remote_ems is True
        assert config.registers.read_only is False
        assert config.registers.read_write is False
        assert config.registers.write_only is False
        assert config.scan_interval.low == 1200
        assert config.scan_interval.medium == 120
        assert config.scan_interval.high == 20
        assert config.scan_interval.realtime == 2

    def test_configure_device_lists(self):
        config = DeviceConfig()
        config.configure({"inverters": [1, 2, 3], "ac-chargers": [10], "dc-chargers": [20, 21]})
        assert config.inverters == [1, 2, 3]
        assert config.ac_chargers == [10]
        assert config.dc_chargers == [20, 21]

    def test_configure_default_inverter(self):
        config = DeviceConfig()
        config.configure({"host": "localhost"})
        # Should default to [1] if empty
        assert config.inverters == [1]
