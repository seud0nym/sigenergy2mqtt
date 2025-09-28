__all__ = ["get_pvoutput_services"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
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
            if isinstance(sensor, TotalLifetimePVEnergy):
                status.register("generation", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, TotalLoadConsumption) and Config.pvoutput.consumption == "consumption":
                status.register("consumption", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, PlantTotalImportedEnergy) and Config.pvoutput.consumption == "imported":
                status.register("consumption", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, TotalDailyPVEnergy):
                output.register("generation", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, TotalLoadDailyConsumption) and Config.pvoutput.consumption == "consumption":
                output.register("consumption", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, GridSensorDailyImportEnergy):
                if Config.pvoutput.consumption == "imported":
                    output.register("consumption", sensor.state_topic, unit2gain(sensor))
                output.register("imports", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, GridSensorDailyExportEnergy):
                output.register("exports", sensor.state_topic, unit2gain(sensor))
            if isinstance(sensor, PlantPVPower):
                plant_pv_power = sensor
            if isinstance(sensor, TotalPVPower):
                total_pv_power = sensor
            if isinstance(sensor, (PVVoltageSensor, EnphaseVoltage)):
                status.register("voltage", sensor.state_topic)
            for k, v in donation.items():
                if sensor.__class__.__name__.lower() == v.lower():
                    if sensor._data_type == ModbusClient.DATATYPE.STRING:
                        logger.warning(f"PVOutput extended field '{k}' is configured to use sensor '{v}', which does not have a numeric data type")
                    else:
                        status.register(k, sensor.state_topic, 1.0)

    if total_pv_power is not None:
        output.register("power", total_pv_power.state_topic, unit2gain(total_pv_power))
    elif plant_pv_power is not None:
        output.register("power", plant_pv_power.state_topic, unit2gain(plant_pv_power))

    if Config.pvoutput.temperature_topic:
        status.register("temperature", Config.pvoutput.temperature_topic)

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
