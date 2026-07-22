from __future__ import annotations

from sigenergy2mqtt.common import (
    PERCENTAGE,
    DeviceClass,
    InputType,
    Protocol,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactiveEnergy,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from sigenergy2mqtt.common.types import NonInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmSensor, DiscoveryKeys, NumericSensor, ReadOnlySensor, ScanInterval


class PSSModelType(ReadOnlySensor, NonInverter):
    ADDRESS = 32500

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Model Type",
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
        self["entity_category"] = "diagnostic"


class PSSSerialNumber(ReadOnlySensor, NonInverter):
    ADDRESS = 32515

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Serial Number",
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
        self["entity_category"] = "diagnostic"


class PSSCommunicationStatus(ReadOnlySensor, NonInverter):
    ADDRESS = 32525

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Communication Status",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_communication_status",
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


class PSSTeleindication1(AlarmSensor):
    ADDRESS = 32526

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Teleindication1",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_teleindication_1",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PSS",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Measurement & control unit general trip"
            case 1:
                return "Measurement & control unit general alarm"
            case 2:
                return "Transformer heavy gas trip"
            case 3:
                return "Transformer light gas alarm"
            case 4:
                return "Transformer pressure relief trip"
            case 5:
                return "Transformer low oil level alarm"
            case 6:
                return "Transformer high oil level alarm"
            case 7:
                return "Transformer oil high temperature alarm"
            case 8:
                return "Transformer oil over-temperature trip"
            case 9:
                return "Transformer winding high temperature alarm"
            case 10:
                return "Transformer winding over-temperature trip"
            case 11:
                return "Low voltage room dual smoke sensor trip"
            case 12:
                return "Medium voltage room dual smoke sensor trip"
            case 13:
                return "Low voltage room maintenance door open trip"
            case 14:
                return "Transformer room door open trip"
            case 15:
                return "LA low voltage cabinet over-temperature trip"
            case _:
                return None


class PSSTeleindication2(AlarmSensor):
    ADDRESS = 32527

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Teleindication2",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_teleindication_2",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PSS",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "LB low voltage cabinet over-temperature trip"
            case 1:
                return "Medium voltage room over-temperature trip"
            case 2:
                return "Medium voltage cabinet insulation gas low pressure alarm"
            case 3:
                return "Emergency stop"
            case 4:
                return "Medium voltage room air conditioner/heat exchanger fault"
            case 5:
                return "LA Low voltage room heat exchanger fault"
            case 6:
                return "LB Low voltage room heat exchanger fault"
            case 7:
                return "Low voltage room smoke sensor alarm"
            case 8:
                return "Medium voltage room smoke sensor alarm"
            case 9:
                return "Medium voltage cabinet G3 circuit breaker switch-off failure"
            case 10:
                return "LA low voltage cabinet SPD fault"
            case 11:
                return "LB low voltage cabinet SPD fault"
            case 12:
                return "Distribution cabinet SPD fault"
            case 13:
                return "LA low voltage cabinet over-temperature alarm"
            case 14:
                return "LB low voltage cabinet over-temperature alarm"
            case 15:
                return "Medium voltage room over-temperature alarm"
            case _:
                return None


class PSSTeleindication3(AlarmSensor):
    ADDRESS = 32528

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Teleindication3",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_teleindication_3",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PSS",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "LA low voltage cabinet IMD pre-alarm"
            case 1:
                return "LA low voltage cabinet IMD alarm"
            case 2:
                return "LB low voltage cabinet IMD pre-alarm"
            case 3:
                return "LB low voltage cabinet IMD alarm"
            case 4:
                return "UPS fault alarm"
            case 5:
                return "LA low voltage cabinet circuit breaker switch-on"
            case 6:
                return "LA low voltage cabinet circuit breaker switch-off"
            case 7:
                return "LA low voltage cabinet circuit breaker fault trip"
            case 8:
                return "LA low voltage cabinet circuit breaker remote control"
            case 9:
                return "LB low voltage cabinet circuit breaker switch-on"
            case 10:
                return "LB low voltage cabinet circuit breaker switch-off"
            case 11:
                return "LB low voltage cabinet circuit breaker fault trip"
            case 12:
                return "LB low voltage cabinet circuit breaker remote control"
            case 13:
                return "Medium voltage cabinet G3 circuit breaker switch-on"
            case 14:
                return "Medium voltage cabinet G3 circuit breaker switch-off"
            case 15:
                return "Medium voltage cabinet G3 disconnector switch switch-on"
            case _:
                return None


class PSSTeleindication4(AlarmSensor):
    ADDRESS = 32529

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Teleindication4",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_teleindication_4",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PSS",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Medium voltage cabinet G3 disconnector switch switch-off"
            case 1:
                return "Medium voltage cabinet G3 earthing switch switch-on"
            case 2:
                return "Medium voltage cabinet G3 earthing switch switch-off"
            case 3:
                return "Medium voltage cabinet G3 energy storage coil not charged"
            case 4:
                return "Medium voltage cabinet G3 circuit breaker remote control"
            case 5:
                return "Medium voltage cabinet G1 load switch switch-on"
            case 6:
                return "Medium voltage cabinet G1 load switch switch-off"
            case 7:
                return "Medium voltage cabinet G1 earthing switch switch-on"
            case 8:
                return "Medium voltage cabinet G1 earthing switch switch-off"
            case 9:
                return "Medium voltage cabinet G2 load switch switch-on"
            case 10:
                return "Medium voltage cabinet G2 load switch switch-off"
            case 11:
                return "Medium voltage cabinet G2 earthing switch switch-on"
            case 12:
                return "Medium voltage cabinet G2 earthing switch switch-off"
            case 13:
                return "Low voltage room LA operation door open"
            case 14:
                return "Low voltage room LB operation door open"
            case 15:
                return "Medium voltage room door open"
            case _:
                return None


class PSSTeleindication5(AlarmSensor):
    ADDRESS = 32530

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Teleindication5",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_teleindication_5",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="PSS",
            protocol_version=Protocol.V2_9,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Medium voltage cabinet G1 cable L1 phase over-temperature"
            case 1:
                return "Medium voltage cabinet G1 cable L2 phase over-temperature"
            case 2:
                return "Medium voltage cabinet G1 cable L3 phase over-temperature"
            case 3:
                return "Medium voltage cabinet G2 cable L1 phase over-temperature"
            case 4:
                return "Medium voltage cabinet G2 cable L2 phase over-temperature"
            case 5:
                return "Medium voltage cabinet G2 cable L3 phase over-temperature"
            case 6:
                return "Medium voltage cabinet G3 cable L1 phase over-temperature"
            case 7:
                return "Medium voltage cabinet G3 cable L2 phase over-temperature"
            case 8:
                return "Medium voltage cabinet G3 cable L3 phase over-temperature"
            case 9:
                return "Medium voltage protection general protection"
            case 10:
                return "Medium voltage protection general alarm"
            case _:
                return None


class PSSMVPhaseACurrent(NumericSensor, NonInverter):
    ADDRESS = 32531

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Current",
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
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSMVPhaseBCurrent(NumericSensor, NonInverter):
    ADDRESS = 32533

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Current",
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
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSMVPhaseCCurrent(NumericSensor, NonInverter):
    ADDRESS = 32535

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Current",
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
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSMVZeroSequenceCurrent(NumericSensor, NonInverter):
    ADDRESS = 32537

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Zero Sequence Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_zero_sequence_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSMVFrequency(NumericSensor, NonInverter):
    ADDRESS = 32539

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSMVTemperature(NumericSensor, NonInverter):
    ADDRESS = 32540

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Temperature",
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
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVHumidity(NumericSensor, NonInverter):
    ADDRESS = 32541

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Humidity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_humidity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.HUMIDITY,
            icon="mdi:water-percent",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG1CableL1PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32542

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G1 Cable L1 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g1_cable_l1_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG1CableL2PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32543

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G1 Cable L2 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g1_cable_l2_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG1CableL3PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32544

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G1 Cable L3 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g1_cable_l3_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG2CableL1PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32545

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G2 Cable L1 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g2_cable_l1_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG2CableL2PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32546

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G2 Cable L2 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g2_cable_l2_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG2CableL3PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32547

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G2 Cable L3 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g2_cable_l3_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG3CableL1PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32548

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G3 Cable L1 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g3_cable_l1_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG3CableL2PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32549

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G3 Cable L2 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g3_cable_l2_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSMVG3CableL3PhaseTemperature(NumericSensor, NonInverter):
    ADDRESS = 32550

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="G3 Cable L3 Phase Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_mv_g3_cable_l3_phase_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSLATemperature(NumericSensor, NonInverter):
    ADDRESS = 32551

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSLAHumidity(NumericSensor, NonInverter):
    ADDRESS = 32552

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Humidity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_humidity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.HUMIDITY,
            icon="mdi:water-percent",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 32553

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Voltage",
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
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBVoltage(NumericSensor, NonInverter):
    ADDRESS = 32555

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCVoltage(NumericSensor, NonInverter):
    ADDRESS = 32557

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAABLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32559

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="AB Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_ab_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLABCLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32561

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="BC Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_bc_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLACALineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32563

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="CA Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_ca_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseACurrent(NumericSensor, NonInverter):
    ADDRESS = 32565

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBCurrent(NumericSensor, NonInverter):
    ADDRESS = 32567

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCCurrent(NumericSensor, NonInverter):
    ADDRESS = 32569

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseAActivePower(NumericSensor, NonInverter):
    ADDRESS = 32571

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Active Power",
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
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBActivePower(NumericSensor, NonInverter):
    ADDRESS = 32573

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCActivePower(NumericSensor, NonInverter):
    ADDRESS = 32575

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLATotalActivePower(NumericSensor, NonInverter):
    ADDRESS = 32577

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Active Power",
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
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseAReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32579

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32581

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32583

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLATotalReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32585

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_total_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseAApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32587

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32589

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32591

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLATotalApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32593

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_total_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseAPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32595

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_a_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseBPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32596

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_b_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLAPhaseCPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32597

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_phase_c_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLATotalPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32598

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_total_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLAFrequency(NumericSensor, NonInverter):
    ADDRESS = 32599

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAForwardActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32600

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_forward_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAReverseActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32604

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_reverse_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAForwardReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32608

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_forward_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLAReverseReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32612

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_la_reverse_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBTemperature(NumericSensor, NonInverter):
    ADDRESS = 32616

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSLBHumidity(NumericSensor, NonInverter):
    ADDRESS = 32617

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Humidity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_humidity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.HUMIDITY,
            icon="mdi:water-percent",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 32618

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBVoltage(NumericSensor, NonInverter):
    ADDRESS = 32620

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCVoltage(NumericSensor, NonInverter):
    ADDRESS = 32622

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBABLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32624

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="AB Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_ab_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBBCLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32626

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="BC Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_bc_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBCALineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32628

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="CA Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_ca_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseACurrent(NumericSensor, NonInverter):
    ADDRESS = 32630

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBCurrent(NumericSensor, NonInverter):
    ADDRESS = 32632

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCCurrent(NumericSensor, NonInverter):
    ADDRESS = 32634

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseAActivePower(NumericSensor, NonInverter):
    ADDRESS = 32636

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBActivePower(NumericSensor, NonInverter):
    ADDRESS = 32638

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCActivePower(NumericSensor, NonInverter):
    ADDRESS = 32640

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBTotalActivePower(NumericSensor, NonInverter):
    ADDRESS = 32642

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_total_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseAReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32644

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32646

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32648

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBTotalReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32650

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_total_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseAApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32652

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32654

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32656

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBTotalApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32658

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_total_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseAPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32660

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_a_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseBPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32661

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_b_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLBPhaseCPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32662

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_phase_c_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLBTotalPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32663

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_total_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSLBFrequency(NumericSensor, NonInverter):
    ADDRESS = 32664

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBForwardActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32665

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_forward_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBReverseActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32669

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_reverse_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBForwardReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32673

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_forward_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSLBReverseReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32677

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_lb_reverse_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSTransformerOilSurfaceTemperature(NumericSensor, NonInverter):
    ADDRESS = 32681

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Oil Surface Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_transformer_oil_surface_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSTransformerWindingTemperature(NumericSensor, NonInverter):
    ADDRESS = 32682

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Winding Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_transformer_winding_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetTemperature(NumericSensor, NonInverter):
    ADDRESS = 32683

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Temperature",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_temperature",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=UnitOfTemperature.CELSIUS,
            device_class=DeviceClass.TEMPERATURE,
            icon="mdi:thermometer",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetHumidity(NumericSensor, NonInverter):
    ADDRESS = 32684

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Humidity",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_humidity",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.medium(plant_index),
            unit=PERCENTAGE,
            device_class=DeviceClass.HUMIDITY,
            icon="mdi:water-percent",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseAVoltage(NumericSensor, NonInverter):
    ADDRESS = 32685

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBVoltage(NumericSensor, NonInverter):
    ADDRESS = 32687

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCVoltage(NumericSensor, NonInverter):
    ADDRESS = 32689

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetABLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32691

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="AB Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_ab_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetBCLineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32693

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="BC Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_bc_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetCALineVoltage(NumericSensor, NonInverter):
    ADDRESS = 32695

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="CA Line Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_ca_line_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseACurrent(NumericSensor, NonInverter):
    ADDRESS = 32697

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBCurrent(NumericSensor, NonInverter):
    ADDRESS = 32699

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCCurrent(NumericSensor, NonInverter):
    ADDRESS = 32701

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseAActivePower(NumericSensor, NonInverter):
    ADDRESS = 32703

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBActivePower(NumericSensor, NonInverter):
    ADDRESS = 32705

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCActivePower(NumericSensor, NonInverter):
    ADDRESS = 32707

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetTotalActivePower(NumericSensor, NonInverter):
    ADDRESS = 32709

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Active Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_total_active_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseAReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32711

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32713

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32715

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetTotalReactivePower(NumericSensor, NonInverter):
    ADDRESS = 32717

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Reactive Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_total_reactive_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
            device_class=DeviceClass.REACTIVE_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseAApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32719

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32721

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32723

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetTotalApparentPower(NumericSensor, NonInverter):
    ADDRESS = 32725

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Apparent Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_total_apparent_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfApparentPower.KILOVOLT_AMPERE,
            device_class=DeviceClass.APPARENT_POWER,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseAPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32727

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase A Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_a_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseBPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32728

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase B Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_b_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetPhaseCPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32729

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Phase C Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_phase_c_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetTotalPowerFactor(NumericSensor, NonInverter):
    ADDRESS = 32730

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Total Power Factor",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_total_power_factor",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.INT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=None,
            device_class=DeviceClass.POWER_FACTOR,
            icon="mdi:angle-acute",
            gain=1000,
            precision=3,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetFrequency(NumericSensor, NonInverter):
    ADDRESS = 32731

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Frequency",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_frequency",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfFrequency.HERTZ,
            device_class=DeviceClass.FREQUENCY,
            icon="mdi:sine-wave",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetForwardActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32732

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_forward_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetReverseActiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32736

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Active Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_reverse_active_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetForwardReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32740

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Forward Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_forward_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )


class PSSDistributionCabinetReverseReactiveEnergy(NumericSensor, NonInverter):
    ADDRESS = 32744

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            availability_control_sensor=None,
            name="Reverse Reactive Energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_pss_{device_address}_distribution_cabinet_reverse_reactive_energy",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=4,
            data_type=ModbusDataType.UINT64,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
            device_class=DeviceClass.REACTIVE_ENERGY,
            icon="mdi:lightning-bolt",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_9,
        )
