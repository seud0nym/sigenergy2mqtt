__all__ = ["get_pvoutput_services"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.smartport.enphase import EnphaseVoltage
from sigenergy2mqtt.main.thread_config import ThreadConfig
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, UnitOfEnergy, UnitOfPower
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

    for device in [device for config in configs for device in config.devices]:
        for sensor in [
            sensor
            for sensor in device.get_all_sensors().values()
            if sensor.publishable and sensor.device_class in (DeviceClass.ENERGY, DeviceClass.POWER, DeviceClass.VOLTAGE) and sensor.state_topic is not None
        ]:
            if isinstance(sensor, TotalLifetimePVEnergy):
                status.register_generation(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, TotalLoadConsumption) and Config.pvoutput.consumption == "consumption":
                status.register_consumption(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, PlantTotalImportedEnergy) and Config.pvoutput.consumption == "imported":
                status.register_consumption(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, TotalDailyPVEnergy):
                output.register_generation(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, TotalLoadDailyConsumption) and Config.pvoutput.consumption == "consumption":
                output.register_consumption(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, GridSensorDailyImportEnergy) and Config.pvoutput.consumption == "imported":
                output.register_consumption(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, GridSensorDailyExportEnergy) and Config.pvoutput.exports:
                output.register_exports(sensor.state_topic, unit2gain(sensor))
            elif isinstance(sensor, PlantPVPower) and Config.pvoutput.peak_power:
                plant_pv_power = sensor
            elif isinstance(sensor, TotalPVPower) and Config.pvoutput.peak_power:
                total_pv_power = sensor
            elif isinstance(sensor, (PVVoltageSensor, EnphaseVoltage)):
                status.register_voltage(sensor.state_topic)

    if total_pv_power is not None:
        output.register_power(total_pv_power.state_topic, unit2gain(total_pv_power))
    elif plant_pv_power is not None:
        output.register_power(plant_pv_power.state_topic, unit2gain(plant_pv_power))

    if Config.pvoutput.temperature_topic:
        status.register_temperature(Config.pvoutput.temperature_topic)

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
