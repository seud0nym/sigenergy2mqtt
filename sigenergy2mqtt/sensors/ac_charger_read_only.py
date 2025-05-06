from .base import AlarmCombinedSensor, AlarmSensor, DeviceClass, InputType, ReadOnlySensor
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower


# 5.5 AC-Charger running information address definition (read-only register)


class ACChargerRunningState(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Running State",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_running_state",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32000,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:ev-station",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        """ https://www.mathworks.com/help/autoblks/ug/charge-an-electric-vehicle.html
        0: System init - System is initialising # Not part of the IEC 61851-1 standard
        1: A1/A2 - Vehicle is not connected # A1: Charger not ready, A2: Charger ready
        2: B1 - Vehicle connected and not ready to accept energy, Charger not ready to supply energy
        3: B2 - Vehicle connected and not ready to accept energy, Charger ready to supply energy
        4: C1 - Vehicle connected and ready to accept energy, EV does not require charging area ventilation, Charger not ready to supply energy
        5: C2 - Vehicle connected and ready to accept energy, EV does not require charging area ventilation, Charger ready to supply energy
        6: F - Fault Other Charger problem (can be intentionally set by the Charger, for example, that maintenance is required)
        7: E - Error Charger disconnected from vehicle / Charger disconnected from utility, Charger loss of utility power or control pilot short to control pilot reference
        """
        if raw:
            return value
        elif value is None:
            return None
        else:
            match value:
                case 0:
                    return "Initialising"
                case 1:
                    return "EV not connected"
                case 2:
                    return "Charger and EV not ready"
                case 3:
                    return "Charger ready; EV not ready"
                case 4:
                    return "Charger not ready; EV ready"
                case 5:
                    return "Charging"
                case 6:
                    return "Fault"
                case 7:
                    return "Error"
                case _:
                    return f"Unknown State code: {value}"


class ACChargerTotalEnergyConsumed(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Total Energy Consumed",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_total_energy_consumed",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32001,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True


class ACChargerChargingPower(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Charging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32003,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=10,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
        )
        self["enabled_by_default"] = True


class ACChargerRatedPower(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Rated Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32005,
            count=2,
            data_type=ModbusClient.DATATYPE.UINT32,
            scan_interval=600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
        )


class ACChargerRatedCurrent(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Rated Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32007,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=600,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
        )


class ACChargerRatedVoltage(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Rated Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32009,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=600,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
        )


class ACChargerInputBreaker(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Input Breaker",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_input_breaker",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32010,
            count=2,
            data_type=ModbusClient.DATATYPE.INT32,
            scan_interval=600,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
        )


class ACChargerAlarm1(AlarmSensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Alarm 1",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=32012,
        )

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:
            case 0:
                return "5001_1: Grid overvoltage"
            case 1:
                return "5001_2: Grid undervoltage"
            case 2:
                return "5001_3: Overload"
            case 3:
                return "5001_4: Short circuit"
            case 4:
                return "5001_5: Charging output overcurrent"
            case 5:
                return "5001_6: Leak current out of limit"
            case 6:
                return "5001_7: Grounding fault"
            case 7:
                return "5001_8: Abnormal phase sequence of grid wiring"
            case 8:
                return "5001_9: PEN Fault"
            case _:
                return None


class ACChargerAlarm2(AlarmSensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Alarm 2",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=32013,
        )

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:
            case 0:
                return "5002_1: Leak current detection circuit fault"
            case 1:
                return "5002_2: Relay stuck"
            case 2:
                return "5002_3: Pilot circuit fault"
            case 3:
                return "5002_4: Auxiliary power supply module fault"
            case 4:
                return "5002_5: Electric lock fault"
            case 5:
                return "5002_6: Lamp panel communication fault"
            case _:
                return None


class ACChargerAlarm3(AlarmSensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="AC Charger Alarm 3",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_3",
            plant_index=plant_index,
            device_address=device_address,
            address=32014,
        )

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:
            case 0:
                return "5003: Too high internal temperature"
            case 1:
                return "5004: Charging cable fault"
            case 2:
                return "5005: Meter communication fault"
            case _:
                return None


class ACChargerAlarms(AlarmCombinedSensor):
    def __init__(self, plant_index: int, device_address: int, *alarms: AlarmSensor):
        super().__init__(
            "Alarms",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            *alarms,
        )
