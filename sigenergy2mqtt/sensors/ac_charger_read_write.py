from .base import DeviceClass, InputType, StateClass, NumericSensor, RemoteEMSMixin, WriteOnlySensor
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.const import UnitOfElectricCurrent


# 5.6 AC-Charger parameter setting address definition (holding register)


class ACChargerStatus(WriteOnlySensor):
    # 0:Stop 1:Start
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_status",
            plant_index=plant_index,
            device_address=device_address,
            address=42000,
        )
        self["icon"] = "mdi:ev-station"


class ACChargerOutputCurrent(NumericSensor):
    # Range [6, X]
    # X is the smaller value between the rated current and the AC-Charger input breaker rated current.
    def __init__(
        self,
        remote_ems: RemoteEMSMixin,
        plant_index: int,
        device_address: int,
        input_breaker: float,
        rated_current: float,
    ):
        super().__init__(
            remote_ems=remote_ems,
            name="Output Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_output_current",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=42001,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            min=6.0,
            max=min(input_breaker, rated_current),
        )
