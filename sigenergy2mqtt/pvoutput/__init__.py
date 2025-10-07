__all__ = ["get_pvoutput_services"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config, CONSUMPTION, IMPORTED, OutputField, StatusField
from sigenergy2mqtt.devices.smartport.enphase import EnphaseVoltage
from sigenergy2mqtt.main.thread_config import ThreadConfig
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.sensors.inverter_read_only import PVVoltageSensor
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, GridSensorDailyImportEnergy, TotalDailyPVEnergy, TotalLifetimePVEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import PlantPVPower, PlantTotalImportedEnergy, TotalLoadConsumption, TotalLoadDailyConsumption
import logging


def get_pvoutput_services(configs: list[ThreadConfig]) -> list[PVOutputStatusService | PVOutputOutputService]:
    logger = logging.getLogger("pvoutput")
    logger.setLevel(Config.pvoutput.log_level)

    status = PVOutputStatusService(logger)
    output = PVOutputOutputService(logger)

    plant_pv_power: PlantPVPower = None
    total_pv_power: TotalPVPower = None

    donation = {k: v for k, v in Config.pvoutput.extended.items() if v != ""}

    for device in [device for config in configs for device in config.devices]:
        for sensor in [sensor for sensor in device.get_all_sensors().values() if sensor.publishable and sensor.state_topic is not None]:
            match sensor:
                case GridSensorDailyExportEnergy():
                    output.register(OutputField.EXPORTS, sensor.state_topic, unit2gain(sensor))
                case GridSensorDailyImportEnergy():
                    if Config.pvoutput.consumption == IMPORTED:
                        output.register(OutputField.CONSUMPTION, sensor.state_topic, unit2gain(sensor))
                    output.register(OutputField.IMPORTS, sensor.state_topic, unit2gain(sensor))
                case PlantPVPower():
                    plant_pv_power = sensor
                case PlantTotalImportedEnergy():
                    if Config.pvoutput.consumption == IMPORTED:
                        status.register(StatusField.CONSUMPTION, sensor.state_topic, unit2gain(sensor))
                case PVVoltageSensor() | EnphaseVoltage():
                    status.register(StatusField.VOLTAGE, sensor.state_topic)
                case TotalDailyPVEnergy():
                    output.register(OutputField.GENERATION, sensor.state_topic, unit2gain(sensor))
                case TotalLifetimePVEnergy():
                    status.register(StatusField.GENERATION, sensor.state_topic, unit2gain(sensor))
                case TotalLoadConsumption():
                    if Config.pvoutput.consumption == CONSUMPTION:
                        status.register(StatusField.CONSUMPTION, sensor.state_topic, unit2gain(sensor))
                case TotalLoadDailyConsumption():
                    if Config.pvoutput.consumption == CONSUMPTION:
                        output.register(OutputField.CONSUMPTION, sensor.state_topic, unit2gain(sensor))
                case TotalPVPower():
                    total_pv_power = sensor
            for k, v in donation.items():
                if sensor.__class__.__name__.lower() == v.lower():
                    if sensor._data_type == ModbusClient.DATATYPE.STRING:
                        logger.warning(f"PVOutput extended field '{k}' is configured to use sensor '{v}', which does not have a numeric data type")
                    else:
                        status.register(k, sensor.state_topic, 1.0)

    if total_pv_power is not None:
        output.register(OutputField.POWER, total_pv_power.state_topic, unit2gain(total_pv_power))
    elif plant_pv_power is not None:
        output.register(OutputField.POWER, plant_pv_power.state_topic, unit2gain(plant_pv_power))

    if Config.pvoutput.temperature_topic:
        status.register(StatusField.TEMPERATURE, Config.pvoutput.temperature_topic)

    return [status, output]


def unit2gain(sensor: Sensor) -> float:
    match sensor.unit:
        case UnitOfEnergy.WATT_HOUR | UnitOfPower.WATT:
            gain = 1.0
        case UnitOfEnergy.KILO_WATT_HOUR | UnitOfPower.KILO_WATT:
            gain = 1000.0
        case UnitOfEnergy.MEGA_WATT_HOUR | UnitOfPower.MEGA_WATT:
            gain = 1000000.0
        case _:
            gain = sensor.gain
    return gain
