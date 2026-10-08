import logging
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Settings, _promote_cli_to_env, active_config, cli, const
from sigenergy2mqtt.main.service_setup import setup_services
from sigenergy2mqtt.main.thread_config import thread_config_registry


@pytest.fixture
def publish_config(tmp_path, monkeypatch):
    path = tmp_path / "publish.yaml"
    path.write_text("{}\n")
    monkeypatch.setenv(const.SIGENERGY2MQTT_CONFIG, str(path))
    for name in (const.SIGENERGY2MQTT_NO_METRICS, const.SIGENERGY2MQTT_PUBLISH_METRICS, const.SIGENERGY2MQTT_PUBLISH_RUNTIME_CONFIG):
        monkeypatch.delenv(name, raising=False)
    return path


def test_publish_defaults(publish_config, caplog):
    settings = Settings()
    assert settings.metrics_enabled is False
    assert settings.runtime_config_enabled is False
    _promote_cli_to_env(cli.parse_args([]))
    assert Settings().metrics_enabled is False
    assert Settings().runtime_config_enabled is False
    assert "deprecated" not in caplog.text


def test_publish_help_text():
    help_text = cli.get_parser().format_help()
    assert "--publish-metrics" in help_text
    assert "--publish-runtime-config" in help_text
    assert "--no-metrics          Deprecated:" in help_text


@pytest.mark.parametrize("key, env, field", [
    ("publish-metrics", const.SIGENERGY2MQTT_PUBLISH_METRICS, "metrics_enabled"),
    ("publish-runtime-config", const.SIGENERGY2MQTT_PUBLISH_RUNTIME_CONFIG, "runtime_config_enabled"),
])
@pytest.mark.parametrize("value", [True, False])
def test_publish_yaml_env_cli_precedence(publish_config, monkeypatch, key, env, field, value):
    publish_config.write_text(f"{key}: {str(value).lower()}\n")
    assert getattr(Settings(), field) is value

    monkeypatch.setenv(env, str(not value).lower())
    assert getattr(Settings(), field) is not value

    _promote_cli_to_env(cli.parse_args([f"--{key}"]))
    assert getattr(Settings(), field) is True


@pytest.mark.parametrize("source", ["yaml", "env"])
@pytest.mark.parametrize("value", [True, False])
def test_deprecated_metrics_preserves_value_and_warns(publish_config, monkeypatch, caplog, source, value):
    if source == "yaml":
        publish_config.write_text(f"no-metrics: {str(value).lower()}\n")
        option = "no-metrics"
    else:
        monkeypatch.setenv(const.SIGENERGY2MQTT_NO_METRICS, str(value).lower())
        option = const.SIGENERGY2MQTT_NO_METRICS

    with caplog.at_level(logging.WARNING):
        assert Settings().metrics_enabled is not value
    assert any(option in record.message and "deprecated" in record.message for record in caplog.records)


def test_deprecated_metrics_cli_overrides_positive_env(publish_config, monkeypatch, caplog):
    monkeypatch.setenv(const.SIGENERGY2MQTT_PUBLISH_METRICS, "true")
    _promote_cli_to_env(cli.parse_args(["--no-metrics"]))
    assert Settings().metrics_enabled is False
    assert any("--no-metrics" in record.message and "deprecated" in record.message for record in caplog.records)


@pytest.mark.parametrize("source", ["yaml", "env", "cli"])
def test_positive_metrics_takes_precedence_in_same_source(publish_config, monkeypatch, caplog, source):
    if source == "yaml":
        publish_config.write_text("no-metrics: true\npublish-metrics: true\n")
    elif source == "env":
        monkeypatch.setenv(const.SIGENERGY2MQTT_NO_METRICS, "true")
        monkeypatch.setenv(const.SIGENERGY2MQTT_PUBLISH_METRICS, "true")
    else:
        _promote_cli_to_env(cli.parse_args(["--no-metrics", "--publish-metrics"]))
    assert Settings().metrics_enabled is True
    assert "deprecated" in caplog.text


@pytest.mark.parametrize("yaml, env, value, expected", [
    ("no-metrics: false", const.SIGENERGY2MQTT_PUBLISH_METRICS, "false", False),
    ("no-metrics: true", const.SIGENERGY2MQTT_PUBLISH_METRICS, "true", True),
    ("publish-metrics: false", const.SIGENERGY2MQTT_NO_METRICS, "false", True),
    ("publish-metrics: true", const.SIGENERGY2MQTT_NO_METRICS, "true", False),
])
def test_metrics_env_overrides_yaml_across_old_and_new_options(publish_config, monkeypatch, caplog, yaml, env, value, expected):
    publish_config.write_text(f"{yaml}\n")
    monkeypatch.setenv(env, value)
    assert Settings().metrics_enabled is expected
    assert "deprecated" in caplog.text


def test_publish_metrics_cli_overrides_deprecated_env(publish_config, monkeypatch):
    monkeypatch.setenv(const.SIGENERGY2MQTT_NO_METRICS, "true")
    _promote_cli_to_env(cli.parse_args(["--publish-metrics"]))
    assert Settings().metrics_enabled is True


@pytest.mark.parametrize("metrics", [True, False])
@pytest.mark.parametrize("runtime_config", [True, False])
def test_service_selection(publish_config, metrics, runtime_config):
    active_config.metrics_enabled = metrics
    active_config.runtime_config_enabled = runtime_config
    active_config.diagnostics.enabled = False
    active_config.pvoutput.enabled = False
    active_config.influxdb.enabled = False
    active_config.clean = True
    thread_config_registry.clear()
    try:
        with (
            patch("sigenergy2mqtt.main.service_setup.is_docker", return_value=False),
            patch("sigenergy2mqtt.main.service_setup.SettingsService") as settings_service,
            patch("sigenergy2mqtt.main.service_setup.MetricsService") as metrics_service,
        ):
            configs = setup_services([], ProtocolVersion.V2_8)
            assert settings_service.call_count == int(runtime_config)
            assert metrics_service.call_count == int(metrics)
            assert len(configs) == int(metrics or runtime_config)
            if configs:
                assert configs[0].name == "Services"
                assert len(configs[0].devices) == int(metrics) + int(runtime_config)
                if metrics:
                    metrics_service.assert_called_once_with(ProtocolVersion.V2_8)
    finally:
        thread_config_registry.clear()
