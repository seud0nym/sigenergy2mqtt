from .base import DeviceClass, InputType, NumericSensor, AvailabilityMixin, ReservedSensor, SelectSensor, SwitchSensor, WriteOnlySensor
from .const import PERCENTAGE, UnitOfFrequency, UnitOfPower, UnitOfReactivePower
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.mqtt import MqttClient
from typing import Any
import logging


# 5.2 Plant parameter setting address definition (holding register)


class PlantStatus(WriteOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Plant Power On/Off",
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
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
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
            availability_control_sensor=None,
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
            minimum=-60.0,
            maximum=60.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class ActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
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
            minimum=-100.00,
            maximum=100.00,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-100.00,100.00]"
        return attributes


class QSAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
            minimum=-60.0,
            maximum=60.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PowerFactorAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    # Range: (-1,-0.8]U[0.8, 1]
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
            minimum=(-1.0, -0.8),
            maximum=(0.8, 1.0),
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [(-1.0, -0.8) U (0.8, 1.0)]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class IndependentPhasePowerControl(SwitchSensor, AvailabilityMixin, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled.
    def __init__(self, plant_index: int, output_type: int):
        super().__init__(
            availability_control_sensor=None,
            name="Independent Phase Power Control",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_independent_phase_power_control",
            plant_index=plant_index,
            device_address=247,
            address=40030,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            protocol_version=Protocol.V1_8,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled"
        return attributes


class PhaseActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, independent_phase_power_control: IndependentPhasePowerControl, output_type: int, phase: str):
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
            availability_control_sensor=independent_phase_power_control,
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
    def __init__(self, plant_index: int, independent_phase_power_control: IndependentPhasePowerControl, output_type: int, phase: str):
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
            availability_control_sensor=independent_phase_power_control,
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
    def __init__(self, plant_index: int, independent_phase_power_control: IndependentPhasePowerControl, output_type: int, phase: str):
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
            availability_control_sensor=independent_phase_power_control,
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
            minimum=-100.00,
            maximum=100.00,
        )
        if output_type != 2:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]"
        return attributes


class PhaseQSAdjustmentTargetValue(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, independent_phase_power_control: IndependentPhasePowerControl, output_type: int, phase: str):
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
            availability_control_sensor=independent_phase_power_control,
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
            minimum=-60.00,
            maximum=60.00,
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


class RemoteEMS(SwitchSensor, HybridInverter, PVInverter, AvailabilityMixin):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Remote EMS",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems",
            plant_index=plant_index,
            device_address=247,
            address=40029,
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS"
        return attributes


class RemoteEMSControlMode(SelectSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
            name="Remote EMS Control Mode",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems_control_mode",
            plant_index=plant_index,
            device_address=247,
            address=40031,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            options=[
                "PCS remote control",  # 0
                "Standby",  # 1
                "Maximum Self-consumption (Default)",  # 2
                "Command Charging (Consume power from the grid first)",  # 3
                "Command Charging (Consume power from the PV first)",  # 4
                "Command Discharging (Output power from PV first)",  # 5
                "Command Discharging (Output power from the battery first)",  # 6
            ],
            protocol_version=Protocol.V1_8,
        )

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if Config.home_assistant.enabled:
            self.is_charging_mode_topic = f"{base}/is_charging_mode"
            self.is_discharging_mode_topic = f"{base}/is_discharging_mode"
            self.is_charging_discharging_topic = f"{base}/is_command_mode"
        return base

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

    async def value_is_valid(self, modbus: ModbusClient, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and await self._availability_control_sensor.get_state(raw=True, republish=True, modbus=modbus) in (0, "0"):
            logging.error(f"{self.__class__.__name__} Failed to write '{self['options'][raw_value]}' ({raw_value}): {self._availability_control_sensor.name} is not enabled")
            return False
        return await super().value_is_valid(modbus, raw_value)


class RemoteEMSLimit(NumericSensor):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin,
        remote_ems_mode: RemoteEMSControlMode,
        charging: bool,
        discharging: bool,
        name: str,
        object_id: str,
        plant_index: int,
        address: int,
        icon: str,
        maximum: float,
        protocol_version: Protocol,
    ):
        super().__init__(
            availability_control_sensor=availability_control_sensor,
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
            maximum=maximum,
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

    async def value_is_valid(self, modbus: ModbusClient, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._availability_control_sensor.latest_raw_state == 0:
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': {self._availability_control_sensor.name} is not enabled")
            return False
        return await super().value_is_valid(modbus, raw_value)


class MaxChargingLimit(RemoteEMSLimit, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin, remote_ems_mode: RemoteEMSControlMode, rated_charging_power: float):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=False,
            name="Max Charging Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_charging_limit",
            plant_index=plant_index,
            address=40032,
            icon="mdi:battery-charging-high",
            maximum=rated_charging_power,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Charging"
        return attributes

    async def value_is_valid(self, modbus: ModbusClient, raw_value: float | int | str) -> bool:
        if self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (3, 4):
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Charging")
            return False
        return await super().value_is_valid(modbus, raw_value)


class MaxDischargingLimit(RemoteEMSLimit, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin, remote_ems_mode: RemoteEMSControlMode, rated_discharging_power: float):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            name="Max Discharging Limit",
            charging=False,
            discharging=True,
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_discharging_limit",
            plant_index=plant_index,
            address=40034,
            icon="mdi:battery-charging-low",
            maximum=rated_discharging_power,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0, Rated ESS charging power]. Takes effect when Remote EMS control mode (40031) is set to Command Discharging"
        return attributes

    async def value_is_valid(self, modbus: ModbusClient, raw_value: float | int | str) -> bool:
        if self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (5, 6):
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Discharging")
            return False
        return await super().value_is_valid(modbus, raw_value)


class PVMaxPowerLimit(RemoteEMSLimit, HybridInverter):
    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin, remote_ems_mode: RemoteEMSControlMode):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=True,
            name="PV Max Power Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_max_power_limit",
            plant_index=plant_index,
            address=40036,
            icon="mdi:solar-power",
            maximum=4294967.295,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging"
        return attributes

    async def value_is_valid(self, modbus: ModbusClient, raw_value: float | int | str) -> bool:
        if self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (3, 4, 5, 6):
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Charging/Discharging")
            return False
        return await super().value_is_valid(modbus, raw_value)


class GridMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
            maximum=4294967.295,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class GridMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
            maximum=4294967.295,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PCSMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
            maximum=4294967.295,
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
            availability_control_sensor=None,
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
            maximum=4294967.295,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally."
        return attributes


class ESSBackupSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSChargeCutOffSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSDischargeCutOffSOC(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
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
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ActivePowerRegulationGradient(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Active Power Regulation Gradient",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_regulation_gradient",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40049,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit="%/s",
            device_class=None,
            state_class=None,
            icon="mdi:gradient-horizontal",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_8,
            maximum=5000,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0,5000]。Percentage of rated power adjusted per second"
        return attributes


class GridCodeLVRT(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Ride Through",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt",
            plant_index=plant_index,
            device_address=247,
            address=40051,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeLVRTReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Reactive Power Compensation Factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40052,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeLVRTNegativeSequenceReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Negative Sequence Reactive Power Compensation Factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_negative_sequence_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40053,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=20.0,  # Protocol says 0.0-10.0 but live systems are returning 20.0???? (https://github.com/seud0nym/sigenergy2mqtt/issues/80#issuecomment-3689277867)
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeLVRTMode(SelectSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Mode",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_mode",
            plant_index=plant_index,
            device_address=247,
            address=40054,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            options=[
                "Reactive power compensation current, active zero-current mode",  # 0
                None,  # 1
                "Zero-current mode",  # 2
                "Constant current mode",  # 3
                "Reactive dynamic current, active zero-current mode",  # 4
                "Reactive power compensation current, active constant-current mode",  # 5
            ],
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeLVRTVoltageProtectionBlocking(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Grid Voltage Protection Blocking",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_grid_voltage_protection_blocking",
            plant_index=plant_index,
            device_address=247,
            address=40055,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )


class GridCodeHVRT(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="High Voltage Ride Through",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt",
            plant_index=plant_index,
            device_address=247,
            address=40056,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeHVRTReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Reactive Power Compensation Factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40057,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeHVRTNegativeSequenceReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Negative Sequence Reactive Power Compensation Factor",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_negative_sequence_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40058,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeHVRTMode(SelectSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Mode",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_mode",
            plant_index=plant_index,
            device_address=247,
            address=40059,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            options=[
                "Reactive power compensation current, active zero-current mode",  # 0
                None,  # 1
                "Zero-current mode",  # 2
                "Constant current mode",  # 3
                "Reactive dynamic current, active hold mode",  # 4
                "Reactive power compensation current, active constant-current mode",  # 5
            ],
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeHVRTVoltageProtectionBlocking(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Grid Voltage Protection Blocking",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_grid_voltage_protection_blocking",
            plant_index=plant_index,
            device_address=247,
            address=40060,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )


class GridCodeOverFrequencyDerating(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_over_frequency_derating",
            plant_index=plant_index,
            device_address=247,
            address=40061,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeOverFrequencyDeratingPowerRampRate(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Power Ramp Rate",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_power_ramp_rate",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40062,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,100.0]"
        return attributes


class GridCodeOverFrequencyDeratingTriggerFrequency(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Trigger Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_trigger_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40063,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            minimum=1.0 * rated_frequency,
            maximum=1.2 * rated_frequency,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[1.0*Fn, 1.2*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeOverFrequencyDeratingCutOffFrequency(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Cut-Off Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_cut_off_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40064,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            minimum=1.0 * rated_frequency,
            maximum=1.2 * rated_frequency,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[1.0*Fn, 1.2*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeUnderFrequencyPowerBoost(SwitchSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost",
            plant_index=plant_index,
            device_address=247,
            address=40065,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeUnderFrequencyPowerBoostPowerRampRate(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Power Ramp Rate",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_power_ramp_rate",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40066,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,100.0]"
        return attributes


class GridCodeUnderFrequencyPowerBoostTriggerFrequency(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Trigger Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_trigger_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40067,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            minimum=0.8 * rated_frequency,
            maximum=1.0 * rated_frequency,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0.8*Fn, 1.0*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeUnderFrequencyPowerBoostCutOffFrequency(NumericSensor, HybridInverter):
    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Cut-Off Frequency",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_cut_off_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40068,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=Config.devices[plant_index].scan_interval.medium if plant_index < len(Config.devices) else 60,
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            minimum=0.8 * rated_frequency,
            maximum=1.0 * rated_frequency,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0.8*Fn, 1.0*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes
