from .base import (
    BatteryEnergyAccumulationSensor,
    DeviceClass,
    EnergyDailyAccumulationSensor,
    ObservableMixin,
    PVPowerSensor,
    Sensor,
    StateClass,
    EnergyLifetimeAccumulationSensor,
    DerivedSensor,
    ModBusSensor,
)
from .const import UnitOfPower
from .plant_read_only import BatteryPower, GridSensorActivePower, PlantPVPower
from dataclasses import dataclass
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.mqtt import MqttClient
from sigenergy2mqtt.sensors.inverter_read_only import AccumulatedChargeEnergy, AccumulatedDischargeEnergy, DailyChargeEnergy, DailyDischargeEnergy
import logging


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

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if not issubclass(type(sensor), BatteryPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
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

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if not issubclass(type(sensor), BatteryPower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
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

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if not issubclass(type(sensor), GridSensorActivePower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
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

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if not issubclass(type(sensor), GridSensorActivePower):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        self.set_latest_state(
            0 if values[-1][1] <= 0 else round(values[-1][1], self._precision),
        )
        return True


class PlantConsumedPower(DerivedSensor):
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
        self.battery_power: float = None
        self.grid_sensor_active_power: float = None
        self.pv_power: float = None

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if self.battery_power is None or self.grid_sensor_active_power is None or self.pv_power is None:
            if self._debug_logging:
                logging.debug(f"Publishing {self.__class__.__name__} SKIPPED - battery_power={self.battery_power} grid_sensor_active_power={self.grid_sensor_active_power} pv_power={self.pv_power}")
            return  # until all values populated, can't do calculation
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        self.battery_power = None
        self.grid_sensor_active_power = None
        self.pv_power = None

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if issubclass(type(sensor), BatteryPower):
            self.battery_power = values[-1][1] * sensor.gain
        elif issubclass(type(sensor), GridSensorActivePower):
            self.grid_sensor_active_power = values[-1][1] * sensor.gain
        elif issubclass(type(sensor), (PlantPVPower, TotalPVPower)):
            self.pv_power = values[-1][1] * sensor.gain
        else:
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        if self.battery_power is None or self.grid_sensor_active_power is None or self.pv_power is None:
            return False  # until all values populated, can't do calculation
        self.set_latest_state(round((self.pv_power + self.grid_sensor_active_power - self.battery_power) / self.gain, self._precision))
        return True


class TotalPVPower(DerivedSensor, ObservableMixin):
    @dataclass
    class Value:
        gain: float
        state: float = None

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
        self.register_source_sensors(*sensors)

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source in self._sources:
            self._sources[source].state = (value if isinstance(value, float) else float(value)) * self._sources[source].gain
            if sum([1 for value in self._sources.values() if value.state is None]) == 0:
                self.set_latest_state(round(sum([value.state for value in self._sources.values()]) / self.gain, self._precision))
                await self.publish(mqtt, modbus, republish=True)
            elif self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Updated from topic '{source}' - {self._sources=}")
        else:
            logging.error(f"Attempt to call {self.__class__.__name__}.notify with topic '{source}', but topic is not registered")

    def observable_topics(self) -> set[str]:
        topics: set[str] = set()
        if Config.devices[self._plant_index].smartport.enabled:
            for topic in Config.devices[self._plant_index].smartport.mqtt:
                if topic.topic and topic.topic != "":  # Command line/Environment variable overrides can cause an empty topic
                    self._sources[topic.topic] = TotalPVPower.Value(topic.gain)
                    topics.add(topic.topic)
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} Added MQTT topic {topic.topic} as source")
                else:
                    logging.warning(f"{self.__class__.__name__} Empty MQTT topic ignored")
        return topics

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if sum([1 for value in self._sources.values() if value.state is None]) > 0:
            if self._debug_logging:
                logging.debug(f"Publishing {self.__class__.__name__} SKIPPED - {self._sources=}")
            return  # until all values populated, can't do calculation
        if self._debug_logging:
            logging.debug(f"Publishing {self.__class__.__name__} - {self._sources=}")
        await super().publish(mqtt, modbus, republish=republish)
        # reset internal values to missing for next calculation
        for value in self._sources.values():
            value.state = None

    def register_source_sensors(self, *sensors: Sensor):
        for sensor in sensors:
            assert isinstance(sensor, PVPowerSensor), f"Contributing sensors to TotalPVPower must be instances of PVPowerSensor ({sensor.__class__.__name__})"
            self._sources[sensor.unique_id] = TotalPVPower.Value(sensor.gain)
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Added sensor {sensor.unique_id} ({sensor.__class__.__name__}) as source")

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if not isinstance(sensor, PVPowerSensor):
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        elif sensor.unique_id not in self._sources:
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from '{sensor.unique_id}' ({sensor.__class__.__name__}), but sensor is not registered")
            return False
        self._sources[sensor.unique_id].state = values[-1][1] * sensor.gain
        if sum([1 for value in self._sources.values() if value.state is None]) > 0:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Updated from sensor '{sensor.unique_id}' - {self._sources=}")
            return False  # until all values populated, can't do calculation
        self.set_latest_state(round(sum([value.state for value in self._sources.values()]) / self.gain, self._precision))
        return True


class GridSensorLifetimeExportEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, source: GridSensorExportPower):
        super().__init__(
            name="Lifetime Energy Exported",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_lifetime_export_energy",
            source=source,
            icon="mdi:transmission-tower-export",
        )


class GridSensorDailyExportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: GridSensorLifetimeExportEnergy):
        super().__init__(
            name="Daily Energy Exported",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_export_energy",
            source=source,
            icon="mdi:transmission-tower-export",
        )


class GridSensorLifetimeImportEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, source: GridSensorImportPower):
        super().__init__(
            name="Lifetime Energy Imported",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_lifetime_import_energy",
            source=source,
            icon="mdi:transmission-tower-import",
        )


class GridSensorDailyImportEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: GridSensorLifetimeImportEnergy):
        super().__init__(
            name="Daily Energy Imported",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_grid_sensor_daily_import_energy",
            source=source,
            icon="mdi:transmission-tower-import",
        )


class PlantLifetimeConsumedEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantConsumedPower):
        super().__init__(
            name="Lifetime Consumption",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_consumed_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_lifetime_consumed_energy",
            source=source,
            icon="mdi:home-lightning-bolt-outline",
        )


class PlantDailyConsumedEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantLifetimeConsumedEnergy):
        super().__init__(
            name="Daily Consumption",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_consumed_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_consumed_energy",
            source=source,
            icon="mdi:home-lightning-bolt-outline",
        )


class PlantLifetimePVEnergy(EnergyLifetimeAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantPVPower | TotalPVPower):
        super().__init__(
            name="Lifetime Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_lifetime_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_lifetime_pv_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class PlantDailyPVEnergy(EnergyDailyAccumulationSensor):
    def __init__(self, plant_index: int, source: PlantLifetimePVEnergy):
        super().__init__(
            name="Daily Production",
            unique_id=f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_pv_energy",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_pv_energy",
            source=source,
            icon="mdi:solar-power-variant",
        )


class PlantDailyChargeEnergy(BatteryEnergyAccumulationSensor):
    def __init__(self, plant_index: int, *sensors: DailyChargeEnergy):
        super().__init__(
            "Daily Charge Energy",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_charge_energy",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_charge_energy",
            *sensors,
        )


class PlantDailyDischargeEnergy(BatteryEnergyAccumulationSensor):
    def __init__(self, plant_index: int, *sensors: DailyDischargeEnergy):
        super().__init__(
            "Daily Discharge Energy",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_daily_discharge_energy",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_daily_discharge_energy",
            *sensors,
        )


class PlantAccumulatedChargeEnergy(BatteryEnergyAccumulationSensor):
    def __init__(self, plant_index: int, *sensors: AccumulatedChargeEnergy):
        super().__init__(
            "Lifetime Charge Energy",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_charge_energy",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_accumulated_charge_energy",
            *sensors,
        )


class PlantAccumulatedDischargeEnergy(BatteryEnergyAccumulationSensor):
    def __init__(self, plant_index: int, *sensors: AccumulatedDischargeEnergy):
        super().__init__(
            "Lifetime Discharge Energy",
            f"{Config.home_assistant.unique_id_prefix}_{plant_index}_accumulated_discharge_energy",
            f"{Config.home_assistant.entity_id_prefix}_{plant_index}_accumulated_discharge_energy",
            *sensors,
        )
