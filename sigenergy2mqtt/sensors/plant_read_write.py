from .base import DeviceClass, InputType, NumericSensor, RemoteEMSMixin, ReadWriteSensor, SwitchSensor, WriteOnlySensor
from pymodbus import ExceptionResponse
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from sigenergy2mqtt.sensors.const import PERCENTAGE, UnitOfPower, UnitOfReactivePower
from typing import Any
import logging


# 5.2 Plant parameter setting address definition (holding register)


class PlantStatus(WriteOnlySensor, HybridInverter, PVInverter):
    # 0:Stop 1:Start
    def __init__(self, plant_index: int):
        super().__init__(
            name="Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_status",
            plant_index=plant_index,
            device_address=247,
            address=40000,
        )


class ActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Active Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40001,
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


class ReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40003,
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

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class ActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Active Power Percentage Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40005,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            min=-100.00,
            max=100.00,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-100.00,100.00]"
        return attributes


class QSAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Q/S Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_q_s_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40006,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=None,
            min=-60.0,
            max=60.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PowerFactorAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    # Range: (-1,-0.8]U[0.8, 1]
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Power Factor Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_power_factor_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40007,
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

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: (-1, -0.8] U [0.8, 1]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PhaseActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, output_type: int, phase: str):
        match phase:
            case "A":
                address = 40008
            case "B":
                address = 40010
            case "C":
                address = 40012
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            remote_ems=remote_ems,
            name=f"Phase {phase} Active Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=address,
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
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N"
        return attributes


class PhaseReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, output_type: int, phase: str):
        match phase:
            case "A":
                address = 40014
            case "B":
                address = 40016
            case "C":
                address = 40018
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            remote_ems=remote_ems,
            name=f"Phase {phase} Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=address,
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
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N"
        return attributes


class PhaseActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, output_type: int, phase: str):
        match phase:
            case "A":
                address = 40020
            case "B":
                address = 40021
            case "C":
                address = 40022
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            remote_ems=remote_ems,
            name=f"Phase {phase} Active Power Percentage Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            min=-100.00,
            max=100.00,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]"
        return attributes


class PhaseQSAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, output_type: int, phase: str):
        match phase:
            case "A":
                address = 40023
            case "B":
                address = 40024
            case "C":
                address = 40025
            case _:
                raise ValueError("Phase must be 'A', 'B', or 'C'")
        super().__init__(
            remote_ems=remote_ems,
            name=f"Phase {phase} Q/S Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_q_s_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            min=-60.00,
            max=60.00,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]"
        return attributes


class RemoteEMS(SwitchSensor, HybridInverter, PVInverter, RemoteEMSMixin):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Remote EMS",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40029,
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

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS"
        return attributes


class IndependentPhasePowerControl(SwitchSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled.
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, output_type: int):
        super().__init__(
            remote_ems=remote_ems,
            name="Independent Phase Power Control",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_independent_phase_power_control",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40030,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=None,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled"
        return attributes


class RemoteEMSControlMode(ReadWriteSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Remote EMS Control Mode",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems_control_mode",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40031,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:list-status",
            gain=None,
            precision=None,
        )
        self["platform"] = "select"
        self["options"] = [
            "PCS remote control",
            "Standby",
            "Maximum Self-consumption (Default)",
            "Command Charging (Consume power from the grid first)",
            "Command Charging (Consume power from the PV first)",
            "Command Discharging (Output power from PV first)",
            "Command Discharging (Output power from the battery first)",
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
            return f"Unknown Mode: {value}"

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool | Exception | ExceptionResponse:
        result = False
        index = None
        try:
            index = self["options"].index(value)
        except ValueError:
            try:
                index = int(value)
            except ValueError:
                pass
        if index is not None and 0 <= index <= 6:
            result = await super().set_value(modbus, mqtt, index, source, handler)
        else:
            logging.warning(f"{self.name} - Ignored attempt to set value to '{value}': Not a valid mode")
        if result:
            pass
        return result


class MaxChargingLimit(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, rated_charging_power: float):
        super().__init__(
            remote_ems=remote_ems,
            name="Max Charging Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_charging_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40032,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-charging-high",
            gain=1000,
            precision=2,
            min=0,
            max=rated_charging_power,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging"
        return attributes


class MaxDischargingLimit(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, rated_discharging_power: float):
        super().__init__(
            remote_ems=remote_ems,
            name="Max Discharging Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_discharging_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40034,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-charging-low",
            gain=1000,
            precision=2,
            min=0,
            max=rated_discharging_power,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging"
        return attributes


class PVMaxPowerLimit(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="PV Max Power Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_max_power_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40036,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:solar-power",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging"
        return attributes


class GridMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Grid Max Export Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40038,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-export",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class GridMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Grid Max Import Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40040,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-import",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PCSMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="PCS Max Export Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40042,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-negative",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally."
        return attributes

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if value == 0xFFFFFFFF:
            logging.warning(f"{self.name} - Register is not valid, setting publishable to False ({value=})")
            self.publishable = False
            return None
        else:
            return value


class PCSMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="PCS Max Import Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40044,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-positive",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally."
        return attributes


class ESSBackupSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Backup SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_backup_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40046,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            min=0.00,
            max=100.00,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSChargeCutOffSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Charge Cut-Off SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_charge_cut_off_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40047,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            min=0.00,
            max=100.00,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSDischargeCutOffSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            remote_ems=None,
            name="Discharge Cut-Off SoC",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_discharge_cut_off_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40048,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            min=0.00,
            max=100.00,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes
