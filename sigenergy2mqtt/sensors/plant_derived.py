from .base import DeviceClass, EnergyDailyAccumulationSensor, ObservableMixin, PVPowerSensor, Sensor, StateClass, DerivedSensor, ModbusSensor
from .const import UnitOfEnergy, UnitOfPower
from .plant_read_only import (
    BatteryPower,
    GridSensorActivePower,
    ESSTotalChargedEnergy,
    ESSTotalDischargedEnergy,
    PlantPVPower,
    PlantPVTotalGeneration,
    PlantTotalExportedEnergy,
    PlantTotalImportedEnergy,
    ThirdPartyLifetimePVEnergy,
)
from dataclasses import dataclass
from enum import StrEnum
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import DeviceRegistry
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Dict
import logging
import time


class BatteryChargingPower(DerivedSensor):
    def __init__(self, plant_index: int, battery_power: BatteryPower):
        super().__init__(
            name="Battery Charging Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_battery_charging_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_battery_charging_power",
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-plus",
            gain=None,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower &gt; 0"
        return attributes

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), BatteryPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self._precision),
        )
        return True


class BatteryDischargingPower(DerivedSensor):
    def __init__(self, plant_index: int, battery_power: BatteryPower):
        super().__init__(
            name="Battery Discharging Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_battery_discharging_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_battery_discharging_power",
            unit=UnitOfPower.WATT,
            device_class=battery_power.device_class,
            state_class=battery_power.state_class,
            icon="mdi:battery-minus",
            gain=None,
            precision=2,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower &lt; 0"
        return attributes

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), BatteryPower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] >= 0 else round(values[-1][1] * -1, self._precision),
        )
        return True


class GridSensorExportPower(DerivedSensor):
    def __init__(self, plant_index: int, active_power: GridSensorActivePower):
        super().__init__(
            name="Export Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_export_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_export_power",
            unit=UnitOfPower.WATT,
            device_class=active_power.device_class,
            state_class=active_power.state_class,
            icon="mdi:transmission-tower-export",
            gain=None,
            precision=active_power.precision,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower &lt; 0 &times; -1"
        return attributes

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), GridSensorActivePower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] >= 0 else round(values[-1][1] * -1, self._precision),
        )
        return True


class GridSensorImportPower(DerivedSensor):
    def __init__(self, plant_index: int, active_power: GridSensorActivePower):
        super().__init__(
            name="Import Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_import_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_import_power",
            unit=UnitOfPower.WATT,
            device_class=active_power.device_class,
            state_class=active_power.state_class,
            icon="mdi:transmission-tower-import",
            gain=None,
            precision=active_power.precision,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower &gt; 0"
        return attributes

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if not issubclass(type(sensor), GridSensorActivePower):
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self._precision),
        )
        return True


class PlantConsumedPower(DerivedSensor, ObservableMixin):
    @dataclass
    class Value:
        gain: float = 1.0
        negate: bool = False
        interval: int = None
        state: float = None
        last_update: float = None

        def __repr__(self):
            if self.last_update:
                if self.state is not None:
                    return f"{self.state}"
                else:
                    return f"{time.time() - self.last_update:.1f}s ago"
            else:
                return "Never"

    def __init__(self, plant_index: int):
        super().__init__(
            name="Consumed Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_consumed_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_consumed_power",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:home-lightning-bolt-outline",
            gain=None,
            precision=2,
        )
        self._plant_index = plant_index
        self._sanity.min_value = 0.0
        self._sources: dict[str, PlantConsumedPower.Value] = {
            "battery": PlantConsumedPower.Value(negate=True),
            "grid": PlantConsumedPower.Value(),
            "pv": PlantConsumedPower.Value(),
        }

    def _set_latest_consumption(self):
        if any(value.state is None for value in self._sources.values()):
            return False
        consumed_power = sum([value.state for value in self._sources.values() if value.state])
        if consumed_power < 0:
            logging.debug(f"{self.__class__.__name__} consumed_power ({consumed_power}) is NEGATIVE! {self._sources} Adjusting to zero...")
            consumed_power = 0
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} Publishing READY   - {self._sources}")
        self.set_latest_state(consumed_power)
        return True

    def _update_source(self, source: str, value: float) -> None:
        self._sources[source].state = (-value if self._sources[source].negate else value) * self._sources[source].gain
        self._sources[source].last_update = time.time()

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "TotalPVPower &plus; GridSensorActivePower &minus; BatteryPower &minus; ACChargerChargingPower &minus; DCChargerOutputPower"
        return attributes

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if not republish:
            if not self._set_latest_consumption():
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} Publishing SKIPPED - {self._sources}")
                return  # until all values populated, can't do calculation
            republish = True  # if we got here, we have a valid value to publish
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        for value in self._sources.values():
            value.state = None

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, topic: str, handler: MqttHandler) -> bool:
        if topic in self._sources:
            self._update_source(topic, value if isinstance(value, float) else float(value))
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Updated from topic '{topic}' - {self._sources}")
            if self._set_latest_consumption():
                await self.publish(mqtt, modbus, republish=True)
        else:
            logging.warning(f"Attempt to call {self.__class__.__name__}.notify with topic '{topic}', but topic is not registered")

    def observable_topics(self) -> set[str]:
        topics: set[str] = set()
        for charger in [device for device in DeviceRegistry.get(self._plant_index) if device.__class__.__name__.endswith("Charger")]:
            for sensor in charger.get_all_sensors().values():
                if sensor["object_id"].endswith("rated_charging_power") or sensor["object_id"].endswith("dc_charger_output_power"):
                    self._sources[sensor.state_topic] = PlantConsumedPower.Value(gain=sensor.gain, negate=True, interval=sensor.scan_interval)
                    topics.add(sensor.state_topic)
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} Added MQTT topic {sensor.state_topic} as source")
        return topics

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if issubclass(type(sensor), BatteryPower):
            self._update_source("battery", values[-1][1])
        elif issubclass(type(sensor), GridSensorActivePower):
            self._update_source("grid", values[-1][1])
        elif issubclass(type(sensor), (PlantPVPower, TotalPVPower)):
            self._update_source("pv", values[-1][1])
        else:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        return self._set_latest_consumption()


class TotalPVPower(DerivedSensor, ObservableMixin):
    class SourceType(StrEnum):
        SMARTPORT = "s"
        FAILOVER = "f"
        MANDATORY = "m"

    @dataclass
    class Value:
        gain: float
        type: str
        enabled: bool = True
        state: float = None

        def __repr__(self):
            return f"{self.state} ({self.type.name}/{'enabled' if self.enabled else 'disabled'})"

    def __init__(self, plant_index: int, *sensors: Sensor):
        super().__init__(
            name="Total PV Power",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_total_pv_power",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_total_pv_power",
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=None,
            precision=2,
        )
        self._plant_index = plant_index
        self._sources: dict[str, TotalPVPower.Value] = dict()
        self.register_source_sensors(*sensors, type=TotalPVPower.SourceType.MANDATORY, enabled=True)

    def failback(self, source: str):
        logging.info(f"{self.__class__.__name__} Re-enabling '{source}' as source because state updated (state={self._sources[source].state})")
        self._sources[source].enabled = True
        for id, value in self._sources.items():
            if value.type == TotalPVPower.SourceType.FAILOVER:
                logging.info(f"{self.__class__.__name__} Disabling '{id}' as failover source because state updated from SmartPort sensor '{source}'")
                value.enabled = False

    def failover(self, smartport_sensor: Sensor) -> bool:
        failed_over = False
        for id, value in self._sources.items():
            if value.type == TotalPVPower.SourceType.FAILOVER:
                if value.enabled:
                    return True
                logging.info(f"{self.__class__.__name__} Enabling '{id}' as failover source because SmartPort sensor '{smartport_sensor.unique_id}' failed")
                value.enabled = True
                failed_over = True
        if failed_over and smartport_sensor.unique_id in self._sources:
            logging.info(f"{self.__class__.__name__} Disabling '{smartport_sensor.unique_id}' as SmartPort source because failover sources enabled")
            self._sources[smartport_sensor.unique_id].enabled = False
        return failed_over

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        if Config.devices[self._plant_index].smartport.enabled:
            attributes["source"] = "PV Power + (sum of all Smart-Port PV Power sensors)"
        else:
            attributes["source"] = "PV Power + Third-Party PV Power"
        return attributes

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, topic: str, handler: MqttHandler) -> bool:
        if topic in self._sources:
            if not self._sources[topic].enabled and self._sources[topic].type == TotalPVPower.SourceType.SMARTPORT:
                self.failback(topic)
            self._sources[topic].state = (value if isinstance(value, float) else float(value)) * self._sources[topic].gain
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Updated from ({'enabled' if self._sources[topic].enabled else 'disabled'}) topic '{topic}' - {self._sources=}")
            if self._sources[topic].enabled and not any(value.state is None for value in self._sources.values() if value.enabled):
                self.set_latest_state(sum([value.state for value in self._sources.values() if value.enabled]))
                await self.publish(mqtt, modbus, republish=True)
        else:
            logging.warning(f"Attempt to call {self.__class__.__name__}.notify with topic '{topic}', but topic is not registered")

    def observable_topics(self) -> set[str]:
        topics: set[str] = set()
        if Config.devices[self._plant_index].smartport.enabled:
            for topic in Config.devices[self._plant_index].smartport.mqtt:
                if topic.topic and topic.topic != "":  # Command line/Environment variable overrides can cause an empty topic
                    self._sources[topic.topic] = TotalPVPower.Value(topic.gain, type=TotalPVPower.SourceType.SMARTPORT)
                    topics.add(topic.topic)
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} Added Smart-Port MQTT topic {topic.topic} as source")
                else:
                    logging.warning(f"{self.__class__.__name__} Empty Smart-Port MQTT topic ignored")
        return topics

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if not republish:
            if any(value.state is None for value in self._sources.values() if value.enabled):
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} Publishing SKIPPED - {self._sources=}")
                return  # until all values populated, can't do calculation
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Publishing READY   - {self._sources=}")
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        for value in self._sources.values():
            value.state = None

    def register_source_sensors(self, *sensors: Sensor, type: SourceType, enabled: bool = True) -> None:
        for sensor in sensors:
            assert isinstance(sensor, PVPowerSensor), f"Contributing sensors to TotalPVPower must be instances of PVPowerSensor ({sensor.__class__.__name__})"
            self._sources[sensor.unique_id] = TotalPVPower.Value(sensor.gain, type=type, enabled=enabled)
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Added sensor {sensor.unique_id} ({sensor.__class__.__name__}) as source ({type=} {enabled=})")

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        source = sensor.unique_id
        if not isinstance(sensor, PVPowerSensor):
            logging.warning(f"{self.__class__.__name__} IGNORED attempt to call set_source_values from {sensor.__class__.__name__} - not PVPower instance")
            return False
        elif source not in self._sources:
            logging.warning(f"{self.__class__.__name__} IGNORED attempt to call set_source_values from '{source}' ({sensor.__class__.__name__}) - sensor is not registered")
            return False
        if not self._sources[source].enabled and self._sources[source].type == TotalPVPower.SourceType.SMARTPORT:
            self.failback(source)
        self._sources[source].state = values[-1][1]
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} Updated from {'enabled' if self._sources[source].enabled else 'disabled'} source '{source}' - {self._sources=}")
        if not self._sources[source].enabled or any(value.state is None for value in self._sources.values() if value.enabled):
            return False  # until all enabled values populated, can't do calculation
        self.set_latest_state(sum([value.state for value in self._sources.values() if value.enabled]))
        return True


class GridSensorDailyExportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantTotalExportedEnergy):
        super().__init__(
            name="Daily Exported Energy",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantTotalExportedEnergy &minus; PlantTotalExportedEnergy at last midnight"
        return attributes


class GridSensorDailyImportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantTotalImportedEnergy):
        super().__init__(
            name="Daily Imported Energy",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantTotalImportedEnergy &minus; PlantTotalImportedEnergy at last midnight"
        return attributes


class TotalLifetimePVEnergy(DerivedSensor):
    def __init__(self, plant_index: int):
        super().__init__(
            name="Lifetime Total PV Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_pv_energy",
            object_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_pv_energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:solar-power-variant-outline",
            gain=100,
            precision=2,
        )
        self["enabled_by_default"] = True
        self.plant_lifetime_pv_energy: float = None
        self.plant_3rd_party_lifetime_pv_energy: float = None

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "&sum; of PlantPVTotalGeneration and ThirdPartyLifetimePVEnergy"
        return attributes

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}  # Unpublish the reset sensor as was a ResettableAccumulationSensor prior to Modbus Protocol v2.7
        return components

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if self.plant_lifetime_pv_energy is None or self.plant_3rd_party_lifetime_pv_energy is None:
            if self._debug_logging:
                logging.debug(
                    f"{self.__class__.__name__} Publishing SKIPPED - plant_lifetime_pv_energy={self.plant_lifetime_pv_energy} plant_3rd_party_lifetime_pv_energy={self.plant_3rd_party_lifetime_pv_energy}"
                )
            return  # until all values populated, can't do calculation
        if self._debug_logging:
            logging.debug(
                f"{self.__class__.__name__} Publishing READY   - plant_lifetime_pv_energy={self.plant_lifetime_pv_energy} plant_3rd_party_lifetime_pv_energy={self.plant_3rd_party_lifetime_pv_energy}"
            )
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        self.plant_lifetime_pv_energy = None
        self.plant_3rd_party_lifetime_pv_energy = None

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if issubclass(type(sensor), PlantPVTotalGeneration):
            self.plant_lifetime_pv_energy = values[-1][1]
        elif issubclass(type(sensor), ThirdPartyLifetimePVEnergy):
            self.plant_3rd_party_lifetime_pv_energy = values[-1][1]
        else:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        if self.plant_lifetime_pv_energy is None or self.plant_3rd_party_lifetime_pv_energy is None:
            return False  # until all values populated, can't do calculation
        total = self.plant_lifetime_pv_energy + self.plant_3rd_party_lifetime_pv_energy
        self.set_latest_state(total)
        return True


class TotalDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: TotalLifetimePVEnergy):
        super().__init__(
            name="Daily Total PV Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_total_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_total_daily_pv_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "TotalLifetimePVEnergy &minus; TotalLifetimePVEnergy at last midnight"
        return attributes


class PlantDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantPVTotalGeneration):
        super().__init__(
            name="Daily PV Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_pv_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight"
        return attributes


class PlantDailyChargeEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: ESSTotalChargedEnergy):
        super().__init__(
            name="Daily Charge Energy",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_charge_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_charge_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "&sum; of DailyChargeEnergy across all Inverters associated with the Plant"
        return attributes


class PlantDailyDischargeEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: ESSTotalDischargedEnergy):
        super().__init__(
            name="Daily Discharge Energy",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_discharge_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_discharge_energy",
            source=source,
        )

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = "&sum; of DailyDischargeEnergy across all Inverters associated with the Plant"
        return attributes
