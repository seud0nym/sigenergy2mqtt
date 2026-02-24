from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusDataType

from .base import DeviceClass, InputType, NumericSensor, ScanInterval, StateClass, WriteOnlySensor
from .const import UnitOfElectricCurrent

# 5.6 AC-Charger parameter setting address definition (holding register)


class ACChargerStatus(WriteOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Stop/Start",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}",
            plant_index=plant_index,
            device_address=device_address,
            address=42000,
            protocol_version=Protocol.V2_0,
            payload_off="stop",
            payload_on="start",
            name_off="Stop",
            name_on="Start",
            icon_off="mdi:stop",
            icon_on="mdi:play",
            value_off=1,  # Values are inverted as per protocol to map to Home Assistant buttons
            value_on=0,  # Values are inverted as per protocol to map to Home Assistant buttons
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0:Start 1:Stop"
        return attributes


class ACChargerOutputCurrent(NumericSensor):
    # Range [6, X]
    # X is the smaller value between the rated current and the AC-Charger input breaker rated current.
    def __init__(
        self,
        plant_index: int,
        device_address: int,
        input_breaker: float,
        rated_current: float,
    ):
        super().__init__(
            availability_control_sensor=None,
            name="Output Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_output_current",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=42001,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
            minimum=6.0,
            maximum=min(input_breaker, rated_current),
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [6, smaller of 'AC-Charger Rated Current' and 'AC-Charger Input Breaker Rated Current']"
        return attributes
