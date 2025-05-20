import asyncio
import logging
from pathlib import Path
from instances import get_sensor_instances, cancel_sensor_futures

from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.base import WriteOnlySensor


logging.getLogger("root").setLevel(logging.DEBUG)

derived = {
    "BatteryChargingPower": "BatteryPower &gt; 0",
    "BatteryDischargingPower": "BatteryPower &lt; 0",
    "EnphasePVPower": "Enphase Envoy API",
    "EnphaseLifetimePVEnergy": "Enphase Envoy API when EnphasePVPower derived",
    "EnphaseDailyPVEnergy": "Enphase Envoy API when EnphasePVPower derived",
    "EnphaseCurrent": "Enphase Envoy API when EnphasePVPower derived",
    "EnphaseFrequency": "Enphase Envoy API when EnphasePVPower derived",
    "EnphasePowerFactor": "Enphase Envoy API when EnphasePVPower derived",
    "EnphaseReactivePower": "Enphase Envoy API when EnphasePVPower derived",
    "EnphaseVoltage": "Enphase Envoy API when EnphasePVPower derived",
    "GridSensorDailyExportEnergy": "GridSensorLifetimeExportEnergy &minus; GridSensorLifetimeExportEnergy at last midnight",
    "GridSensorDailyImportEnergy": "GridSensorLifetimeImportEnergy &minus; GridSensorLifetimeImportEnergy at last midnight",
    "GridSensorExportPower": "GridSensorActivePower &lt; 0 &times; -1",
    "GridSensorImportPower": "GridSensorActivePower &gt; 0",
    "GridSensorLifetimeExportEnergy": "Riemann &sum; of GridSensorExportPower",
    "GridSensorLifetimeImportEnergy": "Riemann &sum; of GridSensorImportPower",
    "InverterBatteryChargingPower": "ChargeDischargePower &gt; 0",
    "InverterBatteryDischargingPower": "ChargeDischargePower &lt; 0 &times; -1",
    "InverterDailyPVEnergy": "InverterLifetimePVEnergy &minus; InverterLifetimePVEnergy at last midnight",
    "InverterLifetimePVEnergy": "Riemann &sum; of InverterPVPower",
    "PVStringDailyEnergy": "PVStringLifetimeEnergy &minus; PVStringLifetimeEnergy at last midnight",
    "PVStringLifetimeEnergy": "Riemann &sum; of PVStringPower",
    "PVStringPower": "PVVoltageSensor &times; PVCurrentSensor",
    "PlantAccumulatedChargeEnergy": "&sum; of AccumulatedChargeEnergy across all Inverters associated with the Plant",
    "PlantAccumulatedDischargeEnergy": "&sum; of AccumulatedDischargeEnergy across all Inverters associated with the Plant",
    "PlantConsumedPower": "(either PlantPVPower _or_ TotalPVPower) &plus; GridSensorActivePower &minus; BatteryPower",
    "PlantDailyChargeEnergy": "&sum; of DailyChargeEnergy across all Inverters associated with the Plant",
    "PlantDailyConsumedEnergy": "PlantLifetimeConsumedEnergy &minus; PlantLifetimeConsumedEnergy at last midnight",
    "PlantDailyDischargeEnergy": "&sum; of DailyDischargeEnergy across all Inverters associated with the Plant",
    "PlantDailyPVEnergy": "PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight",
    "PlantLifetimeConsumedEnergy": "Riemann &sum; of PlantConsumedPower",
    "PlantLifetimePVEnergy": "Riemann &sum; of (either PlantPVPower _or_ TotalPVPower)",
    "TotalPVPower": "PlantPVPower &plus; &sum; of all configured SmartPort MQTT sources and SmartPort modules",
    "GeneralPCSAlarm": "Modbus Registers 30027 and 30028",
    "ACChargerAlarms": "Modbus Registers 32012, 32013, and 32014",
    "InverterPCSAlarm": "Modbus Registers 30605 and 30606",
}


async def sensor_index():
    def published_topics(device):
        f.write("| Sensor Class | Unit | Gain | State Topic | Interval | Source | Applicable To |\n")
        f.write("|--------------|------|-----:|-------------|---------:|--------|---------------|\n")
        for key in [key for key, value in mqtt_sensors.items() if "state_topic" in value and not isinstance(value, WriteOnlySensor)]:
            sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device:
                sensor_name = sensor.__class__.__name__
                f.write(f"| {sensor_name} | {'' if sensor.unit is None else sensor.unit} | {'' if sensor.gain is None else sensor.gain} | {sensor.state_topic} <br/> {hass_sensors[key].state_topic} |")
                if hasattr(sensor, "scan_interval"):
                    f.write(f" {sensor.scan_interval}s ")
                f.write("|")
                if sensor_name in derived:
                    f.write(derived[sensor_name])
                elif hasattr(sensor, "_address"):
                    f.write(f"Modbus Register {sensor._address} ")
                f.write("|")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid&nbsp;Inverter ")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV&nbsp;Inverter ")
                f.write("|\n")

    def subscribed_topics(device):
        f.write("| Sensor Class | Command Topic | Target | Applicable To |\n")
        f.write("|--------------|---------------|--------|---------------|\n")
        for key in [key for key, value in mqtt_sensors.items() if "command_topic" in value]:
            sensor = mqtt_sensors[key]
            sensor_parent = None if not hasattr(sensor, "parent_device") else sensor.parent_device.__class__.__name__
            if sensor_parent == device:
                sensor_name = sensor.__class__.__name__
                f.write(f"| {sensor_name} | {sensor.state_topic} <br/> {hass_sensors[key].state_topic} | ")
                if hasattr(sensor, "_address"):
                    f.write(f"Modbus Register {sensor._address} ")
                f.write("|")
                if sensor_parent in ("Inverter", "ESS", "PVString"):
                    if isinstance(sensor, HybridInverter) and isinstance(sensor, PVInverter):
                        f.write(" Hybrid&nbsp;Inverter <br/> PV&nbsp;Inverter ")
                    elif isinstance(sensor, HybridInverter):
                        f.write(" Hybrid&nbsp;Inverter ")
                    elif isinstance(sensor, PVInverter):
                        f.write(" PV&nbsp;Inverter ")
                f.write("|\n")

    readme = Path("sigenergy2mqtt/sensors/README.md")
    assert readme.exists(), f"README.md file not found at {readme}"
    hass_sensors = await get_sensor_instances(hass=True)
    mqtt_sensors = await get_sensor_instances(hass=False)
    with readme.open("w") as f:
        f.write("# MQTT Topics\n")
        f.write("\nTopics prefixed with `homeassistant/` are used when the `home-assistant` configuration `enabled` option in the configuration file,\n")
        f.write("or the `SIGENERGY2MQTT_HASS_ENABLED` environment variable, are set to true, or the `--hass-enabled` command line option is specified.\n")
        f.write("Otherwise, the topics prefixed with `sigenergy2mqtt/` are used.\n")
        f.write("\nThe number after the `sigen_` prefix represents the host index from the configuration file, starting from 0. (Home Assistant configuration may change the `sigen` topic prefix.)")
        f.write("\nInverter, AC Charger and DC Charger indexes use the device address (slave ID) as specified in the configuration file.\n")
        f.write("\nScan Intervals are shown in seconds. Intervals for derived sensors are dependent on the source sensors.\n")
        f.write("\n## Published Topics\n")
        f.write("\n### Plant\n")
        published_topics("PowerPlant")
        f.write("\n#### Grid Sensor\n")
        published_topics("GridSensor")
        f.write("\n#### Smart-Port\n")
        published_topics("SmartPort")
        f.write("\n### Inverter\n")
        published_topics("Inverter")
        f.write("\n#### Energy Storage System\n")
        published_topics("ESS")
        f.write("\n#### PV String\n")
        published_topics("PVString")
        f.write("\n### AC Charger\n")
        published_topics("ACCharger")
        f.write("\n### DC Charger\n")
        published_topics("DCCharger")
        f.write("\n## Subscribed Topics\n")
        f.write("\n### Plant\n")
        subscribed_topics("PowerPlant")
        f.write("\n### Inverter\n")
        subscribed_topics("Inverter")
        f.write("\n### AC Charger\n")
        subscribed_topics("ACCharger")
        f.write("\n### DC Charger\n")
        subscribed_topics("DCCharger")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sensor_index())
    cancel_sensor_futures()
    loop.close()
