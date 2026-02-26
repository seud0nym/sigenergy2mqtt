import logging
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sigenergy2mqtt.config import Config, _swap_active_config, const


class TestConfigEnvironmentOverrides:
    def test_all_env_overrides(self, monkeypatch):
        monkeypatch.setenv(const.SIGENERGY2MQTT_LOG_LEVEL, "DEBUG")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "10.0.0.1")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_BROKER, "mqtt.local")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_USERNAME, "user")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_PASSWORD, "pass")

        with _swap_active_config(Config()) as cfg:
            cfg.reload()
            assert cfg.log_level == logging.DEBUG
            assert len(cfg.modbus) >= 1
            assert cfg.modbus[0].host == "10.0.0.1"
            assert cfg.mqtt.broker == "mqtt.local"
            assert cfg.mqtt.username == "user"
            assert cfg.mqtt.password == "pass"

    def test_unknown_env_var(self, monkeypatch):
        monkeypatch.setenv("SIGENERGY2MQTT_UNKNOWN_VAR", "foo")
        # Should just ignore unknown SIGENERGY2MQTT vars without error
        with _swap_active_config(Config()) as cfg:
            cfg.reload()

    def test_invalid_env_var(self, monkeypatch):
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_PORT, "not-a-port")
        with _swap_active_config(Config()) as cfg:
            with pytest.raises(Exception):
                cfg.reload()


class TestConfigSensorOverrides:
    def test_sensor_overrides_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("sensor-overrides:\n  BatteryPower:\n    precision: 2\n    icon: mdi:battery\n")
        with _swap_active_config(Config()) as cfg:
            cfg.load(str(config_file))
            assert cfg.sensor_overrides["BatteryPower"]["precision"] == 2
            assert cfg.sensor_overrides["BatteryPower"]["icon"] == "mdi:battery"

    def test_invalid_sensor_override_key(self, tmp_path):
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("sensor-overrides:\n  BatteryPower:\n    unknown: foo\n")
        with _swap_active_config(Config()) as cfg:
            with pytest.raises(ValidationError, match="property is not known"):
                cfg.load(str(config_file))

    def test_invalid_sensor_override_structure(self, tmp_path):
        config_file = tmp_path / "invalid_struct.yaml"
        config_file.write_text("sensor-overrides: not-a-dict\n")
        with _swap_active_config(Config()) as cfg:
            with pytest.raises(ValidationError):
                cfg.load(str(config_file))


class TestConfigAutoDiscovery:
    def test_auto_discovery_force(self, tmp_path, monkeypatch):
        discovered = [{"host": "192.168.1.200", "port": 502, "inverters": [1]}]

        with patch("sigenergy2mqtt.config.config.auto_discovery_scan", return_value=discovered) as mock_scan:
            with _swap_active_config(Config()) as cfg:
                monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, "force")
                monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "192.168.1.1")
                cfg.persistent_state_path = tmp_path
                cfg.reload()
                mock_scan.assert_called_once()
                # It should have written to cache in tmp_path
                cache_file = tmp_path / "auto-discovery.yaml"
                assert cache_file.is_file()
                # Under Pydantic, the env override for modbus host morphs the 0th auto-discovered device!
                # So we expect 1 device, but the host overrides the discovered host.
                assert len(cfg.modbus) == 1
                assert cfg.modbus[0].host == "192.168.1.1"

    def test_auto_discovery_cached(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "auto-discovery.yaml"
        cache_file.write_text("- host: 192.168.1.100\n  port: 502\n  inverters: [1]\n")

        with patch("sigenergy2mqtt.config.config.auto_discovery_scan") as mock_scan:
            with _swap_active_config(Config()) as cfg:
                monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, "once")
                monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "192.168.1.1")
                cfg.persistent_state_path = tmp_path
                cfg.reload()
                mock_scan.assert_not_called()
                # Should load from cache and merge env. Env morphs host at idx 0.
                assert len(cfg.modbus) == 1
                assert cfg.modbus[0].host == "192.168.1.1"


class TestConfigFileLoading:
    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("modbus:\n  - host: 192.168.1.50\n    port: 502\n")

        # Clear SIGENERGY2MQTT_ vars that might override our config
        original_env = {k: v for k, v in os.environ.items() if k.startswith("SIGENERGY2MQTT_")}
        for k in original_env:
            del os.environ[k]

        try:
            with _swap_active_config(Config()) as cfg:
                cfg.load(str(config_file))
                assert cfg._source == str(config_file)
                assert len(cfg.modbus) >= 1
                assert cfg.modbus[0].host == "192.168.1.50"
        finally:
            os.environ.update(original_env)

    def test_load_empty_file(self, tmp_path, caplog):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        original_env = {k: v for k, v in os.environ.items() if k.startswith("SIGENERGY2MQTT_")}
        for k in original_env:
            del os.environ[k]
        try:
            with _swap_active_config(Config()) as cfg:
                with caplog.at_level(logging.WARNING):
                    from pydantic import ValidationError

                    with pytest.raises(ValidationError):
                        cfg.load(str(config_file))
        finally:
            os.environ.update(original_env)
