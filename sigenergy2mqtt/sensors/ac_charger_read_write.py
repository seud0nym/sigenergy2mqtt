from .base import DeviceClass, InputType, StateClass, NumericSensor, WriteOnlySensor
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.sensors.const import UnitOfElectricCurrent


# 5.6 AC-Charger parameter setting address definition (holding register)


class ACChargerStatus(WriteOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Stop/Start",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}",
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
            value_off=1,
            value_on=0,
        )

    def get_attributes(self) -> dict[str, any]:
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
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_output_current",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=42001,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
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

    def get_attributes(self) -> dict[str, any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [6, smaller of 'AC-Charger Rated Current' and 'AC-Charger Input Breaker Rated Current']"
        return attributes
