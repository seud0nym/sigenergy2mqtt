import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice


class DCCharger(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
    ):
        name = "Sigenergy DC Charger" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} DC Charger"
        super().__init__(NonInverter(), name, plant_index, device_address, "DC Charger", protocol_version, translate=False)

    @classmethod
    async def create(cls, plant_index: int, device_address: int, protocol_version: Protocol) -> "DCCharger":
        charger = cls(plant_index, device_address, protocol_version)
        await charger._register_sensors(plant_index, device_address)
        return charger

    async def _register_sensors(self, plant_index: int, device_address: int) -> None:
        self._add_read_sensor(ro.DCChargerOutputPower(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingCapacity(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerCurrentChargingDuration(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleBatteryVoltage(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleChargingCurrent(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerVehicleSoC(plant_index, device_address))
        self._add_read_sensor(ro.InverterAlarm5(plant_index, device_address))
        self._add_read_sensor(ro.DCChargerRunningState(plant_index, device_address))

        self._add_writeonly_sensor(rw.DCChargerStatus(plant_index, device_address))
