import pytest
from ruamel.yaml import YAML

from sigenergy2mqtt.config import Config, const
from sigenergy2mqtt.config.config import active_config


def write_yaml(tmp_path, data: dict) -> str:
    p = tmp_path / "cfg.yaml"
    with p.open("w") as f:
        YAML(typ="safe").dump(data, f)
    return str(p)


def test_reload_applies_yaml(tmp_path, monkeypatch):
    data = {
        "log-level": "DEBUG",
        "modbus": [{"host": "m1.local", "port": 1502}],
    }
    fn = write_yaml(tmp_path, data)

    # Directly configure from the parsed data to exercise _configure
    original_modbus = list(active_config.modbus)
    try:
        active_config.modbus.clear()
        with open(fn, "r") as f:
            parsed = YAML(typ="safe").load(f)
        active_config._configure(parsed)

        assert active_config.log_level == getattr(__import__("logging"), "DEBUG")
        # Ensure modbus device was configured (check at least port)
        assert len(active_config.modbus) >= 1
        assert active_config.modbus[0].port == 1502
    finally:
        active_config.modbus.clear()
        active_config.modbus.extend(original_modbus)


def test_reload_env_overrides(monkeypatch):
    # Set environment variables for modbus host/port to exercise env overrides
    monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "8.8.8.8")
    monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_PORT, "1503")

    # Reset devices and clear any source so reload uses env overrides
    original_modbus = list(active_config.modbus)
    original_source = active_config._source
    try:
        active_config.modbus.clear()
        active_config._source = None
        # Reload should apply overrides and create a modbus device
        active_config.reload()
        assert len(active_config.modbus) >= 1
        assert active_config.modbus[0].host == "8.8.8.8"
        assert active_config.modbus[0].port == 1503
    finally:
        active_config.modbus.clear()
        active_config.modbus.extend(original_modbus)
        active_config._source = original_source


def test_reload_invalid_yaml(tmp_path):
    # Write invalid YAML
    p = tmp_path / "bad.yaml"
    p.write_text("influxdb: [\n  - invalid")
    original_source = active_config._source
    try:
        active_config._source = str(p)
        with pytest.raises(Exception):
            active_config.reload()
    finally:
        active_config._source = original_source


def test_configure_unknown_key(tmp_path):
    data = {"unknown-section": {"foo": "bar"}}
    # Ensure _configure raises on unknown key processing
    with pytest.raises(ValueError):
        Config._configure(data, override=False)
