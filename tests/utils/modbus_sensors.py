import asyncio
import logging
import os
import sys
from typing import cast

from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.pdu import ModbusPDU

os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sigenergy2mqtt.common import HybridInverter, Protocol, ProtocolApplies, PVInverter
from sigenergy2mqtt.config import active_config, initialize
from sigenergy2mqtt.devices import ACCharger, DCCharger, Device, Inverter, PowerPlant
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent, ACChargerRunningState
from sigenergy2mqtt.sensors.ac_charger_read_write import ACChargerStatus
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, ModbusSensorMixin, Sensor
from sigenergy2mqtt.sensors.inverter_read_only import DCChargerVehicleBatteryVoltage, InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount, PVStringCount, RatedGridVoltage
from sigenergy2mqtt.sensors.inverter_read_write import DCChargerStatus, InverterStatus, ReservedInverterRemoteEMSDispatch
from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedFrequency, PlantRatedChargingPower, PlantRatedDischargingPower
from sigenergy2mqtt.sensors.plant_read_write import PlantStatus

initialize()

FIRMWARE_VERSION: str = "V100R001C00SPC112B107G"
INPUT_BREAKER: float = 16.0
OUTPUT_TYPE: int = 2
PACK_BCU_COUNT: int = 3
PV_STRING_COUNT: int = 36
RATED_CHARGING_POWER: float = 12.6
RATED_CURRENT: float = 32.0
RATED_DISCHARGING_POWER: float = 13.68
RATED_FREQUENCY: float = 50.0


class DummyModbusClient(ModbusClientMixin):
    def __init__(self, model_id: str, serial_number: str):
        rated_charging_power = PlantRatedChargingPower(0)
        rated_discharging_power = PlantRatedDischargingPower(0)
        rated_frequency = GridCodeRatedFrequency(0)

        model = InverterModel(0, 1)
        serial = InverterSerialNumber(0, 1)
        firmware = InverterFirmwareVersion(0, 1)
        pv_strings = PVStringCount(0, 1)
        output_type = OutputType(0, 1)
        pack_bcu_count = PACKBCUCount(0, 1)

        input_breaker = ACChargerInputBreaker(0, 1)
        rated_current = ACChargerRatedCurrent(0, 1)

        self.data = {
            rated_charging_power.address: self.convert_to_registers(rated_charging_power.state2raw(RATED_CHARGING_POWER), rated_charging_power.data_type),
            rated_discharging_power.address: self.convert_to_registers(rated_discharging_power.state2raw(RATED_DISCHARGING_POWER), rated_discharging_power.data_type),
            rated_frequency.address: self.convert_to_registers(rated_frequency.state2raw(RATED_FREQUENCY), rated_frequency.data_type),
            model.address: self.convert_to_registers(model_id, model.data_type),
            serial.address: self.convert_to_registers(serial_number, serial.data_type),
            firmware.address: self.convert_to_registers(FIRMWARE_VERSION, firmware.data_type),
            pv_strings.address: self.convert_to_registers(pv_strings.state2raw(PV_STRING_COUNT), pv_strings.data_type),
            output_type.address: self.convert_to_registers(output_type.state2raw(OUTPUT_TYPE), output_type.data_type),  # 2 = 3-phase (L1/L2/L3/N)
            pack_bcu_count.address: self.convert_to_registers(pack_bcu_count.state2raw(PACK_BCU_COUNT), pack_bcu_count.data_type),
            input_breaker.address: self.convert_to_registers(input_breaker.state2raw(INPUT_BREAKER), input_breaker.data_type),
            rated_current.address: self.convert_to_registers(rated_current.state2raw(RATED_CURRENT), rated_current.data_type),
        }

    def get_state(self, address: int, device_id: int) -> ModbusPDU:
        result = self.data.get(address, None)
        if result is None:
            raise ValueError(f"Unknown address {address}")
        return ModbusPDU(registers=result)

    async def read_holding_registers(self, address: int, count: int, device_id: int, trace: bool = False) -> ModbusPDU:
        return self.get_state(address, device_id)

    async def read_input_registers(self, address: int, count: int, device_id: int, trace: bool = False) -> ModbusPDU:
        return self.get_state(address, device_id)


async def get_sensor_instances(
    hass: bool = False,
    plant_index: int = 0,
    hybrid_inverter_device_address: int = 1,
    pv_inverter_device_address: int = 1,
    dc_charger_device_address: int = 1,
    ac_charger_device_address: int = 2,
    protocol_version: Protocol | None = None,
    concrete_sensor_check: bool = True,
) -> dict[str, Sensor]:
    if protocol_version is None:
        protocol_version = list(Protocol)[-1]
    logging.info(f"Sigenergy Modbus Protocol V{protocol_version.value} [{ProtocolApplies(protocol_version)}] ({hass=})")

    if len(active_config.modbus) <= plant_index:
        active_config.reload()

    active_config.modbus[plant_index].dc_chargers.append(dc_charger_device_address)
    active_config.modbus[plant_index].ac_chargers.append(ac_charger_device_address)

    active_config.modbus[plant_index].smartport.enabled = True
    active_config.modbus[plant_index].smartport.module.name = "enphase"
    active_config.modbus[plant_index].smartport.module.pv_power = "EnphasePVPower"
    active_config.modbus[plant_index].smartport.module.testing = True

    active_config.home_assistant.enabled = hass
    active_config.influxdb.enabled = True

    hi_device_type = HybridInverter(has_grid_code_interface=True, has_independent_phase_power_control_interface=True)
    hi_modbus_client = DummyModbusClient("SigenStor EC 12.0 TP", "CMU123A45BP678")
    pv_device_type = PVInverter(has_grid_code_interface=True, has_independent_phase_power_control_interface=True)
    pv_modbus_client = DummyModbusClient("Sigen PV Max 5.0 TP", "CMU876A54BP321")

    plant = await PowerPlant.create(plant_index, hi_device_type, protocol_version, OUTPUT_TYPE, hi_modbus_client)
    hybrid_inverter = await Inverter.create(plant_index, hybrid_inverter_device_address, hi_device_type, protocol_version, hi_modbus_client)
    pv_inverter = await Inverter.create(plant_index, pv_inverter_device_address, pv_device_type, protocol_version, pv_modbus_client)
    dc_charger = await DCCharger.create(plant_index, dc_charger_device_address, protocol_version)
    ac_charger = await ACCharger.create(plant_index, ac_charger_device_address, protocol_version, hi_modbus_client)

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
        for d in s.derived_sensors.values():
            add_sensor_instance(d)

    find_concrete_classes(Sensor)
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
                if (
                    address
                    not in (
                        InverterModel.ADDRESS,  # 31000
                        RatedGridVoltage.ADDRESS,  # 31500
                        DCChargerVehicleBatteryVoltage.ADDRESS,  # 32000
                        ACChargerRunningState.ADDRESS,  # 32000
                        PlantStatus.ADDRESS,  # 40000
                        InverterStatus.ADDRESS,  # 40500
                        DCChargerStatus.ADDRESS,  # 41000
                        ReservedInverterRemoteEMSDispatch.ADDRESS,  # 41500
                        ACChargerStatus.ADDRESS,  # 42000
                    )
                    and last_address + last_count < address
                ):
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


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(get_sensor_instances())
    loop.close()
