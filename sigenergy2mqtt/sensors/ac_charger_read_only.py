from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, StateClass, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import DiscoveryKeys, ScanInterval

from .base import AlarmCombinedSensor, AlarmSensor, ReadOnlySensor

# 5.5 AC-Charger running information address definition (read-only register)


class ACChargerRunningState(ReadOnlySensor):
    ADDRESS = 32000

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running State",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_running_state",
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
            icon="mdi:ev-station",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_0,
        )
        options: list[str] = [  # https://www.mathworks.com/help/autoblks/ug/charge-an-electric-vehicle.html
            "Initialising",  # 0: System init - System is initialising # Not part of the IEC 61851-1 standard
            "EV not connected",  # 1: A1/A2 - Vehicle is not connected
            "Charger and EV not ready",  # 2: B1 - Vehicle connected and not ready to accept energy, Charger not ready to supply energy
            "Charger ready; EV not ready",  # 3: B2 - Vehicle connected and not ready to accept energy, Charger ready to supply energy
            "Charger not ready; EV ready",  # 4: C1 - Vehicle connected and ready to accept energy, EV does not require charging area ventilation, Charger not ready to supply energy
            "Charging",  # 5: C2 - Vehicle connected and ready to accept energy, EV does not require charging area ventilation, Charger ready to supply energy
            "Fault",  # 6: F - Fault Other Charger problem (can be intentionally set by the Charger, for example, that maintenance is required)
            "Error",  # 7: E - Error Charger disconnected from vehicle / Charger disconnected from utility, Charger loss of utility power or control pilot short to control pilot reference
        ]
        self["enabled_by_default"] = True
        self[DiscoveryKeys.OPTIONS] = options
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            else:
                return f"Unknown State code: {value}"
        else:
            return f"Unknown State code: {value}"


class ACChargerTotalEnergyConsumed(ReadOnlySensor):
    ADDRESS = 32001

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Total Energy Consumed",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_total_energy_consumed",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.high(plant_index),
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
        )
        self["enabled_by_default"] = True


class ACChargerChargingPower(ReadOnlySensor):
    ADDRESS = 32003

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Charging Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.realtime(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_0,
        )
        self["enabled_by_default"] = True


class ACChargerRatedPower(ReadOnlySensor):
    ADDRESS = 32005

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerRatedCurrent(ReadOnlySensor):
    ADDRESS = 32007

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Current",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerRatedVoltage(ReadOnlySensor):
    ADDRESS = 32009

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Voltage",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_0,
        )


class ACChargerInputBreaker(ReadOnlySensor):
    ADDRESS = 32010

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Input Breaker",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_input_breaker",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=ScanInterval.low(plant_index),
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerAlarm1(AlarmSensor):
    ADDRESS = 32012

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 1",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="EVAC",
            protocol_version=Protocol.V2_0,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Grid over-voltage"
            case 1:
                return "Grid under-voltage"
            case 2:
                return "Overload"
            case 3:
                return "Short circuit"
            case 4:
                return "Charging output over-current"
            case 5:
                return "Leak current out of limit"
            case 6:
                return "Grounding fault"
            case 7:
                return "Abnormal phase sequence of grid wiring"
            case 8:
                return "PEN Fault"
            case _:
                return None


class ACChargerAlarm2(AlarmSensor):
    ADDRESS = 32013

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 2",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="EVAC",
            protocol_version=Protocol.V2_0,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Leak current detection circuit fault"
            case 1:
                return "Relay stuck"
            case 2:
                return "Pilot circuit fault"
            case 3:
                return "Auxiliary power supply module fault"
            case 4:
                return "Electric lock fault"
            case 5:
                return "Lamp panel communication fault"
            case _:
                return None


class ACChargerAlarm3(AlarmSensor):
    ADDRESS = 32014

    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 3",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_3",
            plant_index=plant_index,
            device_address=device_address,
            address=self.ADDRESS,
            alarm_type="EVAC",
            protocol_version=Protocol.V2_0,
        )

    def decode_alarm_bit(self, bit_position: int):
        match bit_position:
            case 0:
                return "Too high internal temperature"
            case 1:
                return "Charging cable fault"
            case 2:
                return "Meter communication fault"
            case _:
                return None


class ACChargerAlarms(AlarmCombinedSensor):
    def __init__(self, plant_index: int, device_address: int, *alarms: AlarmSensor):
        super().__init__(
            "Alarms",
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            *alarms,
        )
