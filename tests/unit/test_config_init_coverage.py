import os
from unittest.mock import MagicMock, patch

import pytest

import sigenergy2mqtt.config as config_mod
from sigenergy2mqtt.config.const import SIGENERGY2MQTT_CONFIG


@pytest.fixture
def mock_active_config():
    from sigenergy2mqtt.config.config import Config, _swap_active_config

    mock = MagicMock(spec=Config)
    with _swap_active_config(mock):
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
        # Mock vars(args) for _promote_cli_to_env
        mock.return_value = args
        yield mock


@pytest.fixture
def mock_system_init():
    with patch("sigenergy2mqtt.config.active_config.system_initialize") as mock:
        mock.return_value = "/mock/path"
        yield mock


@pytest.fixture
def mock_promote_cli_to_env():
    with patch("sigenergy2mqtt.config._promote_cli_to_env") as mock:
        yield mock


def test_initialize_env_config_exists(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test loading from SIGENERGY2MQTT_CONFIG environment variable."""
    with patch.dict(os.environ, {SIGENERGY2MQTT_CONFIG: "/path/to/config.yaml"}), patch("os.path.isfile", side_effect=lambda x: x == "/path/to/config.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/path/to/config.yaml")


def test_initialize_env_config_not_found(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test handling of missing file specified in SIGENERGY2MQTT_CONFIG."""
    with patch.dict(os.environ, {SIGENERGY2MQTT_CONFIG: "/nonexistent/config.yaml"}), patch("os.path.isfile", return_value=False):
        from sigenergy2mqtt.config import ConfigurationError

        with pytest.raises(ConfigurationError, match="Specified config file"):
            config_mod.initialize()


def test_initialize_fallback_etc(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test fallback to /etc/sigenergy2mqtt.yaml."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", side_effect=lambda x: x == "/etc/sigenergy2mqtt.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/etc/sigenergy2mqtt.yaml")


def test_initialize_fallback_data(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test fallback to /data/sigenergy2mqtt.yaml."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", side_effect=lambda x: x == "/data/sigenergy2mqtt.yaml"):
        config_mod.initialize()
        mock_active_config.load.assert_called_once_with("/data/sigenergy2mqtt.yaml")


def test_initialize_default_reload(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test defaulting to active_config.reload() when no config files are found."""
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", return_value=False):
        config_mod.initialize()
        mock_active_config.reload.assert_called_once()
        mock_active_config.load.assert_not_called()


def test_initialize_exception_handling(mock_active_config, mock_cli_parse, mock_system_init, mock_promote_cli_to_env):
    """Test general exception handling (ConfigurationError)."""
    mock_active_config.reload.side_effect = Exception("Reload failed")
    with patch.dict(os.environ, {}, clear=True), patch("os.path.isfile", return_value=False):
        from sigenergy2mqtt.config import ConfigurationError

        with pytest.raises(ConfigurationError, match="Error processing configuration: Reload failed"):
            config_mod.initialize()
