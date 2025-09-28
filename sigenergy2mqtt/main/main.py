from .thread_config import ThreadConfig, ThreadConfigFactory
from .threading import start
from pymodbus import pymodbus_apply_logging_config
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.pvoutput import get_pvoutput_services
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PVStringCount
from sigenergy2mqtt.sensors.plant_read_only import PlantRatedChargingPower, PlantRatedDischargingPower
from typing import Tuple
import logging
import re
import signal


async def async_main() -> None:
    pymodbus_apply_logging_config(Config.get_modbus_log_level())
    configure_logging()

    for plant_index in range(len(Config.devices)):
        device = Config.devices[plant_index]
        if device.registers.read_only or device.registers.read_write or device.registers.write_only:
            config: ThreadConfig = ThreadConfigFactory.get_config(device.host, device.port)
            modbus = ModbusClient(device.host, port=device.port)
            async with modbus:
                logging.info(f"Connected to Modbus interface at {device.host}:{device.port} for register probing")
                plant: PowerPlant = None  # Make sure plant is only created with first inverter
                inverters: dict[int, str] = {}
                for device_address in device.inverters:
                    inverter, plant_tmp = await make_plant_and_inverter(plant_index, modbus, device_address, plant)
                    if plant is None and plant_tmp is not None:
                        plant = plant_tmp
                        config.add_device(plant_index, plant)
                        remote_ems = plant.sensors[f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_40029"]
                        assert remote_ems is not None, "Failed to find RemoteEMS instance"
                    if inverter is not None:
                        inverters[device_address] = inverter.unique_id
                        config.add_device(plant_index, inverter)
                if plant and len(device.dc_chargers) == 0:
                    logging.debug(f"No DC chargers defined for plant {device.host}:{device.port} - disabling DC charger statistics interface sensors")
                    plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_30252", search_children=True).publishable = False
                    plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_30256", search_children=True).publishable = False
                else:
                    for device_address in device.dc_chargers:
                        charger = await make_dc_charger(plant_index, device_address, inverters[device_address], remote_ems)
                        config.add_device(plant_index, charger)
                if plant and len(device.ac_chargers) == 0:
                    logging.debug(f"No AC chargers defined for plant {device.host}:{device.port} - disabling AC charger statistics interface sensors")
                    plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_30232", search_children=True).publishable = False
                else:
                    for device_address in device.ac_chargers:
                        charger = await make_ac_charger(plant_index, modbus, device_address, plant, remote_ems)
                        config.add_device(plant_index, charger)
                logging.info(f"Disconnecting from Modbus interface at {device.host}:{device.port} - register probing complete")
        else:
            logging.info(f"Ignored Modbus host {device.host} (device index {plant_index}): all registers are disabled (read-only=false read-write=false write-only=false)")

    configs: list[ThreadConfig] = ThreadConfigFactory.get_configs()

    svc_thread_cfg = ThreadConfig(None, None, "Services")
    svc_thread_cfg.add_device(-1, MetricsService())

    if Config.pvoutput.enabled and not Config.clean:
        for service in get_pvoutput_services(configs):
            svc_thread_cfg.add_device(-1, service)

    configs.insert(0, svc_thread_cfg)

    def configure_for_restart(caught, frame):
        logging.info(f"Signal {caught} received - reconfiguring for restart")
        Config.home_assistant.enabled = False  # Disable publishing Home Assistant offline availability since we are going to restart
        exit_on_signal(caught, frame)

    def exit_on_signal(caught, frame):
        logging.info(f"Signal {caught} received - Shutdown commenced")
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        for config in configs:
            config.offline()

    def reload_on_signal(caught, frame):
        logging.info(f"Signal {caught} received - Reloading configuration")
        Config.reload()
        configure_logging()
        for config in configs:
            config.reload_config()

    signal.signal(signal.SIGINT, exit_on_signal)
    signal.signal(signal.SIGHUP, reload_on_signal)
    signal.signal(signal.SIGTERM, exit_on_signal)
    signal.signal(signal.SIGUSR1, configure_for_restart)

    await start(configs)
    logging.info("Shutdown completed")


def configure_logging():
    root = logging.getLogger("root")
    pymodbus = logging.getLogger("pymodbus")
    paho_mqtt = logging.getLogger("paho.mqtt")
    pvoutput = logging.getLogger("pvoutput")
    if root.level != Config.log_level:
        if root.level != logging.NOTSET:
            root.log(root.level, f"sigenergy2mqtt log-level changed to {logging.getLevelName(Config.log_level)}")
        root.setLevel(Config.log_level)
    if pymodbus.level != Config.get_modbus_log_level():
        if pymodbus.level != logging.NOTSET:
            pymodbus.log(root.level, f"pymodbus log-level changed to {logging.getLevelName(Config.get_modbus_log_level())}")
        pymodbus.propagate = False
        pymodbus.setLevel(Config.get_modbus_log_level())
    if paho_mqtt.level != Config.mqtt.log_level:
        if paho_mqtt.level != logging.NOTSET:
            paho_mqtt.log(root.level, f"paho.mqtt log-level changed to {logging.getLevelName(Config.mqtt.log_level)}")
        paho_mqtt.setLevel(Config.mqtt.log_level)
    if pvoutput.level != Config.pvoutput.log_level:
        if pvoutput.level != logging.NOTSET:
            pvoutput.log(root.level, f"pvoutput log-level changed to {logging.getLevelName(Config.pvoutput.log_level)}")
        pvoutput.setLevel(Config.pvoutput.log_level)


async def make_ac_charger(plant_index, modbus, device_address, plant, remote_ems):
    input_breaker = ACChargerInputBreaker(plant_index, device_address)
    rated_current = ACChargerRatedCurrent(plant_index, device_address)
    ip_value = await input_breaker.get_state(modbus=modbus)
    rc_value = await rated_current.get_state(modbus=modbus)
    charger = ACCharger(plant_index, device_address, remote_ems, ip_value, rc_value, input_breaker, rated_current)
    charger.via_device = plant.unique_id
    return charger


async def make_dc_charger(plant_index, device_address, inverter_unique_id, remote_ems):
    charger = DCCharger(plant_index, device_address, remote_ems)
    charger.via_device = inverter_unique_id
    return charger


serial_numbers = []


async def make_plant_and_inverter(plant_index, modbus, device_address, plant) -> Tuple[Inverter, HybridInverter | PVInverter, PowerPlant, any]:
    serial = InverterSerialNumber(plant_index, device_address)
    serial_number = await serial.get_state(modbus=modbus)

    if serial_number in serial_numbers:
        logging.info(f"Inverter serial number {serial_number} has already been detected - ignoring")
        return None, None

    model = InverterModel(plant_index, device_address)
    firmware = InverterFirmwareVersion(plant_index, device_address)
    strings = PVStringCount(plant_index, device_address)
    output_type = OutputType(plant_index, device_address)

    model_id = await model.get_state(modbus=modbus)
    firmware_version = await firmware.get_state(modbus=modbus)
    pv_string_count = await strings.get_state(modbus=modbus)
    output_type_state = await output_type.get_state(raw=True, modbus=modbus)
    match output_type_state:
        case 0:  # L/N
            power_phases = 1
        case 3:  # L1/L2/N
            power_phases = 2
        case _:
            power_phases = 3

    if re.search(r"EC|Hybrid|PG|PV.*M1-HYA", model_id):
        device_type = HybridInverter()
    else:
        device_type = PVInverter()

    if plant is None:
        rated_charging_power = PlantRatedChargingPower(plant_index)
        rated_discharging_power = PlantRatedDischargingPower(plant_index)
        rcp_value = await rated_charging_power.get_state(modbus=modbus)
        rdp_value = await rated_discharging_power.get_state(modbus=modbus)
        plant = PowerPlant(plant_index, device_type, output_type_state, power_phases, rcp_value, rdp_value, rated_charging_power, rated_discharging_power)

    inverter = Inverter(plant_index, device_address, device_type, model_id, serial_number, firmware_version, pv_string_count, power_phases, strings, output_type, firmware, model, serial)
    inverter.via_device = plant.unique_id

    serial_numbers.append(serial_number)

    return inverter, plant
