import logging
import time

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
        description="Battery SoC",
        scan_interval=5,
        unit="%",
        last_state=95.5,
    )
    svc._topics["sigenergy2mqtt/sigen_0_plant_battery_soc/state"] = ms

    ms2 = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="PlantRunningState",
        description="Running State",
        scan_interval=5,
        unit=None,
        last_state="Running",
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
    assert diagnostics["Stale"] is True
    assert diagnostics["Monitored Topics"] == 2

    # Cover _collect_plant_states (lines 189)
    # The first time it gets the cached snapshot from _collect_dashboard_states
    plant_states = await svc._collect_plant_states()
    assert plant_states["Battery SoC"] == "95.5%"
    assert plant_states["Running State"] == "Running"

    # Expire cache and run again to cover re-generating snapshot
    svc._topics_snapshot["timestamp"] = 0
    await svc._collect_plant_states()


@pytest.mark.asyncio
async def test_collect_plant_states_lifetime_formatting_and_single_plant():
    svc = MonitorService([])

    # Test _format_lifetime logic:
    # >1000 kWh -> MWh conversion (lines 199-200)
    # None state -> "unknown" (lines 201-202)
    # unit None -> str(last_state) (lines 203-204)
    # unit with <=1000 or non-kWh -> "value unit" (line 205)
    ms_mwh = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="TotalLifetimePVEnergy",
        description="Total Lifetime PV Energy",
        scan_interval=5,
        unit="kWh",
        last_state=1500.0,
    )
    ms_unknown = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="TotalLoadConsumption",
        description="Total Load Consumption",
        scan_interval=5,
        unit="kWh",
        last_state=None,
    )
    rs_single = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="PlantRunningState",
        description="Running State",
        scan_interval=5,
        unit=None,
        last_state="Running",
    )
    gs_single = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="GridStatus",
        description="Grid Status",
        scan_interval=5,
        unit=None,
        last_state="Connected",
    )
    ga_single = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="GridActivity",
        description="Grid Activity",
        scan_interval=5,
        unit=None,
        last_state="Exporting",
    )

    svc._topics = {
        "topic/pv": ms_mwh,
        "topic/load": ms_unknown,
        "topic/rs": rs_single,
        "topic/gs": gs_single,
        "topic/ga": ga_single,
    }

    svc._topics_snapshot = {"timestamp": 0, "snapshot": None}
    plant_states = await svc._collect_plant_states()

    assert plant_states["Total Lifetime PV Energy"] == "1.50 MWh"
    assert plant_states["Total Load Consumption"] == "unknown"
    assert plant_states["Running State"] == "Running"
    assert plant_states["Grid Status"] == "Connected"
    assert plant_states["Grid Activity"] == "Exporting"
    assert plant_states["Alarms"] == "No"


@pytest.mark.asyncio
async def test_collect_plant_states_format_lifetime_helper_branches():
    svc = MonitorService([])
    ms_kwh = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="TotalLifetimePVEnergy",
        description="Total Lifetime PV Energy",
        scan_interval=5,
        unit="kWh",
        last_state=500.0,
    )
    ms_no_unit = MonitoredSensor(
        device_name="PowerPlant[plant=0,dev=1]",
        sensor_name="TotalLoadConsumption",
        description="Total Load Consumption",
        scan_interval=5,
        unit=None,
        last_state=42,
    )
    svc._topics = {
        "topic/pv": ms_kwh,
        "topic/load": ms_no_unit,
    }
    svc._topics_snapshot = {"timestamp": 0, "snapshot": None}
    plant_states = await svc._collect_plant_states()
    assert plant_states["Total Lifetime PV Energy"] == "500.0 kWh"
    assert plant_states["Total Load Consumption"] == "42"


@pytest.mark.asyncio
async def test_collect_plant_states_multi_plant():
    svc = MonitorService([])
    svc._topics_snapshot = {"timestamp": 0, "snapshot": None}

    rs_p0 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="PlantRunningState[plant=0]",
        description="Plant Running State",
        scan_interval=5,
        unit=None,
        last_state="Running",
    )
    rs_p1 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="PlantRunningState[plant=1]",
        description="Plant Running State",
        scan_interval=5,
        unit=None,
        last_state="Standby",
    )
    gs_p0 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="GridStatus[plant=0]",
        description="Grid Status",
        scan_interval=5,
        unit=None,
        last_state="Connected",
    )
    gs_p1 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="GridStatus[plant=1]",
        description="Grid Status",
        scan_interval=5,
        unit=None,
        last_state="Disconnected",
    )
    ga_p0 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="GridActivity[plant=0]",
        description="Grid Activity",
        scan_interval=5,
        unit=None,
        last_state="Exporting",
    )
    ga_p1 = MonitoredSensor(
        device_name="PowerPlant",
        sensor_name="GridActivity[plant=1]",
        description="Grid Activity",
        scan_interval=5,
        unit=None,
        last_state="Importing",
    )

    svc._topics = {
        "topic/rs_p0": rs_p0,
        "topic/rs_p1": rs_p1,
        "topic/gs_p0": gs_p0,
        "topic/gs_p1": gs_p1,
        "topic/ga_p0": ga_p0,
        "topic/ga_p1": ga_p1,
    }

    plant_states = await svc._collect_plant_states()
    assert plant_states["Plant Running State_0"] == "Running"
    assert plant_states["Plant Running State_1"] == "Standby"
    assert plant_states["Grid Status_0"] == "Connected"
    assert plant_states["Grid Status_1"] == "Disconnected"
    assert plant_states["Grid Activity_0"] == "Exporting"
    assert plant_states["Grid Activity_1"] == "Importing"
