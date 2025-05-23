__all__ = ["get_pvoutput_host_config"]

from .output import PVOutputOutputService
from .status import PVOutputStatusService
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import PowerPlant
from sigenergy2mqtt.main import HostConfig
from sigenergy2mqtt.sensors.plant_derived import GridSensorDailyExportEnergy, PlantDailyConsumedEnergy, PlantDailyPVEnergy, PlantLifetimePVEnergy, PlantLifetimeConsumedEnergy, TotalPVPower
from sigenergy2mqtt.sensors.plant_read_only import PlantPVPower
import logging


def get_pvoutput_host_config(configs: list[HostConfig], next_plant_index: int) -> HostConfig:
    logger = logging.getLogger("pvoutput")
    logger.setLevel(Config.pvoutput.log_level)

    pvoutput = HostConfig(None, None, "PVOutput")
    status = PVOutputStatusService(next_plant_index, logger)
    output = PVOutputOutputService(next_plant_index, logger)

    plant_pv_power: PlantPVPower = None
    total_pv_power: TotalPVPower = None
    for sensor in [sensor for config in configs for device in config.devices if isinstance(device, PowerPlant) for sensor in device.sensors.values()]:
        if isinstance(sensor, PlantLifetimePVEnergy):
            status.register_generation(sensor.state_topic, sensor.gain)
        elif isinstance(sensor, PlantLifetimeConsumedEnergy) and Config.pvoutput.consumption:
            status.register_consumption(sensor.state_topic, sensor.gain)
        elif isinstance(sensor, PlantDailyPVEnergy):
            output.register_generation(sensor.state_topic, sensor.gain)
        elif isinstance(sensor, PlantDailyConsumedEnergy) and Config.pvoutput.consumption:
            output.register_consumption(sensor.state_topic, sensor.gain)
        elif isinstance(sensor, GridSensorDailyExportEnergy) and Config.pvoutput.exports:
            output.register_exports(sensor.state_topic, sensor.gain)
        elif isinstance(sensor, PlantPVPower) and Config.pvoutput.peak_power:
            plant_pv_power = sensor
        elif isinstance(sensor, TotalPVPower) and Config.pvoutput.peak_power:
            total_pv_power = sensor
        
    if total_pv_power is not None:
        output.register_power(total_pv_power.state_topic, total_pv_power.gain)
    elif plant_pv_power is not None:
        output.register_power(plant_pv_power.state_topic, plant_pv_power.gain)

    pvoutput.add_device(next_plant_index, status)
    pvoutput.add_device(next_plant_index, output)

    return pvoutput
