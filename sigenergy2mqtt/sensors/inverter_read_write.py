from .base import DeviceClass, InputType, NumericSensor, ReadOnlySensor, SwitchSensor, WriteOnlySensor
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.const import PERCENTAGE, UnitOfPower, UnitOfReactivePower


# 5.4 Hybrid inverter parameter setting address definition (holding register)


class InverterStatus(WriteOnlySensor, HybridInverter, PVInverter):
    # 0:Stop 1:Start
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_status",
            plant_index=plant_index,
            device_address=device_address,
            address=40500,
        )


class GridCode(ReadOnlySensor, HybridInverter):  # Seems like a dangerous thing to be able to change, so leave it read-only
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
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, modbus, raw=False, republish=False):
        value = await super().get_state(modbus=modbus, raw=raw, republish=republish)
        if raw:
            return value
        elif value is None:
            return None
        else:
            match value:
                case 1:
                    return "Germany"
                case 2:
                    return "UK"
                case 3:
                    return "Italy"
                case 4:
                    return "Spain"
                case 5:
                    return "Portugal"
                case 6:
                    return "France"
                case 7:
                    return "Poland"
                case 8:
                    return "Hungary"
                case 9:
                    return "Belgium"
                case 10:
                    return "Norway"
                case 11:
                    return "Sweden"
                case 12:
                    return "Finland"
                case 13:
                    return "Denmark"
                case 19:
                    return "Australia"
                case 26:
                    return "Austria"
                case 36:
                    return "Ireland"
                case _:
                    return f"Unknown Country Code {value}"


class DCChargerStatus(WriteOnlySensor, HybridInverter):
    # 0:Stop 1:Start
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="DC Charger Status",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_status",
            plant_index=plant_index,
            device_address=device_address,
            address=41000,
        )
        self["icon"] = "mdi:ev-station"


class InverterRemoteEMSDispatch(SwitchSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
            name="Remote EMS Dispatch",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_remote_ems_dispatch",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=41500,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=None,
        )


class InverterActivePowerFixedValueAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
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
        )


class InverterReactivePowerFixedValueAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
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
        )


class InverterActivePowerPercentageAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
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
            precision=2,
            min=-100.00,
            max=100.00,
        )


class InverterReactivePowerQSAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
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
            precision=2,
            min=-60.0,
            max=60.0,
        )


class InverterPowerFactorAdjustment(NumericSensor, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            remote_ems=None,
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
            min=-1.0,
            max=1.0,
        )
