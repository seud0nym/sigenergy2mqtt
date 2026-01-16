import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import ConsumptionMethod
from sigenergy2mqtt.config import const
from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.config.pvoutput_config import ConsumptionSource, VoltageSource
from sigenergy2mqtt.modbus.types import ModbusDataType


class TestConfigEnvironmentOverrides:
    @pytest.fixture(autouse=True)
    def reset_config(self):
        # Reset Config state before each test
        Config.modbus = []
        Config.sensor_overrides = {}
        # Re-initialize default modbus config as reload() expects existing structure or creates new?
        # reload() resets 'overrides' dict but applies to Config.modbus (list).
        # We need to ensure Config.modbus has at least one item if we want to test overrides on it,
        # or rely on reload() creating it if empty?
        # reload() logic: "modbus": [{"smart-port": ...}] in default overrides.
        # But _configure appends if index >= len.
        Config.home_assistant = MagicMock()  # Mock to avoid validation errors if needed, or rely on real object?
        # Real object is safer for coverage.
        from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
        from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
        from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration

        Config.home_assistant = HomeAssistantConfiguration()
        Config.mqtt = MqttConfiguration()
        Config.pvoutput = PVOutputConfiguration()
        yield
        Config.modbus = []

    def test_all_env_overrides(self):
        env_vars = {
            const.SIGENERGY2MQTT_CONSUMPTION: "total",
            const.SIGENERGY2MQTT_LOG_LEVEL: "DEBUG",
            const.SIGENERGY2MQTT_DEBUG_SENSOR: "sensor.test_debug",
            const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW: "123.4",
            const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK: "true",
            const.SIGENERGY2MQTT_NO_METRICS: "true",
            # Home Assistant
            const.SIGENERGY2MQTT_HASS_ENABLED: "true",
            const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX: "true",
            const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX: "ha_prefix",
            const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX: "ha_dev_prefix",
            const.SIGENERGY2MQTT_HASS_DISCOVERY_ONLY: "true",
            const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX: "ha_disc_prefix",
            const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX: "ha_uid_prefix",
            const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS: "true",
            # Modbus (assuming index 0)
            const.SIGENERGY2MQTT_MODBUS_HOST: "192.168.1.100",
            const.SIGENERGY2MQTT_MODBUS_PORT: "5020",
            const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL: "INFO",
            const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID: "1,2",
            const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID: "3",
            const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID: "4",
            const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS: "true",
            const.SIGENERGY2MQTT_MODBUS_READ_ONLY: "true",
            const.SIGENERGY2MQTT_MODBUS_READ_WRITE: "true",
            const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY: "true",
            const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING: "true",
            const.SIGENERGY2MQTT_MODBUS_RETRIES: "5",
            const.SIGENERGY2MQTT_MODBUS_TIMEOUT: "2.5",
            const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW: "60",
            const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM: "30",
            const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH: "10",
            const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME: "1",
            # Smart Port
            const.SIGENERGY2MQTT_SMARTPORT_ENABLED: "true",
            const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME: "common",
            const.SIGENERGY2MQTT_SMARTPORT_HOST: "192.168.1.101",
            const.SIGENERGY2MQTT_SMARTPORT_USERNAME: "sp_user",
            const.SIGENERGY2MQTT_SMARTPORT_PASSWORD: "sp_pass",
            const.SIGENERGY2MQTT_SMARTPORT_PV_POWER: "sp_pv",
            const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC: "sp/topic",
            const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN: "100",
            # MQTT
            const.SIGENERGY2MQTT_MQTT_BROKER: "mqtt.broker",
            const.SIGENERGY2MQTT_MQTT_PORT: "1883",
            const.SIGENERGY2MQTT_MQTT_KEEPALIVE: "60",
            const.SIGENERGY2MQTT_MQTT_TLS: "true",
            const.SIGENERGY2MQTT_MQTT_TLS_INSECURE: "true",
            const.SIGENERGY2MQTT_MQTT_TRANSPORT: "websockets",
            const.SIGENERGY2MQTT_MQTT_ANONYMOUS: "true",
            const.SIGENERGY2MQTT_MQTT_LOG_LEVEL: "ERROR",
            const.SIGENERGY2MQTT_MQTT_USERNAME: "mqtt_user",
            const.SIGENERGY2MQTT_MQTT_PASSWORD: "mqtt_pass",
            # PVOutput
            const.SIGENERGY2MQTT_PVOUTPUT_ENABLED: "true",
            const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS: "true",
            const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS: "true",
            const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL: "DEBUG",
            const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR: "23",
            const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON: '[{"periods": [{"type": "peak", "start": "10:00", "end": "11:00"}]}]',
            const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING: "true",
            const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING: "true",
            const.SIGENERGY2MQTT_PVOUTPUT_API_KEY: "0123456789abcdef0123456789abcdef01234567",
            const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID: "12345",
            const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION: "imported",
            const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC: "temp/topic",
            const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE: "phase-a",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7: "v7_val",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8: "v8_val",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9: "v9_val",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10: "v10_val",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11: "v11_val",
            const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12: "v12_val",
        }

        with patch.dict(os.environ, env_vars), patch("importlib.import_module") as mock_import:
            # Mock the module returned
            mock_import.return_value = MagicMock()
            Config.reload()

        # Verify Core
        assert Config.consumption == ConsumptionMethod.TOTAL
        assert Config.log_level == logging.DEBUG
        # Config.sensor_debug_logging is NOT set by SIGENERGY2MQTT_DEBUG_SENSOR, only specific sensor override
        assert Config.sensor_debug_logging is False
        assert Config.sensor_overrides["sensor.test_debug"]["debug-logging"] is True
        assert Config.sanity_check_default_kw == 123.4
        assert Config.ems_mode_check is False  # no-ems-mode-check=true -> ems_mode_check=False
        assert Config.metrics_enabled is False  # no-metrics=true -> metrics_enabled=False

        # Verify Home Assistant
        assert Config.home_assistant.enabled is True
        assert Config.home_assistant.edit_percentage_with_box is True
        assert Config.home_assistant.entity_id_prefix == "ha_prefix"
        assert Config.home_assistant.device_name_prefix == "ha_dev_prefix"
        assert Config.home_assistant.discovery_only is True
        assert Config.home_assistant.discovery_prefix == "ha_disc_prefix"
        assert Config.home_assistant.unique_id_prefix == "ha_uid_prefix"
        assert Config.home_assistant.use_simplified_topics is True

        # Verify Modbus
        assert len(Config.modbus) >= 1
        mb = Config.modbus[0]
        assert mb.host == "192.168.1.100"
        assert mb.port == 5020
        assert mb.log_level == logging.INFO
        assert mb.inverters == [1, 2]
        assert mb.ac_chargers == [3]
        assert mb.dc_chargers == [4]
        assert mb.registers.no_remote_ems is True
        assert mb.registers.read_only is True
        assert mb.registers.read_write is True
        assert mb.registers.write_only is True
        assert mb.disable_chunking is True
        assert mb.retries == 5
        assert mb.timeout == 2.5
        assert mb.scan_interval.low == 60
        assert mb.scan_interval.medium == 30
        assert mb.scan_interval.high == 10
        assert mb.scan_interval.realtime == 1

        # Smart Port
        assert mb.smartport.enabled is True
        assert mb.smartport.module.name == "common"
        assert mb.smartport.module.host == "192.168.1.101"
        assert mb.smartport.module.username == "sp_user"
        assert mb.smartport.module.password == "sp_pass"
        assert mb.smartport.module.pv_power == "sp_pv"
        assert mb.smartport.mqtt[0].topic == "sp/topic"
        assert mb.smartport.mqtt[0].gain == 100

        # MQTT
        assert Config.mqtt.broker == "mqtt.broker"
        assert Config.mqtt.port == 1883
        assert Config.mqtt.keepalive == 60
        assert Config.mqtt.tls is True
        assert Config.mqtt.tls_insecure is True
        assert Config.mqtt.transport == "websockets"
        assert Config.mqtt.anonymous is True
        assert Config.mqtt.log_level == logging.ERROR
        assert Config.mqtt.username == "mqtt_user"
        assert Config.mqtt.password == "mqtt_pass"

        # PVOutput
        assert Config.pvoutput.enabled is True
        assert Config.pvoutput.exports is True
        assert Config.pvoutput.imports is True
        assert Config.pvoutput.log_level == logging.DEBUG
        assert Config.pvoutput.output_hour == 23
        assert len(Config.pvoutput.tariffs) == 1
        assert Config.pvoutput.calc_debug_logging is True
        assert Config.pvoutput.update_debug_logging is True
        assert Config.pvoutput.api_key == "0123456789abcdef0123456789abcdef01234567"
        assert Config.pvoutput.system_id == "12345"
        assert Config.pvoutput.consumption == ConsumptionSource.IMPORTED
        assert Config.pvoutput.temperature_topic == "temp/topic"
        assert Config.pvoutput.voltage == VoltageSource.PHASE_A
        assert Config.pvoutput.extended["v7"] == "v7_val"
        assert Config.pvoutput.extended["v8"] == "v8_val"
        assert Config.pvoutput.extended["v9"] == "v9_val"
        assert Config.pvoutput.extended["v10"] == "v10_val"
        assert Config.pvoutput.extended["v11"] == "v11_val"
        assert Config.pvoutput.extended["v12"] == "v12_val"

    def test_unknown_env_var(self):
        with patch.dict(os.environ, {"SIGENERGY2MQTT_UNKNOWN_THING": "value"}):
            with patch("logging.warning") as mock_warn:
                Config.reload()
                mock_warn.assert_called()
                args = mock_warn.call_args[0][0]
                assert "UNKNOWN env/cli override" in args
                assert "SIGENERGY2MQTT_UNKNOWN_THING" in args

    def test_invalid_env_var(self):
        with patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "INVALID_LEVEL"}):
            # check_log_level raises ValueError
            with pytest.raises(Exception) as excinfo:
                Config.reload()
            assert "when processing override" in str(excinfo.value)


class TestConfigSensorOverrides:
    @pytest.fixture(autouse=True)
    def reset_config(self):
        Config.modbus = []
        Config.sensor_overrides = {}
        from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
        from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
        from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration

        Config.home_assistant = HomeAssistantConfiguration()
        Config.mqtt = MqttConfiguration()
        Config.pvoutput = PVOutputConfiguration()
        yield
        Config.modbus = []
        Config.sensor_overrides = {}

    def test_sensor_overrides_yaml(self):
        data = {
            "sensor-overrides": {
                "sensor.test1": {
                    "debug-logging": True,
                    "gain": 10,
                    "icon": "mdi:flash",
                    "max-failures": 5,
                    "max-failures-retry-interval": 60,
                    "precision": 2,
                    "publishable": False,
                    "publish-raw": True,
                    "scan-interval": 30,
                    "sanity-check-max-value": 1000.0,
                    "sanity-check-min-value": -100.0,
                    "sanity-check-delta": True,
                    "unit-of-measurement": "kWh",
                },
            },
            "modbus": [{"host": "127.0.0.1"}],
        }
        Config._configure(data)

        assert "sensor.test1" in Config.sensor_overrides
        overrides = Config.sensor_overrides["sensor.test1"]
        assert overrides["debug-logging"] is True
        assert overrides["gain"] == 10
        assert overrides["icon"] == "mdi:flash"
        assert overrides["max-failures"] == 5
        assert overrides["max-failures-retry-interval"] == 60
        assert overrides["precision"] == 2
        assert overrides["publishable"] is False
        assert overrides["publish-raw"] is True
        assert overrides["scan-interval"] == 30
        assert overrides["sanity-check-max-value"] == 1000.0
        assert overrides["sanity-check-min-value"] == -100.0
        assert overrides["sanity-check-delta"] is True
        assert overrides["unit-of-measurement"] == "kWh"

    def test_invalid_sensor_override_key(self):
        data = {
            "sensor-overrides": {
                "sensor.test1": {"unknown-key": "value"},
            },
            "modbus": [{"host": "127.0.0.1"}],
        }
        with pytest.raises(ValueError) as excinfo:
            Config._configure(data)
        assert "not known or not overridable" in str(excinfo.value)

    def test_invalid_sensor_override_structure(self):
        data = {
            "sensor-overrides": "not-a-dict",
            "modbus": [{"host": "127.0.0.1"}],
        }
        with pytest.raises(ValueError) as excinfo:
            Config._configure(data)
        assert "must contain a list of class names" in str(excinfo.value)


class TestConfigAutoDiscovery:
    @pytest.fixture(autouse=True)
    def reset_config(self):
        Config.modbus = []
        Config.sensor_overrides = {}
        Config._source = None
        from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
        from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
        from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration

        Config.home_assistant = HomeAssistantConfiguration()
        Config.mqtt = MqttConfiguration()
        Config.pvoutput = PVOutputConfiguration()
        yield
        Config.modbus = []
        Config._source = None

    def test_auto_discovery_force(self):
        env_vars = {
            const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY: "force",
            const.SIGENERGY2MQTT_MODBUS_HOST: "192.168.1.1",
        }
        discovered = [{"host": "192.168.1.200", "port": 502, "inverters": [1]}]

        with (
            patch.dict(os.environ, env_vars, clear=False),
            patch("sigenergy2mqtt.config.config.auto_discovery_scan", return_value=discovered) as mock_scan,
            patch("builtins.open", MagicMock()),
            patch("sigenergy2mqtt.config.config.YAML") as mock_yaml,
        ):
            mock_yaml.return_value.load.return_value = None
            mock_yaml.return_value.dump = MagicMock()
            Config.reload()
            mock_scan.assert_called_once()

    def test_auto_discovery_cached(self, tmp_path):
        cache_file = tmp_path / "auto-discovery.yaml"
        cache_file.write_text("- host: 192.168.1.100\n  port: 502\n  inverters: [1]\n")

        env_vars = {
            const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY: "once",
            const.SIGENERGY2MQTT_MODBUS_HOST: "192.168.1.1",
        }
        Config.persistent_state_path = tmp_path

        with patch.dict(os.environ, env_vars, clear=False), patch("sigenergy2mqtt.config.config.auto_discovery_scan") as mock_scan:
            Config.reload()
            mock_scan.assert_not_called()
            assert len(Config.modbus) >= 1


class TestConfigFileLoading:
    @pytest.fixture(autouse=True)
    def reset_config(self):
        Config.modbus = []
        Config.sensor_overrides = {}
        Config._source = None
        from sigenergy2mqtt.config.home_assistant_config import HomeAssistantConfiguration
        from sigenergy2mqtt.config.mqtt_config import MqttConfiguration
        from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration

        Config.home_assistant = HomeAssistantConfiguration()
        Config.mqtt = MqttConfiguration()
        Config.pvoutput = PVOutputConfiguration()
        yield
        Config.modbus = []
        Config._source = None

    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("modbus:\n  - host: 192.168.1.50\n    port: 502\n")

        # Clear env vars that might override our config
        with patch.dict(os.environ, {}, clear=True):
            Config.load(str(config_file))

        assert Config._source == str(config_file)
        assert len(Config.modbus) >= 1
        assert Config.modbus[0].host == "192.168.1.50"

    def test_load_empty_file(self, tmp_path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with patch("logging.warning") as mock_warn:
            Config.load(str(config_file))
            mock_warn.assert_called()
            args = mock_warn.call_args[0][0]
            assert "contains no keys" in args
