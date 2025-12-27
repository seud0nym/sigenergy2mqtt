from .base import DeviceClass, InputType, NumericSensor, ReservedSensor, WriteOnlySensor
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.const import PERCENTAGE, UnitOfPower, UnitOfReactivePower


# 5.4 Hybrid inverter parameter setting address definition (holding register)


class InverterStatus(WriteOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Inverter Power On/Off",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_status",
            plant_index=plant_index,
            device_address=device_address,
            address=40500,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, any]:
        attributes = super().get_attributes()
        attributes["comment"] = "0:Stop 1:Start"
        return attributes


class ReservedGridCode(ReservedSensor, HybridInverter):  # 40501 Marked as Reserved in v2.7 2025-05-23
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Grid Code",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_grid_code",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=40501,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:earth",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )


class DCChargerStatus(WriteOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="DC Charger Stop/Start",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}",
            plant_index=plant_index,
            device_address=device_address,
            address=41000,
            protocol_version=Protocol.V1_8,
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


class ReservedInverterRemoteEMSDispatch(ReservedSensor, PVInverter):  # 41500 Marked as Reserved in v2.8 2025-11-20
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Remote EMS Dispatch",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_remote_ems_dispatch",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41500,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_5,
        )


class InverterActivePowerFixedValueAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Active Power Fixed Value Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power_fixed_value_adjustment",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41501,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
        )


class InverterReactivePowerFixedValueAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reactive Power Fixed Value Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power_fixed_value_adjustment",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41503,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
        )


class InverterActivePowerPercentageAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Active Power Percentage Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power_percentage_adjustment",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41505,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_5,
            minimum=-100.00,
            maximum=100.00,
        )


class InverterReactivePowerQSAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reactive Power Q/S Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power_q_s_adjustment",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41506,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_5,
            minimum=-60.0,
            maximum=60.0,
        )


class InverterPowerFactorAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Power Factor Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_power_factor_adjustment",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41507,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
            minimum=-1.0,
            maximum=1.0,
        )
