from typing import Any, Dict
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
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

    def state2raw(self, state) -> float | int | str:
        offset = state.replace("UTC", "")
        sign = 1 if offset[0] == "+" else -1
        hours, minutes = map(int, offset[1:].split(":"))
        total_minutes = sign * (hours * 60 + minutes)
        return int(total_minutes)


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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:pencil",
            gain=None,
            precision=None,
        )
        self["options"] = [
            "Max Self Consumption",  # 0
            "Sigen AI",  # 1
            "Time of Use",  # 2
            None,  # 3
            None,  # 4
            "Full Feed-in to Grid",  # 5
            None,  # 6
            "Remote EMS",  # 7
            None,  # 8
            "Time-Based Control",  # 9
        ]

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif 0 <= value <= (len(self["options"]) - 1) and self["options"][value] is not None:
            return self["options"][value]
        else:
            return f"Unknown Mode: {value}"


class GridSensorStatus(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True
        self["options"] = [
            "Not Connected",  # 0
            "Connected",  # 1
        ]

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif 0 <= value <= (len(self["options"]) - 1):
            return self["options"][value]
        else:
            return f"Unknown Status: {value}"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Gateway or meter connection status"
        return attributes


class GridSensorActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:transmission-tower",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True
        self._sanity.max_value = 100000  # 100kW
        self._sanity.min_value = -100000  # -100kW

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridSensorReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,  # UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=None,  # 1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True
        self["options"] = [
            "On Grid",  # 0
            "Off Grid (auto)",  # 1
            "Off Grid (manual)",  # 2
        ]

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif 0 <= value <= (len(self["options"]) - 1):
            return self["options"][value]
        else:
            return f"Unknown Status: {value}"


class MaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "This should be the base value of all active power adjustment actions"
        return attributes


class MaxApparentPower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "This should be the base value of all reactive power adjustment actions"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class PlantPhaseActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30015
            case "B":
                address = 30017
            case "C":
                address = 30019
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PlantPhaseReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30021
            case "B":
                address = 30023
            case "C":
                address = 30025
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class GeneralAlarm1(Alarm1Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__("PCS Alarms 1", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_1", plant_index, 247, 30027)

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralAlarm2(Alarm2Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__("PCS Alarms 2", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_2", plant_index, 247, 30028)

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralPCSAlarm(AlarmCombinedSensor):
    def __init__(self, plant_index: int, *alarms: AlarmSensor):
        super().__init__(
            "PCS Alarms",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_general_pcs_alarm",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_pcs_alarm",
            *alarms,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        attributes["source"] = "Modbus Registers 30027 and 30028"
        return attributes


class GeneralAlarm3(Alarm3Sensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__("ESS Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_3", plant_index, 247, 30029)

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralAlarm4(Alarm4Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__("Gateway Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_4", plant_index, 247, 30030)

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class BatteryPower(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "ESS Power: <0 = discharging >0 = charging"
        return attributes


class AvailableMaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Feed to the AC terminal. Count only the running inverters"
        return attributes


class AvailableMinActivePower(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class AvailableMaxReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Feed to the AC terminal. Count only the running inverters"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class AvailableMaxChargingPower(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-plus-outline",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


class AvailableMaxDischargingPower(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-minus-outline",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class PlantRunningState(RunningStateSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__("Running State", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_running_state", plant_index, 247, 30051)


class GridPhaseAActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridPhaseBActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridPhaseCActivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridPhaseAReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


class GridPhaseBReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


class GridPhaseCReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


class AvailableMaxChargingCapacity(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-plus",
            gain=100,
            precision=1,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


class AvailableMaxDischargingCapacity(ReadOnlySensor, HybridInverter):
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-minus",
            gain=100,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class GeneralAlarm5(Alarm5Sensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__("DC Charger Alarms", f"{Config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_5", plant_index, 247, 30072)

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


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
            scan_interval=Config.devices[plant_index].scan_interval.low if plant_index < len(Config.devices) else 600,
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
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
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-heart-variant",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "This value is the weighted average of the SOH of all ESS devices in the power plant, with each rated capacity as the weight"
        return attributes


class PlantPVTotalGeneration(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime PV Production",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_plant_lifetime_pv_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30088,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
        )


class TotalLoadDailyConsumption(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Daily Consumption",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_consumed_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30092,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:home-lightning-bolt-outline",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True
        self._sanity.min_value = None

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class TotalLoadConsumption(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Consumption",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_consumed_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30094,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:home-lightning-bolt-outline",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class SmartLoadTotalConsumption(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, address: int, smart_load_index: int):
        assert 1 <= smart_load_index <= 24, "smart_load_index must be between 1 and 24"
        super().__init__(
            name=f"Smart Load {smart_load_index:02} Total Consumption",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_smart_load_{smart_load_index:02}_total_consumption",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:lightning-bolt-circle",
            gain=100,
            precision=2,
        )


class SmartLoadPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, address: int, smart_load_index: int):
        assert 1 <= smart_load_index <= 24, "smart_load_index must be between 1 and 24"
        super().__init__(
            name=f"Smart Load {smart_load_index:02} Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_smart_load_{smart_load_index:02}_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt-outline",
            gain=1000,
            precision=2,
        )


class ThirdPartyPVPower(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Third-Party PV Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_third_party_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30194,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # 1000,
            precision=2,
        )


class ThirdPartyLifetimePVEnergy(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Third-Party PV Production",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_third_party_pv_lifetime_production",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30196,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
        )


class ESSTotalChargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Charge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30200,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_charge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class ESSTotalDischargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Discharge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30204,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_discharge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class EVDCTotalChargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime DC EV Charge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_evdc_total_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30208,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:ev-station",
            gain=100,
            precision=2,
        )


class EVDCTotalDischargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime DC EV Discharge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_evdc_total_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30212,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:ev-station",
            gain=100,
            precision=2,
        )


class PlantTotalImportedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Imported Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30216,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class PlantTotalExportedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Exported Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30220,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
            unique_id_override=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor
        return components


class PlantTotalGeneratorOutputEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Generator Output Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_plant_total_generator_output_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=30224,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:generator-stationary",
            gain=100,
            precision=2,
        )


# region New statistics interface (Modbus Protocol v2.7+)


class StatisticsInterfaceSensor(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        address: int,
        scan_interval: int,
        icon: str,
        input_type: InputType = InputType.INPUT,
        device_address: int = 247,
        count: int = 4,
        data_type: ModbusClient.DATATYPE = ModbusClient.DATATYPE.UINT64,
        unit: str = UnitOfEnergy.KILO_WATT_HOUR,
        device_class: DeviceClass = DeviceClass.ENERGY,
        state_class: StateClass = StateClass.TOTAL_INCREASING,
        gain: float = 100,
        precision: int = 2,
        unique_id_override: str = None,
    ):
        super().__init__(
            name=name,
            object_id=object_id,
            input_type=input_type,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=count,
            data_type=data_type,
            scan_interval=scan_interval,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
            unique_id_override=unique_id_override,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = (
            "After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data"
        )
        return attributes


class SITotalCommonLoadConsumption(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Common Load Consumption",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_common_load_consumption",
            plant_index=plant_index,
            address=30228,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:home-lightning-bolt-outline",
        )


class SITotalEVACChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total AC EV Charge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_si_total_ev_ac_charged_energy",
            plant_index=plant_index,
            address=30232,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            icon="mdi:ev-station",
        )


class SITotalSelfPVGeneration(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total PV Production",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_si_total_self_pv_generation",
            plant_index=plant_index,
            address=30236,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            icon="mdi:solar-power-variant",
        )


class SITotalThirdPartyPVGeneration(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Third-Party PV Production",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_si_total_third_party_pv_generation",
            plant_index=plant_index,
            address=30240,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            icon="mdi:solar-power-variant",
        )


class SITotalChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Charge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_charged_energy",
            plant_index=plant_index,
            address=30244,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:battery-arrow-up",
        )


class SITotalDischargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Discharge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_discharged_energy",
            plant_index=plant_index,
            address=30248,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:battery-arrow-down",
        )


class SITotalEVDCChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total DC EV Charge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_evdc_total_charge_energy",
            plant_index=plant_index,
            address=30252,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:ev-station",
        )


class SITotalEVDCDischargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total DC EV Discharge Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_evdc_total_discharge_energy",
            plant_index=plant_index,
            address=30256,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:ev-station",
        )


class SITotalImportedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Imported Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_imported_energy",
            plant_index=plant_index,
            address=30260,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:transmission-tower-import",
        )


class SITotalExportedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Exported Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_exported_energy",
            plant_index=plant_index,
            address=30264,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:transmission-tower-export",
        )


class SITotalGeneratorOutputEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Generator Output Energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_si_total_generator_output_energy",
            plant_index=plant_index,
            address=30268,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            icon="mdi:generator-stationary",
        )


# endregion
