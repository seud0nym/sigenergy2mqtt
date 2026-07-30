"""Tests for DiagnosticsConfig model."""

import asyncio
from unittest.mock import patch as mpatch

import pytest

from sigenergy2mqtt.config.models.diagnostics import DiagnosticsConfig


class TestDiagnosticsConfigDefaults:
    """Verify default field values are correct."""

    def test_default_values(self):
        config = DiagnosticsConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8502
        assert config.refresh_interval == 5.0

    def test_custom_host(self):
        config = DiagnosticsConfig(host="192.168.1.1")
        assert config.host == "192.168.1.1"

    def test_custom_port(self):
        config = DiagnosticsConfig(port=9000)
        assert config.port == 9000

    def test_custom_refresh_interval(self):
        config = DiagnosticsConfig(**{"refresh-interval": 10.0})
        assert config.refresh_interval == 10.0

    def test_alias_key_refresh_interval(self):
        """refresh-interval alias should be accepted."""
        config = DiagnosticsConfig(**{"refresh-interval": 2.5})
        assert config.refresh_interval == 2.5

    def test_snake_case_refresh_interval(self):
        """refresh_interval snake_case should also be accepted (populate_by_name=True)."""
        config = DiagnosticsConfig(refresh_interval=3.0)
        assert config.refresh_interval == 3.0


class TestDiagnosticsConfigValidation:
    """Verify validation constraints are enforced."""

    def test_port_minimum(self):
        """port must be >= 1."""
        with pytest.raises(Exception):
            DiagnosticsConfig(port=0)

    def test_port_maximum(self):
        """port must be <= 65535."""
        with pytest.raises(Exception):
            DiagnosticsConfig(port=65536)

    def test_port_minimum_valid(self):
        """port of 1 is valid."""
        config = DiagnosticsConfig(port=1)
        assert config.port == 1

    def test_port_maximum_valid(self):
        """port of 65535 is valid."""
        config = DiagnosticsConfig(port=65535)
        assert config.port == 65535

    def test_refresh_interval_zero_invalid(self):
        """refresh-interval must be > 0."""
        with pytest.raises(Exception):
            DiagnosticsConfig(**{"refresh-interval": 0.0})

    def test_refresh_interval_negative_invalid(self):
        """refresh-interval must be > 0 (negative is invalid)."""
        with pytest.raises(Exception):
            DiagnosticsConfig(**{"refresh-interval": -1.0})

    def test_refresh_interval_small_positive_valid(self):
        """A small positive float for refresh-interval is valid."""
        config = DiagnosticsConfig(**{"refresh-interval": 0.1})
        assert config.refresh_interval == pytest.approx(0.1)

    def test_host_empty_string_allowed(self):
        """An empty host string is accepted (no pattern restriction on host)."""
        config = DiagnosticsConfig(host="")
        assert config.host == ""


class TestDiagnosticsConfigEnvVars:
    """Verify that diagnostics can be configured via environment variables."""

    def test_env_host_override(self, monkeypatch, tmp_path):
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_DIAGNOSTICS_HOST", "192.168.1.1")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.diagnostics.host == "192.168.1.1"

    def test_env_port_override(self, monkeypatch, tmp_path):
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_DIAGNOSTICS_PORT", "9999")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.diagnostics.port == 9999

    def test_env_refresh_interval_override(self, monkeypatch, tmp_path):
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.setenv("SIGENERGY2MQTT_DIAGNOSTICS_REFRESH_INTERVAL", "15.0")
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.diagnostics.refresh_interval == pytest.approx(15.0)

    def test_defaults_when_no_env_vars_set(self, monkeypatch, tmp_path):
        """Without any env vars, diagnostics defaults should apply."""
        from sigenergy2mqtt.config import Config, _swap_active_config

        monkeypatch.delenv("SIGENERGY2MQTT_DIAGNOSTICS_HOST", raising=False)
        monkeypatch.delenv("SIGENERGY2MQTT_DIAGNOSTICS_PORT", raising=False)
        monkeypatch.delenv("SIGENERGY2MQTT_DIAGNOSTICS_REFRESH_INTERVAL", raising=False)
        with mpatch("sigenergy2mqtt.config.config.Config._perform_auto_discovery", return_value=None):
            with _swap_active_config(Config()) as cfg:
                cfg.persistent_state_path = tmp_path
                asyncio.run(cfg.reload())
                assert cfg.diagnostics.host == "127.0.0.1"
                assert cfg.diagnostics.port == 8502
                assert cfg.diagnostics.refresh_interval == pytest.approx(5.0)
