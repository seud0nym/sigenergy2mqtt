import pytest
from sigenergy2mqtt.monitor.dashboard import extract_dashboard_state
from sigenergy2mqtt.monitor.sensor import MonitoredSensor

def test_extract_dashboard_state_full_plant():
    state = {
        # Plant LIVE fields
        "sigenergy2mqtt/sigen_0_plant_battery_soc/state": MonitoredSensor(
            device_name="PowerPlant[plant=0,dev=1]",
            sensor_name="PlantBatterySoC",
            description="Battery SoC",
            scan_interval=5,
            unit="%",
            last_state=95.5
        ),
        "sigenergy2mqtt/sigen_0_plant_rated_energy_capacity/state": MonitoredSensor(
            device_name="PowerPlant[plant=0,dev=1]",
            sensor_name="PlantRatedEnergyCapacity",
            description="Rated Energy Capacity",
            scan_interval=5,
            unit="kWh",
            last_state=10.0
        ),
        # Inverter 1 LIVE fields
        "sigenergy2mqtt/sigen_0_inverter_1_active_power/state": MonitoredSensor(
            device_name="Inverter[plant=0,dev=1]",
            sensor_name="InverterActivePower",
            description="Active Power",
            scan_interval=5,
            unit="W",
            last_state=1500
        ),
        # Inverter 2 config fields
        "sigenergy2mqtt/sigen_0_inverter_2_model/state": MonitoredSensor(
            device_name="Inverter[plant=0,dev=2]",
            sensor_name="InverterModel",
            description="Inverter Model",
            scan_interval=5,
            unit=None,
            last_state="SigenStor"
        ),
        # DCCharger 1
        "sigenergy2mqtt/sigen_0_dc_charger_1_running_state/state": MonitoredSensor(
            device_name="DCCharger[plant=0,dev=1]",
            sensor_name="DCChargerRunningState",
            description="Running State",
            scan_interval=5,
            unit=None,
            last_state="Charging"
        ),
        # ACCharger 2
        "sigenergy2mqtt/sigen_0_ac_charger_2_alarm/state": MonitoredSensor(
            device_name="ACCharger[plant=0,dev=2]",
            sensor_name="ACChargerAlarm",
            description="Alarm",
            scan_interval=5,
            unit=None,
            last_state="No Alarm"
        ),
    }

    result = extract_dashboard_state(state)
    
    assert result["plant"]["battery_soc"]["value"] == 95.5
    assert result["plant"]["battery_soc"]["unit"] == "%"
    assert result["plant"]["has_battery"] is True
    assert result["plant"]["config"]["rated_energy_capacity"]["value"] == 10.0
    
    assert result["inverters"]["1"]["active_power"]["value"] == 1500
    assert "config" in result["inverters"]["1"]
    
    assert result["inverters"]["2"]["config"]["model"]["value"] == "SigenStor"
    
    assert result["dc_chargers"]["1"]["running_state"]["value"] == "Charging"
    assert result["ac_chargers"]["2"]["alarm"]["value"] == "No Alarm"

def test_extract_dashboard_state_no_battery():
    # To cover line 181 and missing devices case
    state = {
        "sigenergy2mqtt/sigen_0_plant_grid_status/state": MonitoredSensor(
            device_name="PowerPlant[plant=0,dev=1]",
            sensor_name="PlantGridStatus",
            description="Grid Status",
            scan_interval=5,
            unit=None,
            last_state="On-grid"
        )
    }
    result = extract_dashboard_state(state)
    assert result["plant"]["has_battery"] is False
    assert result["inverters"] == {}
    assert result["dc_chargers"] == {}
    assert result["ac_chargers"] == {}

def test_extract_dashboard_state_invalid_device():
    # To cover skipping unrecognized device types
    state = {
        "sigenergy2mqtt/sigen_0_unknown_1_test/state": MonitoredSensor(
            device_name="UnknownDevice[plant=0,dev=1]",
            sensor_name="TestSensor",
            description="Test Sensor",
            scan_interval=5,
            unit=None,
            last_state=1
        ),
        "sigenergy2mqtt/sigen_0_unmatched/state": MonitoredSensor(
            device_name="NotMatchRegex",
            sensor_name="TestSensor2",
            description="Test Sensor 2",
            scan_interval=5,
            unit=None,
            last_state=1
        )
    }
    result = extract_dashboard_state(state)
    assert result["plant"] == {"config": {}, "has_battery": False}
    assert result["inverters"] == {}
