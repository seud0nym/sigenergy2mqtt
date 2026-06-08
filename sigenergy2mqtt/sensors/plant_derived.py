import logging
import time
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import ConsumptionMethod, DeviceClass, HybridInverter, Protocol, PVInverter, StateClass, UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerChargingPower
from sigenergy2mqtt.sensors.base import UnpublishResetSensorMixin
from sigenergy2mqtt.sensors.base.accumulation import SimpleEnergyDailyAccumulationSensor
from sigenergy2mqtt.sensors.inverter_derived import InverterSelfConsumedPower
from sigenergy2mqtt.sensors.inverter_read_only import DCChargerOutputPower

from .base import CrossDeviceDerivedSensor, DerivedSensor, EnergyDailyAccumulationSensor, PVPowerSensor, Sensor
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


class BatteryChargingPower(DerivedSensor, HybridInverter):
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
            source_sensors=(battery_power,),
        )
        self.protocol_version = battery_power.protocol_version
        self.sanity_check.min_raw = 0.0

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower > 0"
        return attributes

    def set_source_values(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, BatteryPower):
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(
            0 if raw <= 0 else round(raw, self.precision),
        )
        return True


class BatteryDischargingPower(DerivedSensor, HybridInverter):
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
            source_sensors=(battery_power,),
        )
        self.protocol_version = battery_power.protocol_version
        self.sanity_check.min_raw = 0.0

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "BatteryPower < 0 × -1"
        return attributes

    def set_source_values(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, BatteryPower):
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(
            0 if raw >= 0 else round(raw * -1, self.precision),
        )
        return True


class GridSensorExportPower(DerivedSensor, HybridInverter, PVInverter):
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
            source_sensors=(active_power,),
        )
        self.protocol_version = active_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower < 0 × -1"
        return attributes

    def set_source_values(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, GridSensorActivePower):
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(
            0 if raw >= 0 else round(raw * -1, self.precision),
        )
        return True


class GridSensorImportPower(DerivedSensor, HybridInverter, PVInverter):
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
            source_sensors=(active_power,),
        )
        self.protocol_version = active_power.protocol_version

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "GridSensorActivePower > 0"
        return attributes

    def set_source_values(self, sensor: Sensor) -> bool:
        if not isinstance(sensor, GridSensorActivePower):
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        self.set_latest_state(
            0 if raw <= 0 else round(raw, self.precision),
        )
        return True


class TotalPVPower(DerivedSensor, HybridInverter, PVInverter):
    @dataclass
    class Value:
        gain: float
        state: float | None = None
        last_update: float | None = None

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
            source_sensors=sensors,
        )
        self._sources: dict[str, TotalPVPower.Value] = {sensor.unique_id: TotalPVPower.Value(gain=1.0) for sensor in sensors}

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "PV Power + Third-Party PV Power"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if not republish:
            if any(value.state is None for value in self._sources.values()):
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

    def set_source_values(self, sensor: Sensor) -> bool:
        source = sensor.unique_id
        if not isinstance(sensor, PVPowerSensor):
            logging.warning(f"{self.log_identity} IGNORED attempt to call set_source_values from {sensor.log_identity} - not PVPowerSensor instance")
            return False
        elif source not in self._sources:
            logging.warning(f"{self.log_identity} IGNORED attempt to call set_source_values from '{source}' ({sensor.__class__.__name__}) - sensor is not registered")
            return False
        raw_state = getattr(sensor, "latest_raw_state", None)
        if raw_state is None:
            return False
        self._sources[source].state = float(raw_state)
        self._sources[source].last_update = time.time()
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Updated from source '{source}' - {self._sources=}")
        if any(value.state is None for value in self._sources.values()):
            return False  # until all values populated, can't do calculation
        self.set_latest_state(sum([value.state for value in self._sources.values() if value.state is not None]))
        return True


class PlantConsumedPower(CrossDeviceDerivedSensor, HybridInverter, PVInverter):
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

    def __init__(self, plant_index: int, method: ConsumptionMethod = ConsumptionMethod.CALCULATED, *sources: Sensor):
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
        self._initial_sources: list[Sensor] = []
        for s in sources:
            if isinstance(s, Sensor):
                self._initial_sources.append(s)

        self._grid_status: int | None = None
        self.sanity_check.min_raw = 0.0
        self._sources: dict[str, PlantConsumedPower.Value] = dict()
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

    def finalise_binding(self, plant_index: int) -> bool:
        """Discover all publishable ACChargerChargingPower and DCChargerOutputPower sensors
        across the plant and wire them as cross-device sources.
        """
        sources_to_bind = list(self._initial_sources)

        if self.method == ConsumptionMethod.CALCULATED:
            from sigenergy2mqtt.devices.base.registry import DeviceRegistry
            from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerChargingPower
            from sigenergy2mqtt.sensors.inverter_read_only import DCChargerOutputPower

            for device in DeviceRegistry.get(plant_index):
                for sensor in device.get_all_sensors(search_children=True).values():
                    if isinstance(sensor, (ACChargerChargingPower, DCChargerOutputPower)):
                        sources_to_bind.append(sensor)
                        self._sources[sensor.unique_id] = PlantConsumedPower.Value(gain=sensor.gain, negate=True, interval=sensor.scan_interval, requires_grid=True)
                        if self.debug_logging:
                            logging.debug(f"{self.log_identity} Added cross-device sensor {sensor.unique_id} as source")

        if sources_to_bind:
            self.declare_cross_device_sources(*sources_to_bind)
            return super().finalise_binding(plant_index)
        return True

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

    def set_source_values(self, sensor: Sensor) -> bool:
        if sensor.latest_raw_state is None:
            return False
        raw = float(sensor.latest_raw_state)
        if isinstance(sensor, TotalLoadPower):
            self._update_source(ConsumptionMethod.TOTAL.value, raw)
        elif isinstance(sensor, GeneralLoadPower):
            self._update_source(ConsumptionMethod.GENERAL.value, raw)
        elif isinstance(sensor, BatteryPower):
            self._update_source("battery", raw)
        elif isinstance(sensor, GridSensorActivePower):
            self._update_source("grid", raw)
        elif isinstance(sensor, (PlantPVPower, TotalPVPower)):
            self._update_source("pv", raw)
        elif isinstance(sensor, GridStatus):
            if self.method == ConsumptionMethod.CALCULATED:
                grid = int(sensor.latest_raw_state)
                if grid != self._grid_status:
                    if self._grid_status is not None:
                        if grid == 0:
                            logging.info(f"{self.log_identity} Grid restored - including AC/DC charger power in consumption calculations")
                        else:
                            logging.warning(f"{self.log_identity} Off Grid detected - ignoring AC/DC charger power in consumption calculations")
                    self._grid_status = grid
        elif isinstance(sensor, (ACChargerChargingPower, DCChargerOutputPower)):
            self._update_source(sensor.unique_id, raw)
        else:
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        return self._set_latest_consumption()


class GridSensorDailyExportEnergy(EnergyDailyAccumulationSensor, HybridInverter, PVInverter):
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


class GridSensorDailyImportEnergy(EnergyDailyAccumulationSensor, HybridInverter, PVInverter):
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


class TotalLifetimePVEnergy(UnpublishResetSensorMixin, DerivedSensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, plant_pv_total_generation: PlantPVTotalGeneration, third_party_lifetime_pv_energy: ThirdPartyLifetimePVEnergy):
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
            source_sensors=(plant_pv_total_generation, third_party_lifetime_pv_energy),
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

    def set_source_values(self, sensor: Sensor) -> bool:
        if sensor.latest_raw_state is None:
            return False
        if isinstance(sensor, PlantPVTotalGeneration):
            self.plant_lifetime_pv_energy = float(sensor.latest_raw_state)
        elif isinstance(sensor, ThirdPartyLifetimePVEnergy):
            self.plant_3rd_party_lifetime_pv_energy = float(sensor.latest_raw_state)
        else:
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if self.plant_lifetime_pv_energy is None or self.plant_3rd_party_lifetime_pv_energy is None:
            return False  # until all values populated, can't do calculation
        total = self.plant_lifetime_pv_energy + self.plant_3rd_party_lifetime_pv_energy
        self.set_latest_state(total)
        return True


class TotalDailyPVEnergy(EnergyDailyAccumulationSensor, HybridInverter, PVInverter):
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


class PlantDailyPVEnergy(EnergyDailyAccumulationSensor, HybridInverter, PVInverter):
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


class PlantDailyChargeEnergy(EnergyDailyAccumulationSensor, HybridInverter):
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


class PlantDailyDischargeEnergy(EnergyDailyAccumulationSensor, HybridInverter):
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


class PlantSelfConsumedPower(CrossDeviceDerivedSensor, HybridInverter):
    def __init__(self, plant_index: int):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Self-Consumed Power",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_self_consumed_power",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_self_consumed_power",
            data_type=ModbusDataType.INT32,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:battery-unknown",
            gain=None,
            precision=0,  # Intentional rounding to nearest watt
            protocol_version=Protocol.V1_8,
        )
        # _values is populated in finalise_binding() once inverter sensors are known
        self._values: dict[str, int | None] = {}

    def finalise_binding(self, plant_index: int) -> bool:
        """Discover all publishable InverterSelfConsumedPower sensors across inverters
        and wire them as cross-device sources.
        """
        from sigenergy2mqtt.devices.base.registry import DeviceRegistry
        from sigenergy2mqtt.sensors.inverter_derived import InverterSelfConsumedPower

        sources: list[InverterSelfConsumedPower] = []
        for device in DeviceRegistry.get(plant_index):
            for sensor in device.get_all_sensors(search_children=True).values():
                if isinstance(sensor, InverterSelfConsumedPower) and sensor.publishable:
                    sources.append(sensor)

        if not sources:
            logging.warning(f"{self.log_identity} no publishable InverterSelfConsumedPower sensors found - PlantSelfConsumedPower will not be published")
            return False

        self._values = {s.object_id: None for s in sources}
        self.declare_cross_device_sources(*sources)
        return super().finalise_binding(plant_index)

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "∑ of InverterSelfConsumedPower across all Inverters associated with the Plant"
        return attributes

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        if any(v is None for v in self._values.values()):
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Publishing SKIPPED - values={self._values}")
            return False  # until all values populated, can't do calculation
        if self.debug_logging:
            logging.debug(f"{self.log_identity} Publishing READY   - values={self._values}")
        await super().publish(mqtt_client, modbus_client, republish=republish)
        # reset internal values to missing for next calculation
        for k in self._values.keys():
            self._values[k] = None
        return True

    def set_source_values(self, sensor: Sensor) -> bool:
        if sensor.latest_raw_state is None:
            return False
        if isinstance(sensor, InverterSelfConsumedPower):
            self._values[sensor.object_id] = int(sensor.latest_raw_state)
        else:
            logging.warning(f"{self.log_identity} Attempt to call set_source_values from {sensor.log_identity}")
            return False
        if any(v is None for v in self._values.values()):
            return False  # until all values populated, can't do calculation
        state = sum([v for v in self._values.values() if v is not None])
        if self.debug_logging:
            logging.debug(f"{self.log_identity} values={self._values} state={state}")
        self.set_latest_state(state)
        return True


class PlantDailySelfConsumedEnergy(SimpleEnergyDailyAccumulationSensor, HybridInverter):
    def __init__(self, plant_index: int, self_consumed_power: PlantSelfConsumedPower):
        # Set properties before super().__init__ so that log_identity is correctly generated
        self.plant_index = plant_index
        super().__init__(
            name="Daily Self Consumed Energy",
            unique_id=f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_daily_self_consumed_energy",
            object_id=f"{active_config.home_assistant.entity_id_prefix}_{plant_index}_daily_self_consumed_energy",
            source=self_consumed_power,
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["source"] = "Riemann ∑ of PlantSelfConsumedPower since midnight"
        return attributes
