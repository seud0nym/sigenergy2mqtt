import asyncio
import logging
import time
from unittest.mock import MagicMock, patch

import pytest
from sigenergy2mqtt.common import service_health_registry
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.monitor.sensor import MonitoredSensor
from sigenergy2mqtt.monitor.service import MonitorService

class FakeMqttClient:
    def __init__(self, client_id=b"Monitor"):
        self._client_id = client_id
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

@pytest.mark.asyncio
async def test_check_mqtt_debug_logging(monkeypatch):
    svc = MonitorService([])
    mqtt_client = FakeMqttClient(b"Monitor")
    
    class MockMqttHealth:
        connected = True
        last_message_at = time.monotonic() - 1
        last_publish_ack_at = time.monotonic() - 1
        connect_count = 1
        disconnect_count = 0

    class MockMqttHealthNoMsg:
        connected = True
        last_message_at = None
        last_publish_ack_at = None
        connect_count = 1
        disconnect_count = 0

    monkeypatch.setattr("sigenergy2mqtt.monitor.service.mqtt_health_registry.snapshot", lambda: {"Monitor": MockMqttHealth(), "Other": MockMqttHealthNoMsg()})
    
    # Enable debug logging to cover lines 107-110
    monkeypatch.setattr(logging.getLogger(), "isEnabledFor", lambda level: True if level == logging.DEBUG else False)
    
    # This covers lines 103-110 (both if and else branches)
    connected, count = svc._check_mqtt(mqtt_client)
    assert connected is True
    assert count == 2

def test_check_service_health_pvoutput_and_influxdb(monkeypatch):
    svc = MonitorService([])
    
    # Enable pvoutput and influxdb health monitoring
    monkeypatch.setattr(active_config.pvoutput, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.pvoutput, "health_monitoring", True, raising=False)
    monkeypatch.setattr(active_config.influxdb, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.influxdb, "health_monitoring", True, raising=False)
    
    # Configure mock modbus list so that keys_to_check is initially empty in _check_service_health, triggering line 127
    monkeypatch.setattr(active_config, "modbus", [], raising=False)
    
    service_health_registry.set_health("pvoutput", True)
    service_health_registry.set_health("influxdb", True)
    
    # Call _check_service_health to cover lines 117-119 and 127
    healthy, contributors = svc._check_service_health()
    assert healthy is True
    assert contributors["pvoutput"] is True
    assert contributors["influxdb"] is True

@pytest.mark.asyncio
async def test_collect_dashboard_states_and_diagnostics():
    svc = MonitorService([])
    
    # Add a monitored sensor to cover topics processing
    ms = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="PlantBatterySoC",
        scan_interval=5,
        unit="%",
        last_state=95.5
    )
    svc._topics["sigenergy2mqtt/sigen_0_plant_battery_soc/state"] = ms
    
    ms2 = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="PlantRunningState",
        scan_interval=5,
        unit=None,
        last_state="Running"
    )
    svc._topics["sigenergy2mqtt/sigen_0_plant_running_state/state"] = ms2
    
    # Cover _collect_dashboard_states (lines 154-161)
    dashboard_states = await svc._collect_dashboard_states()
    assert dashboard_states["plant"]["battery_soc"]["value"] == 95.5
    
    # Call it again to cover the caching branch (snapshot already exists and is fresh)
    await svc._collect_dashboard_states()
    
    # Cover _collect_diagnostics (lines 175-181, 185)
    diagnostics = await svc._collect_diagnostics()
    assert diagnostics["status"] == "unknown"  # Since _last_published_at is 0
    assert diagnostics["stale"] is True
    assert diagnostics["monitored_topics"] == 2
    
    # Cover _collect_plant_states (lines 189)
    # The first time it gets the cached snapshot from _collect_dashboard_states
    plant_states = await svc._collect_plant_states()
    assert plant_states["ess_soc_pct"] == 95.5
    assert plant_states["running_state"] == "Running"
    
    # Expire cache and run again to cover re-generating snapshot
    svc._topics_snapshot["timestamp"] = 0
    await svc._collect_plant_states()
