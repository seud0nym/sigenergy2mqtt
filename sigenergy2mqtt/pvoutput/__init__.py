__all__ = ["get_pvoutput_services"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from .topic import Topic
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config, ConsumptionSource, OutputField, StatusField
from sigenergy2mqtt.devices.smartport.enphase import EnphaseVoltage
from sigenergy2mqtt.main.thread_config import ThreadConfig
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.sensors.inverter_read_only import DailyChargeEnergy, DailyDischargeEnergy, PVVoltageSensor
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
import logging


def get_pvoutput_services(configs: list[ThreadConfig]) -> list[PVOutputStatusService | PVOutputOutputService]:
    logger = logging.getLogger("pvoutput")
    logger.setLevel(Config.pvoutput.log_level)

    plant_pv_power: PlantPVPower = None
    total_pv_power: TotalPVPower = None

    donation = {k: v for k, v in Config.pvoutput.extended.items() if v != ""}

    extended_data: dict[StatusField, str] = {field: None for field in StatusField}
    status_topics: dict[StatusField, list[Topic]] = {field: [] for field in StatusField}
    output_topics: dict[OutputField, list[Topic]] = {field: [] for field in OutputField}

    for device in [device for config in configs for device in config.devices]:
        for sensor in [sensor for sensor in device.get_all_sensors().values() if sensor.publishable and sensor.raw_state_topic is not None]:
            match sensor:
                case DailyChargeEnergy():
                    if Config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case DailyDischargeEnergy():
                    if Config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                case ESSTotalChargedEnergy():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_CHARGED].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    status_topics[StatusField.BATTERY_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    if Config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case ESSTotalDischargedEnergy():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_DISCHARGED].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                    status_topics[StatusField.BATTERY_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                    if Config.pvoutput.consumption == ConsumptionSource.NET_OF_BATTERY:
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor, negate=True)))
                case GridSensorDailyExportEnergy():
                    sensor.publish_raw = True
                    output_topics[OutputField.EXPORTS].append(Topic(sensor.raw_state_topic, None, get_gain(sensor)))
                case GridSensorDailyImportEnergy():
                    sensor.publish_raw = True
                    gain = get_gain(sensor)
                    if Config.pvoutput.consumption == ConsumptionSource.IMPORTED:
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, gain))
                    output_topics[OutputField.IMPORTS].append(Topic(sensor.raw_state_topic, None, gain))
                case PlantBatterySoC():
                    status_topics[StatusField.BATTERY_SOC].append(Topic(sensor.state_topic, sensor.scan_interval))  # Need percentage, not raw
                case PlantPVPower():
                    plant_pv_power = sensor
                case PlantRatedEnergyCapacity():
                    sensor.publish_raw = True
                    status_topics[StatusField.BATTERY_CAPACITY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case PlantTotalImportedEnergy():
                    if Config.pvoutput.consumption == ConsumptionSource.IMPORTED:
                        sensor.publish_raw = True
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case PVVoltageSensor() | EnphaseVoltage():
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
                    if Config.pvoutput.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.NET_OF_BATTERY):
                        sensor.publish_raw = True
                        status_topics[StatusField.CONSUMPTION_ENERGY].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                        status_topics[StatusField.CONSUMPTION_POWER].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case TotalLoadDailyConsumption():
                    if Config.pvoutput.consumption in (ConsumptionSource.CONSUMPTION, ConsumptionSource.NET_OF_BATTERY):
                        sensor.publish_raw = True
                        output_topics[OutputField.CONSUMPTION].append(Topic(sensor.raw_state_topic, sensor.scan_interval, get_gain(sensor)))
                case TotalPVPower():
                    total_pv_power = sensor
            for k, v in donation.items():
                if sensor.__class__.__name__.lower() == v.lower() or sensor["object_id"] == v or f"sensor.{sensor['object_id']}" == v:
                    if sensor._data_type == ModbusClient.DATATYPE.STRING:
                        logger.warning(f"PVOutput extended field '{k}' is configured to use sensor '{v}', which does not have a numeric data type")
                    else:
                        status_topics[k].append(Topic(sensor.state_topic, getattr(sensor, "scan_interval", None), precision=sensor.precision))  # Used displayed value, not raw
                        extended_data[k] = sensor.device_class

    if total_pv_power is not None:
        total_pv_power.publish_raw = True
        output_topics[OutputField.PEAK_POWER].append(Topic(total_pv_power.raw_state_topic, None, get_gain(total_pv_power)))
    elif plant_pv_power is not None:
        plant_pv_power.publish_raw = True
        output_topics[OutputField.PEAK_POWER].append(Topic(plant_pv_power.raw_state_topic, plant_pv_power.scan_interval, get_gain(plant_pv_power)))

    if Config.pvoutput.temperature_topic:
        status_topics[StatusField.TEMPERATURE].append(Topic(Config.pvoutput.temperature_topic, scan_interval=None))

    status = PVOutputStatusService(logger, status_topics, extended_data)
    output = PVOutputOutputService(logger, output_topics)

    return [status, output]


def get_gain(sensor: Sensor, negate: bool = False) -> float:
    if sensor.gain is None:
        gain = 1.0
    elif sensor.unit in (UnitOfEnergy.KILO_WATT_HOUR, UnitOfPower.KILO_WATT) and sensor.gain == 100:
        gain = 10.0
    else:
        gain = float(sensor.gain)
    return gain if negate is False else gain * -1.0
