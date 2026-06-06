from __future__ import annotations

import sigenergy2mqtt.sensors.plant_ess_preheating_read_write as rw
from sigenergy2mqtt.common import DeviceType, Protocol
from sigenergy2mqtt.devices import ModbusDevice


class ESSPreHeating(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant ESS Pre-Heating"
        plant_suffix = "" if plant_index == 0 else str(plant_index + 1)
        super().__init__(device_type, name, plant_index, 247, "ESS Pre-Heating", protocol_version, plant_suffix=plant_suffix)

    @classmethod
    async def create(cls, plant_index: int, device_type: DeviceType, rated_charging_power: float, rated_discharging_power: float, protocol_version: Protocol) -> "ESSPreHeating":
        ess_preheating = ESSPreHeating(plant_index, device_type, protocol_version)
        await ess_preheating._register_sensors(rated_charging_power, rated_discharging_power)
        return ess_preheating

    async def _register_sensors(self, rated_charging_power: float, rated_discharging_power: float) -> None:
        mode = rw.ESSPreHeatingMode(self.plant_index)
        self._add_sensor(rw.ESSPreHeatingEnable(self.plant_index))
        self._add_sensor(mode)
        self._add_sensor(rw.ESSPreHeatingAdvanceEnable(self.plant_index, mode))

        for tou_index in range(1, 31):
            start_address = 50003 + (tou_index - 1) * 6
            end_address = start_address + 2
            power_address = start_address + 4

            self._add_sensor(rw.ESSPreHeatingTOUTimeStart(self.plant_index, tou_index, start_address))
            self._add_sensor(rw.ESSPreHeatingTOUTimeEnd(self.plant_index, tou_index, end_address))
            self._add_sensor(rw.ESSPreHeatingTOUTargetPower(self.plant_index, tou_index, power_address, rated_charging_power, rated_discharging_power))

        self._add_sensor(rw.ESSPreHeatingReservedSOC(self.plant_index))
