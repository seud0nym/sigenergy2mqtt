from .device import ModbusDevice
from sigenergy2mqtt.config import Protocol
import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw


class DCCharger(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
    ):
        super().__init__(None, "Sigenergy DC Charger", plant_index, device_address, "DC Charger", protocol_version)

        self._add_read_sensor(ro.DCChargerOutputPower(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingCapacity(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingDuration(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleBatteryVoltage(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleChargingCurrent(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleSoC(plant_index, device_address))
        self._add_read_sensor(ro.InverterAlarm5(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerRunningState(plant_index, device_address))

        self._add_writeonly_sensor(rw.DCChargerStatus(plant_index, device_address))
