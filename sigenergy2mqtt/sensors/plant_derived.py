import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Deque

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import PERCENTAGE, ConsumptionMethod, DeviceClass, Protocol, StateClass, UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import DeviceRegistry
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerChargingPower
from sigenergy2mqtt.sensors.base import UnpublishResetSensorMixin, _sanitize_path_component
from sigenergy2mqtt.sensors.inverter_read_only import DCChargerOutputPower
from sigenergy2mqtt.sensors.plant_read_only import ChargeCutOffSoC, PlantBatterySoC

from .base import DerivedSensor, EnergyDailyAccumulationSensor, ObservableMixin, PVPowerSensor, Sensor, SubstituteMixin
from .plant_read_only import (
    BatteryPower,
    ESSTotalChargedEnergy,
    ESSTotalDischargedEnergy,
    GeneralLoadPower,
    GridSensorActivePower,
    GridStatus,
    PlantPVPower,
    PlantPVTotalGeneration,
    PlantTotalExportedEnergy,
    PlantTotalImportedEnergy,
    ThirdPartyLifetimePVEnergy,
    TotalLoadPower,
)


class BatteryChargingPower(DerivedSensor):
    def __init__(self, plant_index: int, battery_power: BatteryPower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Battery Charging Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_battery_charging_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_battery_charging_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-plus",
            gain=None,
            precision=2,
        )
        self.protocol_version = battery_power.protocol_version
        self.sanity_check.min_raw = 0.0

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower > 0"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, BatteryPower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self.precision),
        )
        return True


class BatteryDischargingPower(DerivedSensor):
    def __init__(self, plant_index: int, battery_power: BatteryPower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Battery Discharging Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_battery_discharging_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_battery_discharging_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-minus",
            gain=None,
            precision=2,
        )
        self.protocol_version = battery_power.protocol_version
        self.sanity_check.min_raw = 0.0

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower < 0 × -1"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, BatteryPower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(
            0 if values[-1][1] >= 0 else round(values[-1][1] * -1, self.precision),
        )
        return True


class GridSensorExportPower(DerivedSensor):
    def __init__(self, plant_index: int, active_power: GridSensorActivePower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Export Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_export_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_export_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=active_power.device_class,
            state_class=active_power.state_class,
            icon="mdi:transmission-tower-export",
            gain=None,
            precision=active_power.precision,
        )
        self.protocol_version = active_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower < 0 × -1"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, GridSensorActivePower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(
            0 if values[-1][1] >= 0 else round(values[-1][1] * -1, self.precision),
        )
        return True


class GridSensorImportPower(DerivedSensor):
    def __init__(self, plant_index: int, active_power: GridSensorActivePower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Import Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_import_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_import_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=active_power.device_class,
            state_class=active_power.state_class,
            icon="mdi:transmission-tower-import",
            gain=None,
            precision=active_power.precision,
        )
        self.protocol_version = active_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower > 0"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if not isinstance(sensor, GridSensorActivePower):
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self.precision),
        )
        return True


class TotalPVPower(DerivedSensor, ObservableMixin, SubstituteMixin):
    class SourceType(StrEnum):
        SMARTPORT = "s"
        FAILOVER = "f"
        MANDATORY = "m"

    @dataclass
    class Value:
        gain: float
        type: str
        enabled: bool = True
        state: float | None = None
        last_update: float | None = None

        def __repr__(self):
            return f"{self.state} ({self.type}/{'enabled' if self.enabled else 'disabled'})"

    def __init__(self, plant_index: int, *sensors: Sensor):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Total PV Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_total_pv_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_total_pv_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,
            precision=2,
        )
        self._sources: dict[str, TotalPVPower.Value] = dict()
        self._topics: set[str] = set()
        self.register_source_sensors(*sensors, type=TotalPVPower.SourceType.MANDATORY, enabled=True)  # Register sensor sources
        self.register_mqtt_sources()

    async def _check_smartport_timeouts(self) -> None:
        now = time.time()
        timeout = active_config.modbus[self.plant_index].scan_interval.realtime * 5  # 5x poll interval grace period
        for source_id, value in self._sources.items():
            if value.enabled and value.type == TotalPVPower.SourceType.SMARTPORT:
                if value.last_update and (now - value.last_update > timeout):
                    logging.warning(f"{self.log_identity} Failover triggered: Source '{source_id}' timed out (last_update={now - value.last_update:.1f}s ago, timeout={timeout}s)")
                    self.failover(source_id)

    def fallback(self, source: str):
        logging.info(f"{self.log_identity} Re-enabling '{source}' as source because state updated (state={self._sources[source].state})")
        self._sources[source].enabled = True
        for id, value in self._sources.items():
            if value.type == TotalPVPower.SourceType.FAILOVER:
                logging.info(f"{self.log_identity} Disabling '{id}' as failover source because state updated from SmartPort sensor '{source}'")
                value.enabled = False

    def failover(self, smartport_sensor: Sensor | str) -> bool:
        failed_over = False
        source_id = smartport_sensor if isinstance(smartport_sensor, str) else smartport_sensor.unique_id
        for id, value in self._sources.items():
            if value.type == TotalPVPower.SourceType.FAILOVER:
                if value.enabled:
                    return True
                logging.info(f"{self.log_identity} Enabling '{id}' as failover source because SmartPort sensor '{source_id}' failed")
                value.enabled = True
                failed_over = True
        if failed_over and source_id in self._sources:
            logging.info(f"{self.log_identity} Disabling '{source_id}' as SmartPort source because failover sources enabled")
            self._sources[source_id].enabled = False
        if failed_over:
            logging.info(f"{self.log_identity} Resetting failure count from {self._failures} to 0 because failover source enabled")
            self._failures = 0
            self._next_retry = None
        return failed_over

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        if active_config.modbus[self.plant_index].smartport.enabled:
            attributes["source"] = "PV Power + (sum of all Smart-Port PV Power sensors)"
        else:
            attributes["source"] = "PV Power + Third-Party PV Power"
        return attributes

    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self._sources:
            if not self._sources[source].enabled and self._sources[source].type == TotalPVPower.SourceType.SMARTPORT:
                self.fallback(source)
            self._sources[source].state = (value if isinstance(value, float) else float(value)) * self._sources[source].gain
            self._sources[source].last_update = time.time()
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Updated from ({'enabled' if self._sources[source].enabled else 'disabled'}) topic {source} - {self._sources=}")
            if self._sources[source].enabled and not any(value.state is None for value in self._sources.values() if value.enabled):
                self.set_latest_state(sum([value.state for value in self._sources.values() if value.state is not None and value.enabled]))
                await self.publish(mqtt_client, modbus_client, republish=True)
            return True
        else:
            logging.warning(f"Attempt to call {self.log_identity}.notify with topic {source}, but topic is not registered")
            return False

    def observable_topics(self) -> set[str]:
        return set(self._topics)

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if not republish:
            await self._check_smartport_timeouts()
            if any(value.state is None for value in self._sources.values() if value.enabled):
                if self.debug_logging:
                    logging.debug(f"{self.log_identity} Publishing SKIPPED - {self._sources=}")
                return False  # until all values populated, can't do calculation
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Publishing READY   - {self._sources=}")
        await super().publish(mqtt_client, modbus_client, republish=republish)
        if not republish:
            # reset internal values to missing for next calculation
            for value in self._sources.values():
                value.state = None
        return True

    def register_mqtt_sources(self):
        if active_config.modbus[self.plant_index].smartport.enabled:  # Register MQTT sources
            for topic in active_config.modbus[self.plant_index].smartport.mqtt:  # pyright: ignore[reportGeneralTypeIssues]
                if topic.topic and topic.topic != "":  # Command line/Environment variable overrides can cause an empty topic
                    self._sources[topic.topic] = TotalPVPower.Value(topic.gain, type=TotalPVPower.SourceType.SMARTPORT)
                    self._topics.add(topic.topic)
                    if self.debug_logging:
                        logging.debug(f"{self.log_identity} Added Smart-Port MQTT topic {topic.topic} as source")
                else:
                    logging.warning(f"{self.log_identity} Empty Smart-Port MQTT topic ignored")

    def register_source_sensors(self, *sensors: Sensor, type: SourceType, enabled: bool = True) -> None:
        for sensor in sensors:
            assert isinstance(sensor, PVPowerSensor), f"Contributing sensors to TotalPVPower must be instances of PVPowerSensor ({sensor.__class__.__name__})"
            self._sources[sensor.unique_id] = TotalPVPower.Value(sensor.gain, type=type, enabled=enabled)
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Added sensor {sensor.unique_id} ({sensor.__class__.__name__}) as source ({type=} {enabled=})")

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        source = sensor.unique_id
        if not isinstance(sensor, PVPowerSensor):
            logging.warning(f"{self.log_identity} IGNORED attempt to call set_source_values from {sensor.log_identity} - not PVPowerSensor instance")
            return False
        elif source not in self._sources:
            logging.warning(f"{self.log_identity} IGNORED attempt to call set_source_values from '{source}' ({sensor.__class__.__name__}) - sensor is not registered")
            return False
        if not self._sources[source].enabled and self._sources[source].type == TotalPVPower.SourceType.SMARTPORT:
            self.fallback(source)
        self._sources[source].state = values[-1][1]
        self._sources[source].last_update = time.time()
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Updated from {'enabled' if self._sources[source].enabled else 'disabled'} source '{source}' - {self._sources=}")
        if not self._sources[source].enabled or any(value.state is None for value in self._sources.values() if value.enabled):
            return False  # until all enabled values populated, can't do calculation
        self.set_latest_state(sum([value.state for value in self._sources.values() if value.state is not None and value.enabled]))
        return True


class PlantConsumedPower(DerivedSensor, ObservableMixin):
    @dataclass
    class Value:
        gain: float = 1.0
        negate: bool = False
        interval: int | None = None
        state: float | None = None
        last_update: float | None = None
        requires_grid: bool = False

        def __repr__(self):
            if self.last_update:
                if self.state is not None:
                    return f"{self.state}"
                else:
                    return f"{time.time() - self.last_update:.1f}s ago"
            else:
                return "Never"

    def __init__(self, plant_index: int, method: ConsumptionMethod = ConsumptionMethod.CALCULATED):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Consumed Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_consumed_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_consumed_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-lightning-bolt-outline",
            gain=None,
            precision=2,
        )
        self.method = method
        self._grid_status: int | None = None
        self.sanity_check.min_raw = 0.0
        self._sources: dict[str, PlantConsumedPower.Value] = dict()
        self._topics: set[str] = set()
        match self.method:
            case ConsumptionMethod.CALCULATED:
                self._sources.update({"battery": PlantConsumedPower.Value(negate=True), "grid": PlantConsumedPower.Value(), "pv": PlantConsumedPower.Value()})
                self.protocol_version = Protocol.N_A
            case ConsumptionMethod.GENERAL:
                self._sources.update({ConsumptionMethod.GENERAL.value: PlantConsumedPower.Value()})
                self.protocol_version = Protocol.V2_8
            case ConsumptionMethod.TOTAL:
                self._sources.update({ConsumptionMethod.TOTAL.value: PlantConsumedPower.Value()})
                self.protocol_version = Protocol.V2_8

    def _set_latest_consumption(self) -> bool:
        if any(value.state is None for value in self._sources.values() if not value.requires_grid or (value.requires_grid and self._grid_status == 0)):
            return False
        consumed_power = sum([value.state for value in self._sources.values() if value.state is not None and (not value.requires_grid or (value.requires_grid and self._grid_status == 0))])
        if consumed_power < 0:
            logging.debug(f"{self.log_identity} consumed_power ({consumed_power}) is NEGATIVE! {self._sources} Adjusting to zero...")
            consumed_power = 0
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Publishing READY   - {self._sources}")
        self.set_latest_state(consumed_power)
        return True

    def _update_source(self, source: str, value: float) -> None:
        self._sources[source].state = (-value if self._sources[source].negate else value) * self._sources[source].gain
        self._sources[source].last_update = time.time()

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        match self.method:
            case ConsumptionMethod.CALCULATED:
                attributes["source"] = "TotalPVPower + GridSensorActivePower − BatteryPower − ACChargerChargingPower − DCChargerOutputPower"
            case ConsumptionMethod.GENERAL:
                attributes["source"] = "GeneralLoadPower"
            case ConsumptionMethod.TOTAL:
                attributes["source"] = "TotalLoadPower"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if not republish:
            if not self._set_latest_consumption():
                if self.debug_logging:
                    logging.debug(f"{self.log_identity} Publishing SKIPPED - {self._sources}")
                return False  # until all values populated, can't do calculation
            republish = True  # if we got here, we have a valid value to publish
        await super().publish(mqtt_client, modbus_client, republish=republish)
        # reset internal values to missing for next calculation
        for value in self._sources.values():
            value.state = None
        return True

    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self._sources:
            self._update_source(source, value if isinstance(value, float) else float(value))
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Updated from topic {source} - {self._sources}")
            if self._set_latest_consumption():
                await self.publish(mqtt_client, modbus_client, republish=True)
            return True
        else:
            logging.warning(f"Attempt to call {self.log_identity}.notify with topic {source}, but topic is not registered")
        return False

    def observable_topics(self) -> set[str]:
        if not self._topics:
            chargers = [device for device in DeviceRegistry.get(self.plant_index) if device.__class__.__name__.endswith("Charger")]
            for charger in chargers:
                for sensor in charger.get_all_sensors().values():
                    if isinstance(sensor, (ACChargerChargingPower, DCChargerOutputPower)):
                        self._sources[sensor.state_topic] = PlantConsumedPower.Value(gain=sensor.gain, negate=True, interval=sensor.scan_interval, requires_grid=True)
                        self._topics.add(sensor.state_topic)
                        if self.debug_logging:
                            logging.debug(f"{self.log_identity} Added MQTT topic {sensor.state_topic} as source")
        return set(self._topics)

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if isinstance(sensor, TotalLoadPower):
            self._update_source(ConsumptionMethod.TOTAL.value, values[-1][1])
        elif isinstance(sensor, GeneralLoadPower):
            self._update_source(ConsumptionMethod.GENERAL.value, values[-1][1])
        elif isinstance(sensor, BatteryPower):
            self._update_source("battery", values[-1][1])
        elif isinstance(sensor, GridSensorActivePower):
            self._update_source("grid", values[-1][1])
        elif isinstance(sensor, (PlantPVPower, TotalPVPower)):
            self._update_source("pv", values[-1][1])
        elif isinstance(sensor, GridStatus):
            if self.method == ConsumptionMethod.CALCULATED:
                grid = int(values[-1][1])
                if grid != self._grid_status:
                    if self._grid_status is not None:
                        if grid == 0:
                            logging.info(f"{self.log_identity} Grid restored - including AC/DC charger power in consumption calculations")
                        else:
                            logging.warning(f"{self.log_identity} Off Grid detected - ignoring AC/DC charger power in consumption calculations")
                    self._grid_status = grid
        else:
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        return self._set_latest_consumption()


class GridSensorDailyExportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantTotalExportedEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Exported Energy",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantTotalExportedEnergy − PlantTotalExportedEnergy at last midnight"
        return attributes


class GridSensorDailyImportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantTotalImportedEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Imported Energy",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantTotalImportedEnergy − PlantTotalImportedEnergy at last midnight"
        return attributes


class TotalLifetimePVEnergy(UnpublishResetSensorMixin, DerivedSensor):
    def __init__(self, plant_index: int):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Lifetime Total PV Production",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_pv_energy",
            object_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_pv_energy",  # Originally was a ResettableAccumulationSensor prior to Modbus Protocol v2.7, but need to keep the same object_id for backward compatibility
            data_type=ModbusDataType.UINT32,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant-outline",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True
        self.protocol_version = Protocol.V2_7
        self.plant_lifetime_pv_energy: float | None = None
        self.plant_3rd_party_lifetime_pv_energy: float | None = None

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "∑ of PlantPVTotalGeneration and ThirdPartyLifetimePVEnergy"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if self.plant_lifetime_pv_energy is None or self.plant_3rd_party_lifetime_pv_energy is None:
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Publishing SKIPPED - plant_lifetime_pv_energy={self.plant_lifetime_pv_energy} plant_3rd_party_lifetime_pv_energy={self.plant_3rd_party_lifetime_pv_energy}")
            return False  # until all values populated, can't do calculation
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Publishing READY   - plant_lifetime_pv_energy={self.plant_lifetime_pv_energy} plant_3rd_party_lifetime_pv_energy={self.plant_3rd_party_lifetime_pv_energy}")
        await super().publish(mqtt_client, modbus_client, republish=republish)
        # reset internal values to missing for next calculation
        self.plant_lifetime_pv_energy = None
        self.plant_3rd_party_lifetime_pv_energy = None
        return True

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if isinstance(sensor, PlantPVTotalGeneration):
            self.plant_lifetime_pv_energy = values[-1][1]
        elif isinstance(sensor, ThirdPartyLifetimePVEnergy):
            self.plant_3rd_party_lifetime_pv_energy = values[-1][1]
        else:
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        if self.plant_lifetime_pv_energy is None or self.plant_3rd_party_lifetime_pv_energy is None:
            return False  # until all values populated, can't do calculation
        total = self.plant_lifetime_pv_energy + self.plant_3rd_party_lifetime_pv_energy
        self.set_latest_state(total)
        return True


class TotalDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: TotalLifetimePVEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Total PV Production",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_total_daily_pv_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_total_daily_pv_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "TotalLifetimePVEnergy − TotalLifetimePVEnergy at last midnight"
        return attributes


class PlantDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantPVTotalGeneration):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily PV Production",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_daily_pv_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_pv_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantLifetimePVEnergy − PlantLifetimePVEnergy at last midnight"
        return attributes


class PlantDailyChargeEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: ESSTotalChargedEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Charge Energy",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_daily_charge_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_charge_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "∑ of DailyChargeEnergy across all Inverters associated with the Plant"
        return attributes


class PlantDailyDischargeEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: ESSTotalDischargedEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Discharge Energy",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_daily_discharge_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_discharge_energy",
            source=source,
        )
        self.protocol_version = source.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "∑ of DailyDischargeEnergy across all Inverters associated with the Plant"
        return attributes


class PlantBatteryRTE(DerivedSensor):
    def __init__(self, plant_index: int, soc: PlantBatterySoC, charge_cut_off_soc: ChargeCutOffSoC, charged: ESSTotalChargedEnergy, discharged: ESSTotalDischargedEnergy):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Battery RTE",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_battery_rte",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_battery_rte",
            data_type=ModbusDataType.UINT16,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-sync",
            gain=None,
            precision=2,
        )
        self.protocol_version = Protocol.V2_7
        self._soc_sensor = soc
        self._charge_cut_off_soc_sensor = charge_cut_off_soc
        self._charged_sensor = charged
        self._discharged_sensor = discharged

        self._data: dict[str, float | None] = {
            "charge_cut_off_soc": 100.0,
            "soc": None,
            "charged": None,
            "discharged": None,
            "previous_charged": None,
            "previous_discharged": None,
        }

        # Use sanitized unique_id for file paths
        uid = str(self.unique_id)
        if uid.startswith("<MagicMock"):  # For testing
            uid = "mock_uid"

        safe_uid = _sanitize_path_component(uid)
        self._persistent_state_file = Path(active_config.persistent_state_path, f"{safe_uid}.state")
        self._load_persisted_state()

    @property
    def _charge_cut_off_soc(self) -> float | None:
        """SoC at which charging is cut-off."""
        return self._data["charge_cut_off_soc"]

    @_charge_cut_off_soc.setter
    def _charge_cut_off_soc(self, value: float | None) -> None:
        self._data["charge_cut_off_soc"] = value

    @property
    def _soc(self) -> float | None:
        """Current SoC."""
        return self._data["soc"]

    @_soc.setter
    def _soc(self, value: float | None) -> None:
        self._data["soc"] = value

    @property
    def _charged(self) -> float | None:
        """Current Lifetime Charged."""
        return self._data["charged"]

    @_charged.setter
    def _charged(self, value: float | None) -> None:
        self._data["charged"] = value

    @property
    def _discharged(self) -> float | None:
        """Current Lifetime Discharged."""
        return self._data["discharged"]

    @_discharged.setter
    def _discharged(self, value: float | None) -> None:
        self._data["discharged"] = value

    @property
    def _previous_charged(self) -> float | None:
        """Lifetime Charged when battery was last at charge_cut_off_soc."""
        return self._data["previous_charged"]

    @_previous_charged.setter
    def _previous_charged(self, value: float | None) -> None:
        self._data["previous_charged"] = value

    @property
    def _previous_discharged(self) -> float | None:
        """Lifetime Discharged when battery was last at charge_cut_off_soc."""
        return self._data["previous_discharged"]

    @_previous_discharged.setter
    def _previous_discharged(self, value: float | None) -> None:
        self._data["previous_discharged"] = value

    @property
    def _is_full(self) -> bool:
        return self._soc is not None and self._charge_cut_off_soc is not None and self._soc >= self._charge_cut_off_soc

    @property
    def last_rte(self) -> float | None:
        if self._is_full and self._previous_charged is not None and self._previous_discharged is not None and self._charged is not None and self._discharged is not None:
            return (self._discharged - self._previous_discharged) / (self._charged - self._previous_charged) * 100
        else:
            return None

    @property
    def lifetime_rte(self) -> float | None:
        if self._is_full and self._charged is not None and self._discharged is not None:
            return self._discharged / self._charged * 100
        return None

    def _load_persisted_state(self) -> None:
        """Load accumulated value from persistent storage."""
        if self._persistent_state_file.is_file():
            try:
                with self._persistent_state_file.open("r") as f:
                    saved: dict[str, float | None] = json.load(f)
                    if saved:
                        logging.debug(f"{self.log_identity} Loaded current state from {self._persistent_state_file} ({saved})")
                        self._data = saved
                        state = self.last_rte
                        if state is not None:
                            self.set_latest_state(state)
                        return
            except (OSError, ValueError, PermissionError) as e:
                logging.warning(f"{self.log_identity} Failed to read {self._persistent_state_file}: {e}")
            except Exception as e:
                logging.error(f"{self.log_identity} Unexpected error reading {self._persistent_state_file}: {e}")

    async def _persist_state(self) -> None:
        try:
            with self._persistent_state_file.open("w") as f:
                json.dump(self._data, f)
        except (OSError, ValueError, PermissionError) as e:
            logging.warning(f"{self.log_identity} Failed to write {self._persistent_state_file}: {e}")
        except Exception as e:
            logging.error(f"{self.log_identity} Unexpected error writing {self._persistent_state_file}: {e}")

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = (
            "(ESSTotalDischargedEnergy now - ESSTotalDischargedEnergy when last full) ÷ (ESSTotalChargedEnergy now - ESSTotalChargedEnergy when last full) × 100 when PlantBatterySoC was last == ChargeCutOffSoC"
        )
        return attributes

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        return await super().get_state(raw=raw, republish=republish, **kwargs)

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        persist = False
        if isinstance(sensor, ChargeCutOffSoC):
            persist = True
            if self.debug_logging:
                logging.debug(f"{self.log_identity} ChargeCutOffSoC updated: {values[-1][1]}")
            self._charge_cut_off_soc = values[-1][1] / self._charge_cut_off_soc_sensor.gain
        elif isinstance(sensor, PlantBatterySoC):
            # When SoC >= ChargeCutOffSoC, set the previous charged/discharged energy to current charged/discharged energy
            # Since SoC can stay at the same level for extended periods, we have to make sure that we do not do it more than once
            soc = values[-1][1] / self._soc_sensor.gain
            if self.debug_logging:
                logging.debug(f"{self.log_identity} PlantBatterySoC updated: {soc}")
            old_soc = self._soc
            self._soc = soc
            if (
                self._soc is not None  # State of Charge has been set at least once
                and self._charge_cut_off_soc is not None
                and soc != old_soc  # State of Charge has changed
                and soc >= self._charge_cut_off_soc  # State of Charge has reached maximum
                and self._charged is not None  # Charged energy has been set at least once
                and self._discharged is not None  # Discharged energy has been set at least once
            ):
                persist = True
                if self.debug_logging:
                    logging.debug(f"{self.log_identity} PlantBatterySoC >= ChargeCutOffSoC ({self._charge_cut_off_soc}), moving charged/discharged energy to previous charged/discharged energy")
                self._previous_charged = self._charged
                self._previous_discharged = self._discharged
                # Reset the charged/discharged energy to None so that they are ready to be updated with current figures
                self._charged = None
                self._discharged = None
                # Force an update to get current charged/discharged energy
                self._charged_sensor.force_publish = True
                self._discharged_sensor.force_publish = True
            elif self.debug_logging:
                logging.debug(
                    f"{self.log_identity} Not moving charged/discharged energy to previous charged/discharged energy ({old_soc=} -> {soc=} charge_cut_off_soc={self._charge_cut_off_soc} charged={self._charged} discharged={self._discharged})"
                )
        elif isinstance(sensor, ESSTotalChargedEnergy):
            if self._is_full:
                charged = values[-1][1] / self._charged_sensor.gain
                if charged != self._charged:
                    persist = True
                    self._charged = charged
                    if self.debug_logging:
                        logging.debug(f"{self.log_identity} Charged energy updated: {values[-1][1]}")
            elif self.debug_logging:
                logging.debug(f"{self.log_identity} Not updating charged energy - SoC is less than Charge Cut Off SoC (soc={self._soc} charge_cut_off_soc={self._charge_cut_off_soc})")
        elif isinstance(sensor, ESSTotalDischargedEnergy):
            if self._is_full:
                discharged = values[-1][1] / self._discharged_sensor.gain
                if discharged != self._discharged:
                    persist = True
                    self._discharged = discharged
                    if self.debug_logging:
                        logging.debug(f"{self.log_identity} Discharged energy updated: {values[-1][1]}")
            elif self.debug_logging:
                logging.debug(f"{self.log_identity} Not updating discharged energy - SoC is less than Charge Cut Off SoC (soc={self._soc} charge_cut_off_soc={self._charge_cut_off_soc})")
        else:
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
        if persist:
            # This is a fire and forget operation - we don't want to wait for the state to be persisted
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Persisting state to {self._persistent_state_file}")
            coro = self._persist_state()
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(coro, loop)
                    else:
                        coro.close()
                except Exception as e:
                    logging.warning(f"{self.log_identity} Failed to persist state: {e}")
                    coro.close()
            except Exception as e:
                logging.warning(f"{self.log_identity} Failed to persist state: {e}")
                coro.close()
        state = self.last_rte
        if state is None:
            lifetime = self.lifetime_rte
            if lifetime is not None:
                for sensor in [s for s in self.derived_sensors.values() if isinstance(s, PlantLifetimeBatteryRTE)]:
                    sensor.set_source_values(self, None)  # type: ignore[arg-type] - PlantLifetimeBatteryRTE does not use the values argument
                return False
        else:
            self.set_latest_state(state)
        return True


class PlantLifetimeBatteryRTE(DerivedSensor):
    def __init__(self, plant_index: int):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Lifetime Battery RTE",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_battery_rte",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_lifetime_battery_rte",
            data_type=ModbusDataType.UINT16,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-sync-outline",
            gain=None,
            precision=2,
        )
        self.protocol_version = Protocol.V2_7

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "ESSTotalDischargedEnergy ÷ ESSTotalChargedEnergy × 100 when PlantBatterySoC was last == ChargeCutOffSoC"
        return attributes

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        if isinstance(sensor, PlantBatteryRTE):
            state = sensor.lifetime_rte
            if state is None:
                return False
            self.set_latest_state(state)
            return True
        else:
            logging.warning(f"Attempt to call {self.log_identity}.set_source_values from {sensor.log_identity}")
            return False
