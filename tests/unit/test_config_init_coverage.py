import os
from unittest.mock import MagicMock, patch

import pytest

import sigenergy2mqtt.config as config_mod
from sigenergy2mqtt.config.const import SIGENERGY2MQTT_CONFIG


@pytest.fixture
def mock_active_config():
    with patch("sigenergy2mqtt.config.active_config") as mock:
        yield mock


@pytest.fixture
def mock_cli_parse():
    with patch("sigenergy2mqtt.config.cli.parse_args") as mock:
        # Create a mock that looks more like what the real parser returns
        args = MagicMock()
        args.show_version = False
        args.clean = False
        args.validate_only = False
        args.discovery_only = False
        # Mock vars(args) for _apply_cli_overrides
        mock.return_value = args
        yield mock


@pytest.fixture
def mock_system_init():
    with patch("sigenergy2mqtt.config._Config.system_initialize") as mock:
        mock.return_value = "/mock/path"
        yield mock


@pytest.fixture
def mock_apply_cli_overrides():
    with patch("sigenergy2mqtt.config._apply_cli_overrides") as mock:
        yield mock


def test_initialize_env_config_exists(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test loading from SIGENERGY2MQTT_CONFIG environment variable."""
    with patch.dict(os.environ, {SIGENERGY2MQTT_CONFIG: "/path/to/config.yaml"}), patch("os.path.isfile", side_effect=lambda x: x == "/path/to/config.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/path/to/config.yaml")


def test_initialize_env_config_not_found(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test handling of missing file specified in SIGENERGY2MQTT_CONFIG."""
    with patch.dict(os.environ, {SIGENERGY2MQTT_CONFIG: "/nonexistent/config.yaml"}), patch("os.path.isfile", return_value=False), patch("sys.exit") as mock_exit, patch("logging.critical") as mock_log:
        config_mod.initialize()
        mock_log.assert_called()
        assert "Specified config file" in mock_log.call_args[0][0]
        mock_exit.assert_called_once_with(1)


def test_initialize_fallback_etc(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test fallback to /etc/sigenergy2mqtt.yaml."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", side_effect=lambda x: x == "/etc/sigenergy2mqtt.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/etc/sigenergy2mqtt.yaml")


def test_initialize_fallback_data(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test fallback to /data/sigenergy2mqtt.yaml."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", side_effect=lambda x: x == "/data/sigenergy2mqtt.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/data/sigenergy2mqtt.yaml")


def test_initialize_default_reload(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test defaulting to active_config.reload() when no config files are found."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", return_value=False):
        config_mod.initialize()
        mock_active_config.reload.assert_called_once()
        mock_active_config.load.assert_not_called()


def test_initialize_exception_handling(mock_active_config, mock_cli_parse, mock_system_init, mock_apply_cli_overrides):
    """Test general exception handling (logging and sys.exit(1))."""
    mock_active_config.reload.side_effect = Exception("Reload failed")
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", return_value=False), patch("sys.exit") as mock_exit, patch("logging.critical") as mock_log:
        config_mod.initialize()
        mock_log.assert_called()
        assert "Error processing configuration: Reload failed" in mock_log.call_args[0][0]
        mock_exit.assert_called_once_with(1)
