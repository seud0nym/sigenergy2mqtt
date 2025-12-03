from .base import DeviceClass, InputType, NumericSensor, Protocol, RemoteEMSMixin, ReadWriteSensor, ReservedSensor, SwitchSensor, WriteOnlySensor
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
    def __init__(self, plant_index: int):
        super().__init__(
            name="Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_status",
            plant_index=plant_index,
            device_address=247,
            address=40000,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "0:Stop 1:Start"
        return attributes


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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
            min=-60.0,
            max=60.0,
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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
            min=-1.0,
            max=1.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [(-1, -0.8) U (0.8, 1)]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
            min=-60.00,
            max=60.00,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]"
        return attributes


class Reserved40026(ReservedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Reserved",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_reserved_40026",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=247,
            address=40026,
            count=3,
            data_type=ModbusClient.DATATYPE.STRING,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:comment-question",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_5,
        )


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
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V1_8,
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
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:list-status",
            gain=None,
            precision=None,
            protocol_version=Protocol.V1_8,
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

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if Config.home_assistant.enabled:
            self.is_charging_mode_topic = f"{base}/is_charging_mode"
            self.is_discharging_mode_topic = f"{base}/is_discharging_mode"
            self.is_charging_discharging_topic = f"{base}/is_command_mode"
        return base

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

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> bool:
        result = await super().publish(mqtt, modbus, republish=republish)
        if result and Config.home_assistant.enabled:
            match self.latest_raw_state:
                case 3 | 4:
                    mqtt.publish(self.is_charging_mode_topic, "1", self._qos, self._retain)
                    mqtt.publish(self.is_discharging_mode_topic, "0", self._qos, self._retain)
                    mqtt.publish(self.is_charging_discharging_topic, "1", self._qos, self._retain)
                case 5 | 6:
                    mqtt.publish(self.is_charging_mode_topic, "0", self._qos, self._retain)
                    mqtt.publish(self.is_discharging_mode_topic, "1", self._qos, self._retain)
                    mqtt.publish(self.is_charging_discharging_topic, "1", self._qos, self._retain)
                case _:
                    mqtt.publish(self.is_charging_mode_topic, "0", self._qos, self._retain)
                    mqtt.publish(self.is_discharging_mode_topic, "0", self._qos, self._retain)
                    mqtt.publish(self.is_charging_discharging_topic, "0", self._qos, self._retain)
            return True
        return result

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


class RemoteEMSLimit(NumericSensor, HybridInverter):
    def __init__(
        self,
        remote_ems: RemoteEMSMixin,
        remote_ems_mode: RemoteEMSControlMode,
        charging: bool,
        discharging: bool,
        name: str,
        object_id: str,
        plant_index: int,
        address: int,
        icon: str,
        max: float,
        protocol_version:Protocol,

    ):
        super().__init__(
            remote_ems=remote_ems,
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=address,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon=icon,
            gain=1000,
            precision=2,
            protocol_version=protocol_version,
            min=0,
            max=max,
        )
        self._remote_ems_mode = remote_ems_mode
        self._charging = charging
        self._discharging = discharging

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if Config.home_assistant.enabled:
            if self._charging and self._discharging:
                self["availability"].append({"topic": self._remote_ems_mode.is_charging_discharging_topic, "payload_available": 1, "payload_not_available": 0})
            elif self._charging:
                self["availability"].append({"topic": self._remote_ems_mode.is_charging_mode_topic, "payload_available": 1, "payload_not_available": 0})
            elif self._discharging:
                self["availability"].append({"topic": self._remote_ems_mode.is_discharging_mode_topic, "payload_available": 1, "payload_not_available": 0})
        return base


class MaxChargingLimit(RemoteEMSLimit):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, remote_ems_mode: RemoteEMSControlMode, rated_charging_power: float):
        super().__init__(
            remote_ems=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=False,
            name="Max Charging Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_charging_limit",
            plant_index=plant_index,
            address=40032,
            icon="mdi:battery-charging-high",
            max=rated_charging_power,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging"
        return attributes


class MaxDischargingLimit(RemoteEMSLimit):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, remote_ems_mode: RemoteEMSControlMode, rated_discharging_power: float):
        super().__init__(
            remote_ems=remote_ems,
            remote_ems_mode=remote_ems_mode,
            name="Max Discharging Limit",
            charging=False,
            discharging=True,
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_discharging_limit",
            plant_index=plant_index,
            address=40034,
            icon="mdi:battery-charging-low",
            max=rated_discharging_power,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging"
        return attributes


class PVMaxPowerLimit(RemoteEMSLimit):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, remote_ems_mode: RemoteEMSControlMode):
        super().__init__(
            remote_ems=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=True,
            name="PV Max Power Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_max_power_limit",
            plant_index=plant_index,
            address=40036,
            icon="mdi:solar-power",
            max=4294967.295,
            protocol_version=Protocol.V1_8,
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
            protocol_version=Protocol.V2_5,
            min=0,
            max=4294967.295,
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
            protocol_version=Protocol.V2_5,
            min=0,
            max=4294967.295,
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
            protocol_version=Protocol.V2_5,
            min=0,
            max=4294967.295,
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
            protocol_version=Protocol.V2_5,
            min=0,
            max=4294967.295,
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
            protocol_version=Protocol.V2_6,
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
            protocol_version=Protocol.V2_6,
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
            protocol_version=Protocol.V2_6,
            min=0.00,
            max=100.00,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes
