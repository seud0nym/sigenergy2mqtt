__all__ = ["get_pvoutput_host_config"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.devices import PowerPlant
from sigenergy2mqtt.main import HostConfig
from sigenergy2mqtt.sensors.const import DeviceClass, UnitOfEnergy, UnitOfPower
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, TotalDailyPVEnergy, TotalLifetimePVEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import PlantPVPower, TotalLoadConsumption, TotalLoadDailyConsumption
import logging


def get_pvoutput_host_config(configs: list[HostConfig], next_plant_index: int) -> HostConfig:
    logger = logging.getLogger("pvoutput")
    logger.setLevel(Config.pvoutput.log_level)

    pvoutput = HostConfig(None, None, "PVOutput")
    status = PVOutputStatusService(next_plant_index, logger)
    output = PVOutputOutputService(next_plant_index, logger)

    plant_pv_power: PlantPVPower = None
    total_pv_power: TotalPVPower = None

    for sensor in [
        sensor
        for config in configs
        for device in config.devices
        if isinstance(device, PowerPlant)
        for sensor in device.sensors.values()
        if sensor.publishable and sensor.device_class in (DeviceClass.ENERGY, DeviceClass.POWER) and sensor.state_topic is not None
    ]:
        if isinstance(sensor, TotalLifetimePVEnergy):
            status.register_generation(sensor.state_topic, unit2gain(sensor))
        elif isinstance(sensor, TotalLoadConsumption) and Config.pvoutput.consumption:
            status.register_consumption(sensor.state_topic, unit2gain(sensor))
        elif isinstance(sensor, TotalDailyPVEnergy):
            output.register_generation(sensor.state_topic, unit2gain(sensor))
        elif isinstance(sensor, TotalLoadDailyConsumption) and Config.pvoutput.consumption:
            output.register_consumption(sensor.state_topic, unit2gain(sensor))
        elif isinstance(sensor, GridSensorDailyExportEnergy) and Config.pvoutput.exports:
            output.register_exports(sensor.state_topic, unit2gain(sensor))
        elif isinstance(sensor, PlantPVPower) and Config.pvoutput.peak_power:
            plant_pv_power = sensor
        elif isinstance(sensor, TotalPVPower) and Config.pvoutput.peak_power:
            total_pv_power = sensor

    if total_pv_power is not None:
        output.register_power(total_pv_power.state_topic, unit2gain(total_pv_power))
    elif plant_pv_power is not None:
        output.register_power(plant_pv_power.state_topic, unit2gain(plant_pv_power))

    pvoutput.add_device(next_plant_index, status)
    pvoutput.add_device(next_plant_index, output)

    return pvoutput

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
