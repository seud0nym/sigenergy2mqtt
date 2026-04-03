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
        sequence_number: int | None = None,
        total_count: int | None = None,
    ):
        multi_charger = (total_count or 0) > 1 and sequence_number is not None
        name = "Sigenergy DC Charger"
        sequence_suffix = str(sequence_number) if multi_charger else ""
        super().__init__(
            NonInverter(),
            name,
            plant_index,
            device_address,
            "DC Charger",
            protocol_version,
            sequence_number=sequence_number,
            sequence_suffix=sequence_suffix,
        )

    @classmethod
    async def create(
        cls,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ) -> "DCCharger":
        charger = cls(plant_index, device_address, protocol_version, sequence_number=sequence_number, total_count=total_count)
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
