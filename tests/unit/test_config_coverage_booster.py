import logging
import os
from unittest.mock import patch

import pytest

from sigenergy2mqtt.config import Config, const
from sigenergy2mqtt.config.config import active_config


class TestConfigEnvironmentOverrides:
    @pytest.fixture(autouse=True)
    def reset_config_state(self):
        active_config.reset()
        active_config.reload()
        yield
        active_config.reset()
        active_config.reload()

    def test_all_env_overrides(self, monkeypatch):
        monkeypatch.setenv(const.SIGENERGY2MQTT_LOG_LEVEL, "DEBUG")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "10.0.0.1")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_BROKER, "mqtt.local")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_USERNAME, "user")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MQTT_PASSWORD, "pass")

        active_config.reload()
        assert active_config.log_level == logging.DEBUG
        assert len(active_config.modbus) >= 1
        assert active_config.modbus[0].host == "10.0.0.1"
        assert active_config.mqtt.broker == "mqtt.local"
        assert active_config.mqtt.username == "user"
        assert active_config.mqtt.password == "pass"

    def test_unknown_env_var(self, monkeypatch):
        monkeypatch.setenv("SIGENERGY2MQTT_UNKNOWN_VAR", "foo")
        # Should just ignore unknown SIGENERGY2MQTT vars without error
        active_config.reload()

    def test_invalid_env_var(self, monkeypatch):
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_PORT, "not-a-port")
        with pytest.raises(Exception):
            active_config.reload()


class TestConfigSensorOverrides:
    @pytest.fixture(autouse=True)
    def reset_config_state(self):
        active_config.reset()
        active_config.reload()
        yield
        active_config.reset()
        active_config.reload()

    def test_sensor_overrides_yaml(self, tmp_path):
        data = {"sensor-overrides": {"BatteryPower": {"precision": 2, "icon": "mdi:battery"}}}
        active_config._configure(data)
        assert active_config.sensor_overrides["BatteryPower"]["precision"] == 2
        assert active_config.sensor_overrides["BatteryPower"]["icon"] == "mdi:battery"

    def test_invalid_sensor_override_key(self):
        data = {"sensor-overrides": {"BatteryPower": {"unknown": "foo"}}}
        with pytest.raises(ValueError, match="property is not known"):
            active_config._configure(data)

    def test_invalid_sensor_override_structure(self):
        data = {"sensor-overrides": "not-a-dict"}
        with pytest.raises(ValueError, match="must contain a list of class names"):
            active_config._configure(data)


class TestConfigAutoDiscovery:
    @pytest.fixture(autouse=True)
    def reset_config_state(self):
        active_config.reset()
        active_config.reload()
        yield
        active_config.reset()
        active_config.reload()

    def test_auto_discovery_force(self, tmp_path, monkeypatch):
        discovered = [{"host": "192.168.1.200", "port": 502, "inverters": [1]}]

        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, "force")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "192.168.1.1")

        original_modbus = list(active_config.modbus)
        original_psp = active_config.persistent_state_path
        try:
            with patch("sigenergy2mqtt.config.config.auto_discovery_scan", return_value=discovered) as mock_scan:
                active_config.modbus.clear()
                active_config.persistent_state_path = tmp_path
                Config.reload()
                mock_scan.assert_called_once()
                # It should have written to cache in tmp_path
                cache_file = tmp_path / "auto-discovery.yaml"
                assert cache_file.is_file()
                # And it should have populated Config.
                # Host 192.168.1.1 comes from env override.
                # Host 192.168.1.200 comes from auto-discovery scan.
                assert len(active_config.modbus) >= 2
                hosts = [d.host for d in active_config.modbus]
                assert "192.168.1.1" in hosts
                assert "192.168.1.200" in hosts
        finally:
            active_config.modbus.clear()
            active_config.modbus.extend(original_modbus)
            active_config.persistent_state_path = original_psp

    def test_auto_discovery_cached(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "auto-discovery.yaml"
        cache_file.write_text("- host: 192.168.1.100\n  port: 502\n  inverters: [1]\n")

        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, "once")
        monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "192.168.1.1")

        original_modbus = list(active_config.modbus)
        original_psp = active_config.persistent_state_path
        try:
            with patch("sigenergy2mqtt.config.config.auto_discovery_scan") as mock_scan:
                active_config.modbus.clear()
                active_config.persistent_state_path = tmp_path
                Config.reload()
                mock_scan.assert_not_called()
                # Should load from cache and merge/append with env.
                # Host 192.168.1.1 from env, 192.168.1.100 from cache.
                assert len(active_config.modbus) >= 2
                hosts = [d.host for d in active_config.modbus]
                assert "192.168.1.1" in hosts
                assert "192.168.1.100" in hosts
        finally:
            active_config.modbus = original_modbus
            active_config.persistent_state_path = original_psp


class TestConfigFileLoading:
    @pytest.fixture(autouse=True)
    def reset_config_state(self):
        Config.reset()
        Config.reload()
        yield
        Config.reset()
        Config.reload()

    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("modbus:\n  - host: 192.168.1.50\n    port: 502\n")

        # Clear env vars that might override our config
        original_source = active_config._source
        try:
            with patch.dict(os.environ, {}, clear=True):
                active_config.load(str(config_file))

            assert active_config._source == str(config_file)
            assert len(active_config.modbus) >= 1
            assert active_config.modbus[0].host == "192.168.1.50"
        finally:
            active_config._source = original_source

    def test_load_empty_file(self, tmp_path, caplog):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        original_source = active_config._source
        try:
            with caplog.at_level(logging.WARNING):
                active_config.load(str(config_file))
                assert "contains no keys" in caplog.text
        finally:
            active_config._source = original_source
