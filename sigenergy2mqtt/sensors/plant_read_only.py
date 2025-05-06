from .base import (
    AlarmCombinedSensor,
    AlarmSensor,
    DeviceClass,
    InputType,
    PVPowerSensor,
    StateClass,
    Alarm1Sensor,
    Alarm2Sensor,
    Alarm3Sensor,
    Alarm4Sensor,
    Alarm5Sensor,
    ReadOnlySensor,
    RunningStateSensor,
    TimestampSensor,
)
from datetime import timedelta, timezone
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfReactivePower


# 5.1 Plant running information address definition(read-only register)


class SystemTime(TimestampSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="System Time",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_system_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30000,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
        )


class SystemTimeZone(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="System Time Zone",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_system_time_zone",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30002,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:map-clock",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if value is None:
            return None
        elif raw:
            return value
        else:
            offset = timedelta(minutes=value)
            tz = timezone(offset)
            formatted_offset = tz.tzname(None)
            return formatted_offset


class EMSWorkMode(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="EMS Work Mode",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_ems_work_mode",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30003,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:pencil",
            gain=None,
            precision=None,
        )

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif value == 0:
            return "Max Self Consumption"
        elif value == "1":
            return "Sigen AI Mode"
        elif value == "2":
            return "TOU"
        elif value == "7":
            return "Remote EMS Mode"
        else:
            return f"Unknown Mode: {value}"


class GridSensorStatus(ReadOnlySensor, HybridInverter, PVInverter):
    # Gateway or meter connection status
    def __init__(self, plant_index: int):
        super().__init__(
            name="Grid Sensor Status",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30004,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif value == 0:
            return "Not Connected"
        elif value == 1:
            return "Connected"
        else:
            return f"Unknown Status: {value}"


class GridSensorActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid
    def __init__(self, plant_index: int):
        super().__init__(
            name="Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30005,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:transmission-tower",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class GridSensorReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint;
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30007,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,  # UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=None,  # 1000,
            precision=2,
        )


class GridStatus(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Grid Status",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30009,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif value == 0:
            return "On Grid"
        elif value == 1:
            return "Off Grid (auto)"
        elif value == 2:
            return "Off Grid (manual)"
        else:
            return f"Unknown Status: {value}"


class MaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # This should be the base value of all active power adjustment actions
    def __init__(self, plant_index: int):
        super().__init__(
            name="Max Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30010,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class MaxApparentPower(ReadOnlySensor, HybridInverter, PVInverter):
    # This should be the base value of all reactive power adjustment actions
    def __init__(self, plant_index: int):
        super().__init__(
            name="Max Apparent Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30012,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class PlantBatterySoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30014,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class PlantPhaseAActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase A Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30015,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseBActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase B Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30017,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseCActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase C Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30019,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseAReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase A Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30021,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseBReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase B Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30023,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseCReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase C Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30025,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GeneralAlarm1(Alarm1Sensor, HybridInverter, PVInverter):
    # If any hybrid inverter has alarm, then this alarm will be set accordingly.
    def __init__(self, plant_index: int):
        super().__init__("PCS Alarms 1", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_1", plant_index, 247, 30027)


class GeneralAlarm2(Alarm2Sensor, HybridInverter, PVInverter):
    # If any hybrid inverter has alarm, then this alarm will be set accordingly.
    def __init__(self, plant_index: int):
        super().__init__("PCS Alarms 2", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_2", plant_index, 247, 30028)


class GeneralPCSAlarm(AlarmCombinedSensor):
    def __init__(self, plant_index: int, *alarms: AlarmSensor):
        super().__init__(
            "PCS Alarms",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_general_pcs_alarm",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_pcs_alarm",
            *alarms,
        )


class GeneralAlarm3(Alarm3Sensor, HybridInverter):
    # If any hybrid inverter has alarm, then this alarm will be set accordingly.
    def __init__(self, plant_index: int):
        super().__init__("ESS Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_3", plant_index, 247, 30029)


class GeneralAlarm4(Alarm4Sensor, HybridInverter, PVInverter):
    # If any hybrid inverter has alarm, then this alarm will be set accordingly.
    def __init__(self, plant_index: int):
        super().__init__("Gateway Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_4", plant_index, 247, 30030)


class PlantActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30031,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30033,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPVPower(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="PV Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30035,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class BatteryPower(ReadOnlySensor, HybridInverter):
    # ESS Power: <0 = discharging >0 = charging
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30037,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class AvailableMaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Feed to the AC terminal. Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30039,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class AvailableMinActivePower(ReadOnlySensor, HybridInverter):
    # Absorb from the AC terminal. Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Min Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_min_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30041,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class AvailableMaxReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Feed to the AC terminal. Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30043,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class AvailableMinReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Absorb from the AC terminal. Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Min Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_min_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30045,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class AvailableMaxChargingPower(ReadOnlySensor, HybridInverter):
    # Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Charging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30047,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-plus-outline",
            gain=1000,
            precision=2,
        )


class AvailableMaxDischargingPower(ReadOnlySensor, HybridInverter):
    # Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Discharging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30049,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-minus-outline",
            gain=1000,
            precision=2,
        )


class PlantRunningState(RunningStateSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__("Running State", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_running_state", plant_index, 247, 30051)


class GridPhaseAActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase A Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_a_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30052,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GridPhaseBActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase B Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_b_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30054,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GridPhaseCActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase C Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_c_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30056,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GridPhaseAReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase A Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_a_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30058,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GridPhaseBReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase B Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_b_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30060,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GridPhaseCReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    # Data collected from grid sensor at grid to system checkpoint
    def __init__(self, plant_index: int):
        super().__init__(
            name="Phase C Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_c_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30062,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class AvailableMaxChargingCapacity(ReadOnlySensor, HybridInverter):
    # Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Charging Capacity",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_charging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30064,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-plus",
            gain=100,
            precision=1,
        )


class AvailableMaxDischargingCapacity(ReadOnlySensor, HybridInverter):
    # Count only the running inverters
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Discharging Capacity",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_discharging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30066,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-minus",
            gain=100,
            precision=2,
        )


class PlantRatedChargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Charging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30068,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class PlantRatedDischargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Discharging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30070,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class GeneralAlarm5(Alarm5Sensor, HybridInverter):
    # If any hybrid inverter has alarm, then this alarm will be set accordingly.
    def __init__(self, plant_index: int):
        super().__init__("DC Charger Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_5", plant_index, 247, 30072)


class PlantRatedEnergyCapacity(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Energy Capacity",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_energy_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30083,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-charging",
            gain=100,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class ChargeCutOffSoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Charge Cut-Off SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_charge_cut_off_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30085,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:battery-charging-high",
            gain=10,
            precision=1,
        )


class DischargeCutOffSoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Discharge Cut-Off SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_discharge_cut_off_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30086,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:battery-charging-low",
            gain=10,
            precision=1,
        )


class PlantBatterySoH(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery SoH",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_soh",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30087,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-heart-variant",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True
