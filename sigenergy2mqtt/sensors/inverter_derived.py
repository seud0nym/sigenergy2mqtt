import logging
from dataclasses import dataclass, field
from typing import Any, Deque

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import DeviceClass, HybridInverter, PVInverter, StateClass, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

from .base import DerivedSensor, EnergyDailyAccumulationSensor, EnergyLifetimeAccumulationSensor, Sensor
from .inverter_read_only import ChargeDischargePower, PVCurrentSensor, PVVoltageSensor


class InverterBatteryChargingPower(DerivedSensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int, battery_power: ChargeDischargePower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        super().__init__(
            name="Battery Charging Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_battery_charging_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_charging_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-plus",
            gain=None,
            precision=2,
        )
        self.protocol_version = battery_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "ChargeDischargePower > 0"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, ChargeDischargePower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(0 if values[-1][1] <= 0 else values[-1][1])
        return True


class InverterBatteryDischargingPower(DerivedSensor, HybridInverter):
    def __init__(self, plant_index: int, device_address: int, battery_power: ChargeDischargePower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        super().__init__(
            name="Battery Discharging Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_battery_discharging_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_battery_discharging_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-minus",
            gain=None,
            precision=2,
        )
        self.protocol_version = battery_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "ChargeDischargePower < 0 × -1"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, ChargeDischargePower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(0 if values[-1][1] >= 0 else values[-1][1] * -1)
        return True


_MAX_PV_STRING_POWER_GAP_WARNING_SECONDS = 0.5


class PVStringPower(DerivedSensor, HybridInverter, PVInverter):
    @dataclass
    class Value:
        name: str = field(compare=False, repr=True)
        divisor: float
        value: float | None = None
        timestamp: float = 0

        def apply(self, values: Deque[tuple[float, Any]]) -> None:
            if self.value is not None:
                logging.warning(f"{self.name} Overwriting unconsumed value {self.value} (age={(values[-1][0] - self.timestamp):.2f}s)")
            self.value = values[-1][1] / self.divisor
            self.timestamp = values[-1][0]

    def __init__(self, plant_index: int, device_address: int, string_number: int, voltage: PVVoltageSensor, current: PVCurrentSensor):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        self.string_number = string_number
        super().__init__(
            name="Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-lightning-bolt",
            gain=None,
            precision=0,  # Intentional rounding to nearest watt
        )
        self.amperes: PVStringPower.Value = PVStringPower.Value(f"{self.log_identity[:-1]},value=amperes]", PVCurrentSensor.raw2amps)
        self.volts: PVStringPower.Value = PVStringPower.Value(f"{self.log_identity[:-1]},value=volts]", PVVoltageSensor.raw2volts)
        self.protocol_version = max(voltage.protocol_version, current.protocol_version)

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PVVoltageSensor × PVCurrentSensor"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if self.volts.value is None or self.amperes.value is None:
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Publishing SKIPPED - string={self.string_number} current={self.amperes.value} voltage={self.volts.value}")
            return False  # until all values populated, can't do calculation
        gap = abs(self.volts.timestamp - self.amperes.timestamp)
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Publishing READY   - string={self.string_number} current={self.amperes.value} voltage={self.volts.value} gap={gap:.2f}s")
        if gap > _MAX_PV_STRING_POWER_GAP_WARNING_SECONDS:
            logging.warning(f"{self.log_identity} Publishing WARNING - string={self.string_number} gap between acquiring current and voltage was {gap:.2f}s")
        await super().publish(mqtt_client, modbus_client, republish=republish)  # Publish even if gap exceeds warning threshold
        if not republish:
            # reset internal values to missing for next calculation
            self.volts.value = None
            self.amperes.value = None
        return True

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if isinstance(sensor, PVVoltageSensor):
            self.volts.apply(values)
        elif isinstance(sensor, PVCurrentSensor):
            self.amperes.apply(values)
        else:
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        if self.volts.value is None or self.amperes.value is None:
            return False  # until all values populated, can't do calculation
        state = self.volts.value * self.amperes.value
        if self.debug_logging:
            logging.debug(f"{self.log_identity} source values populated - setting latest state ({self.amperes.value}A * {self.volts.value}V = {state}W)")
        self.set_latest_state(state)
        return True


class PVStringLifetimeEnergy(EnergyLifetimeAccumulationSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int, string_number: int, source: PVStringPower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        self.string_number = string_number
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_lifetime_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_lifetime_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Riemann ∑ of PVStringPower"
        return attributes


class PVStringDailyEnergy(EnergyDailyAccumulationSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int, string_number: int, source: PVStringLifetimeEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        self.string_number = string_number
        super().__init__(
            name="Daily Production",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_daily_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_daily_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PVStringLifetimeEnergy − PVStringLifetimeEnergy at last midnight"
        return attributes
