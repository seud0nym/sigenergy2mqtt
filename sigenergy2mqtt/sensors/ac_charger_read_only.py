from typing import cast

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus.types import ModbusDataType

from .base import AlarmCombinedSensor, AlarmSensor, DeviceClass, InputType, ReadOnlySensor
from .const import StateClass, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower

# 5.5 AC-Charger running information address definition (read-only register)


class ACChargerRunningState(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Running State",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_running_state",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32000,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=Config.modbus[plant_index].scan_interval.high if plant_index < len(Config.modbus) else 10,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:ev-station",
            gain=None,
            precision=None,
            protocol_version=Protocol.V2_0,
        )
        self["enabled_by_default"] = True
        self["options"] = [
            "Initialising",  # 0
            "EV not connected",  # 1
            "Charger and EV not ready",  # 2
            "Charger ready; EV not ready",  # 3
            "Charger not ready; EV ready",  # 4
            "Charging",  # 5
            "Fault",  # 6
            "Error",  # 7
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self["options"])) - 1  # pyrefly: ignore

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
        elif isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            else:
                return f"Unknown State code: {value}"
        else:
            return f"Unknown State code: {value}"


class ACChargerTotalEnergyConsumed(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Total Energy Consumed",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_total_energy_consumed",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32001,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=Config.modbus[plant_index].scan_interval.high if plant_index < len(Config.modbus) else 10,
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
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Charging Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_charging_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32003,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=Config.modbus[plant_index].scan_interval.realtime if plant_index < len(Config.modbus) else 5,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_0,
        )
        self["enabled_by_default"] = True


class ACChargerRatedPower(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_power",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32005,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=Config.modbus[plant_index].scan_interval.low if plant_index < len(Config.modbus) else 600,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:car-electric",
            gain=1000,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerRatedCurrent(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32007,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=Config.modbus[plant_index].scan_interval.low if plant_index < len(Config.modbus) else 600,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerRatedVoltage(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Rated Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_rated_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32009,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=Config.modbus[plant_index].scan_interval.low if plant_index < len(Config.modbus) else 600,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:car-electric",
            gain=10,
            precision=1,
            protocol_version=Protocol.V2_0,
        )


class ACChargerInputBreaker(ReadOnlySensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Input Breaker",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_input_breaker",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=32010,
            count=2,
            data_type=ModbusDataType.INT32,
            scan_interval=Config.modbus[plant_index].scan_interval.low if plant_index < len(Config.modbus) else 600,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:car-electric",
            gain=100,
            precision=2,
            protocol_version=Protocol.V2_0,
        )


class ACChargerAlarm1(AlarmSensor):
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 1",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_1",
            plant_index=plant_index,
            device_address=device_address,
            address=32012,
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
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 2",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_2",
            plant_index=plant_index,
            device_address=device_address,
            address=32013,
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
    def __init__(self, plant_index: int, device_address: int):
        super().__init__(
            name="Alarm 3",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm_3",
            plant_index=plant_index,
            device_address=device_address,
            address=32014,
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
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_ac_charger_{device_address}_alarm",
            *alarms,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Modbus Registers 32012-32014"
        return attributes
