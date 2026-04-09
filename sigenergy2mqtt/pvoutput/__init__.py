"""PVOutput service wiring for Sigenergy sensors.

This module inspects all configured devices and sensors, selects compatible
topics, and builds the two PVOutput service devices used at runtime:
:class:`~sigenergy2mqtt.pvoutput.status.PVOutputStatusService` and
:class:`~sigenergy2mqtt.pvoutput.output.PVOutputOutputService`.
"""

from __future__ import annotations

from sigenergy2mqtt.common.consumption_source import ConsumptionSource
from sigenergy2mqtt.common.output_field import OutputField
from sigenergy2mqtt.common.status_field import StatusField
from sigenergy2mqtt.common.voltage_source import VoltageSource

__all__ = ["get_pvoutput_services"]

import logging
import os
from typing import TYPE_CHECKING

from sigenergy2mqtt.common import UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.smartport.enphase import EnphaseVoltage
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import Sensor, TypedSensorMixin
from sigenergy2mqtt.sensors.inverter_read_only import DailyChargeEnergy, DailyDischargeEnergy, PhaseVoltage, PVVoltageSensor
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, GridSensorDailyImportEnergy, TotalDailyPVEnergy, TotalLifetimePVEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import (
    ESSTotalChargedEnergy,
    ESSTotalDischargedEnergy,
    PlantBatterySoC,
    PlantPVPower,
    PlantRatedEnergyCapacity,
    PlantTotalImportedEnergy,
    TotalLoadConsumption,
    TotalLoadDailyConsumption,
)

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from .topic import Topic

if TYPE_CHECKING:
    from sigenergy2mqtt.main.thread_config import ThreadConfig


def get_gain(sensor: Sensor, negate: bool = False) -> float:
    """Return the topic gain that normalizes sensor values for PVOutput.

    Args:
        sensor: Source sensor whose scaling is converted into PVOutput units.
        negate: When ``True``, return the gain as a negative multiplier.
    """
    if sensor.gain is None:
        gain = 1.0
    elif sensor.unit in (UnitOfEnergy.KILO_WATT_HOUR, UnitOfPower.KILO_WATT) and sensor.gain == 100:
        gain = 10.0
    else:
        gain = float(sensor.gain)
    return gain if negate is False else gain * -1.0


def _is_home_assistant_addon_runtime() -> bool:
    """Return True when running inside a Home Assistant app container."""
    if any(os.getenv(var) for var in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN", "HASSIO")):
        return True
    return os.path.isfile("/data/options.json")


def _as_explicit_mqtt_topic(value: str) -> str | None:
    """Extract a direct MQTT topic from a configured extended-field value."""
    v = value.strip()
    if v.lower().startswith("mqtt:"):
        return v[5:].strip() or None
    if "/" in v:
        return v
    return None


def _as_home_assistant_sensor_entity(value: str) -> str | None:
    """Return a Home Assistant sensor entity id when configured and supported."""
    v = value.strip()
    if v.lower().startswith("ha:"):
        v = v[3:].strip()
    if not v.startswith("sensor."):
        return None
    if not _is_home_assistant_addon_runtime():
        return None
    object_id = v[7:]
    if not object_id:
        return None
    return f"sensor.{object_id}"


def get_pvoutput_services(configs: list[ThreadConfig]) -> list[PVOutputStatusService | PVOutputOutputService]:
    """Build and configure PVOutput status/output service devices.

    The function scans all publishable sensors from all thread configs,
    maps each sensor to the relevant PVOutput status/output field(s), and
    enables raw publishing where required so MQTT receives numeric values that
    can be uploaded directly.

    Args:
        configs: Thread configurations containing discovered devices.

    Returns:
        A two-item list with status and output services, or an empty list when
        PVOutput support is disabled in configuration.
    """
    if not active_config.pvoutput.enabled:
        return []
    logger = logging.getLogger("pvoutput")
    logger.setLevel(active_config.pvoutput.log_level)

    plant_pv_power: PlantPVPower | None = None
    total_pv_power: TotalPVPower | None = None

    donation = {k: v for k, v in active_config.pvoutput.extended.items() if isinstance(v, str) and v.strip() != ""}  # type: ignore[reportGeneralTypeIssues]
    matched_extended: set[StatusField] = set()
    ha_extended_entities: dict[StatusField, str] = {}

    extended_data: dict[StatusField, str | None] = {field: None for field in StatusField}
    status_topics: dict[StatusField, list[Topic]] = {field: [] for field in StatusField}
    output_topics: dict[OutputField, list[Topic]] = {field: [] for field in OutputField}

    for device in [device for config in configs for device in config.devices]:
        for sensor in [sensor for sensor in device.get_all_sensors().values() if sensor.publishable and sensor.raw_state_topic is not None]:
            match sensor:
                case DailyChargeEnergy():
                    if active_config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case DailyDischargeEnergy():
                    if active_config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                case ESSTotalChargedEnergy():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_CHARGED].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    status_topics[StatusField.BATTERY_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    if active_config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case ESSTotalDischargedEnergy():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_DISCHARGED].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    status_topics[StatusField.BATTERY_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                    if active_config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                case GridSensorDailyExportEnergy():
                    sensor.publish_raw = True
                    output_topics[OutputField.EXPORTS].append(Topic(sensor.raw_state_topic, None, get_gain(sensor)))
                case GridSensorDailyImportEnergy():
                    sensor.publish_raw = True
                    gain = get_gain(sensor)
                    if active_config.pvoutput.consumption == ConsumptionSource.IMPORTED:
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, None, gain))
                    output_topics[OutputField.IMPORTS].append(Topic(sensor.raw_state_topic, None, gain))
                case PhaseVoltage():
                    if (
                        active_config.pvoutput.voltage == VoltageSource.L_N_AVG
                        or active_config.pvoutput.voltage == VoltageSource.L_L_AVG
                        or (active_config.pvoutput.voltage == VoltageSource.PHASE_A and sensor.phase == "A")
                        or (active_config.pvoutput.voltage == VoltageSource.PHASE_B and sensor.phase == "B")
                        or (active_config.pvoutput.voltage == VoltageSource.PHASE_C and sensor.phase == "C")
                    ):
                        status_topics[StatusField.VOLTAGE].append(Topic(sensor.state_topic, getattr(sensor, "scan_interval", None)))  # Need voltage, not raw
                case PlantBatterySoC():
                    status_topics[StatusField.BATTERY_SOC].append(Topic(sensor.state_topic, sensor.scan_interval))  # Need percentage, not raw
                case PlantPVPower():
                    plant_pv_power = sensor
                case PlantRatedEnergyCapacity():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_CAPACITY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case PlantTotalImportedEnergy():
                    if active_config.pvoutput.consumption == ConsumptionSource.IMPORTED:
                        sensor.publish_raw = True
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case PVVoltageSensor() | EnphaseVoltage():
                    if active_config.pvoutput.voltage == VoltageSource.PV:
                        status_topics[StatusField.VOLTAGE].append(Topic(sensor.state_topic, getattr(sensor, "scan_interval", None)))  # Need voltage, not raw
                case TotalDailyPVEnergy():
                    sensor.publish_raw = True
                    output_topics[OutputField.GENERATION].append(Topic(sensor.raw_state_topic, None, get_gain(sensor)))
                case TotalLifetimePVEnergy():
                    sensor.publish_raw = True
                    gain = get_gain(sensor)
                    status_topics[StatusField.GENERATION_ENERGY].append(Topic(sensor.raw_state_topic, None, gain))
                    status_topics[StatusField.GENERATION_POWER].append(Topic(sensor.raw_state_topic, None, get_gain(sensor)))
                case TotalLoadConsumption():
                    if active_config.pvoutput.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.NET_OF_BATTERY):
                        sensor.publish_raw = True
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case TotalLoadDailyConsumption():
                    if active_config.pvoutput.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.NET_OF_BATTERY):
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case TotalPVPower():
                    total_pv_power = sensor
            for k, v in donation.items():
                if (sensor.__class__.__name__.lower() == v.lower() or sensor["object_id"] == v or f"sensor.{sensor['object_id']}" == v) and isinstance(sensor, TypedSensorMixin):
                    if sensor.data_type == ModbusDataType.STRING:
                        logger.warning(f"PVOutput extended field '{k}' is configured to use sensor '{v}', which does not have a numeric data type")
                    else:
                        key = StatusField(k)
                        status_topics[key].append(Topic(sensor.state_topic, getattr(sensor, "scan_interval", None), precision=sensor.precision))  # Used displayed value, not raw
                        extended_data[key] = sensor.device_class
                        matched_extended.add(key)

    for k, v in donation.items():
        key = StatusField(k)
        if key in matched_extended:
            continue
        entity_id = _as_home_assistant_sensor_entity(v)
        if entity_id is not None:
            ha_extended_entities[key] = entity_id
            status_topics[key].append(Topic(f"__ha_sensor__:{entity_id}", scan_interval=None))
            logger.info(f"PVOutput extended field '{k}' mapped Home Assistant sensor '{v}' to Supervisor API entity '{entity_id}'")
            matched_extended.add(key)
            continue
        topic = _as_explicit_mqtt_topic(v)
        if topic is not None:
            status_topics[key].append(Topic(topic, scan_interval=None))
            logger.info(f"PVOutput extended field '{k}' configured as direct MQTT topic '{topic}'")
            matched_extended.add(key)
            continue
        if v.startswith("sensor.") or v.lower().startswith("ha:sensor."):
            logger.warning(f"PVOutput extended field '{k}' Home Assistant sensor source '{v}' ignored: only available when running as a Home Assistant app")

    if total_pv_power is not None:
        total_pv_power.publish_raw = True
        output_topics[OutputField.PEAK_POWER].append(Topic(total_pv_power.raw_state_topic, None, get_gain(total_pv_power)))
    elif plant_pv_power is not None:
        plant_pv_power.publish_raw = True
        output_topics[OutputField.PEAK_POWER].append(Topic(plant_pv_power.raw_state_topic, plant_pv_power.scan_interval, get_gain(plant_pv_power)))

    if active_config.pvoutput.temperature_topic:
        temp_source = active_config.pvoutput.temperature_topic.strip()
        temp_entity_id = _as_home_assistant_sensor_entity(temp_source)
        if temp_entity_id is not None:
            ha_extended_entities[StatusField.TEMPERATURE] = temp_entity_id
            status_topics[StatusField.TEMPERATURE].append(Topic(f"__ha_sensor__:{temp_entity_id}", scan_interval=None))
            logger.info(f"PVOutput temperature source mapped Home Assistant sensor '{temp_source}' to Supervisor API entity '{temp_entity_id}'")
        else:
            temp_topic = _as_explicit_mqtt_topic(temp_source) or temp_source
            status_topics[StatusField.TEMPERATURE].append(Topic(temp_topic, scan_interval=None))
            if temp_topic != temp_source:
                logger.info(f"PVOutput temperature source configured as direct MQTT topic '{temp_topic}'")
            elif temp_source.startswith("sensor.") or temp_source.lower().startswith("ha:sensor."):
                logger.warning(f"PVOutput temperature source '{temp_source}' ignored as Home Assistant sensor source because app runtime was not detected; using literal MQTT topic")

    status = PVOutputStatusService(logger, status_topics, extended_data, ha_extended_entities)
    output = PVOutputOutputService(logger, output_topics)

    return [status, output]
