from typing import cast

import sigenergy2mqtt.sensors.ac_charger_read_only as ro
import sigenergy2mqtt.sensors.ac_charger_read_write as rw
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient


class ACCharger(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: Protocol,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ):
        multi_charger = (total_count or 0) > 1 and sequence_number is not None
        name = "Sigenergy AC Charger"
        sequence_suffix = f" {sequence_number}" if multi_charger else ""
        super().__init__(
            NonInverter(),
            name,
            plant_index,
            device_address,
            "AC Charger",
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
        modbus_client: ModbusClient,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ) -> "ACCharger":
        charger = cls(plant_index, device_address, protocol_version, sequence_number=sequence_number, total_count=total_count)
        await charger._register_sensors(plant_index, device_address, modbus_client)
        return charger

    async def _register_sensors(self, plant_index: int, device_address: int, modbus_client: ModbusClient) -> None:
        input_breaker = ro.ACChargerInputBreaker(plant_index, device_address)
        rated_current = ro.ACChargerRatedCurrent(plant_index, device_address)
        ib_value = await input_breaker.get_state(modbus_client=modbus_client)
        rc_value = await rated_current.get_state(modbus_client=modbus_client)

        self._add_read_sensor(ro.ACChargerRunningState(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerTotalEnergyConsumed(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerChargingPower(plant_index, device_address))
        self._add_read_sensor(ro.ACChargerRatedPower(plant_index, device_address))
        self._add_read_sensor(rated_current)
        self._add_read_sensor(ro.ACChargerRatedVoltage(plant_index, device_address))
        self._add_read_sensor(input_breaker)
        self._add_read_sensor(
            ro.ACChargerAlarms(
                plant_index,
                device_address,
                ro.ACChargerAlarm1(plant_index, device_address),
                ro.ACChargerAlarm2(plant_index, device_address),
                ro.ACChargerAlarm3(plant_index, device_address),
            )
        )
        self._add_read_sensor(rw.ACChargerOutputCurrent(plant_index, device_address, cast(float, ib_value), cast(float, rc_value)))

        self._add_writeonly_sensor(rw.ACChargerStatus(plant_index, device_address))
