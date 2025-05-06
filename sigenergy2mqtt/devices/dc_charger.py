from .device import ModBusDevice
from sigenergy2mqtt.sensors.base import RemoteEMSMixin
import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw


class DCCharger(ModBusDevice):
    def __init__(self, plant_index: int, device_address: int, remote_ems: RemoteEMSMixin):
        super().__init__(None, "Sigenergy DC Charger", plant_index, device_address, "DC Charger")

        # region read sensors
        self._add_read_sensor(ro.DCChargerOutputPower(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingCapacity(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingDuration(plant_index, device_address))
        self._add_read_sensor(ro.VehicleBatteryVoltage(plant_index, device_address))
        self._add_read_sensor(ro.VehicleChargingCurrent(plant_index, device_address))
        self._add_read_sensor(ro.VehicleSoC(plant_index, device_address))
        self._add_read_sensor(ro.InverterAlarm5(plant_index, device_address))
        # endregion

        self._add_writeonly_sensor(rw.DCChargerStatus(plant_index, device_address))
