"""Tests for HealthCheckConfig and is_docker() helper."""

import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from sigenergy2mqtt.config.models.health_check import HealthCheckConfig
from sigenergy2mqtt.config.config import is_docker


class TestHealthCheckConfigDefaults:
    def test_default_values(self):
        config = HealthCheckConfig()
        assert config.enabled is True
        assert config.interval == 30
        assert config.timeout == 5
        assert config.start_period == 45
        assert config.retries == 3

    def test_enabled_false(self):
        config = HealthCheckConfig(enabled=False)
        assert config.enabled is False

    def test_custom_values(self):
        config = HealthCheckConfig(
            enabled=False,
            interval=60,
            timeout=10,
            retries=5,
            **{"start-period": 90},
        )
        assert config.enabled is False
        assert config.interval == 60
        assert config.timeout == 10
        assert config.start_period == 90
        assert config.retries == 5

    def test_alias_key_start_period(self):
        """start-period alias should be accepted."""
        config = HealthCheckConfig(**{"start-period": 120})
        assert config.start_period == 120

    def test_interval_minimum(self):
        """interval must be >= 1."""
        with pytest.raises(Exception):
            HealthCheckConfig(interval=0)

    def test_timeout_minimum(self):
        """timeout must be >= 1."""
        with pytest.raises(Exception):
            HealthCheckConfig(timeout=0)

    def test_start_period_zero_allowed(self):
        """start-period of 0 is valid."""
        config = HealthCheckConfig(**{"start-period": 0})
        assert config.start_period == 0

    def test_retries_minimum(self):
        """retries must be >= 1."""
        with pytest.raises(Exception):
            HealthCheckConfig(retries=0)


class TestIsDocker:
    def test_is_docker_via_dockerenv(self, tmp_path, monkeypatch):
        """Returns True if /.dockerenv file exists."""
        fake_dockerenv = tmp_path / ".dockerenv"
        fake_dockerenv.touch()
        with patch("sigenergy2mqtt.config.config.Path") as mock_path_cls:
            def path_factory(p):
                if p == "/.dockerenv":
                    m = MagicMock()
                    m.is_file.return_value = True
                    return m
                # fallback to a real-looking mock that says no docker in cgroup
                m2 = MagicMock()
                m2.is_file.return_value = False
                m2.read_text.return_value = ""
                return m2
            mock_path_cls.side_effect = path_factory
            assert is_docker() is True

    def test_is_docker_via_cgroup(self, monkeypatch):
        """Returns True if /proc/self/cgroup contains 'docker'."""
        with patch("sigenergy2mqtt.config.config.Path") as mock_path_cls:
            def path_factory(p):
                if p == "/.dockerenv":
                    m = MagicMock()
                    m.is_file.return_value = False
                    return m
                # cgroup
                m2 = MagicMock()
                m2.is_file.return_value = True
                m2.read_text.return_value = "12:devices:/docker/abc123"
                return m2
            mock_path_cls.side_effect = path_factory
            assert is_docker() is True

    def test_not_docker(self, monkeypatch):
        """Returns False if neither dockerenv nor cgroup hints are present."""
        with patch("sigenergy2mqtt.config.config.Path") as mock_path_cls:
            def path_factory(p):
                if p == "/.dockerenv":
                    m = MagicMock()
                    m.is_file.return_value = False
                    return m
                m2 = MagicMock()
                m2.is_file.return_value = True
                m2.read_text.return_value = "12:devices:/system.slice/app.service"
                return m2
            mock_path_cls.side_effect = path_factory
            assert is_docker() is False


class TestHealthCheckConfigEnvVars:
    """Verify that health-check can be configured via environment variables through the reload path."""

    def test_env_enabled_false(self, monkeypatch, tmp_path):
        from unittest.mock import patch as mpatch
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_HEALTH_CHECK_ENABLED", "false")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.health_check.enabled is False

    def test_env_interval_override(self, monkeypatch, tmp_path):
        from unittest.mock import patch as mpatch
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_HEALTH_CHECK_INTERVAL", "60")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.health_check.interval == 60

    def test_env_timeout_override(self, monkeypatch, tmp_path):
        from unittest.mock import patch as mpatch
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_HEALTH_CHECK_TIMEOUT", "10")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.health_check.timeout == 10

    def test_env_start_period_override(self, monkeypatch, tmp_path):
        from unittest.mock import patch as mpatch
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_HEALTH_CHECK_START_PERIOD", "90")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.health_check.start_period == 90

    def test_env_retries_override(self, monkeypatch, tmp_path):
        from unittest.mock import patch as mpatch
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_HEALTH_CHECK_RETRIES", "5")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.health_check.retries == 5
