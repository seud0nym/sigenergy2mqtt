from typing import cast

import sigenergy2mqtt.sensors.inverter_read_only as ro
import sigenergy2mqtt.sensors.inverter_read_write as rw
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus import ModbusClient


class DCCharger(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        protocol_version: ProtocolVersion,
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
        protocol_version: ProtocolVersion,
        modbus_client: ModbusClient,
        sequence_number: int | None = None,
        total_count: int | None = None,
    ) -> "DCCharger":
        charger = cls(plant_index, device_address, protocol_version, sequence_number=sequence_number, total_count=total_count)
        await charger._register_sensors(plant_index, device_address, modbus_client)
        return charger

    async def _register_sensors(self, plant_index: int, device_address: int, modbus_client: ModbusClient) -> None:
        rated_charging_power = ro.DCChargerRatedChargingPower(plant_index, device_address)
        rated_discharging_power = ro.DCChargerRatedDischargingPower(plant_index, device_address)
        rcp_value = await rated_charging_power.get_state(modbus_client=modbus_client, raw=True)
        rdp_value = await rated_discharging_power.get_state(modbus_client=modbus_client, raw=True)

        self._add_sensor(ro.DCChargerOutputPower(plant_index, device_address))
        self._add_sensor(ro.DCChargerCurrentChargingCapacity(plant_index, device_address))
        self._add_sensor(ro.DCChargerCurrentChargingDuration(plant_index, device_address))
        self._add_sensor(ro.DCChargerVehicleBatteryVoltage(plant_index, device_address))
        self._add_sensor(ro.DCChargerVehicleChargingCurrent(plant_index, device_address))
        self._add_sensor(ro.DCChargerVehicleSoC(plant_index, device_address))
        self._add_sensor(ro.InverterAlarm5(plant_index, device_address))
        self._add_sensor(ro.DCChargerRunningState(plant_index, device_address))
        self._add_sensor(ro.DCChargerDischargingCurrent(plant_index, device_address))
        self._add_sensor(ro.DCChargerCurrentDischargingCapacity(plant_index, device_address))
        self._add_sensor(ro.DCChargerCurrentDischargingDuration(plant_index, device_address))
        self._add_sensor(ro.DCChargerTotalChargingCapacity(plant_index, device_address))
        self._add_sensor(ro.DCChargerTotalDischargingCapacity(plant_index, device_address))
        self._add_sensor(rated_charging_power)
        self._add_sensor(rated_discharging_power)

        self._add_sensor(rw.DCChargerStatus(plant_index, device_address))
        self._add_sensor(rw.DCChargerMaxChargingPowerLimit(plant_index, device_address, rated_charging_power=cast(float, rcp_value)))
        self._add_sensor(rw.DCChargerMaxDischargingPowerLimit(plant_index, device_address, rated_discharging_power=cast(float, rdp_value)))

        self._add_sensor(rw.Reserved41001(plant_index, device_address))
