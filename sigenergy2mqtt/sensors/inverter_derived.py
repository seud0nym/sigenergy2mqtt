from .base import DeviceClass, EnergyDailyAccumulationSensor, PVCurrentSensor, PVVoltageSensor, StateClass, EnergyLifetimeAccumulationSensor, DerivedSensor, ModbusSensor
from .const import UnitOfPower
from .inverter_read_only import ChargeDischargePower, InverterPVPower
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.mqtt import MqttClient
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import logging


class InverterBatteryChargingPower(DerivedSensor):
    def __init__(self, plant_index: int, device_address: int, battery_power: ChargeDischargePower):
        super().__init__(
            name="Battery Charging Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_battery_charging_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_charging_power",
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-plus",
            gain=None,
            precision=2,
        )

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), ChargeDischargePower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self._precision),
        )
        return True


class InverterBatteryDischargingPower(DerivedSensor):
    def __init__(self, plant_index: int, device_address: int, battery_power: ChargeDischargePower):
        super().__init__(
            name="Battery Discharging Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_battery_discharging_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_discharging_power",
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-minus",
            gain=None,
            precision=2,
        )

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), ChargeDischargePower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] >= 0 else round(values[-1][1] * -1, self._precision),
        )
        return True


class InverterLifetimePVEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, device_address: int, source: InverterPVPower):
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_lifetime_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_lifetime_pv_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class InverterDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, device_address: int, source: InverterLifetimePVEnergy):
        super().__init__(
            name="Daily Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_daily_pv_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class PVStringPower(DerivedSensor):
    def __init__(self, plant_index: int, device_address: int, string_number: int, voltage: PVVoltageSensor, current: PVCurrentSensor):
        super().__init__(
            name="Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_power",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-lightning-bolt",
            gain=None,
            precision=2,
        )
        self.current: float = None
        self.current_gain: float = current.gain
        self.voltage: float = None
        self.voltage_gain: float = voltage.gain

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if self.voltage is None or self.current is None:
            if self._debug_logging:
                logging.debug(f"Publishing {self.__class__.__name__} SKIPPED - current={self.current} voltage={self.voltage}")
            return  # until all values populated, can't do calculation
        if self._debug_logging:
            logging.debug(f"Publishing {self.__class__.__name__} READY - current={self.current} voltage={self.voltage}")
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        self.voltage = None
        self.current = None

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if issubclass(type(sensor), PVVoltageSensor):
            self.voltage = values[-1][1] / self.voltage_gain
        elif issubclass(type(sensor), PVCurrentSensor):
            self.current = values[-1][1] / self.current_gain
        else:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        if self.voltage is None or self.current is None:
            return False  # until all values populated, can't do calculation
        self.set_latest_state(self.voltage * self.current)
        return True


class PVStringLifetimeEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, device_address: int, string_number: int, source: PVStringPower):
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_lifetime_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_lifetime_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class PVStringDailyEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, device_address: int, string_number: int, source: PVStringLifetimeEnergy):
        super().__init__(
            name="Daily Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_daily_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_daily_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )
