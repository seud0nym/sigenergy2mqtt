"""PID (Power Inverter Device) read-only sensors."""

from __future__ import annotations

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfFrequency, UnitOfTemperature
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import NumericSensor, ReadOnlySensor, ScanInterval


class PIDModelType(ReadOnlySensor, NonInverter):
    ADDRESS = 33000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Model Type",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_model_type",
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


class PIDSerialNumber(ReadOnlySensor, NonInverter):
    ADDRESS = 33015

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Serial Number",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_serial_number",
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


class PIDMachineFirmwareVersion(ReadOnlySensor, NonInverter):
    ADDRESS = 33025

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Machine Firmware Version",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_firmware_version",
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


class PIDCommunicationStatus(ReadOnlySensor, NonInverter):
    ADDRESS = 33040

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Communication Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_communication_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:wifi",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )


class PIDRunningStatus(ReadOnlySensor, NonInverter):
    ADDRESS = 33041

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="PID Running Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_running_status",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:run",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )


class PID_ABLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33042

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID AB Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_ab_line_voltage",
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


class PID_BCLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33044

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID BC Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_bc_line_voltage",
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


class PID_CALineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33046

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID CA Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_ca_line_voltage",
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


class PID_PhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 33048

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Phase A Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_phase_a_voltage",
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


class PID_PhaseBVoltage(NumericSensor, NonInverter):
    ADDRESS = 33050

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Phase B Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_phase_b_voltage",
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


class PID_PhaseCVoltage(NumericSensor, NonInverter):
    ADDRESS = 33052

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Phase C Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_phase_c_voltage",
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


class PID_GridFrequency(NumericSensor, NonInverter):
    ADDRESS = 33054

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Grid Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_grid_frequency",
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


class PID_OutputVoltage(NumericSensor, NonInverter):
    ADDRESS = 33055

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Output Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_output_voltage",
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
            icon="mdi:lightning-bolt",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PID_BusVoltage(NumericSensor, NonInverter):
    ADDRESS = 33056

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Bus Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_bus_voltage",
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
            icon="mdi:lightning-bolt",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PID_InverterVoltage(NumericSensor, NonInverter):
    ADDRESS = 33057

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Inverter Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_inverter_voltage",
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


class PID_InverterCurrent(NumericSensor, NonInverter):
    ADDRESS = 33059

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Inverter Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_inverter_current",
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
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PID_OutputCurrent(NumericSensor, NonInverter):
    ADDRESS = 33060

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Output Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_output_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PID_InternalTemperature1(NumericSensor, NonInverter):
    ADDRESS = 33061

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Internal Temperature 1",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_internal_temperature_1",
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


class PID_InternalTemperature2(NumericSensor, NonInverter):
    ADDRESS = 33062

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Internal Temperature 2",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_internal_temperature_2",
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


class PID_InternalTemperature3(NumericSensor, NonInverter):
    ADDRESS = 33063

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Internal Temperature 3",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_internal_temperature_3",
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


class PID_InternalTemperature4(NumericSensor, NonInverter):
    ADDRESS = 33064

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Internal Temperature 4",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_internal_temperature_4",
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


class PID_InternalTemperature5(NumericSensor, NonInverter):
    ADDRESS = 33065

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="PID Internal Temperature 5",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_internal_temperature_5",
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
