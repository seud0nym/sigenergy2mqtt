from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import DeviceClass, HybridInverter, ProtocolVersion, PVInverter, StateClass, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.sensors.base import SanityCheckException
from sigenergy2mqtt.sensors.inverter_read_only import ActivePower

from .base import DerivedSensor, EnergyDailyAccumulationSensor, EnergyLifetimeAccumulationSensor, Sensor
from .inverter_read_only import ChargeDischargePower, PVCurrentSensor, PVVoltageSensor

logger = logging.getLogger(__name__)


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
            source_sensors=(battery_power,),
        )
        self.protocol_version = battery_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "ChargeDischargePower > 0"
        return attributes

    def update_from_source_sensor(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, ChargeDischargePower):
            logger.warning(f"{self.log_identity} Attempt to call update_from_source_sensor from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(max(0, raw))
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
            source_sensors=(battery_power,),
        )
        self.protocol_version = battery_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "ChargeDischargePower < 0 × -1"
        return attributes

    def update_from_source_sensor(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, ChargeDischargePower):
            logger.warning(f"{self.log_identity} Attempt to call update_from_source_sensor from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(0 if raw >= 0 else raw * -1)
        return True


_MAX_PV_STRING_POWER_GAP_WARNING_SECONDS = 0.5


class PVStringPower(DerivedSensor, HybridInverter, PVInverter):
    @dataclass
    class Value:
        name: str = field(compare=False, repr=True)
        divisor: float
        value: float | None = None
        timestamp: float = 0
        owner: PVStringPower | None = field(default=None, compare=False, repr=False)

        def apply(self, sensor: Sensor) -> None:
            if self.owner is not None:
                self.owner._log_unconsumed_source_value(self.name, self.value, self.timestamp, sensor)
            raw = sensor.latest_raw_state
            if raw is None:
                return
            self.value = float(raw) / self.divisor
            source_timestamp = self.owner._source_timestamp(sensor) if self.owner is not None else sensor.latest_time
            self.timestamp = source_timestamp if source_timestamp is not None else 0

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
            source_sensors=(voltage, current),
        )
        self.amperes: PVStringPower.Value = PVStringPower.Value(f"{self.log_identity[:-1]},value=amperes]", PVCurrentSensor.raw2amps, owner=self)
        self.volts: PVStringPower.Value = PVStringPower.Value(f"{self.log_identity[:-1]},value=volts]", PVVoltageSensor.raw2volts, owner=self)
        self.protocol_version = max(voltage.protocol_version, current.protocol_version)

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PVVoltageSensor × PVCurrentSensor"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if self.volts.value is None or self.amperes.value is None:
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Publishing SKIPPED - current={self.amperes.value} voltage={self.volts.value}")
            return False  # until all values populated, can't do calculation
        pending_update = self._pending_update
        gap = abs(self.volts.timestamp - self.amperes.timestamp)
        if self.debug_logging:
            logger.debug(f"{self.log_identity} Publishing READY   - current={self.amperes.value} voltage={self.volts.value} gap={gap:.2f}s")
            if gap > _MAX_PV_STRING_POWER_GAP_WARNING_SECONDS:
                logger.debug(f"{self.log_identity} Publishing WARNING - gap between acquiring current and voltage was {gap:.2f}s")
        published = await super().publish(mqtt_client, modbus_client, republish=republish)  # Publish even if gap exceeds warning threshold
        if published is False and pending_update:
            return False
        if not republish:
            # reset internal values to missing for next calculation
            self.volts.value = None
            self.amperes.value = None
        return bool(published)

    def update_from_source_sensor(self, sensor: Sensor) -> bool:
        if sensor.latest_raw_state is None:
            return False
        if isinstance(sensor, PVVoltageSensor):
            self.volts.apply(sensor)
        elif isinstance(sensor, PVCurrentSensor):
            self.amperes.apply(sensor)
        else:
            logger.warning(f"{self.log_identity} Attempt to call update_from_source_sensor from {sensor.log_identity}")
            return False
        if self.volts.value is None or self.amperes.value is None:
            return False  # until all values populated, can't do calculation
        state = self.volts.value * self.amperes.value
        if self.debug_logging:
            logger.debug(f"{self.log_identity} source values populated - setting latest state ({self.amperes.value}A * {self.volts.value}V = {state}W)")
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


class InverterSelfConsumedPower(DerivedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int, active_power: ActivePower, battery_power: ChargeDischargePower, *pv_string_power: PVStringPower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        self.device_address = device_address
        super().__init__(
            name="Self-Consumed Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_inverter_{device_address}_self_consumed_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_self_consumed_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-unknown",
            gain=None,
            precision=0,  # Intentional rounding to nearest watt
            protocol_version=ProtocolVersion.V1_8,
            source_sensors=(active_power, battery_power, *pv_string_power),
        )

        self.active_power: int | None = None
        self.battery_power: int | None = None
        self.pv_string_power: dict[int, int | None] = {p.string_number: None for p in pv_string_power}
        self._source_timestamps: dict[str, float | None] = {"active_power": None, "battery_power": None, **{f"pv_string_power_{p.string_number}": None for p in pv_string_power}}
        self._source_sensors: dict[str, Sensor] = {"active_power": active_power, "battery_power": battery_power, **{f"pv_string_power_{p.string_number}": p for p in pv_string_power}}
        self._incomplete_snapshot_logged = False

        self.sanity_check.min_raw = 0  # Watts
        self.sanity_check.max_raw = 3000  # Watts

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Estimate of inverter self-consumption (ActivePower − ChargeDischargePower − ∑[PVStringPower])"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if self.active_power is None or self.battery_power is None or any(p is None for p in self.pv_string_power.values()):
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Publishing SKIPPED - active_power={self.active_power} battery_power={self.battery_power} pv_string_power={[p for p in self.pv_string_power.values()]}")
            return False
        pending_update = self._pending_update
        if self.debug_logging:
            logger.debug(f"{self.log_identity} Publishing READY   - active_power={self.active_power} battery_power={self.battery_power} pv_string_power={[p for p in self.pv_string_power.values()]}")
        published = await super().publish(mqtt_client, modbus_client, republish=republish)  # Publish even if gap exceeds warning threshold
        if published is False and pending_update:
            return False
        if not republish:
            # reset internal values to missing for next calculation
            self.active_power = None
            self.battery_power = None
            self.pv_string_power = {p: None for p in self.pv_string_power}
            self._source_timestamps = {name: None for name in self._source_timestamps}
            self._incomplete_snapshot_logged = False
        return bool(published)

    def update_from_source_sensor(self, sensor: Sensor) -> bool:
        if sensor.latest_raw_state is None:
            return False
        self._discard_stale_snapshot()
        if isinstance(sensor, ActivePower):
            self._log_unconsumed_source_value("active_power", self.active_power, self._source_timestamps["active_power"], sensor)
            self.active_power = int(sensor.latest_raw_state)
            self._source_timestamps["active_power"] = self._source_timestamp(sensor)
        elif isinstance(sensor, ChargeDischargePower):
            self._log_unconsumed_source_value("battery_power", self.battery_power, self._source_timestamps["battery_power"], sensor)
            self.battery_power = int(sensor.latest_raw_state)
            self._source_timestamps["battery_power"] = self._source_timestamp(sensor)
        elif isinstance(sensor, PVStringPower):
            source_name = f"pv_string_power_{sensor.string_number}"
            self._log_unconsumed_source_value(source_name, self.pv_string_power[sensor.string_number], self._source_timestamps[source_name], sensor)
            self.pv_string_power[sensor.string_number] = int(sensor.latest_raw_state)
            self._source_timestamps[source_name] = self._source_timestamp(sensor)
        else:
            logger.warning(f"{self.log_identity} Attempt to call update_from_source_sensor from {sensor.log_identity}")
            return False
        if self.active_power is None or self.battery_power is None or any(p is None for p in self.pv_string_power.values()):
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Publishing SKIPPED - active_power={self.active_power} battery_power={self.battery_power} pv_string_power={[p for p in self.pv_string_power.values()]}")
                if not self._incomplete_snapshot_logged:
                    missing = [name for name, value in (("active_power", self.active_power), ("battery_power", self.battery_power)) if value is None]
                    missing.extend(f"pv_string_power_{string_number}" for string_number, value in self.pv_string_power.items() if value is None)
                    cached_ages = {name: round(time.time() - timestamp, 2) for name, timestamp in self._source_timestamps.items() if timestamp is not None}
                    logger.debug(f"{self.log_identity} Incomplete source snapshot - missing={missing} cached_ages={cached_ages}")
                    self._incomplete_snapshot_logged = True
            return False  # until all values populated, can't do calculation
        total_pv_power = sum([p for p in self.pv_string_power.values() if p is not None])
        state = total_pv_power - self.active_power - self.battery_power
        if state < 0:
            if self.debug_logging:
                logger.debug(f"{self.log_identity} correcting negative self-consumed power - active_power={self.active_power} battery_power={self.battery_power} total_pv_power={total_pv_power} state={state}")
            state = 0
        try:
            self.set_latest_state(state)
        except SanityCheckException as e:
            if self.debug_logging:
                logger.debug(f"{self.log_identity} set_latest_state({state}) FAILED - {e}")
        return True

    def _discard_stale_snapshot(self) -> None:
        """Discard partial source values that survived beyond their source cadence."""
        now = time.time()
        stale_sources = []
        for source_name, value in self._source_timestamps.items():
            if value is None:
                continue
            source_sensor = self._source_sensors.get(source_name)
            expected_interval = self._source_expected_interval(source_sensor) if source_sensor is not None else None
            if expected_interval is not None and now - value > expected_interval:
                stale_sources.append(source_name)

        if not stale_sources:
            return

        logger.warning(f"{self.log_identity} Discarding stale incomplete source snapshot - stale={stale_sources}")
        self.active_power = None
        self.battery_power = None
        self.pv_string_power = {string_number: None for string_number in self.pv_string_power}
        self._source_timestamps = {name: None for name in self._source_timestamps}
        self._incomplete_snapshot_logged = False
