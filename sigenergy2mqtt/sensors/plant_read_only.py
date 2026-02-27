from datetime import timedelta, timezone
from typing import cast

from sigenergy2mqtt.common import Constants, HybridInverter, Protocol, PVInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import DiscoveryKeys, ScanInterval

from .base import (
    Alarm1Sensor,
    Alarm2Sensor,
    Alarm3Sensor,
    Alarm4Sensor,
    Alarm5Sensor,
    AlarmCombinedSensor,
    AlarmSensor,
    DeviceClass,
    InputType,
    PVPowerSensor,
    ReadOnlySensor,
    ReservedSensor,
    RunningStateSensor,
    StateClass,
    TimestampSensor,
    UnpublishResetSensorMixin,
)
from .const import PERCENTAGE, UnitOfApparentPower, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfReactivePower

# 5.1 Plant running information address definition(read-only register)


class SystemTime(TimestampSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="System Time",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_system_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30000,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V1_8,
        )


class SystemTimeZone(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="System Time Zone",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_system_time_zone",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30002,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:map-clock",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if value is None:
            return None
        elif raw:
            return value
        elif isinstance(value, (float, int)):
            offset = timedelta(minutes=value)
            tz = timezone(offset)
            formatted_offset = tz.tzname(None)
            return formatted_offset
        else:
            return None

    def state2raw(self, state) -> float | int | str:
        if isinstance(state, str):
            offset = state.replace("UTC", "")
            if not offset:
                return 0
            sign = 1 if offset[0] == "+" else -1
            hours, minutes = map(int, offset[1:].split(":"))
            return sign * (hours * 60 + minutes)
        return int(state)


class EMSWorkMode(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="EMS Work Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_ems_work_mode",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30003,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:pencil",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self[DiscoveryKeys.OPTIONS] = [
            "Max Self Consumption",  # 0
            "Sigen AI",  # 1
            "Time of Use",  # 2
            "",  # 3
            "",  # 4
            "Full Feed-in to Grid",  # 5
            "VPP Scheduling",  # 6 (https://github.com/TypQxQ/Sigenergy-Local-Modbus/pull/289)
            "Remote EMS",  # 7
            "",  # 8
            "Time-Based Control",  # 9
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1  # pyrefly: ignore

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            else:
                return f"Unknown Mode: {value}"
        else:
            return f"Unknown Mode: {value}"


class GridSensorStatus(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Grid Sensor Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30004,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self[DiscoveryKeys.OPTIONS] = [
            "Not Connected",  # 0
            "Connected",  # 1
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1  # pyrefly: ignore

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)):
            return self._get_option(int(value)) or f"Unknown Status: {value}"
        else:
            return f"Unknown Status: {value}"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Gateway or meter connection status"
        return attributes


class GridSensorActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30005,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:transmission-tower",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.max_raw = 100000  # 100kW
        self.sanity_check.min_raw = -100000  # -100kW

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridSensorReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_sensor_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30007,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,  # Consistent with GridSensorActivePower
            device_class=None,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=None,  # Consistent with GridSensorActivePower
            precision=2,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


class GridStatus(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Grid Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30009,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self[DiscoveryKeys.OPTIONS] = [
            "On Grid",  # 0
            "Off Grid (auto)",  # 1
            "Off Grid (manual)",  # 2
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1  # pyrefly: ignore

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)):
            return self._get_option(int(value)) or f"Unknown Status: {value}"
        else:
            return f"Unknown Status: {value}"


class MaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Max Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30010,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "This should be the base value of all active power adjustment actions"
        return attributes


class MaxApparentPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Max Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30012,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "This should be the base value of all reactive power adjustment actions"
        return attributes


class PlantBatterySoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30014,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class PlantPhaseActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, power_phases: int, phase: str):
        match phase:
            case "A":
                address = 30015
            case "B":
                address = 30017
            case "C":
                address = 30019
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        phase_label = f" {phase}" if power_phases > 1 else ""
        phase_slug = phase.lower()
        super().__init__(
            name=f"Phase{phase_label} Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase_slug}_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )


class PlantPhaseReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, power_phases: int, phase: str):
        match phase:
            case "A":
                address = 30021
            case "B":
                address = 30023
            case "C":
                address = 30025
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        phase_label = f" {phase}" if power_phases > 1 else ""
        phase_slug = phase.lower()
        super().__init__(
            name=f"Phase{phase_label} Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase_slug}_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )


class GeneralAlarm1(Alarm1Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "PCS Alarms 1",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_1",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30027,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralAlarm2(Alarm2Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "PCS Alarms 2",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_2",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30028,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralPCSAlarm(AlarmCombinedSensor):
    def __init__(self, plant_index: int, *alarms: AlarmSensor):
        super().__init__(
            "PCS Alarms",
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_general_pcs_alarm",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_pcs_alarm",
            *alarms,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralAlarm3(Alarm3Sensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "ESS Alarms",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_3",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30029,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class GeneralAlarm4(Alarm4Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "Gateway Alarms",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_4",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30030,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class PlantActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30031,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class PlantReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30033,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class PlantPVPower(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="PV Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30035,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class BatteryPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30037,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-battery-outline",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "ESS Power: <0 = discharging >0 = charging"
        return attributes


class AvailableMaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30039,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Feed to the AC terminal. Count only the running inverters"
        return attributes


class AvailableMinActivePower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Min Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_min_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30041,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class AvailableMaxReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30043,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Feed to the AC terminal. Count only the running inverters"
        return attributes


class AvailableMinReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Min Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_min_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30045,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class AvailableMaxChargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Charging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30047,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-plus-outline",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


class AvailableMaxDischargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Discharging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30049,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-minus-outline",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Absorb from the AC terminal. Count only the running inverters"
        return attributes


class PlantRunningState(RunningStateSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "Running State",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_running_state",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30051,
            protocol_version=Protocol.V1_8,
        )


class GridPhaseActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30052
            case "B":
                address = 30054
            case "C":
                address = 30056
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_{phase.lower()}_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint; >0 buy from grid; <0 sell to grid"
        return attributes


class GridPhaseReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30058
            case "B":
                address = 30060
            case "C":
                address = 30062
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_{phase.lower()}_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Data collected from grid sensor at grid to system checkpoint"
        return attributes


class AvailableMaxChargingCapacity(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Charging Capacity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_charging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30064,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-plus",
            gain=100,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


class AvailableMaxDischargingCapacity(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Available Max Discharging Capacity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_available_max_discharging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30066,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-minus",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Count only the running inverters"
        return attributes


class PlantRatedChargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Charging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30068,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class PlantRatedDischargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Discharging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30070,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class GeneralAlarm5(Alarm5Sensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            "DC Charger Alarms",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_alarm_5",
            plant_index,
            Constants.PLANT_DEVICE_ADDRESS,
            30072,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "If any hybrid inverter has alarm, then this alarm will be set accordingly"
        return attributes


class Reserved30073(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reserved",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_reserved_30073",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30073,
            count=10,
            data_type=ModbusDataType.STRING,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:comment-question",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_5,
        )


class PlantRatedEnergyCapacity(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Energy Capacity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_rated_energy_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30083,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-charging",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_5,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class ChargeCutOffSoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Charge Cut-Off SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_charge_cut_off_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30085,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:battery-charging-high",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_5,
        )


class DischargeCutOffSoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Discharge Cut-Off SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_discharge_cut_off_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30086,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:battery-charging-low",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_5,
        )


class PlantBatterySoH(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Battery SoH",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_battery_soh",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30087,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-heart-variant",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_5,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "This value is the weighted average of the SOH of all ESS devices in the power plant, with each rated capacity as the weight"
        return attributes


class PlantPVTotalGeneration(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime PV Production",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_plant_lifetime_pv_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30088,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
        )


class TotalLoadDailyConsumption(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Daily Consumption",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30092,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:home-lightning-bolt-outline",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
            unique_id_override=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = None


class TotalLoadConsumption(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Consumption",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30094,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:home-lightning-bolt-outline",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_consumed_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class SmartLoadTotalConsumption(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, address: int, smart_load_index: int):
        assert 1 <= smart_load_index <= 24, "smart_load_index must be between 1 and 24"
        super().__init__(
            name=f"Smart Load {smart_load_index:02} Total Consumption",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_smart_load_{smart_load_index:02}_total_consumption",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:lightning-bolt-circle",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
            smart_load_index=f"{smart_load_index:02}",
        )


class SmartLoadPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, address: int, smart_load_index: int):
        assert 1 <= smart_load_index <= 24, "smart_load_index must be between 1 and 24"
        super().__init__(
            name=f"Smart Load {smart_load_index:02} Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_smart_load_{smart_load_index:02}_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:lightning-bolt-outline",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_6,
            smart_load_index=f"{smart_load_index:02}",
        )


class ThirdPartyPVPower(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Third-Party PV Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_third_party_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30194,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V2_7,
        )


class ThirdPartyLifetimePVEnergy(ReadOnlySensor, PVPowerSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Third-Party PV Production",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_third_party_pv_lifetime_production",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30196,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
        )


class ESSTotalChargedEnergy(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Charge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_charge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30200,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_charge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class ESSTotalDischargedEnergy(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Discharge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_discharge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30204,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_discharge_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class EVDCTotalChargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime DC EV Charge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_evdc_total_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30208,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:ev-station",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
        )


class EVDCTotalDischargedEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime DC EV Discharge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_evdc_total_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30212,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:ev-station",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
        )


class PlantTotalImportedEnergy(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Imported Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30216,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class PlantTotalExportedEnergy(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Exported Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30220,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class PlantTotalGeneratorOutputEnergy(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Generator Output Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_plant_total_generator_output_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30224,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:generator-stationary",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
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
    ):
        super().__init__(
            name=name,
            object_id=object_id,
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=scan_interval,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon=icon,
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_7,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "After upgrading the device firmware to support the new Statistics Interface, the register values will reset to 0 and start fresh counting without inheriting historical data"
        return attributes


class SITotalCommonLoadConsumption(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Common Load Consumption",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_common_load_consumption",
            plant_index=plant_index,
            address=30228,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:home-lightning-bolt-outline",
        )


class SITotalEVACChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total AC EV Charge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_si_total_ev_ac_charged_energy",
            plant_index=plant_index,
            address=30232,
            scan_interval=ScanInterval.high(plant_index),
            icon="mdi:ev-station",
        )


class SITotalSelfPVGeneration(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total PV Production",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_si_total_self_pv_generation",
            plant_index=plant_index,
            address=30236,
            scan_interval=ScanInterval.high(plant_index),
            icon="mdi:solar-power-variant",
        )


class SITotalThirdPartyPVGeneration(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Third-Party PV Production",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_si_total_third_party_pv_generation",
            plant_index=plant_index,
            address=30240,
            scan_interval=ScanInterval.high(plant_index),
            icon="mdi:solar-power-variant",
        )


class SITotalChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Charge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_charged_energy",
            plant_index=plant_index,
            address=30244,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:battery-arrow-up",
        )


class SITotalDischargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Discharge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_discharged_energy",
            plant_index=plant_index,
            address=30248,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:battery-arrow-down",
        )


class SITotalEVDCChargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total DC EV Charge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_evdc_total_charge_energy",
            plant_index=plant_index,
            address=30252,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:ev-station",
        )


class SITotalEVDCDischargedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total DC EV Discharge Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_evdc_total_discharge_energy",
            plant_index=plant_index,
            address=30256,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:ev-station",
        )


class SITotalImportedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Imported Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_imported_energy",
            plant_index=plant_index,
            address=30260,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:transmission-tower-import",
        )


class SITotalExportedEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Exported Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_exported_energy",
            plant_index=plant_index,
            address=30264,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:transmission-tower-export",
        )


class SITotalGeneratorOutputEnergy(StatisticsInterfaceSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Generator Output Energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_si_total_generator_output_energy",
            plant_index=plant_index,
            address=30268,
            scan_interval=ScanInterval.medium(plant_index),
            icon="mdi:generator-stationary",
        )


# endregion


class ReservedPVTotalGenerationToday(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="PV Total Generation Today",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pv_total_generation_today",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30272,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-power-variant",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_8,
        )


class ReservedPVTotalGenerationYesterday(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="PV Total Generation Yesterday",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pv_total_generation_yesterday",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30274,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-power-variant",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_8,
        )


class GridCodeRatedFrequency(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_rated_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30276,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class GridCodeRatedVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Rated Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_rated_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30277,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class CurrentControlCommandValue(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Current Control Command Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_current_control_command_value",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30279,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Use of Remote Output Control in Japan"
        return attributes


class Alarm6(AlarmSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Alarm 6",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_merged_alarm_6",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30280,
            alarm_type="Plant",
            protocol_version=Protocol.V2_8,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Gateway communication abnormal"
            case 1:
                return "Meter communication abnormal"
            case 2:
                return "AC power sensor communication abnormal"
            case 6:
                return "Hard protection against grid-feed power limit exceeding"
            case 8:
                return "Generator failure to start"
            case 10:
                return "CLS fault"
            case _:
                return None


class Alarm7(AlarmSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Alarm 7",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_merged_alarm_7",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30281,
            alarm_type="Plant",
            protocol_version=Protocol.V2_8,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "OVGR fault"
            case 1:
                return "RPR Fault"
            case _:
                return None


class PlantAlarms(AlarmCombinedSensor):
    def __init__(self, plant_index: int, *alarms: AlarmSensor):
        super().__init__(
            "Plant Alarms",
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_plant_alarms",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_alarms",
            *alarms,
        )


class GeneralLoadPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="General Load Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_general_load_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30282,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:meter-electric-outline",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V2_8,
        )


class TotalLoadPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Total Load Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_total_load_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=30284,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:meter-electric",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V2_8,
        )


class ReservedGridPhaseVoltage(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30286
            case "B":
                address = 30288
            case "C":
                address = 30290
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_{phase.lower()}_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_8,
            phase=phase,
        )


class ReservedGridPhaseCurrent(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, phase: str):
        match phase:
            case "A":
                address = 30292
            case "B":
                address = 30294
            case "C":
                address = 30296
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            name=f"Phase {phase} Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_phase_{phase.lower()}_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_8,
            phase=phase,
        )
