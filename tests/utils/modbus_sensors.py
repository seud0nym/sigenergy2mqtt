import asyncio
import logging
import os
import sys
from typing import cast

from sigenergy2mqtt.common import HybridInverter, PVInverter
from sigenergy2mqtt.devices import Device

os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from sigenergy2mqtt.common import Protocol, ProtocolApplies
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, EnergyDailyAccumulationSensor, ModbusSensorMixin, Sensor
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount, PVStringCount
from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedFrequency, PlantRatedChargingPower, PlantRatedDischargingPower


async def get_sensor_instances(
    hass: bool = False,
    plant_index: int = 0,
    protocol_version: Protocol | None = None,
    hybrid_inverter_device_address: int = 1,
    pv_inverter_device_address: int = 1,
    dc_charger_device_address: int = 1,
    ac_charger_device_address: int = 2,
    concrete_sensor_check: bool = True,
) -> dict[str, Sensor]:
    if protocol_version is None:
        protocol_version = list(Protocol)[-1]
    logging.info(f"Sigenergy Modbus Protocol V{protocol_version.value} [{ProtocolApplies(protocol_version)}] ({hass=})")

    Config.modbus[plant_index].dc_chargers.append(dc_charger_device_address)
    Config.modbus[plant_index].ac_chargers.append(ac_charger_device_address)

    Config.modbus[plant_index].smartport.enabled = True
    Config.modbus[plant_index].smartport.module.name = "enphase"
    Config.modbus[plant_index].smartport.module.pv_power = "EnphasePVPower"
    Config.modbus[plant_index].smartport.module.testing = True

    Config.home_assistant.enabled = hass

    hi = HybridInverter()
    hi.has_grid_code_interface = True
    hi.has_independent_phase_power_control_interface = True
    pv = PVInverter()
    pv.has_grid_code_interface = True
    pv.has_independent_phase_power_control_interface = True

    plant = PowerPlant(
        plant_index=plant_index,
        device_type=hi,
        protocol_version=protocol_version,
        output_type=2,
        power_phases=3,
        rcp_value=12.6,
        rdp_value=13.68,
        rf_value=50.0,
        rated_charging_power=PlantRatedChargingPower(plant_index),
        rated_discharging_power=PlantRatedDischargingPower(plant_index),
        rated_frequency=GridCodeRatedFrequency(plant_index),
    )
    remote_ems = plant.sensors[f"{Config.home_assistant.entity_id_prefix}_0_247_40029"]
    assert remote_ems is not None, "Failed to find RemoteEMS instance"

    hybrid_model = InverterModel(plant_index, hybrid_inverter_device_address)
    hybrid_serial = InverterSerialNumber(plant_index, hybrid_inverter_device_address)
    hybrid_firmware = InverterFirmwareVersion(plant_index, hybrid_inverter_device_address)
    hybrid_pv_strings = PVStringCount(plant_index, hybrid_inverter_device_address)
    hybrid_output_type = OutputType(plant_index, hybrid_inverter_device_address)
    hybrid_pack_bcu_count = PACKBCUCount(plant_index, hybrid_inverter_device_address)
    hybrid_model.set_state("SigenStor EC 12.0 TP")
    hybrid_serial.set_state("CMU123A45BP678")
    hybrid_firmware.set_state("V100R001C00SPC112B107G")
    hybrid_pv_strings.set_state(16)
    hybrid_output_type.set_state(3)
    hybrid_inverter = Inverter(
        plant_index=plant_index,
        device_address=hybrid_inverter_device_address,
        protocol_version=protocol_version,
        device_type=hi,
        model_id=cast(str, hybrid_model.latest_raw_state),
        serial=cast(str, hybrid_serial.latest_raw_state),
        firmware=cast(str, hybrid_firmware.latest_raw_state),
        battery_count=3,
        strings=cast(int, hybrid_pv_strings.latest_raw_state),
        power_phases=3,
        pv_string_count=hybrid_pv_strings,
        output_type=hybrid_output_type,
        firmware_version=hybrid_firmware,
        model=hybrid_model,
        serial_number=hybrid_serial,
        pack_bcu_count=hybrid_pack_bcu_count,
    )

    pv_model = InverterModel(plant_index, pv_inverter_device_address)
    pv_serial = InverterSerialNumber(plant_index, pv_inverter_device_address)
    pv_firmware = InverterFirmwareVersion(plant_index, pv_inverter_device_address)
    pv_pv_strings = PVStringCount(plant_index, pv_inverter_device_address)
    pv_output_type = OutputType(plant_index, pv_inverter_device_address)
    pv_pack_bcu_count = PACKBCUCount(plant_index, hybrid_inverter_device_address)
    pv_model.set_state("Sigen PV Max 5.0 TP")
    pv_serial.set_state("CMU876A65BP321")
    pv_firmware.set_state("V100R001C00SPC112B107G")
    pv_pv_strings.set_state(36)
    pv_output_type.set_state(3)
    pv_inverter = Inverter(
        plant_index=plant_index,
        device_address=pv_inverter_device_address,
        protocol_version=protocol_version,
        device_type=pv,
        model_id=cast(str, pv_model.latest_raw_state),
        serial=cast(str, pv_serial.latest_raw_state),
        firmware=cast(str, pv_firmware.latest_raw_state),
        battery_count=0,
        strings=cast(int, pv_pv_strings.latest_raw_state),
        power_phases=3,
        pv_string_count=pv_pv_strings,
        output_type=pv_output_type,
        firmware_version=pv_firmware,
        model=pv_model,
        serial_number=pv_serial,
        pack_bcu_count=pv_pack_bcu_count,
    )

    dc_charger = DCCharger(plant_index, dc_charger_device_address, protocol_version)

    input_breaker = ACChargerInputBreaker(plant_index, ac_charger_device_address)
    rated_current = ACChargerRatedCurrent(plant_index, ac_charger_device_address)
    ac_charger = ACCharger(plant_index, ac_charger_device_address, protocol_version, 16.0, 32.0, input_breaker, rated_current)

    classes: dict[str, int] = {}
    registers: dict[int, Sensor] = {}
    sensors: dict[str, Sensor] = {}

    def find_concrete_classes(superclass):
        for c in superclass.__subclasses__():
            if len(c.__subclasses__()) == 0:
                classes[c.__name__] = 0
            elif c.__name__ != "MetricsSensor":
                find_concrete_classes(c)

    def add_sensor_instance(s):
        key = s.unique_id
        if hasattr(s, "address"):
            if (
                s.address in registers
                and s.device_address == getattr(registers[s.address], "device_address", None)
                and s.__class__.__name__ != registers[s.address].__class__.__name__
                and not (isinstance(s, AlarmSensor) and isinstance(registers[s.address], AlarmCombinedSensor))
                and not (isinstance(s, AlarmCombinedSensor) and isinstance(registers[s.address], AlarmSensor))
            ):
                logging.warning(f"Register {s.address} in {s.__class__.__name__} already defined in {registers[s.address].__class__.__name__}")
            else:
                registers[s.address] = s
        if key not in sensors:
            sensors[key] = s
        elif s.__class__.__name__ != sensors[key].__class__.__name__:
            logging.warning(f"Register {key} in {s.__class__.__name__} already defined in {sensors[key].__class__.__name__}")
        classes[s.__class__.__name__] += 1
        for d in s._derived_sensors.values():
            add_sensor_instance(d)

    find_concrete_classes(Sensor)
    # add_sensor_instance(hybrid_model)
    # add_sensor_instance(hybrid_serial)
    # add_sensor_instance(pv_model)
    # add_sensor_instance(pv_serial)
    for parent in [plant, hybrid_inverter, dc_charger, ac_charger, pv_inverter]:
        devices: list[Device] = [parent]
        devices.extend(parent.children)
        for device in devices:
            for sensor in device.sensors.values():
                if isinstance(sensor, AlarmCombinedSensor):
                    add_sensor_instance(sensor)
                    for alarm in sensor.alarms:
                        add_sensor_instance(alarm)
                else:
                    add_sensor_instance(sensor)

    if concrete_sensor_check:
        previous: tuple[int, int] | None = None
        for address in sorted(registers.keys()):
            sensor = cast(ModbusSensorMixin, registers[address])
            count = sensor.count
            if previous:
                last_address, last_count = previous
                if address not in (30500, 31000, 31500, 32000, 40000, 40500, 41000, 41500, 42000) and last_address + last_count < address:
                    logging.warning(
                        f"Gap detected between register {last_address} (count={last_count} class={registers[last_address].__class__.__name__}) and register {address} (class={registers[address].__class__.__name__})"
                    )
            for i in range(address + 1, address + count):
                if i in registers:
                    logging.warning(f"Register {i} in {sensor.__class__.__name__} overlaps {registers[i].__class__.__name__}")
            previous = (address, count)
        for classname, count in classes.items():
            if count == 0:
                logging.warning(f"Class {classname} has not been used?")

    return sensors


def cancel_sensor_futures():
    for future in EnergyDailyAccumulationSensor.futures:
        future.cancel()


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.DEBUG)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(get_sensor_instances())
    cancel_sensor_futures()
    loop.close()
