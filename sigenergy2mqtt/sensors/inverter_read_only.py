import logging
import math
import time
from typing import cast

from sigenergy2mqtt.common import (
    PERCENTAGE,
    DeviceClass,
    HybridInverter,
    InputType,
    Protocol,
    PVInverter,
    StateClass,
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
from sigenergy2mqtt.common.firmware_version import FirmwareVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import DiscoveryKeys, ScanInterval, UnpublishResetSensorMixin

from .base import (
    Alarm1Sensor,
    Alarm2Sensor,
    Alarm3Sensor,
    Alarm4Sensor,
    Alarm5Sensor,
    AlarmCombinedSensor,
    AlarmSensor,
    ReadOnlySensor,
    ReservedSensor,
    RunningStateSensor,
    TimestampSensor,
)

# 5.3 Hybrid inverter running information address definition (read-only register)


class InverterModel(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Model",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_model",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=15,
            data_type=ModbusDataType.STRING,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class InverterSerialNumber(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30515

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Serial Number",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_serial_number",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=10,
            data_type=ModbusDataType.STRING,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class InverterFirmwareVersion(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30525

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Firmware Version",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_firmware_version",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=15,
            data_type=ModbusDataType.STRING,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:text-short",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if value is not None:
            device = getattr(self, "parent_device", None)
            if device and device["hw"] != value:
                logging.info(f"{device.name} firmware change detected: {device['hw']} -> {value} (device_address={device.device_address})")
                try:
                    previous_version = FirmwareVersion(device["hw"])
                    current_version = FirmwareVersion(cast(str, value))
                    if previous_version.service_pack != current_version.service_pack:
                        from sigenergy2mqtt.main import restart_controller

                        restart_controller.request(f"firmware service pack change on inverter {device.device_address}")
                except ValueError:
                    logging.debug(f"Unable to parse firmware versions for restart decision: old={device['hw']} new={value}")
                device["hw"] = value
        return value


class RatedActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30540

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class MaxRatedApparentPower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30542

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Rated Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_rated_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class InverterMaxActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30544

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class MaxAbsorptionPower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30546

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Absorption Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_absorption_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class RatedBatteryCapacity(ReadOnlySensor, HybridInverter):
    ADDRESS = 30548

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Battery Capacity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_battery_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-high",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["entity_category"] = "diagnostic"


class RatedChargingPower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30550

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Charging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-positive",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class RatedDischargingPower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30552

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Discharging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_discharging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-negative",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class ReservedDailyExportEnergy(ReservedSensor, HybridInverter):  # 30554-30565 Marked as Reserved in v2.4 2025-02-05
    ADDRESS = 30554

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Energy Exported",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_export_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class ReservedAccumulatedExportEnergy(ReservedSensor, HybridInverter):  # 30554-30565 Marked as Reserved in v2.4 2025-02-05
    ADDRESS = 30556

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Energy Exported",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_export_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-export",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class ReservedDailyImportEnergy(ReservedSensor, HybridInverter):  # 30554-30565 Marked as Reserved in v2.4 2025-02-05
    ADDRESS = 30560

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Energy Imported",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_import_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class ReservedAccumulatedImportEnergy(ReservedSensor, HybridInverter):  # 30554-30565 Marked as Reserved in v2.4 2025-02-05
    ADDRESS = 30562

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Energy Imported",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_import_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:transmission-tower-import",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class DailyChargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30566

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Charge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = None


class AccumulatedChargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30568

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Charge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-up",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class DailyDischargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30572

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Discharge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = None


class AccumulatedDischargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30574

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Discharge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_accumulated_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-arrow-down",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class InverterRunningState(RunningStateSensor, HybridInverter, PVInverter):
    ADDRESS = 30578

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running State",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_running_state",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class MaxActivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30579

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Active Power Adjustment",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_active_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class MinActivePowerAdjustment(ReadOnlySensor, HybridInverter):
    ADDRESS = 30581

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Active Power Adjustment",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_active_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class MaxReactivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30583

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Reactive Power Adjustment",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_reactive_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class MinReactivePowerAdjustment(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30585

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Reactive Power Adjustment",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_reactive_power_adjustment",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class ActivePower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30587

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class ReactivePower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30589

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class MaxBatteryChargePower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30591

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Charge Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_charge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-arrow-up",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class MaxBatteryDischargePower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30593

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Discharge Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_discharge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-arrow-down",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class AvailableBatteryChargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30595

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Available Charge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_available_battery_charge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-plus-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["enabled_by_default"] = True


class AvailableBatteryDischargeEnergy(ReadOnlySensor, HybridInverter):
    ADDRESS = 30597

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Available Discharge Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_available_battery_discharge_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:battery-minus-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.delta = False
        self["enabled_by_default"] = True


class ChargeDischargePower(ReadOnlySensor, HybridInverter):
    ADDRESS = 30599

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_charge_discharge_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-charging-outline",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class InverterBatterySoC(ReadOnlySensor, HybridInverter):
    ADDRESS = 30601

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
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


class InverterBatterySoH(ReadOnlySensor, HybridInverter):
    ADDRESS = 30602

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Battery SoH",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_soh",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-heart-variant",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class AverageCellTemperature(ReadOnlySensor, HybridInverter):
    ADDRESS = 30603

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Average Cell Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_average_cell_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = -400  # -40.0 °C
        self.sanity_check.max_raw = 2000  # 200.0 °C


class AverageCellVoltage(ReadOnlySensor, HybridInverter):
    ADDRESS = 30604

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Average Cell Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_average_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class InverterAlarm1(Alarm1Sensor, HybridInverter, PVInverter):
    ADDRESS = 30605

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PCS Alarms 1",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class InverterAlarm2(Alarm2Sensor, HybridInverter, PVInverter):
    ADDRESS = 30606

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PCS Alarms 2",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class InverterPCSAlarm(AlarmCombinedSensor):
    def __init__(self, plant_index: int, device_address: int, *alarms: AlarmSensor):
        super().__init__(
            "PCS Alarms",
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pcs_alarm",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pcs_alarm",
            *alarms,
        )


class InverterAlarm3(Alarm3Sensor, HybridInverter):
    ADDRESS = 30607

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarms",  # ESS
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_3",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class InverterAlarm4(Alarm4Sensor, HybridInverter, PVInverter):
    ADDRESS = 30608

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Gateway Alarms",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_4",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class InverterAlarm5(Alarm5Sensor, HybridInverter):
    ADDRESS = 30609

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarms",  # DC Charger
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_alarm_5",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )


class Reserved30610(ReservedSensor, HybridInverter, PVInverter):
    ADDRESS = 30610

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Reserved",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reserved_30610",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=3,
            data_type=ModbusDataType.STRING,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:comment-question",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_5,
        )


class InverterActivePowerFixedValueAdjustmentFeedback(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30613

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Active Power Fixed Value Adjustment Feedback",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power_fixed_value_adjustment_feedback",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:comment-quote",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_6,
        )


class InverterReactivePowerFixedValueAdjustmentFeedback(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30615

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Reactive Power Fixed Value Adjustment Feedback",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power_fixed_value_adjustment_feedback",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:comment-quote",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_6,
        )


class InverterActivePowerPercentageAdjustmentFeedback(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30617

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Active Power Percentage Adjustment Feedback",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_active_power_percentage_adjustment_feedback",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_6,
        )


class InverterReactivePowerPercentageAdjustmentFeedback(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30618

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Reactive Power Percentage Adjustment Feedback",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_reactive_power_percentage_adjustment_feedback",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            protocol_version=Protocol.V2_6,
        )


class InverterPowerFactorAdjustmentFeedback(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 30619

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Power Factor Adjustment Feedback",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_power_factor_adjustment_feedback",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:adjust",
            gain=1000,
            precision=None,
            protocol_version=Protocol.V2_6,
        )


class InverterMaxBatteryTemperature(ReadOnlySensor, HybridInverter):
    ADDRESS = 30620

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Battery Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_battery_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer-high",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = -400  # -40.0 °C
        self.sanity_check.max_raw = 2000  # 200.0 °C


class InverterMinBatteryTemperature(ReadOnlySensor, HybridInverter):
    ADDRESS = 30621

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Battery Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_battery_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer-low",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = -400  # -40.0 °C
        self.sanity_check.max_raw = 2000  # 200.0 °C


class InverterMaxCellVoltage(ReadOnlySensor, HybridInverter):
    ADDRESS = 30622

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Max Cell Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_max_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class InverterMinCellVoltage(ReadOnlySensor, HybridInverter):
    ADDRESS = 30623

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Min Cell Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_min_cell_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class RatedGridVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Grid Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_grid_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=10,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class RatedGridFrequency(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31001

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Grid Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_rated_grid_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class GridFrequency(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31002

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Grid Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_grid_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class InverterTemperature(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31003

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = -400  # -40.0 °C
        self.sanity_check.max_raw = 2000  # 200.0 °C


class OutputType(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31004

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Output Type",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_output_type",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:home-lightning-bolt",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"
        self[DiscoveryKeys.OPTIONS] = [
            "L/N",  # 0
            "L1/L2/L3",  # 1
            "L1/L2/L3/N",  # 2
            "L1/L2/N",  # 3
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1  # pyrefly: ignore

    @classmethod
    def to_phases(cls, output_type: str | float | int | None) -> int:
        match output_type:
            case 0 | "L/N":
                return 1
            case 1 | 2 | "L1/L2/L3" | "L1/L2/L3/N":
                return 3
            case 3 | "L1/L2/N":
                return 2
            case _:
                raise ValueError(f"Unknown Output Type: {output_type}")

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)) and 0 <= value <= (len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1):
            return cast(list[str], self[DiscoveryKeys.OPTIONS])[int(value)]
        else:
            return f"Unknown Output Type: {value}"


class LineVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    # Invalid when Output Type is L/N, L1/L2/N, or L1/L2/N (sic as per Protocol V2.8 should be L1/L2/L3/N)
    def __init__(self, plant_index: int, device_address: int, phase: str):
        match phase:
            case "A-B":
                address = 31005
            case "B-C":
                address = 31007
            case "C-A":
                address = 31009
            case _:
                raise ValueError("Phase must be 'A-B', 'B-C', or 'C-A'")
        super().__init__(
            name=f"{phase} Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_{phase.lower().replace('-', '_')}_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )


class PhaseVoltage(ReadOnlySensor, HybridInverter, PVInverter):
    PHASE_A_ADDRESS = 31011
    PHASE_B_ADDRESS = 31013
    PHASE_C_ADDRESS = 31015

    def __init__(self, plant_index: int, device_address: int, phase: str, power_phases: int):
        match phase:
            case "A":
                address = PhaseVoltage.PHASE_A_ADDRESS
            case "B":
                address = PhaseVoltage.PHASE_B_ADDRESS
            case "C":
                address = PhaseVoltage.PHASE_C_ADDRESS
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        phase = f" {phase}" if power_phases > 1 else ""
        super().__init__(
            name=f"Phase{phase} Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_{phase.strip().lower()}_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,  # Used for i18n processing
        )
        self.phase = phase


class PhaseCurrent(ReadOnlySensor, HybridInverter, PVInverter):
    PHASE_A_ADDRESS = 31017
    PHASE_B_ADDRESS = 31019
    PHASE_C_ADDRESS = 31021

    def __init__(self, plant_index: int, device_address: int, phase: str, power_phases: int):
        match phase:
            case "A":
                address = PhaseCurrent.PHASE_A_ADDRESS
            case "B":
                address = PhaseCurrent.PHASE_B_ADDRESS
            case "C":
                address = PhaseCurrent.PHASE_C_ADDRESS
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        phase = f" {phase}" if power_phases > 1 else ""
        super().__init__(
            name=f"Phase{phase} Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_phase_{phase.strip().lower()}_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
        )


class PowerFactor(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31023

    def __init__(self, plant_index: int, device_address: int, active_power: ActivePower, reactive_power: ReactivePower):
        super().__init__(
            name="Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            state_class=None,
            icon="mdi:angle-acute",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.min_raw = 0  # 0.0
        self.sanity_check.max_raw = 1000  # 1.0
        self._max_failures_retry_interval = 300
        self._active_power = active_power
        self._reactive_power = reactive_power

    def set_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> None:
        try:
            super().set_state(state)
        except ValueError as e:
            active_power = cast(float, self._active_power.latest_raw_state)
            reactive_power = cast(float, self._reactive_power.latest_raw_state)
            if active_power is not None and reactive_power is not None:
                apparent_power = math.sqrt(active_power**2 + reactive_power**2)
                power_factor = round((abs(active_power) / apparent_power) * self.gain) if apparent_power != 0 else 0
                if self.debug_logging:
                    active_power_time = cast(float, self._active_power.latest_time)  # pyrefly: ignore
                    reactive_power_time = cast(float, self._reactive_power.latest_time)  # pyrefly: ignore
                    logging.debug(
                        f"{self.__class__.__name__} Calculated {power_factor=} from active_power={active_power} @ {time.strftime('%H:%M:%S', time.localtime(active_power_time))} reactive_power={reactive_power} @ {time.strftime('%H:%M:%S', time.localtime(reactive_power_time))} -> {apparent_power=}"
                    )
                logging.info(
                    f"{self.__class__.__name__} Using calculated raw state={power_factor} (Active={self._active_power.latest_raw_state} Reactive={self._reactive_power.latest_raw_state} Apparent={apparent_power}) because {e}"
                )
                super().set_state(power_factor)
            else:
                raise e


class PACKBCUCount(ReadOnlySensor, HybridInverter):
    ADDRESS = 31024

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PACK/BCU Count",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pack_bcu_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:eye",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = 16


class PVStringCount(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31025

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PV String Count",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv_string_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-panel",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"
        self.sanity_check.min_raw = 2
        self.sanity_check.max_raw = 36


class MPPTCount(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31026

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="MPPT Count",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_mppt_count",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-panel",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
        )
        self["entity_category"] = "diagnostic"


class PVCurrentSensor(ReadOnlySensor, HybridInverter, PVInverter):
    raw2amps: float = 100  # divisor to convert raw value to amps

    def __init__(self, plant_index: int, device_address: int, address: int, string_number: int, protocol_version: Protocol):
        assert 1 <= string_number <= 36, "string_number must be between 1 and 36"
        super().__init__(
            name="Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-dc",
            gain=PVCurrentSensor.raw2amps,
            precision=2,
            protocol_version=protocol_version,
        )
        self.string_number = string_number


class PVVoltageSensor(ReadOnlySensor, HybridInverter, PVInverter):
    raw2volts: float = 10  # divisor to convert raw value to volts

    def __init__(self, plant_index: int, device_address: int, address: int, string_number: int, protocol_version: Protocol):
        assert 1 <= string_number <= 36, "string_number must be between 1 and 36"
        super().__init__(
            name="Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=PVVoltageSensor.raw2volts,
            precision=1,
            protocol_version=protocol_version,
        )
        self.string_number = string_number


class InverterPVPower(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31035

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PV Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.WATT,  # Protocol defines kW, but prefer the greater precision of watts
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,  # Protocol defines kW, but prefer the greater precision of watts
            precision=2,
            protocol_version=Protocol.V1_8,
        )
        self["enabled_by_default"] = True


class InsulationResistance(ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31037

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Insulation Resistance",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_insulation_resistance",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit="MΩ",
            device_class=None,
            state_class=None,
            icon="mdi:omega",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class StartupTime(TimestampSensor, HybridInverter, PVInverter):
    ADDRESS = 31038

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Startup Time",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_startup_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V1_8,
        )


class ShutdownTime(TimestampSensor, HybridInverter, PVInverter):
    ADDRESS = 31040

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Shutdown Time",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_shutdown_time",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V1_8,
        )


class DCChargerVehicleBatteryVoltage(ReadOnlySensor, HybridInverter):
    ADDRESS = 31500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle Battery Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_vehicle_battery_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )


class DCChargerVehicleChargingCurrent(ReadOnlySensor, HybridInverter):
    ADDRESS = 31501

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle Charging Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_vehicle_charging_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class DCChargerOutputPower(ReadOnlySensor, HybridInverter):
    ADDRESS = 31502

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Output Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_output_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class DCChargerVehicleSoC(ReadOnlySensor, HybridInverter):
    ADDRESS = 31504

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Vehicle SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_vehicle_soc",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
            protocol_version=Protocol.V1_8,
        )


class DCChargerCurrentChargingCapacity(ReadOnlySensor, HybridInverter):
    ADDRESS = 31505

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Current Charging Capacity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_current_charging_capacity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Single time"
        return attributes


class DCChargerCurrentChargingDuration(ReadOnlySensor, HybridInverter):
    ADDRESS = 31507

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Current Charging Duration",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_current_charging_duration",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfTime.SECONDS,
            device_class=None,
            state_class=None,
            icon="mdi:car-clock",
            gain=1,
            precision=None,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Single time"
        return attributes


class InverterPVDailyGeneration(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31509

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Daily Production",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_daily_pv_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_daily_pv_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True
        self.sanity_check.min_raw = None


class InverterPVLifetimeGeneration(UnpublishResetSensorMixin, ReadOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 31511

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Lifetime Production",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_lifetime_pv_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_6,
            unique_id_override=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_lifetime_pv_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        )
        self["enabled_by_default"] = True


class DCChargerRunningState(ReadOnlySensor, HybridInverter):  # Not applicable to PVInverter as per Protocol V2.9
    ADDRESS = 31513

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running State",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_dc_charger_{device_address}_running_state",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:ev-station",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True
        self[DiscoveryKeys.OPTIONS] = [
            "Idle",  # 0
            "Occupied (Charging Gun plugged in but not detected)",  # 1
            "Preparing (Establishing communication)",  # 2
            "Charging",  # 3
            "Fault",  # 4
            "Scheduled",  # 5
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
                return f"Unknown State code: {value}"
        else:
            return f"Unknown State code: {value}"
