from __future__ import annotations

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfFrequency, UnitOfTemperature
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, DiscoveryKeys, NumericSensor, ReadOnlySensor, ScanInterval


class PIDModelType(ReadOnlySensor, NonInverter):
    ADDRESS = 33000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Model Type",
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
            name="Serial Number",
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
            name="Firmware Version",
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
            name="Communication Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_communication_status",
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
            icon="mdi:wifi",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )
        options: list[str] = [
            "Loading",  # 0
            "Offline",  # 1
            "Online",  # 2
        ]
        self[DiscoveryKeys.OPTIONS] = options
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1


class PIDRunningStatus(ReadOnlySensor, NonInverter):
    ADDRESS = 33041

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_running_status",
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
            icon="mdi:run",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_9,
        )
        options: list[str] = [
            "Idle",  # 0
            "Fault",  # 1
            "IMD Detection",  # 2
            "PID Compensation",  # 3
        ]
        self[DiscoveryKeys.OPTIONS] = options
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1


class PIDABLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33042

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="AB Line Voltage",
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


class PIDBCLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33044

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="BC Line Voltage",
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


class PIDCALineVoltage(NumericSensor, NonInverter):
    ADDRESS = 33046

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="CA Line Voltage",
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


class PIDPhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 33048

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Voltage",
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


class PIDPhaseBVoltage(NumericSensor, NonInverter):
    ADDRESS = 33050

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Voltage",
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


class PIDPhaseCVoltage(NumericSensor, NonInverter):
    ADDRESS = 33052

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Voltage",
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


class PIDGridFrequency(NumericSensor, NonInverter):
    ADDRESS = 33054

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Grid Frequency",
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


class PIDOutputVoltage(NumericSensor, NonInverter):
    ADDRESS = 33055

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Output Voltage",
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


class PIDBusVoltage(NumericSensor, NonInverter):
    ADDRESS = 33056

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Bus Voltage",
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


class PIDInverterVoltage(NumericSensor, NonInverter):
    ADDRESS = 33057

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Inverter Voltage",
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


class PIDInverterCurrent(NumericSensor, NonInverter):
    ADDRESS = 33059

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Inverter Current",
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


class PIDOutputCurrent(NumericSensor, NonInverter):
    ADDRESS = 33060

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Output Current",
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


class PIDInternalTemperature1(NumericSensor, NonInverter):
    ADDRESS = 33061

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Internal Temperature 1",
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


class PIDInternalTemperature2(NumericSensor, NonInverter):
    ADDRESS = 33062

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Internal Temperature 2",
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


class PIDInternalTemperature3(NumericSensor, NonInverter):
    ADDRESS = 33063

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Internal Temperature 3",
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


class PIDInternalTemperature4(NumericSensor, NonInverter):
    ADDRESS = 33064

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Internal Temperature 4",
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


class PIDInternalTemperature5(NumericSensor, NonInverter):
    ADDRESS = 33065

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Internal Temperature 5",
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


class PIDAlarm1(AlarmSensor):
    ADDRESS = 33066

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 1",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PID",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Software version mismatch"
            case 1:
                return "Software and hardware version mismatch"
            case 2:
                return "Startup failure"
            case 3:
                return "Insulation resistance alarm"
            case 4:
                return "Insulation resistance pre-alarm"
            case 5:
                return "Over-temperature"
            case 6:
                return "Power module abnormal"
            case 7:
                return "Fan fault"
            case 8:
                return "Reserved"
            case 9:
                return "Inverter bus over-voltage protection"
            case 10:
                return "Output over-voltage protection"
            case 11:
                return "Inverter output over-voltage protection"
            case 12:
                return "Inverter output over-current protection"
            case 13:
                return "Output over-current protection"
            case 14:
                return "Output failure"
            case 15:
                return "Rs485 communication abnormal"
            case _:
                return None


class PIDAlarm2(AlarmSensor):
    ADDRESS = 33067

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 2",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PID",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Grid power loss"
            case 1:
                return "Grid over-voltage"
            case 2:
                return "Grid under-voltage"
            case 3:
                return "Grid over-frequency"
            case 4:
                return "Grid under-frequency"
            case _:
                return None


class PIDAlarms(AlarmCombinedSensor):
    def __init__(self, plant_index: int, device_address: int, *alarms: AlarmSensor):
        super().__init__(
            "Alarms",
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_pid_{device_address}_alarm",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pid_{device_address}_alarm",
            *alarms,
        )
