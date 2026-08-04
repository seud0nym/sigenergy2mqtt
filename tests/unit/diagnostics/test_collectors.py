import pytest
from unittest.mock import MagicMock

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.diagnostics.collectors import DiagnosticsCollectors
from sigenergy2mqtt.metrics.metrics import Metrics

@pytest.mark.asyncio
async def test_collect_modbus_metrics(monkeypatch):
    monkeypatch.setattr(active_config, "modbus", [MagicMock(disable_chunking=False, timeout=5, retries=3)], raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_modbus_metrics()
    assert "physical_reads_pct" in metrics
    assert "config" in metrics
    assert metrics["config"]["chunking"] == "yes"

@pytest.mark.asyncio
async def test_collect_mqtt_metrics(monkeypatch):
    monkeypatch.setattr(active_config.home_assistant, "enabled", True, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_mqtt_metrics()
    assert "physical_publishes_pct" in metrics
    assert "config" in metrics

@pytest.mark.asyncio
async def test_collect_influxdb_metrics(monkeypatch):
    monkeypatch.setattr(active_config.influxdb, "write_timeout", 10, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_influxdb_metrics()
    assert "write_errors" in metrics
    assert "config" in metrics

@pytest.mark.asyncio
async def test_collect_state_store_metrics(monkeypatch):
    monkeypatch.setattr(active_config.persistence, "mqtt_redundancy", True, raising=False)
    metrics = await DiagnosticsCollectors._diagnostics_collect_state_store_metrics()
    assert "save_max_ms" in metrics
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
    assert "upload_errors" in metrics
    assert "config" in metrics
    assert metrics["config"]["end_of_day"] == "@ status interval"
