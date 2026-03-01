from typing import cast

import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw
from sigenergy2mqtt.common import DeviceType, Protocol
from sigenergy2mqtt.devices import ModbusDevice
from sigenergy2mqtt.modbus.types import ModbusClientType


class GridCode(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
    ):
        name = "Sigenergy Plant Grid Code" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Grid Code"
        super().__init__(device_type, name, plant_index, 247, "Grid Code", protocol_version)

    @classmethod
    async def create(cls, plant_index: int, device_type: DeviceType, protocol_version: Protocol, modbus_client: ModbusClientType) -> "GridCode":
        grid_code = GridCode(plant_index, device_type, protocol_version)
        await grid_code._register_sensors(modbus_client)
        return grid_code

    async def _register_sensors(self, modbus_client: ModbusClientType) -> None:
        rated_frequency = ro.GridCodeRatedFrequency(self.plant_index)
        rf_value = cast(float, await rated_frequency.get_state(modbus_client=modbus_client))

        self._add_read_sensor(rated_frequency)
        self._add_read_sensor(ro.GridCodeRatedVoltage(self.plant_index))

        self._add_read_sensor(rw.GridCodeLVRT(self.plant_index))
        self._add_read_sensor(rw.GridCodeLVRTReactivePowerCompensationFactor(self.plant_index))
        self._add_read_sensor(rw.GridCodeLVRTNegativeSequenceReactivePowerCompensationFactor(self.plant_index))
        self._add_read_sensor(rw.GridCodeLVRTMode(self.plant_index))
        self._add_read_sensor(rw.GridCodeLVRTVoltageProtectionBlocking(self.plant_index))
        self._add_read_sensor(rw.GridCodeHVRT(self.plant_index))
        self._add_read_sensor(rw.GridCodeHVRTReactivePowerCompensationFactor(self.plant_index))
        self._add_read_sensor(rw.GridCodeHVRTNegativeSequenceReactivePowerCompensationFactor(self.plant_index))
        self._add_read_sensor(rw.GridCodeHVRTMode(self.plant_index))
        self._add_read_sensor(rw.GridCodeHVRTVoltageProtectionBlocking(self.plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDerating(self.plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingPowerRampRate(self.plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingTriggerFrequency(self.plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingCutOffFrequency(self.plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoost(self.plant_index))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostPowerRampRate(self.plant_index))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostTriggerFrequency(self.plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostCutOffFrequency(self.plant_index, rf_value))
