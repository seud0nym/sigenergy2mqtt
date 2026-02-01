import pytest
from ruamel.yaml import YAML

from sigenergy2mqtt.config import const
from sigenergy2mqtt.config.config import Config


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
    Config.modbus = []
    with open(fn, "r") as f:
        parsed = YAML(typ="safe").load(f)
    Config._configure(parsed)

    assert Config.log_level == getattr(__import__("logging"), "DEBUG")
    # Ensure modbus device was configured (check at least port)
    assert len(Config.modbus) >= 1
    assert Config.modbus[0].port == 1502


def test_reload_env_overrides(monkeypatch):
    # Set environment variables for modbus host/port to exercise env overrides
    monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_HOST, "8.8.8.8")
    monkeypatch.setenv(const.SIGENERGY2MQTT_MODBUS_PORT, "1503")

    # Reset devices and clear any source so reload uses env overrides
    Config.modbus = []
    Config._source = None

    # Reload should apply overrides and create a modbus device
    Config.reload()
    assert len(Config.modbus) >= 1
    assert Config.modbus[0].host == "8.8.8.8"
    assert Config.modbus[0].port == 1503


def test_reload_invalid_yaml(tmp_path):
    # Write invalid YAML
    p = tmp_path / "bad.yaml"
    p.write_text("influxdb: [\n  - invalid")
    Config._source = str(p)
    with pytest.raises(Exception):
        Config.reload()


def test_configure_unknown_key(tmp_path):
    data = {"unknown-section": {"foo": "bar"}}
    # Ensure _configure raises on unknown key processing
    with pytest.raises(ValueError):
        Config._configure(data, override=False)
