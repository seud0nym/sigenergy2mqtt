import asyncio
import logging
import sys
import os

os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.base import ReservedSensor, Sensor, AlarmCombinedSensor, EnergyDailyAccumulationSensor
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerRatedCurrent, ACChargerInputBreaker
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PVStringCount
from sigenergy2mqtt.sensors.plant_read_only import PlantRatedChargingPower, PlantRatedDischargingPower


async def get_sensor_instances(
    hass: bool = False,
    plant_index: int = 0,
    hybrid_inverter_device_address: int = 1,
    pv_inverter_device_address: int = 1,
    dc_charger_device_address: int = 1,
    ac_charger_device_address: int = 2,
):
    Config.devices[plant_index].dc_chargers.append(dc_charger_device_address)
    Config.devices[plant_index].ac_chargers.append(ac_charger_device_address)

    Config.devices[plant_index].smartport.enabled = True
    Config.devices[plant_index].smartport.module.name = "enphase"
    Config.devices[plant_index].smartport.module.pv_power = "EnphasePVPower"
    Config.devices[plant_index].smartport.module.testing = True

    Config.home_assistant.enabled = hass

    logging.debug(f"Instantiating Power Plant ({hass=})")
    plant = PowerPlant(
        plant_index=plant_index,
        device_type=HybridInverter(),
        output_type=2,
        power_phases=3,
        rcp_value=12.6,
        rdp_value=13.68,
        rated_charging_power=PlantRatedChargingPower(plant_index),
        rated_discharging_power=PlantRatedDischargingPower(plant_index),
    )
    remote_ems = plant.sensors[f"{Config.home_assistant.entity_id_prefix}_0_247_40029"]
    assert remote_ems is not None, "Failed to find RemoteEMS instance"

    logging.debug(f"Instantiating Hybrid Inverter ({hass=})")
    hybrid_model = InverterModel(plant_index, hybrid_inverter_device_address)
    hybrid_serial = InverterSerialNumber(plant_index, hybrid_inverter_device_address)
    hybrid_firmware = InverterFirmwareVersion(plant_index, hybrid_inverter_device_address)
    hybrid_pv_strings = PVStringCount(plant_index, hybrid_inverter_device_address)
    hybrid_output_type = OutputType(plant_index, hybrid_inverter_device_address)
    hybrid_model.set_state("SigenStor EC 12.0 TP")
    hybrid_serial.set_state("CMU123A45BP678")
    hybrid_firmware.set_state("V100R001C00SPC108B088F")
    hybrid_pv_strings.set_state(16)
    hybrid_output_type.set_state(3)
    hybrid_inverter = Inverter(
        plant_index=plant_index,
        device_address=hybrid_inverter_device_address,
        device_type=HybridInverter(),
        model_id=hybrid_model.latest_raw_state,
        serial=hybrid_serial.latest_raw_state,
        firmware=hybrid_firmware.latest_raw_state,
        strings=hybrid_pv_strings.latest_raw_state,
        power_phases=3,
        pv_string_count=hybrid_pv_strings,
        output_type=hybrid_output_type,
        firmware_version=hybrid_firmware,
        model=hybrid_model,
        serial_number=hybrid_serial,
    )

    logging.debug(f"Instantiating PV Inverter ({hass=})")
    pv_model = InverterModel(plant_index, pv_inverter_device_address)
    pv_serial = InverterSerialNumber(plant_index, pv_inverter_device_address)
    pv_firmware = InverterFirmwareVersion(plant_index, pv_inverter_device_address)
    pv_pv_strings = PVStringCount(plant_index, pv_inverter_device_address)
    pv_output_type = OutputType(plant_index, pv_inverter_device_address)
    pv_model.set_state("Sigen PV Max 5.0 TP")
    pv_serial.set_state("CMU876A65BP321")
    pv_firmware.set_state("V100R001C00SPC108B088F")
    pv_pv_strings.set_state(16)
    pv_output_type.set_state(3)
    pv_inverter = Inverter(
        plant_index=plant_index,
        device_address=pv_inverter_device_address,
        device_type=PVInverter(),
        model_id=pv_model.latest_raw_state,
        serial=pv_serial.latest_raw_state,
        firmware=pv_firmware.latest_raw_state,
        strings=pv_pv_strings.latest_raw_state,
        power_phases=3,
        pv_string_count=pv_pv_strings,
        output_type=pv_output_type,
        firmware_version=pv_firmware,
        model=pv_model,
        serial_number=pv_serial,
    )

    logging.debug(f"Instantiating DC Charger ({hass=})")
    dc_charger = DCCharger(plant_index, dc_charger_device_address, remote_ems)

    logging.debug(f"Instantiating AC Charger ({hass=})")
    rated_current = ACChargerRatedCurrent(plant_index, ac_charger_device_address)
    input_breaker = ACChargerInputBreaker(plant_index, ac_charger_device_address)
    ac_charger = ACCharger(plant_index, ac_charger_device_address, remote_ems, 1.0, 2.0, rated_current, input_breaker)

    sensor_count = {}
    sensor_instances = {}

    def find_concrete_classes(superclass):
        for c in superclass.__subclasses__():
            if c.__name__ != "ReservedSensor":
                if len(c.__subclasses__()) == 0:
                    if c.__name__ != "RequisiteSensor":
                        sensor_count[c.__name__] = 0
                else:
                    find_concrete_classes(c)

    def add_sensor_instance(s):
        if isinstance(s, ReservedSensor):
            return
        key = s.unique_id
        if key not in sensor_instances:
            sensor_instances[key] = s
        elif s.__class__.__name__ != sensor_instances[key].__class__.__name__:
            logging.warning(f"Register {key} in {s.__class__.__name__} already defined in {sensor_instances[key].__class__.__name__}")
        sensor_count[s.__class__.__name__] += 1
        for d in s._derived_sensors.values():
            add_sensor_instance(d)

    find_concrete_classes(Sensor)
    # add_sensor_instance(hybrid_model)
    # add_sensor_instance(hybrid_serial)
    # add_sensor_instance(pv_model)
    # add_sensor_instance(pv_serial)
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
    loop = asyncio.new_event_loop()
    loop.run_until_complete(get_sensor_instances())
    cancel_sensor_futures()
    loop.close()
