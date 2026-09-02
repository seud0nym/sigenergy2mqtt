from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.diagnostics.collectors import DiagnosticsCollectors


@pytest.mark.asyncio
async def test_collect_modbus_metrics(monkeypatch):
    monkeypatch.setattr(active_config, "modbus", [MagicMock(disable_chunking=False, timeout=5, retries=3)], raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_modbus_metrics()
    assert "Physical Reads_pct" in metrics
    assert "config" in metrics
    assert metrics["config"]["disable_chunking"] == "no"


@pytest.mark.asyncio
async def test_collect_mqtt_metrics(monkeypatch):
    monkeypatch.setattr(active_config.home_assistant, "enabled", True, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_mqtt_metrics()
    assert "Physical Publishes_pct" in metrics
    assert "config" in metrics


@pytest.mark.asyncio
async def test_collect_influxdb_metrics(monkeypatch):
    monkeypatch.setattr(active_config.influxdb, "write_timeout", 10, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_influxdb_metrics()
    assert "Write Errors" in metrics
    assert "config" in metrics


@pytest.mark.asyncio
async def test_collect_state_store_metrics(monkeypatch):
    monkeypatch.setattr(active_config.persistence, "mqtt_redundancy", True, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_state_store_metrics()
    assert "Save Max_ms" in metrics
    assert "config" in metrics


@pytest.mark.asyncio
async def test_collect_pvoutput_metrics(monkeypatch):
    # active_config.pvoutput
    monkeypatch.setattr(active_config.pvoutput, "exports", True, raising=False)
    monkeypatch.setattr(active_config.pvoutput, "imports", True, raising=False)
    monkeypatch.setattr(active_config.pvoutput, "consumption", MagicMock(value="Consumption"), raising=False)
    monkeypatch.setattr(active_config.pvoutput, "voltage", MagicMock(value="Voltage"), raising=False)
    monkeypatch.setattr(active_config.pvoutput, "output_hour", -1, raising=False)

    # pvoutput.PVOutputSettings
    class FakePVOutputSettings:
        donator = True
        interval = 5

    monkeypatch.setattr("sigenergy2mqtt.pvoutput.PVOutputSettings", FakePVOutputSettings)

    metrics = await DiagnosticsCollectors._diagnostics_collect_pvoutput_metrics()
    assert "Upload Errors" in metrics
    assert "config" in metrics
    assert metrics["config"]["end_of_day"] == "@ status interval"


@pytest.mark.asyncio
async def test_collect_runtime_config():
    from sigenergy2mqtt.config.service import SettingsService
    from sigenergy2mqtt.devices.base.registry import DeviceRegistry

    DeviceRegistry.clear()
    try:
        _ = SettingsService()
        payload = await DiagnosticsCollectors._diagnostics_collect_runtime_config()
        assert "controls" in payload
        controls = payload["controls"]
        assert "log_level" in controls
        assert controls["log_level"]["type"] == "select"
        assert "modbus_log_level" in controls
        assert controls["modbus_log_level"]["type"] == "select"
        assert controls["modbus_log_level"]["value"] != ""
        assert "repeated_state_publish_interval" in controls
        assert controls["repeated_state_publish_interval"]["type"] == "number"
        assert "persistence_debug" in controls
        assert controls["persistence_debug"]["type"] == "switch"
    finally:
        DeviceRegistry.clear()
