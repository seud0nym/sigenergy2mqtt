from .device import ModbusDevice, DeviceType
from sigenergy2mqtt.config import Protocol
import sigenergy2mqtt.sensors.plant_read_only as ro
import sigenergy2mqtt.sensors.plant_read_write as rw


class GridCode(ModbusDevice):
    def __init__(
        self,
        plant_index: int,
        device_type: DeviceType,
        protocol_version: Protocol,
        rf_value: float,
        rated_frequency: ro.GridCodeRatedFrequency,
    ):
        name = "Sigenergy Plant Grid Code" if plant_index == 0 else f"Sigenergy Plant {plant_index + 1} Grid Code"
        super().__init__(device_type, name, plant_index, 247, "Grid Code", protocol_version)

        self._add_read_sensor(rated_frequency)
        self._add_read_sensor(ro.GridCodeRatedVoltage(plant_index))

        self._add_read_sensor(rw.GridCodeLVRT(plant_index))
        self._add_read_sensor(rw.GridCodeLVRTReactivePowerCompensationFactor(plant_index))
        self._add_read_sensor(rw.GridCodeLVRTNegativeSequenceReactivePowerCompensationFactor(plant_index))
        self._add_read_sensor(rw.GridCodeLVRTMode(plant_index))
        self._add_read_sensor(rw.GridCodeLVRTVoltageProtectionBlocking(plant_index))
        self._add_read_sensor(rw.GridCodeHVRT(plant_index))
        self._add_read_sensor(rw.GridCodeHVRTReactivePowerCompensationFactor(plant_index))
        self._add_read_sensor(rw.GridCodeHVRTNegativeSequenceReactivePowerCompensationFactor(plant_index))
        self._add_read_sensor(rw.GridCodeHVRTMode(plant_index))
        self._add_read_sensor(rw.GridCodeHVRTVoltageProtectionBlocking(plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDerating(plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingPowerRampRate(plant_index))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingTriggerFrequency(plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeOverFrequencyDeratingCutOffFrequency(plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoost(plant_index))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostPowerRampRate(plant_index))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostTriggerFrequency(plant_index, rf_value))
        self._add_read_sensor(rw.GridCodeUnderFrequencyPowerBoostCutOffFrequency(plant_index, rf_value))
