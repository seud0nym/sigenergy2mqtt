from .base import (
    AlarmCombinedSensor,
    AlarmSensor,
    DeviceClass,
    InputType,
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
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.sensors.const import (
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)


# 5.3 Hybrid inverter running information address definition (read-only register)


class InverterModel(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Model",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_model",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30500,
            count=15,
            data_type=ModbusClient.DATATYPE.STRING,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"


class InverterSerialNumber(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Serial Number",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_serial_number",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30515,
            count=10,
            data_type=ModbusClient.DATATYPE.STRING,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"


class InverterFirmwareVersion(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Firmware Version",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_firmware_version",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30525,
            count=15,
            data_type=ModbusClient.DATATYPE.STRING,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if "device" in self and value is not None:
            # Firmware has been updated, so need to update the device and to republish discovery
            self.device["hw_version"] = value
        return value


class RatedActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30540,
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


class MaxRatedApparentPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Rated Apparent Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_rated_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30542,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class InverterMaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30544,
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


class MaxAbsorptionPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Absorption Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_absorption_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30546,
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


class RatedBatteryCapacity(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Battery Capacity",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_battery_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30548,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-high",
            gain=100,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class RatedChargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Charging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30550,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-positive",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class RatedDischargingPower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        self["entity_category"] = "diagnostic"
        super().__init__(
            name="Rated Discharging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30552,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-negative",
            gain=1000,
            precision=2,
        )


# region Reserved


class DailyExportEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Energy Exported",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_export_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30554,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
        )
        self._publishable = False  # 30554-30565 Marked as Reserved in v2.4 2025-02-05


class AccumulatedExportEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Energy Exported",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_export_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30556,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
        )
        self._publishable = False  # 30554-30565 Marked as Reserved in v2.4 2025-02-05


class DailyImportEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Energy Imported",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_import_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30560,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
        )
        self._publishable = False  # 30554-30565 Marked as Reserved in v2.4 2025-02-05


class AccumulatedImportEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Energy Imported",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_import_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30562,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
        )
        self._publishable = False  # 30554-30565 Marked as Reserved in v2.4 2025-02-05


# endregion


class DailyChargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Charge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30566,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class AccumulatedChargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Charge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30568,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class DailyDischargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Discharge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30572,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class AccumulatedDischargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Discharge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30574,
            count=4,
            data_type=ModbusClient.DATATYPE.UINT64,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class InverterRunningState(RunningStateSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running State",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_running_state",
            plant_index=plant_index,
            device_address=device_address,
            address=30578,
        )


class MaxActivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Active Power Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_active_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30579,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class MinActivePowerAdjustment(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Active Power Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_active_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30581,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class MaxReactivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Reactive Power Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_reactive_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30583,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class MinReactivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Reactive Power Adjustment",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_reactive_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30585,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class ActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Active Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30587,
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


class ReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30589,
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


class MaxBatteryChargePower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Charge Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_charge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30591,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-arrow-up",
            gain=1000,
            precision=2,
        )


class MaxBatteryDischargePower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Discharge Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_discharge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30593,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-arrow-down",
            gain=1000,
            precision=2,
        )


class AvailableBatteryChargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Available Charge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_available_battery_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30595,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-plus-variant",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class AvailableBatteryDischargeEnergy(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Available Discharge Energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_available_battery_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30597,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-minus-variant",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class ChargeDischargePower(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_charge_discharge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30599,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=5,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-charging-outline",
            gain=None,  # v1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class InverterBatterySoC(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30601,
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


class InverterBatterySoH(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery SoH",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_soh",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30602,
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


class AverageCellTemperature(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Average Cell Temperature",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_average_cell_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30603,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=10,
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class AverageCellVoltage(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Average Cell Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_average_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30604,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class InverterAlarm1(Alarm1Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PCS Alarms 1",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=30605,
        )


class InverterAlarm2(Alarm2Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PCS Alarms 2",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=30606,
        )


class InverterPCSAlarm(AlarmCombinedSensor):
    def __init__(self, plant_index: int, device_address: int, *alarms: AlarmSensor):
        super().__init__(
            "PCS Alarms",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pcs_alarm",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pcs_alarm",
            *alarms,
        )


class InverterAlarm3(Alarm3Sensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarms",  # ESS
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_3",
            plant_index=plant_index,
            device_address=device_address,
            address=30607,
        )


class InverterAlarm4(Alarm4Sensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Gateway Alarms",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_4",
            plant_index=plant_index,
            device_address=device_address,
            address=30608,
        )


class InverterAlarm5(Alarm5Sensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarms",  # DC Charger
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_5",
            plant_index=plant_index,
            device_address=device_address,
            address=30609,
        )


class InverterMaxBatteryTemperature(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Battery Temperature",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30620,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer-high",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class InverterMinBatteryTemperature(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Battery Temperature",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_battery_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30621,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer-low",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class InverterMaxCellVoltage(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Cell Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30622,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = True
        self.publishable = False  # 0x02 ILLEGAL DATA ADDRESS


class InverterMinCellVoltage(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Cell Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=30623,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = True
        self.publishable = False  # 0x02 ILLEGAL DATA ADDRESS


class RatedGridVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Grid Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_grid_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31000,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=600,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=10,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class RatedGridFrequency(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Grid Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_grid_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31001,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=600,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
        )
        self["entity_category"] = "diagnostic"


class GridFrequency(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Grid Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_grid_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31002,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
        )


class InverterTemperature(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Temperature",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31003,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
        )
        self["enabled_by_default"] = True


class OutputType(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Output Type",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_output_type",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31004,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:home-lightning-bolt",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        else:
            match value:
                case 0:
                    return "L/N"
                case 1:
                    return "L1/L2/L3"
                case 2:
                    return "L1/L2/L3/N"
                case 3:
                    return "L1/L2/N"
                case _:
                    return f"Unknown Output Type: {value}"

    async def get_power_phases(self, modbus: ModbusClient) -> int:
        value = await self.get_state(modbus=modbus, raw=True)
        match value:
            case 0:
                return 1
            case 3:
                return 2
            case _:
                return 3


class ABLineVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="A-B Line Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_a_b_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31005,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class BCLineVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="B-C Line Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_b_c_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31007,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class CALineVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="C-A Line Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_c_a_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31009,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class PhaseAVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # When Output Type is L/N, refers to “Phase Voltage”
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase A Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_a_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31011,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class PhaseBVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase B Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_b_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31013,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class PhaseCVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase C Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_c_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31015,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
        )


class PhaseACurrent(ReadOnlySensor, HybridInverter, PVInverter):
    # When Output Type is L/N, refers to “Phase Current”
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase A Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_a_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31017,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=100,
            precision=2,
        )


class PhaseBCurrent(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase B Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_b_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31019,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=100,
            precision=2,
        )


class PhaseCCurrent(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Phase C Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_c_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31021,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=60,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=100,
            precision=2,
        )


class PowerFactor(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Power Factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31023,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            state_class=None,
            icon="mdi:angle-acute",
            gain=1000,
            precision=2,
        )


class PACKBCUCount(ReadOnlySensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PACK/BCU Count",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pack_bcu_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31024,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:eye",
            gain=None,
            precision=None,
        )


class PVStringCount(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PV String Count",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv_string_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31025,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-panel",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"


class MPTTCount(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="MPTT Count",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_mptt_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31026,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=600,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-panel",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"


class InverterPVPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PV Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31035,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.WATT,  # UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # 1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class InsulationResistance(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Insulation Resistance",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_insulation_resistance",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31037,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit="MΩ",
            device_class=None,
            state_class=None,
            icon="mdi:omega",
            gain=1000,
            precision=2,
        )


class StartupTime(TimestampSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Startup Time",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_startup_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31038,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
        )


class ShutdownTime(TimestampSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Shutdown Time",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_shutdown_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31040,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
        )


# region DC Charger


class VehicleBatteryVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle Battery Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_vehicle_battery_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31500,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
        )


class VehicleChargingCurrent(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle Charging Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_vehicle_charging_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31501,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=2,
        )


class DCChargerOutputPower(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="DC Charger Output Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_dc_charger_output_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31502,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
        )


class VehicleSoC(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_vehicle_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31504,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
        )


class DCChargerCurrentChargingCapacity(ReadOnlySensor, HybridInverter, PVInverter):
    # Single time
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="DC Charger Current Charging Capacity",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_dc_charger_current_charging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31505,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
        )


class DCChargerCurrentChargingDuration(ReadOnlySensor, HybridInverter, PVInverter):
    # Single time
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="DC Charger Current Charging Duration",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_dc_charger_current_charging_duration",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=31507,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfTime.SECONDS,
            device_class=None,
            state_class=None,
            icon="mdi:car-clock",
            gain=1,
            precision=None,
        )


# endregion
