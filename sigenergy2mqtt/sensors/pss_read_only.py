"""PSS (Power Storage System) read-only sensors."""

from __future__ import annotations

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfFrequency, UnitOfPower, UnitOfReactivePower, UnitOfTemperature
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import NumericSensor, ReadOnlySensor, ScanInterval


class PSSModelType(ReadOnlySensor, NonInverter):
    ADDRESS = 32500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PSS Model Type",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_model_type",
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
            icon="mdi:information-outline",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )


class PSSSerialNumber(ReadOnlySensor, NonInverter):
    ADDRESS = 32515

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PSS Serial Number",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_serial_number",
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
            icon="mdi:identifier",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )


class PSS_MVPhaseACurrent(NumericSensor, NonInverter):
    ADDRESS = 32531

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [MV] Phase A Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_phase_a_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_MVPhaseBCurrent(NumericSensor, NonInverter):
    ADDRESS = 32533

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [MV] Phase B Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_phase_b_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_MVPhaseCCurrent(NumericSensor, NonInverter):
    ADDRESS = 32535

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [MV] Phase C Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_phase_c_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_MVFrequency(NumericSensor, NonInverter):
    ADDRESS = 32539

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [MV] Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=None,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_MVTemperature(NumericSensor, NonInverter):
    ADDRESS = 32540

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [MV] Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            state_class=None,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSS_LAPhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 32553

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [LA] Phase A Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_LAPhaseAActivePower(NumericSensor, NonInverter):
    ADDRESS = 32571

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [LA] Phase A Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_LATotalActivePower(NumericSensor, NonInverter):
    ADDRESS = 32577

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [LA] Total Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_total_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_LATotalReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32585

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [LA] Total Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_total_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=None,
            state_class=None,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSS_LAFrequency(NumericSensor, NonInverter):
    ADDRESS = 32599

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PSS [LA] Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=None,
            state_class=None,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )
