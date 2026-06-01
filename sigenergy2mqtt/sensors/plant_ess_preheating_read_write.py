from __future__ import annotations

from abc import ABC, abstractmethod

from sigenergy2mqtt.common import PERCENTAGE, Constants, DeviceClass, HybridInverter, InputType, Protocol, UnitOfPower, UnitOfTime
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import NumericSensor, ScanInterval, SelectSensor, SwitchSensor


class ESSPreHeatingEnable(SwitchSensor, HybridInverter):
    ADDRESS = 50000

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Enable",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_enable",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Disable, 1: Enable"
        return attributes


class ESSPreHeatingMode(SelectSensor, HybridInverter):
    ADDRESS = 50001

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_mode",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            options=[
                "Automatic",  # 0
                "Manual",  # 1
            ],
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Automatic, 1: Manual"
        return attributes


class ESSPreHeatingAdvanceEnable(SwitchSensor, HybridInverter):
    ADDRESS = 50002

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Advance Enable",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_advance_enable",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0: Disable, 1: Enable. Takes effect when Preheating Mode is Manual."
        return attributes


class ESSPreHeatingTOUTime(NumericSensor, HybridInverter, ABC):
    def __init__(self, plant_index: int, tou_index: int, label: str, address: int):
        assert label in ("StartTime", "EndTime"), "label must be 'StartTime' or 'EndTime'"
        self.tou_index = tou_index
        super().__init__(
            availability_control_sensor=None,
            name=self._name,
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_tou_{tou_index}_{label.lower()}",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfTime.SECONDS,
            device_class=None,
            state_class=None,
            icon="mdi:clock-outline",
            gain=1,
            precision=0,
            protocol_version=Protocol.V2_9,
        )

    @property
    @abstractmethod
    def _name(self) -> str:
        pass

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Epoch seconds with timezone; local time interpretation depends on the device."
        return attributes


class ESSPreHeatingTOUTimeStart(ESSPreHeatingTOUTime):
    def __init__(self, plant_index: int, tou_index: int, address: int):
        super().__init__(plant_index, tou_index, "StartTime", address)

    @property
    def _name(self) -> str:
        return f"ESS Preheating TOU {self.tou_index} Start Time"


class ESSPreHeatingTOUTimeEnd(ESSPreHeatingTOUTime):
    def __init__(self, plant_index: int, tou_index: int, address: int):
        super().__init__(plant_index, tou_index, "EndTime", address)

    @property
    def _name(self) -> str:
        return f"ESS Preheating TOU {self.tou_index} End Time"


class ESSPreHeatingTOUTargetPower(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, tou_index: int, address: int):
        self.tou_index = tou_index
        super().__init__(
            availability_control_sensor=None,
            name=f"ESS Preheating TOU {tou_index} Target Charging/Discharging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_tou_{tou_index}_target_power",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "<0: discharging, >0: charging"
        return attributes


class ESSPreHeatingReservedSOC(NumericSensor, HybridInverter):
    ADDRESS = 50183

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Preheating Reserved SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ess_preheating_reserved_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_9,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes
