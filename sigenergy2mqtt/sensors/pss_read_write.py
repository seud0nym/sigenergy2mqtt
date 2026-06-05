"""PSS (Power Storage System) read-write sensors."""

from __future__ import annotations

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import WriteOnlySensor


class PSSMVCabinetG3CircuitBreakerSwitchOn(WriteOnlySensor, NonInverter):
    ADDRESS = 42500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G3 Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_cabinet_g3_switch_on",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="on",
            name_off="",
            name_on="Switch MV Cabinet G3 Circuit Breaker On",
            icon_off="mdi:power-off",
            icon_on="mdi:power-on",
        )


class PSSMVCabinetG3CircuitBreakerSwitchOff(WriteOnlySensor, NonInverter):
    ADDRESS = 42501

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G3 Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_cabinet_g3_switch_off",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="off",
            name_off="",
            name_on="Switch MV Cabinet G3 Circuit Breaker Off",
            icon_on="mdi:power-off",
            icon_off="mdi:power-on",
        )


class PSSLALowVoltageCabinetCircuitBreakerSwitchOn(WriteOnlySensor, NonInverter):
    ADDRESS = 42502

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Cabinet Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_low_voltage_cabinet_switch_on",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="on",
            name_off="",
            name_on="Switch LA Low Voltage Cabinet Circuit Breaker On",
            icon_off="mdi:power-off",
            icon_on="mdi:power-on",
        )


class PSSLALowVoltageCabinetCircuitBreakerSwitchOff(WriteOnlySensor, NonInverter):
    ADDRESS = 42503

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Cabinet Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_low_voltage_cabinet_switch_off",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="off",
            name_off="",
            name_on="Switch LA Low Voltage Cabinet Circuit Breaker Off",
            icon_on="mdi:power-off",
            icon_off="mdi:power-on",
        )


class PSSLBLowVoltageCabinetCircuitBreakerSwitchOn(WriteOnlySensor, NonInverter):
    ADDRESS = 42504

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Cabinet Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_low_voltage_cabinet_switch_on",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="on",
            name_off="",
            name_on="Switch LB Low Voltage Cabinet Circuit Breaker On",
            icon_off="mdi:power-off",
            icon_on="mdi:power-on",
        )


class PSSLBLowVoltageCabinetCircuitBreakerSwitchOff(WriteOnlySensor, NonInverter):
    ADDRESS = 42505

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Low Voltage Cabinet Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_low_voltage_cabinet_switch_off",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            protocol_version=Protocol.V2_9,
            payload_off="no-action",
            payload_on="off",
            name_off="",
            name_on="Switch LB Low Voltage Cabinet Circuit Breaker Off",
            icon_on="mdi:power-off",
            icon_off="mdi:power-on",
        )
