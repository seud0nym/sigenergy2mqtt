import collections
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ruamel.yaml import YAML

from sigenergy2mqtt.config import active_config, const

VersionInfo = collections.namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])


def test_system_initialize_missing_branches_3(tmp_path):
    from sigenergy2mqtt.config import ConfigurationError

    with patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 11, 0, "f", 0)):
        with pytest.raises(ConfigurationError):
            active_config.system_initialize()
    with patch("sigenergy2mqtt.config.config.os.path.isdir", return_value=False):
        with pytest.raises(ConfigurationError):
            active_config.system_initialize()


def test_stale_cleanup_full_v6(tmp_path):
    stale = tmp_path / "stale"
    stale.touch()
    os.utime(stale, (0, 0))
    # mocks for path
    mock_path = MagicMock(spec=Path)
    mock_path.is_dir.return_value = True
    mock_path.resolve.return_value = tmp_path
    mock_path.iterdir.return_value = [stale]
    mock_path.__truediv__.return_value = mock_path

    with (
        patch("sigenergy2mqtt.config.config.os.path.isdir", return_value=True),
        patch("sigenergy2mqtt.config.config.os.access", return_value=True),
        patch("sigenergy2mqtt.config.config.Path", return_value=mock_path),
        patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 13, 0, "f", 0)),
    ):
        active_config.system_initialize()


def test_logging_branches_exhaustive_v3():
    with patch("sigenergy2mqtt.config.config.os.isatty", return_value=True), patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 13, 0, "f", 0)):
        try:
            active_config.system_initialize()
        except:
            pass

    mock_p = MagicMock()
    mock_p.is_file.return_value = True
    mock_p.read_text.return_value = "docker"
    with (
        patch("sigenergy2mqtt.config.config.os.isatty", return_value=False),
        patch("sigenergy2mqtt.config.config.Path", return_value=mock_p),
        patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 13, 0, "f", 0)),
    ):
        try:
            active_config.system_initialize()
        except:
            pass

    mock_p2 = MagicMock()
    mock_p2.is_file.return_value = False
    with (
        patch("sigenergy2mqtt.config.config.os.isatty", return_value=False),
        patch("sigenergy2mqtt.config.config.Path", return_value=mock_p2),
        patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 13, 0, "f", 0)),
    ):
        try:
            active_config.system_initialize()
        except:
            pass


def test_reload_exhaustive_v7(tmp_path):
    conf_file = tmp_path / "c.yaml"
    conf_file.write_text("log-level: debug")
    active_config.load(str(conf_file))
    empty_file = tmp_path / "e.yaml"
    empty_file.write_text("")
    with patch.object(active_config, "_source", str(empty_file)):
        active_config.reload()
    cache = tmp_path / "auto-discovery.yaml"
    YAML().dump([], cache)
    with patch.object(active_config, "persistent_state_path", tmp_path), patch.dict(os.environ, {const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY: "once"}):
        active_config.reload()
    with patch.dict(os.environ, {const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY: "force"}):
        with patch("sigenergy2mqtt.config.config.auto_discovery_scan", return_value=[{"host": "h"}]):
            active_config.reload()


# ---------------------------------------------------------------------------
# Tests for sigenergy2mqtt/config/__init__.py  (uncovered lines)
# ---------------------------------------------------------------------------

from types import SimpleNamespace

from sigenergy2mqtt.config import (
    ConfigurationError,
    _promote_cli_to_env,
    initialize,
)


def test_promote_cli_to_env_read_only_branch():
    """Cover lines 77-80: read_only flag sets three env vars atomically."""
    args = SimpleNamespace(
        clean=False,
        discovery_only=False,
        validate_only=False,
        show_version=False,
        **{const.SIGENERGY2MQTT_MODBUS_READ_ONLY: True},
    )
    with patch.dict(os.environ, {}, clear=True):
        _promote_cli_to_env(args)
        assert os.environ[const.SIGENERGY2MQTT_MODBUS_READ_ONLY] == "true"
        assert os.environ[const.SIGENERGY2MQTT_MODBUS_READ_WRITE] == "false"
        assert os.environ[const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY] == "false"


def test_initialize_show_version_returns_false():
    """Cover line 154: show_version causes early return False."""
    fake_args = SimpleNamespace(show_version=True)
    with (
        patch("sigenergy2mqtt.config.active_config.system_initialize", return_value="/tmp"),
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
    ):
        result = initialize(["--version"])
        assert result is False


def test_initialize_log_level_from_env():
    """Cover lines 162-167: log level read from env and applied."""
    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=False,
    )
    with (
        patch("sigenergy2mqtt.config.active_config.system_initialize", return_value="/tmp"),
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        patch("sigenergy2mqtt.config._promote_cli_to_env"),
        patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "DEBUG"}),
        patch("sigenergy2mqtt.config._load_config"),
    ):
        result = initialize()
        assert result is True
        assert active_config.log_level == logging.DEBUG


def test_initialize_log_level_invalid_raises():
    """Cover lines 163-164: unknown log level raises ConfigurationError."""
    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=False,
    )
    with (
        patch("sigenergy2mqtt.config.active_config.system_initialize", return_value="/tmp"),
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        patch("sigenergy2mqtt.config._promote_cli_to_env"),
        patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "BOGUS_LEVEL"}),
    ):
        with pytest.raises(ConfigurationError, match="Unknown log level"):
            initialize()


def test_initialize_validate_only_returns_false():
    """Cover lines 182-183: validate_only returns False."""
    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=True,
    )
    with (
        patch("sigenergy2mqtt.config.active_config.system_initialize", return_value="/tmp"),
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        patch("sigenergy2mqtt.config._promote_cli_to_env"),
        patch.dict(os.environ, {}, clear=True),
        patch("sigenergy2mqtt.config._load_config"),
    ):
        result = initialize()
        assert result is False
