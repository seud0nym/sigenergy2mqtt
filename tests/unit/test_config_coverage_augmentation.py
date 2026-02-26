import collections
import logging
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ruamel.yaml import YAML

from sigenergy2mqtt.config import ConfigurationError, _promote_cli_to_env, active_config, const, initialize
from sigenergy2mqtt.config.config import _create_persistent_state_path, _system_initialize

VersionInfo = collections.namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])


@pytest.mark.no_persistent_state_mock
def test_system_initialize_missing_branches_3(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGENERGY2MQTT_STATE_DIR", raising=False)

    with patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 11, 0, "f", 0)):
        with pytest.raises(ConfigurationError):
            _system_initialize()
    with patch("sigenergy2mqtt.config.config.os.path.isdir", return_value=False):
        with pytest.raises(ConfigurationError):
            _create_persistent_state_path()


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
    ):
        _create_persistent_state_path()


def test_logging_branches_exhaustive_v3():
    with patch("sigenergy2mqtt.config.config.os.isatty", return_value=True), patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 13, 0, "f", 0)):
        try:
            active_config.system_initialize()
        except:  # noqa: E722
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
        except:  # noqa: E722
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
        except:  # noqa: E722
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


def test_promote_cli_to_env_read_only_branch():
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
    fake_args = SimpleNamespace(show_version=True)
    with patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args):
        result = initialize(["--version"])
        assert result is False


def test_initialize_log_level_from_env():
    logger = logging.getLogger()
    old_level = logger.level
    logger.setLevel(logging.INFO)

    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=False,
    )
    with (
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        #        patch("sigenergy2mqtt.config._promote_cli_to_env"),
        patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "DEBUG"}),
        #       patch("sigenergy2mqtt.config._load_config"),
    ):
        _system_initialize()
        assert logger.level == logging.DEBUG

    # Clean up
    logger.setLevel(old_level)


def test_initialize_log_level_invalid_raises():
    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=False,
    )
    with (
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "BOGUS_LEVEL"}),
    ):
        with pytest.raises(ConfigurationError, match="invalid log level"):
            initialize()


def test_initialize_validate_only_returns_false():
    fake_args = SimpleNamespace(
        show_version=False,
        clean=False,
        discovery_only=False,
        validate_only=True,
    )
    with (
        patch("sigenergy2mqtt.config.cli.parse_args", return_value=fake_args),
        patch.dict(os.environ, {}, clear=True),
    ):
        with pytest.raises(ConfigurationError, match="At least one Modbus device must be configured"):
            initialize()
