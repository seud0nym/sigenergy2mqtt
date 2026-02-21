import collections
import json
import logging
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ruamel.yaml import YAML

from sigenergy2mqtt.common import ConsumptionMethod
from sigenergy2mqtt.config import ConsumptionSource, VoltageSource, active_config, const
from sigenergy2mqtt.config.config import active_config

VersionInfo = collections.namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])


def test_validate_logic_exhaustive():
    with patch.object(active_config, "modbus", []):
        with pytest.raises(ValueError, match="At least one"):
            active_config.validate()
        assert active_config.get_modbus_log_level() == logging.WARNING
    from sigenergy2mqtt.config.modbus_config import ModbusConfiguration

    d = ModbusConfiguration()
    d.host = "1.2.3.4"
    d.registers.no_remote_ems = True
    with patch.object(active_config, "modbus", [d]), patch.object(active_config, "ems_mode_check", False):
        with pytest.raises(ValueError, match="no_remote_ems must be False"):
            active_config.validate()
    d.registers.no_remote_ems = False
    d.registers.read_write = False
    with patch.object(active_config, "modbus", [d]), patch.object(active_config, "ems_mode_check", False):
        with pytest.raises(ValueError, match="read_write must be True"):
            active_config.validate()
    d.registers.read_write = True
    with patch.object(active_config, "modbus", [d]), patch.object(active_config.mqtt, "validate"), patch.object(active_config.home_assistant, "validate"), patch.object(active_config.pvoutput, "validate"):
        active_config.validate()


def test_load_from_env_error_handling():
    with patch.dict(os.environ, {const.SIGENERGY2MQTT_DEBUG_SENSOR: "invalid"}, clear=True):
        with pytest.raises(Exception, match="Error processing override"):
            active_config._load_from_env({})


def test_apply_auto_discovery_cases():
    device = {"host": "1.2.3.4", "port": 502}
    from sigenergy2mqtt.config.modbus_config import ModbusConfiguration

    with patch.object(active_config, "modbus", []):
        active_config._apply_auto_discovery([device])
    d = ModbusConfiguration()
    d.host = ""
    with patch.object(active_config, "modbus", [d]):
        active_config._apply_auto_discovery([device])
    d2 = ModbusConfiguration()
    d2.host = "1.2.3.4"
    d2.port = 502
    with patch.object(active_config, "modbus", [d2]), patch.object(d2, "configure"):
        active_config._apply_auto_discovery([device])


def test_process_env_key_all_dynamic():
    overrides = {"home-assistant": {}, "mqtt": {}, "modbus": [{"smart-port": {"mqtt": [{}], "module": {}}}], "influxdb": {}, "pvoutput": {"consumption": "total"}, "sensor-overrides": {}}
    auto_discovered = [{"host": h} for h in ["h", "h2"]]
    for attr in dir(const):
        if attr.startswith("SIGENERGY2MQTT_") and attr != "SIGENERGY2MQTT_CONFIG":
            key = getattr(const, attr)
            val = "true"
            if "PORT" in key:
                val = "502"
            elif "TIMEOUT" in key or "INTERVAL" in key or "FLUSH" in key or "QUERY" in key:
                val = "1"
            elif "RETRIES" in key or "BATCH" in key or "SIZE" in key or "WORKERS" in key or "GAIN" in key or "HOUR" in key or "DEVICE_ID" in key:
                val = "1"
            elif "JSON" in key:
                val = "{}"
            elif "API_KEY" in key or "TOKEN" in key:
                val = "0" * 32
            elif "LOG_LEVEL" in key:
                val = "INFO"
            elif "VOLTAGE" in key:
                val = "pv"
            elif "CONSUMPTION" in key:
                val = "calculated"
            elif "TRANSPORT" in key:
                val = "tcp"
            elif "BUCKET" in key:
                val = "b"
            elif "DATABASE" in key or "ORG" in key:
                val = "x"
            elif "HOST" in key or "BROKER" in key:
                val = "127.0.0.1"
            elif "PREFIX" in key or "NAME" in key or "UNIQUE_ID" in key or "ENTITY_ID" in key:
                val = "p"
            elif "LANGUAGE" in key:
                val = "en"
            try:
                active_config._process_env_key(key, val, overrides, auto_discovered)
            except:
                pass
    active_config._process_env_key("UNKNOWN_XYZ", "val", overrides, auto_discovered)


def test_configure_exhaustive_v9():
    with pytest.raises(ValueError, match="must contain a list"):
        active_config._configure({"modbus": "x"})
    with pytest.raises(ValueError, match="property is not known"):
        active_config._configure({"sensor-overrides": {"S": {"U": 1}}})
    with pytest.raises(ValueError, match="must contain a list"):
        active_config._configure({"sensor-overrides": "x"})
    with pytest.raises(ValueError, match="unknown element"):
        active_config._configure({"U": 1})


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
    _apply_cli_to_env,
    _discover_config_file,
    _is_arg_explicitly_set,
    _load_config,
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
    """Cover lines 182-183: validate_only calls validate() and returns False."""
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
        patch.object(active_config, "validate"),
    ):
        result = initialize()
        assert result is False
        active_config.validate.assert_called_once()
