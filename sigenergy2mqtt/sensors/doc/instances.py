import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.base import Sensor, AlarmCombinedSensor, ModBusSensor, EnergyDailyAccumulationSensor
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerRatedCurrent, ACChargerInputBreaker
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PVStringCount
from sigenergy2mqtt.sensors.plant_read_only import PlantRatedChargingPower, PlantRatedDischargingPower


async def get_sensor_instances(hass: bool = False):
    plant_index = 0
    inverter_device_address = 1
    dc_charger_device_address = 2
    ac_charger_device_address = 3

    Config.devices[plant_index].dc_chargers.append(dc_charger_device_address)
    Config.devices[plant_index].ac_chargers.append(ac_charger_device_address)

    Config.devices[plant_index].smartport.enabled = True
    Config.devices[plant_index].smartport.module.name = "enphase"
    Config.devices[plant_index].smartport.module.pv_power = "EnphasePVPower"
    Config.devices[plant_index].smartport.module.testing = True

    Config.home_assistant.enabled = hass

    logging.info("Creating Power Plant")
    plant = PowerPlant(plant_index, HybridInverter(), 3, 12.6, 13.68, PlantRatedChargingPower(plant_index), PlantRatedDischargingPower(plant_index))
    remote_ems = plant.sensors[f"{Config.home_assistant.entity_id_prefix}_0_247_40029"]
    assert remote_ems is not None, "Failed to find RemoteEMS instance"

    logging.info("Creating Hybrid Inverter")
    hybrid_inverter = Inverter(
        plant_index=plant_index,
        remote_ems=remote_ems,
        device_address=inverter_device_address,
        device_type=HybridInverter(),
        model_id="SigenStor EC 12.0 TP",
        serial="CMU123A45BP678",
        firmware="V100R001C00SPC108B088F",
        strings=16,
        power_phases=3,
        pv_string_count=PVStringCount(plant_index, inverter_device_address),
        output_type=OutputType(plant_index, inverter_device_address),
        firmware_version=InverterFirmwareVersion(plant_index, inverter_device_address),
    )
    logging.info("Creating PV Inverter")
    pv_inverter = Inverter(
        plant_index=plant_index,
        remote_ems=remote_ems,
        device_address=inverter_device_address,
        device_type=PVInverter(),
        model_id="Sigen PV Max 5.0 TP",
        serial="CMU876A65BP321",
        firmware="V100R001C00SPC108B088F",
        strings=2,
        power_phases=3,
        pv_string_count=PVStringCount(plant_index, inverter_device_address),
        output_type=OutputType(plant_index, inverter_device_address),
        firmware_version=InverterFirmwareVersion(plant_index, inverter_device_address),
    )

    plant.add_ess_accumulation_sensors(plant_index, hybrid_inverter, pv_inverter)

    logging.info("Creating DC Charger")
    dc_charger = DCCharger(plant_index, dc_charger_device_address, remote_ems)

    logging.info("Creating DC Charger")
    rated_current = ACChargerRatedCurrent(plant_index, ac_charger_device_address)
    input_breaker = ACChargerInputBreaker(plant_index, ac_charger_device_address)
    ac_charger = ACCharger(plant_index, ac_charger_device_address, remote_ems, 1.0, 2.0, rated_current, input_breaker)

    sensor_count = {}
    sensor_instances = {}

    def find_concrete_classes(superclass):
        for c in superclass.__subclasses__():
            if len(c.__subclasses__()) == 0:
                if c.__name__ != "RequisiteSensor":
                    sensor_count[c.__name__] = 0
            else:
                find_concrete_classes(c)

    def add_sensor_instance(s):
        if isinstance(s, ModBusSensor):
            key = s._address
        else:
            key = s.__class__.__name__
        if key not in sensor_instances:
            sensor_instances[key] = s
        elif s.__class__.__name__ != sensor_instances[key].__class__.__name__:
            logging.warning(f"Register {key} in {s.__class__.__name__} already defined in {sensor_instances[key].__class__.__name__}")
        sensor_count[s.__class__.__name__] += 1
        for d in s._derived_sensors.values():
            add_sensor_instance(d)

    find_concrete_classes(Sensor)
    add_sensor_instance(InverterModel(plant_index, inverter_device_address))
    add_sensor_instance(InverterSerialNumber(plant_index, inverter_device_address))
    for parent in [plant, hybrid_inverter, dc_charger, ac_charger, pv_inverter]:
        devices = [parent]
        devices.extend(parent._children)
        for device in devices:
            for s in device.sensors.values():
                if isinstance(s, AlarmCombinedSensor):
                    add_sensor_instance(s)
                    for alarm in s._alarms:
                        add_sensor_instance(alarm)
                else:
                    add_sensor_instance(s)
    for sensor, count in sensor_count.items():
        if count == 0:
            logging.warning(f"Sensor {sensor} has not been used?")

    return sensor_instances


def cancel_sensor_futures():
    for future in EnergyDailyAccumulationSensor.futures:
        future.cancel()


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_sensor_instances())
    cancel_sensor_futures()
    loop.close()
