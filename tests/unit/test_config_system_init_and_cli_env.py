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
def test_system_initialize_python_version_error(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGENERGY2MQTT_STATE_DIR", raising=False)

    with patch("sigenergy2mqtt.config.config.sys.version_info", VersionInfo(3, 11, 0, "f", 0)):
        with pytest.raises(ConfigurationError):
            _system_initialize()


@pytest.mark.no_persistent_state_mock
def test_create_persistent_state_path_no_writable_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("SIGENERGY2MQTT_STATE_DIR", raising=False)

    with patch("sigenergy2mqtt.config.config.os.path.isdir", return_value=False):
        with pytest.raises(ConfigurationError):
            _create_persistent_state_path()


@pytest.mark.no_persistent_state_mock
def test_create_persistent_state_path(tmp_path, monkeypatch):
    monkeypatch.setenv(const.SIGENERGY2MQTT_STATE_DIR, str(tmp_path))

    expected_path = tmp_path / "sigenergy2mqtt"
    if expected_path.exists():
        expected_path.rmdir()

    created_path = _create_persistent_state_path()
    assert created_path == expected_path
    assert created_path.is_dir()


@pytest.mark.no_persistent_state_mock
def test_create_persistent_state_path_already_exists(tmp_path, monkeypatch):
    monkeypatch.setenv(const.SIGENERGY2MQTT_STATE_DIR, str(tmp_path))

    expected_path = tmp_path / "sigenergy2mqtt"
    expected_path.mkdir()

    created_path = _create_persistent_state_path()
    assert created_path == expected_path
    assert created_path.is_dir()


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
    with patch.object(active_config, "persistent_state_path", tmp_path):
        with patch.dict(os.environ, {const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY: "once"}):
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
        patch.dict(os.environ, {const.SIGENERGY2MQTT_LOG_LEVEL: "DEBUG"}),
        patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[]),
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
        patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[]),
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
        patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[]),
    ):
        with patch.object(active_config, "persistent_state_path", Path("/tmp/nonexistent_test_path")):
            with pytest.raises(ConfigurationError, match="At least one Modbus device must be configured"):
                initialize()


def test_coerce_bool_none():
    from sigenergy2mqtt.config.coerce import _bool, _invert_bool

    assert _bool(None) is None
    assert _invert_bool(None) is None


def test_pvoutput_reshape_extended_fields_not_dict():
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.reshape_extended_fields("not a dict") == "not a dict"


def test_pvoutput_reshape_extended_fields_with_keys():
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    data = {"v7": "value7", "v8": "value8"}
    res = PvOutputConfig.reshape_extended_fields(data)
    assert res == {"extended": {"v7": "value7", "v8": "value8", "v9": "", "v10": "", "v11": "", "v12": ""}}


def test_pvoutput_invalid_api_key():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    with pytest.raises(ValueError, match="pvoutput.api-key must only contain hexadecimal characters"):
        PvOutputConfig.validate_api_key("not-hex!")


def test_pvoutput_consumption_validation():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.validate_consumption(None) is None
    assert PvOutputConfig.validate_consumption(False) is None
    assert PvOutputConfig.validate_consumption("false") is None
    with pytest.raises(ValueError, match="pvoutput.consumption must be false, true"):
        PvOutputConfig.validate_consumption("invalid-consumption")


def test_pvoutput_output_hour():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.validate_output_hour("-1") == -1
    with pytest.raises(ValueError, match="pvoutput.output-hour must be -1 or between 20 and 23"):
        PvOutputConfig.validate_output_hour("10")


def test_pvoutput_voltage():
    import pytest

    from sigenergy2mqtt.common import VoltageSource
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.validate_voltage(VoltageSource.L_N_AVG) == VoltageSource.L_N_AVG
    with pytest.raises(ValueError, match="pvoutput.voltage must be one of:"):
        PvOutputConfig.validate_voltage("invalid-voltage")


def test_pvoutput_tariffs():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.parse_time_periods_field("not a list") == []
    with pytest.raises(ValueError, match="must be a time period definition"):
        PvOutputConfig.parse_time_periods_field(["not-a-dict"])
    with pytest.raises(ValueError, match="contains unknown option"):
        PvOutputConfig.parse_time_periods_field([{"unknown-key": "val"}])
    with pytest.raises(ValueError, match="must contain a 'periods' element"):
        PvOutputConfig.parse_time_periods_field([{"plan": "A"}])


def test_pvoutput_consumption_enabled():
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    cfg = PvOutputConfig(consumption="net-of-battery")
    assert cfg.consumption_enabled is True
    cfg = PvOutputConfig()
    assert cfg.consumption_enabled is False


def test_coerce_str_list_empty():
    from sigenergy2mqtt.config.coerce import _str_list

    assert _str_list("") == []
    assert _str_list("  ,  ") == []


def test_pvoutput_validate_api_key_empty():
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.validate_api_key(None) == ""
    assert PvOutputConfig.validate_api_key("") == ""


def test_pvoutput_validate_consumption_true_str():
    from sigenergy2mqtt.common import ConsumptionSource
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    assert PvOutputConfig.validate_consumption("true") == ConsumptionSource.CONSUMPTION
    assert PvOutputConfig.validate_consumption(True) == ConsumptionSource.CONSUMPTION


def test_pvoutput_validate_output_hour_invalid():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    with pytest.raises(ValueError, match="must be -1 or between 20 and 23"):
        PvOutputConfig.validate_output_hour(19)


def test_pvoutput_tariffs_periods():
    from sigenergy2mqtt.common import TariffType
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    tariffs = PvOutputConfig.parse_time_periods_field([{"periods": [{"type": "shoulder", "start": "00:00", "end": "06:00"}]}])
    assert len(tariffs) == 1
    assert tariffs[0].default == TariffType.SHOULDER
    assert tariffs[0].plan == "Unknown-0"
    assert len(tariffs[0].periods) == 1
    assert tariffs[0].periods[0].start.hour == 0
    assert tariffs[0].periods[0].end.hour == 6


def test_pvoutput_set_testing_flag():
    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    cfg = PvOutputConfig(**{"system-id": "testing", "api-key": "1234abcd"})
    assert cfg.testing is True


def test_pvoutput_check_required_when_enabled():
    import pytest

    from sigenergy2mqtt.config.models.pvoutput import PvOutputConfig

    with pytest.raises(ValueError, match="pvoutput.api-key must be provided when enabled"):
        PvOutputConfig(enabled=True, **{"system-id": "123"})

    with pytest.raises(ValueError, match="pvoutput.system-id must be provided when enabled"):
        PvOutputConfig(enabled=True, **{"api-key": "1234abcd"})

    with pytest.raises(ValueError, match="end time"):
        # We need an invalid periods config. parse_time_periods doesn't actually parse string times as easily to produce invalid ones directly out of box if the strings are valid
        # Let's bypass pydantic parsing for the specific test by mutating post init
        cfg = PvOutputConfig(enabled=True, **{"api-key": "1234abcd", "system-id": "123"})
        from datetime import time

        from sigenergy2mqtt.common import Tariff, TariffType, TimePeriod

        cfg.tariffs = [Tariff(plan="T", default=TariffType.SHOULDER, periods=[TimePeriod(type=TariffType.SHOULDER, start=time(6, 0), end=time(6, 0))])]
        cfg.check_required_when_enabled()
