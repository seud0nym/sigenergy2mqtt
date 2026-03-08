import logging
from typing import cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import PERCENTAGE, Constants, DeviceClass, HybridInverter, InputType, Protocol, PVInverter, UnitOfFrequency, UnitOfPower, UnitOfReactivePower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.sensors.base import AvailabilityMixin, DiscoveryKeys, NumericSensor, ReservedSensor, ScanInterval, SelectSensor, SwitchSensor, ThreePhaseAdjustmentTargetValue, WriteOnlySensor

# 5.2 Plant parameter setting address definition (holding register)


class PlantStatus(WriteOnlySensor, HybridInverter, PVInverter):
    ADDRESS = 40000

    def __init__(self, plant_index: int):
        super().__init__(
            name="Plant Power On/Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_status",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "0:Stop 1:Start"
        return attributes


class ActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40001

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
            name="Active Power Fixed Adjustment Target Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
        )


class ReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40003

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reactive Power Fixed Adjustment Target Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.00 * base value ,60.00 * base value]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class ActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40005

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
            name="Active Power Percentage Adjustment Target Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
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
            protocol_version=Protocol.V1_8,
            minimum=-100.00,
            maximum=100.00,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-100.00,100.00]"
        return attributes


class QSAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40006

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Q/S Adjustment Target Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_q_s_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [-60.0,60.00]. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PowerFactorAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40007

    # Range: (-1,-0.8]U[0.8, 1]
    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Power Factor Adjustment Target Value",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_power_factor_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [(-1.0, -0.8) U (0.8, 1.0)]. Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class IndependentPhasePowerControl(SwitchSensor, AvailabilityMixin, HybridInverter):
    ADDRESS = 40030

    # Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled.
    def __init__(self, plant_index: int, output_type: int):
        super().__init__(
            availability_control_sensor=None,
            name="Independent Phase Power Control",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_independent_phase_power_control",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V1_8,
        )
        if output_type != Constants.THREE_PHASE_OUTPUT_TYPE:  # L1/L2/L3/N
            self.publishable = False

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled"
        return attributes


class PhaseActivePowerFixedAdjustmentTargetValue(ThreePhaseAdjustmentTargetValue, HybridInverter):
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
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
            output_type=output_type,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N"
        return attributes


class PhaseReactivePowerFixedAdjustmentTargetValue(ThreePhaseAdjustmentTargetValue, HybridInverter):
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
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V1_8,
            phase=phase,
            output_type=output_type,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N"
        return attributes


class PhaseActivePowerPercentageAdjustmentTargetValue(ThreePhaseAdjustmentTargetValue, HybridInverter):
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
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            protocol_version=Protocol.V1_8,
            minimum=-100.00,
            maximum=100.00,
            phase=phase,
            output_type=output_type,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]"
        return attributes


class PhaseQSAdjustmentTargetValue(ThreePhaseAdjustmentTargetValue, HybridInverter):
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
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_{phase.lower()}_q_s_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=None,
            protocol_version=Protocol.V1_8,
            minimum=-60.00,
            maximum=60.00,
            phase=phase,
            output_type=output_type,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]"
        return attributes


class Reserved40026(ReservedSensor, HybridInverter, PVInverter):
    ADDRESS = 40026

    def __init__(self, plant_index: int):
        super().__init__(
            name="Reserved",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_reserved_40026",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
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


class RemoteEMS(SwitchSensor, HybridInverter, PVInverter, AvailabilityMixin):
    ADDRESS = 40029

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Remote EMS",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.high(plant_index),
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "When needed to control EMS remotely, this register needs to be enabled. When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS"
        return attributes


class RemoteEMSControlMode(SelectSensor, HybridInverter, PVInverter):
    ADDRESS = 40031

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin):
        super().__init__(
            availability_control_sensor=remote_ems,
            name="Remote EMS Control Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_remote_ems_control_mode",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
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
        if active_config.home_assistant.enabled and active_config.ems_mode_check:
            self.is_charging_mode_topic = f"{base}/is_charging_mode"
            self.is_discharging_mode_topic = f"{base}/is_discharging_mode"
            self.is_charging_discharging_topic = f"{base}/is_command_mode"
        return base

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        result = await super().publish(mqtt_client, modbus_client, republish=republish)
        if result and active_config.home_assistant.enabled and active_config.ems_mode_check:
            match self.latest_raw_state:
                case 3 | 4:
                    mqtt_client.publish(self.is_charging_mode_topic, "1", self._qos, self._retain)
                    mqtt_client.publish(self.is_discharging_mode_topic, "0", self._qos, self._retain)
                    mqtt_client.publish(self.is_charging_discharging_topic, "1", self._qos, self._retain)
                case 5 | 6:
                    mqtt_client.publish(self.is_charging_mode_topic, "0", self._qos, self._retain)
                    mqtt_client.publish(self.is_discharging_mode_topic, "1", self._qos, self._retain)
                    mqtt_client.publish(self.is_charging_discharging_topic, "1", self._qos, self._retain)
                case _:
                    mqtt_client.publish(self.is_charging_mode_topic, "0", self._qos, self._retain)
                    mqtt_client.publish(self.is_discharging_mode_topic, "0", self._qos, self._retain)
                    mqtt_client.publish(self.is_charging_discharging_topic, "0", self._qos, self._retain)
            return True
        return result

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._availability_control_sensor.latest_raw_state in (0, "0"):
            logging.error(
                f"{self.__class__.__name__} Failed to write '{cast(list[str], self['options'])[raw_value] if isinstance(raw_value, int) else raw_value}' ({raw_value}): {self._availability_control_sensor.name} is not enabled"
            )
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class RemoteEMSLimit(NumericSensor, HybridInverter):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        remote_ems_mode: RemoteEMSControlMode | None,
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
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=address,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
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
        if self._remote_ems_mode and active_config.home_assistant.enabled and active_config.ems_mode_check:
            if self._charging and self._discharging:
                cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append(
                    {"topic": self._remote_ems_mode.is_charging_discharging_topic, "payload_available": 1, "payload_not_available": 0}
                )
            elif self._charging:
                cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append({"topic": self._remote_ems_mode.is_charging_mode_topic, "payload_available": 1, "payload_not_available": 0})
            elif self._discharging:
                cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY]).append({"topic": self._remote_ems_mode.is_discharging_mode_topic, "payload_available": 1, "payload_not_available": 0})
        return base

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._availability_control_sensor.latest_raw_state == 0:
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': {self._availability_control_sensor.name} is not enabled")
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class MaxChargingLimit(RemoteEMSLimit):
    ADDRESS = 40032

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin | None, remote_ems_mode: RemoteEMSControlMode | None, rated_charging_power: float):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=False,
            name="Max Charging Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_charging_limit",
            plant_index=plant_index,
            address=self.ADDRESS,
            icon="mdi:battery-charging-high",
            maximum=rated_charging_power,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.max_raw = Constants.UINT32_MAX  # This will be the default value read from Modbus if no value is set by user

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = f"Range: [0, Rated ESS charging power]{'. Takes effect when Remote EMS control mode (40031) is set to Command Charging' if active_config.ems_mode_check else ''}"
        return attributes

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (3, 4) and active_config.ems_mode_check:
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Charging")
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class MaxDischargingLimit(RemoteEMSLimit):
    ADDRESS = 40034

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin | None, remote_ems_mode: RemoteEMSControlMode | None, rated_discharging_power: float):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            name="Max Discharging Limit",
            charging=False,
            discharging=True,
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_max_discharging_limit",
            plant_index=plant_index,
            address=self.ADDRESS,
            icon="mdi:battery-charging-low",
            maximum=rated_discharging_power,
            protocol_version=Protocol.V1_8,
        )
        self.sanity_check.max_raw = Constants.UINT32_MAX  # This will be the default value read from Modbus if no value is set by user

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = f"Range: [0, Rated ESS charging power]{'. Takes effect when Remote EMS control mode (40031) is set to Command Discharging' if active_config.ems_mode_check else ''}"
        return attributes

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (5, 6) and active_config.ems_mode_check:
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Discharging")
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class PVMaxPowerLimit(RemoteEMSLimit):
    ADDRESS = 40036

    def __init__(self, plant_index: int, remote_ems: AvailabilityMixin | None, remote_ems_mode: RemoteEMSControlMode | None):
        super().__init__(
            availability_control_sensor=remote_ems,
            remote_ems_mode=remote_ems_mode,
            charging=True,
            discharging=True,
            name="PV Max Power Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_pv_max_power_limit",
            plant_index=plant_index,
            address=self.ADDRESS,
            icon="mdi:solar-power",
            maximum=4294967.295,
            protocol_version=Protocol.V1_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        if active_config.ems_mode_check:
            attributes["comment"] = "Takes effect when Remote EMS control mode (40031) is set to Command Charging/Discharging"
        return attributes

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        if self._availability_control_sensor is not None and self._remote_ems_mode is not None and self._remote_ems_mode.latest_raw_state not in (3, 4, 5, 6) and active_config.ems_mode_check:
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Remote EMS control mode is not set to Command Charging/Discharging")
            return False
        return await super().value_is_valid(modbus_client, raw_value)


class GridMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40038

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Grid Max Export Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-export",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
            maximum=4294967.295,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class GridMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40040

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Grid Max Import Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-import",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
            maximum=4294967.295,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Grid Sensor needed. Takes effect globally regardless of the EMS operating mode"
        return attributes


class PCSMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40042

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="PCS Max Export Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-negative",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
            maximum=4294967.294,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally."
        return attributes


class PCSMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40044

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="PCS Max Import Limit",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-positive",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_5,
            maximum=4294967.294,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0, 0xFFFFFFFE]。With value 0xFFFFFFFF, register is not valid. In all other cases, Takes effect globally."
        return attributes


class ESSBackupSOC(NumericSensor, HybridInverter):
    ADDRESS = 40046

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Backup SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_backup_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            protocol_version=Protocol.V2_6,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSChargeCutOffSOC(NumericSensor, HybridInverter):
    ADDRESS = 40047

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Charge Cut-Off SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_charge_cut_off_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            protocol_version=Protocol.V2_6,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ESSDischargeCutOffSOC(NumericSensor, HybridInverter):
    ADDRESS = 40048

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Discharge Cut-Off SoC",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_ess_discharge_cut_off_soc",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=10,
            precision=None,
            protocol_version=Protocol.V2_6,
        )
        self["enabled_by_default"] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0.00,100.00]"
        return attributes


class ActivePowerRegulationGradient(NumericSensor, HybridInverter, PVInverter):
    ADDRESS = 40049

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Active Power Regulation Gradient",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_plant_active_power_regulation_gradient",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.medium(plant_index),
            unit="%/s",
            device_class=None,
            state_class=None,
            icon="mdi:gradient-horizontal",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_8,
            maximum=5000,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0,5000]。Percentage of rated power adjusted per second"
        return attributes


class GridCodeLVRT(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40051

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Ride Through",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeLVRTReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    ADDRESS = 40052

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Reactive Power Compensation Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeLVRTNegativeSequenceReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    ADDRESS = 40053

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Negative Sequence Reactive Power Compensation Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_negative_sequence_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=20.0,  # Protocol says 0.0-10.0 but live systems are returning 20.0???? (https://github.com/seud0nym/sigenergy2mqtt/issues/80#issuecomment-3689277867)
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Documented Range: [0,10.0] but using 20.0 as maximum because live systems are returning this value"
        return attributes


class GridCodeLVRTMode(SelectSensor, HybridInverter, PVInverter):
    ADDRESS = 40054

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_mode",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            options=[
                "Reactive power compensation current, active zero-current mode",  # 0
                "",  # 1
                "Zero-current mode",  # 2
                "Constant current mode",  # 3
                "Reactive dynamic current, active zero-current mode",  # 4
                "Reactive power compensation current, active constant-current mode",  # 5
            ],
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeLVRTVoltageProtectionBlocking(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40055

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="LVRT Grid Voltage Protection Blocking",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_lvrt_grid_voltage_protection_blocking",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )


class GridCodeHVRT(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40056

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="High Voltage Ride Through",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeHVRTReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    ADDRESS = 40057

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Reactive Power Compensation Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeHVRTNegativeSequenceReactivePowerCompensationFactor(NumericSensor, HybridInverter):
    ADDRESS = 40058

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Negative Sequence Reactive Power Compensation Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_negative_sequence_reactive_power_compensation_factor",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:counter",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
            maximum=10.0,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,10.0]"
        return attributes


class GridCodeHVRTMode(SelectSensor, HybridInverter, PVInverter):
    ADDRESS = 40059

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Mode",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_mode",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            options=[
                "Reactive power compensation current, active zero-current mode",  # 0
                "",  # 1
                "Zero-current mode",  # 2
                "Constant current mode",  # 3
                "Reactive dynamic current, active hold mode",  # 4
                "Reactive power compensation current, active constant-current mode",  # 5
            ],
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeHVRTVoltageProtectionBlocking(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40060

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="HVRT Grid Voltage Protection Blocking",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_hvrt_grid_voltage_protection_blocking",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )


class GridCodeOverFrequencyDerating(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40061

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeOverFrequencyDeratingPowerRampRate(NumericSensor, HybridInverter):
    ADDRESS = 40062

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Power Ramp Rate",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_power_ramp_rate",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,100.0]"
        return attributes


class GridCodeOverFrequencyDeratingTriggerFrequency(NumericSensor, HybridInverter):
    ADDRESS = 40063

    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Trigger Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_trigger_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[1.0*Fn, 1.2*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeOverFrequencyDeratingCutOffFrequency(NumericSensor, HybridInverter):
    ADDRESS = 40064

    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Over Frequency Derating Cut-Off Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_over_frequency_derating_cut_off_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[1.0*Fn, 1.2*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeUnderFrequencyPowerBoost(SwitchSensor, HybridInverter, PVInverter):
    ADDRESS = 40065

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost",
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            scan_interval=ScanInterval.medium(plant_index),
            protocol_version=Protocol.V2_8,
        )
        self["enabled_by_default"] = True


class GridCodeUnderFrequencyPowerBoostPowerRampRate(NumericSensor, HybridInverter):
    ADDRESS = 40066

    def __init__(self, plant_index: int):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Power Ramp Rate",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_power_ramp_rate",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent-box-outline",
            gain=100,
            precision=1,
            protocol_version=Protocol.V2_8,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range: [0,100.0]"
        return attributes


class GridCodeUnderFrequencyPowerBoostTriggerFrequency(NumericSensor, HybridInverter):
    ADDRESS = 40067

    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Trigger Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_trigger_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0.8*Fn, 1.0*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes


class GridCodeUnderFrequencyPowerBoostCutOffFrequency(NumericSensor, HybridInverter):
    ADDRESS = 40068

    def __init__(self, plant_index: int, rated_frequency: float):
        super().__init__(
            availability_control_sensor=None,
            name="Under-Frequency Power Boost Cut-Off Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_code_under_frequency_power_boost_cut_off_frequency",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=Constants.PLANT_DEVICE_ADDRESS,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
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

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Range:[0.8*Fn, 1.0*Fn] Reference:[Grid code] Rated Frequency (Register 30276)"
        return attributes
