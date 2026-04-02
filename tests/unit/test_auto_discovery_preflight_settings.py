from pathlib import Path

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.const import (
    SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY,
    SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT,
    SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES,
    SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT,
    SIGENERGY2MQTT_MODBUS_PORT,
)


def test_preflight_settings_reads_yaml(monkeypatch, tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "\n".join(
            [
                "modbus-auto-discovery: once",
                "modbus-auto-discovery-timeout: 1.25",
                "modbus-auto-discovery-ping-timeout: 2.5",
                "modbus-auto-discovery-retries: 7",
                "modbus-port: 1502",
            ]
        )
    )

    cfg = Config()
    monkeypatch.delenv(SIGENERGY2MQTT_MODBUS_PORT, raising=False)
    monkeypatch.delenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, raising=False)
    monkeypatch.delenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, raising=False)
    monkeypatch.delenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, raising=False)
    monkeypatch.delenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, raising=False)
    cfg._source = str(cfg_file)
    settings = cfg._load_auto_discovery_settings()
    assert settings.modbus_auto_discovery == "once"
    assert settings.modbus_auto_discovery_timeout == 1.25
    assert settings.modbus_auto_discovery_ping_timeout == 2.5
    assert settings.modbus_auto_discovery_retries == 7
    assert settings.modbus_port == 1502


def test_preflight_settings_env_overrides_yaml(monkeypatch, tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("modbus-auto-discovery: once\nmodbus-auto-discovery-timeout: 1.25\n")

    monkeypatch.setenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY, "force")
    monkeypatch.setenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, "0.75")
    monkeypatch.setenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, "0.8")
    monkeypatch.setenv(SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, "5")
    monkeypatch.setenv(SIGENERGY2MQTT_MODBUS_PORT, "1602")

    cfg = Config()
    cfg._source = str(cfg_file)
    settings = cfg._load_auto_discovery_settings()
    assert settings.modbus_auto_discovery == "force"
    assert settings.modbus_auto_discovery_timeout == 0.75
    assert settings.modbus_auto_discovery_ping_timeout == 0.8
    assert settings.modbus_auto_discovery_retries == 5
    assert settings.modbus_port == 1602
