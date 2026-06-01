"""PSS (Power Storage System) read-write sensors."""

from __future__ import annotations

from sigenergy2mqtt.common import InputType, Protocol
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import ScanInterval, SelectSensor


class PSSMVCabinetG3CircuitBreakerSwitchOn(SelectSensor, NonInverter):
    ADDRESS = 42500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS MV Cabinet G3 Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_cabinet_g3_switch_on",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch On"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )


class PSSMVCabinetG3CircuitBreakerSwitchOff(SelectSensor, NonInverter):
    ADDRESS = 42501

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS MV Cabinet G3 Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_cabinet_g3_switch_off",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch Off"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )


class PSSLALowVoltageCabinetCircuitBreakerSwitchOn(SelectSensor, NonInverter):
    ADDRESS = 42502

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS LA Low Voltage Cabinet Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_low_voltage_cabinet_switch_on",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch On"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )


class PSSLALowVoltageCabinetCircuitBreakerSwitchOff(SelectSensor, NonInverter):
    ADDRESS = 42503

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS LA Low Voltage Cabinet Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_low_voltage_cabinet_switch_off",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch Off"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )


class PSSLBLowVoltageCabinetCircuitBreakerSwitchOn(SelectSensor, NonInverter):
    ADDRESS = 42504

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS LB Low Voltage Cabinet Circuit Breaker Switch On",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_low_voltage_cabinet_switch_on",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch On"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )


class PSSLBLowVoltageCabinetCircuitBreakerSwitchOff(SelectSensor, NonInverter):
    ADDRESS = 42505

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS LB Low Voltage Cabinet Circuit Breaker Switch Off",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_low_voltage_cabinet_switch_off",
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            options=["No Action", "Switch Off"],
            scan_interval=ScanInterval.low(plant_index),
            protocol_version=Protocol.V2_9,
        )
