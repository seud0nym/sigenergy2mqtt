from .base import DeviceClass, InputType, NumericSensor, RemoteEMSMixin, ReadWriteSensor, SwitchSensor, WriteOnlySensor
from pymodbus import ExceptionResponse
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.mqtt import MqttClient
from sigenergy2mqtt.sensors.const import PERCENTAGE, UnitOfPower, UnitOfReactivePower
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
            scan_interval=60,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class ReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40003,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class ActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    # Range: [-100.00,100.00]
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
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-100.00,
            max=100.00,
        )


class QSAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    # Range: [-60.00,60.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Q/S Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_q_s_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40006,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            min=-60.0,
            max=60.0,
        )


class PowerFactorAdjustmentTargetValue(NumericSensor, HybridInverter, PVInverter):
    # Range: (-1,-0.8]U[0.8, 1]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Power Factor Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_power_factor_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40007,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
            min=-1.0,
            max=1.0,
        )


class PhaseAActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase A Active Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40008,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseBActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase B Active Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40010,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseCActivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase C Active Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_active_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40012,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseAReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase A Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40014,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseBReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase B Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40016,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseCReactivePowerFixedAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase C Reactive Power Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_reactive_power_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40018,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=60,
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=1000,
            precision=2,
        )


class PhaseAActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase A Active Power Percentage Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40020,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-100.00,
            max=100.00,
        )


class PhaseBActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase B Active Power Percentage Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40021,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-100.00,
            max=100.00,
        )


class PhaseCActivePowerPercentageAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-100.00,100.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase C Active Power Percentage Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_active_power_percentage_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40022,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-100.00,
            max=100.00,
        )


class PhaseAQSAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase A Q/S Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_a_q_s_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40023,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-60.00,
            max=60.00,
        )


class PhaseBQSAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase B Q/S Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_b_q_s_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40024,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-60.00,
            max=60.00,
        )


class PhaseCQSAdjustmentTargetValue(NumericSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. Range: [-60.00,60.00]
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Phase C Q/S Fixed Adjustment Target Value",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_phase_c_q_s_fixed_adjustment_target_value",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40025,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=60,
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            icon="mdi:percent",
            gain=100,
            precision=2,
            min=-60.00,
            max=60.00,
        )


class RemoteEMS(SwitchSensor, HybridInverter, PVInverter, RemoteEMSMixin):
    # When needed to control EMS remotely, this register needs to be enabled.
    # When enabled, the plant’s EMS Work Mode (30003) will switch to RemoteEMS.
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
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=None,
        )


class IndependentPhasePowerControl(SwitchSensor, HybridInverter):
    # Valid only when Output Type is L1/L2/L3/N. To enable independent phase control, this parameter must be enabled.
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
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
            scan_interval=60,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=None,
        )


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
            scan_interval=60,
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
        elif value == 0:
            return "PCS remote control"
        elif value == 1:
            return "Standby"
        elif value == 2:
            return "Maximum Self-consumption (Default)"
        elif value == 3:
            return "Command Charging (Consume power from the grid first)"
        elif value == 4:
            return "Command Charging (Consume power from the PV first)"
        elif value == 5:
            return "Command Discharging (Output power from PV first)"
        elif value == 6:
            return "Command Discharging (Output power from the battery first)"
        else:
            return f"Unknown Mode: {value}"

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: str, source: str) -> bool | Exception | ExceptionResponse:
        if value == "PCS remote control":
            return await super().set_value(modbus, mqtt, 0, source)
        elif value == "Standby":
            return await super().set_value(modbus, mqtt, 1, source)
        elif value == "Maximum Self-consumption (Default)":
            return await super().set_value(modbus, mqtt, 2, source)
        elif value == "Command Charging (Consume power from the grid first)":
            return await super().set_value(modbus, mqtt, 3, source)
        elif value == "Command Charging (Consume power from the PV first)":
            return await super().set_value(modbus, mqtt, 4, source)
        elif value == "Command Discharging (Output power from PV first)":
            return await super().set_value(modbus, mqtt, 5, source)
        elif value == "Command Discharging (Output power from the battery first)":
            return await super().set_value(modbus, mqtt, 6, source)
        else:
            logging.error(f"{self.name} - Ignored attempt to set value to {value}: Not a valid mode")
            return False


class MaxChargingLimit(NumericSensor, HybridInverter):
    # This register will take effect when Remote EMS Control Mode (40031) is 3 or 4.
    # Range [0, PlantRatedChargingPower (Rated ESS Charging Power)].
    def __init__(
        self,
        plant_index: int,
        remote_ems: RemoteEMSMixin,
        rated_charging_power: float,
        mode: RemoteEMSControlMode,
    ):
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
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-charging-high",
            gain=1000,
            precision=2,
            min=0,
            max=rated_charging_power,
        )
        self._mode = mode

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        assert self._mode.state_topic and not self._mode.state_topic.isspace(), "RemoteEMSControlMode state_topic has not been configured"
        self._remote_ems_control_mode_topic = self._mode.state_topic
        self._sensor_availablity_topic = f"{base}/availability"
        self["availability"].append({"topic": self._sensor_availablity_topic})
        return base

    def observable_topics(self) -> set[str]:
        topics = super().observable_topics()
        topics.add(self._remote_ems_control_mode_topic)
        return topics

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source == self._remote_ems_control_mode_topic:
            if self._sensor_availablity_topic is None:
                logging.error(f"Sensor {self.name} availability topic is not configured??")
                return False
            else:
                mqtt.publish(self._sensor_availablity_topic, "online" if value == 3 or value == 4 else "offline")
                return True
        else:
            return False


class MaxDischargingLimit(NumericSensor, HybridInverter):
    # This register will take effect when Remote EMS Control Mode (40031) is 5 or 6.
    # Range [0, PlantRatedDischargingPower (Rated ESS Discharging Power)].
    def __init__(
        self,
        plant_index: int,
        remote_ems: RemoteEMSMixin,
        rated_discharging_power: float,
        mode: RemoteEMSControlMode,
    ):
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
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:battery-charging-low",
            gain=1000,
            precision=2,
            min=0,
            max=rated_discharging_power,
        )
        self._mode = mode

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        assert self._mode.state_topic and not self._mode.state_topic.isspace(), "RemoteEMSControlMode state_topic has not been configured"
        self._remote_ems_control_mode_topic = self._mode.state_topic
        self._sensor_availablity_topic = f"{base}/availability"
        self["availability"].append({"topic": self._sensor_availablity_topic})
        return base

    def observable_topics(self) -> set[str]:
        topics = super().observable_topics()
        topics.add(self._remote_ems_control_mode_topic)
        return topics

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source == self._remote_ems_control_mode_topic:
            if self._sensor_availablity_topic is None:
                logging.error(f"Sensor {self.name} availability topic is not configured??")
                return False
            else:
                mqtt.publish(self._sensor_availablity_topic, "online" if value == 5 or value == 6 else "offline")
                return True
        else:
            return False


class PVMaxPowerLimit(NumericSensor, HybridInverter):
    # This register will take effect when Remote EMS Control Mode (40031) is 3, 4, 5 or 6.
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin, mode: RemoteEMSControlMode):
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
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:solar-power",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )
        self._mode = mode

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        assert self._mode.state_topic and not self._mode.state_topic.isspace(), "RemoteEMSControlMode state_topic has not been configured"
        self._remote_ems_control_mode_topic = self._mode.state_topic
        self._sensor_availablity_topic = f"{base}/availability"
        self["availability"].append({"topic": self._sensor_availablity_topic})
        return base

    def observable_topics(self) -> set[str]:
        topics = super().observable_topics()
        topics.add(self._remote_ems_control_mode_topic)
        return topics

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source == self._remote_ems_control_mode_topic:
            if self._sensor_availablity_topic is None:
                logging.error(f"Sensor {self.name} availability topic is not configured??")
                return False
            else:
                mqtt.publish(self._sensor_availablity_topic, "online" if value == 3 or value == 4 or value == 5 or value == 6 else "offline")
                return True
        else:
            return False


class GridMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Grid Max Export Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40038,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-export",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )


class GridMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="Grid Max Import Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_grid_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40040,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-import",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )


class PCSMaxExportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="PCS Max Export Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_export_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40042,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-export",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )


class PCSMaxImportLimit(NumericSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, remote_ems: RemoteEMSMixin):
        super().__init__(
            remote_ems=remote_ems,
            name="PCS Max Import Limit",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_plant_pcs_max_import_limit",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=247,
            address=40044,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-import",
            gain=1000,
            precision=2,
            min=0,
            max=4294967.0,
        )
