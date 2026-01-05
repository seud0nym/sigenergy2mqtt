from .thread_config import ThreadConfig, ThreadConfigFactory
from .threading import start
from pathlib import Path
from pymodbus import pymodbus_apply_logging_config
from sigenergy2mqtt.config import Config, ConsumptionMethod, Protocol, ProtocolApplies
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.devices.types import DeviceType, HybridInverter
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.pvoutput import get_pvoutput_services
from sigenergy2mqtt.sensors.base import ModbusSensor
from sigenergy2mqtt.sensors.const import InputType
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount, PVStringCount
from sigenergy2mqtt.sensors.plant_read_only import GridCodeRatedFrequency, PlantRatedChargingPower, PlantRatedDischargingPower
from typing import Tuple
import logging
import signal


serial_numbers = []


async def async_main() -> None:
    pymodbus_apply_logging_config(Config.get_modbus_log_level())
    configure_logging()

    protocol_version: Protocol = None
    for plant_index in range(len(Config.devices)):
        device = Config.devices[plant_index]
        if device.registers.read_only or device.registers.read_write or device.registers.write_only:
            config: ThreadConfig = ThreadConfigFactory.get_config(device.host, device.port, device.timeout, device.retries)
            modbus = ModbusClient(device.host, port=device.port, timeout=device.timeout, retries=device.retries)
            async with modbus:
                logging.info(f"Connected to modbus://{device.host}:{device.port} for register probing")
                plant: PowerPlant = None  # Make sure plant is only created with first inverter
                inverters: dict[int, str] = {}
                for device_address in device.inverters:
                    inverter, plant_tmp = await make_plant_and_inverter(plant_index, modbus, device_address, plant)
                    if plant is None and plant_tmp is not None:
                        plant = plant_tmp
                        availability_control_sensor = plant.sensors[f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_40029"]
                        assert availability_control_sensor is not None, "Failed to find RemoteEMS instance"
                        config.add_device(plant_index, plant)
                        await test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus, plant_index, plant, 30279, 30281, 40049)
                        protocol_version = plant.protocol_version if protocol_version is None or protocol_version < plant.protocol_version else protocol_version
                        if not plant.has_battery:
                            logging.debug(f"No battery modules attached to plant {device.host}:{device.port} - disabling charging/discharging statistics interface sensors")
                            for register in (30244, 30248):
                                si_sensor = plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_{register}", search_children=True)
                                if si_sensor:
                                    si_sensor.publishable = False
                    if inverter is not None:
                        inverters[device_address] = inverter.unique_id
                        config.add_device(plant_index, inverter)
                        await test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus, plant_index, inverter, 30622, 30623)
                if plant and len(device.dc_chargers) == 0:
                    logging.debug(f"No DC chargers defined for plant {device.host}:{device.port} - disabling DC charger statistics interface sensors")
                    for register in (30252, 30256):
                        si_sensor = plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_{register}", search_children=True)
                        if si_sensor:
                            si_sensor.publishable = False
                else:
                    for device_address in device.dc_chargers:
                        charger = await make_dc_charger(plant_index, device_address, plant.protocol_version, inverters[device_address])
                        config.add_device(plant_index, charger)
                if plant and len(device.ac_chargers) == 0:
                    logging.debug(f"No AC chargers defined for plant {device.host}:{device.port} - disabling AC charger statistics interface sensors")
                    si_sensor = plant.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_247_30232", search_children=True)
                    if si_sensor:
                        si_sensor.publishable = False
                else:
                    for device_address in device.ac_chargers:
                        charger = await make_ac_charger(plant_index, modbus, device_address, plant)
                        config.add_device(plant_index, charger)
                logging.info(f"Disconnecting from modbus://{device.host}:{device.port} - register probing complete")
        else:
            logging.info(f"Ignored Modbus host {device.host} (device index {plant_index}): all registers are disabled (read-only=false read-write=false write-only=false)")

    configs: list[ThreadConfig] = ThreadConfigFactory.get_configs()

    svc_thread_cfg = ThreadConfig(None, None, name="Services")
    svc_thread_cfg.add_device(-1, MetricsService(protocol_version))

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

    if Config.home_assistant.enabled:
        current_version_file = Path(Config.persistent_state_path, ".current-version")
        current_version: str = None
        if current_version_file.exists():
            try:
                with current_version_file.open("r") as f:
                    current_version = f.read()
                    logging.debug(f"Loaded '{current_version}' from {current_version_file}")
            except Exception as error:
                logging.error(f"Failed to read {current_version_file}: {error}")
        upgrade_detected: bool = current_version != Config.version()
        if upgrade_detected:
            if current_version:
                logging.info(f"Upgrade to '{Config.version()}' from '{current_version}' detected")
            else:
                logging.info(f"Upgrade to '{Config.version()}' detected")
            logging.debug(f"Writing '{Config.version()}' to {current_version_file}")
            try:
                with current_version_file.open("w") as f:
                    f.write(Config.version())
            except Exception as error:
                logging.error(f"Failed to write to {current_version_file}: {error}")
    else:
        upgrade_detected = False

    await start(configs, False)  # Removed upgrade_clean_required because it deletes associated statistics helper entities (#77)
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


async def get_state(sensor: ModbusSensor, modbus: ModbusClient, device: str, default_value: int | float | str | None = None, raw: bool = False) -> tuple[ModbusSensor, int | float | str | None]:
    try:
        state = await sensor.get_state(raw=raw, modbus=modbus)
        logging.debug(f"READING modbus://{modbus.comm_params.host}:{modbus.comm_params.port} - Acquiring {sensor.__class__.__name__} {'raw ' if raw else ''}{state=} to initialise {device}")
    except Exception as e:
        state = default_value
        logging.debug(f"FAILURE modbus://{modbus.comm_params.host}:{modbus.comm_params.port} - Acquiring {sensor.__class__.__name__} to initialise {device} -> {e} (returning {default_value=})")
    return sensor, state


async def make_ac_charger(plant_index, modbus, device_address, plant):
    input_breaker, ip_value = await get_state(ACChargerInputBreaker(plant_index, device_address), modbus, "ac-charger")
    rated_current, rc_value = await get_state(ACChargerRatedCurrent(plant_index, device_address), modbus, "ac-charger")
    charger = ACCharger(plant_index, device_address, plant.protocol_version, ip_value, rc_value, input_breaker, rated_current)
    charger.via_device = plant.unique_id
    return charger


async def make_dc_charger(plant_index, device_address, protocol_version, inverter_unique_id):
    charger = DCCharger(plant_index, device_address, protocol_version)
    charger.via_device = inverter_unique_id
    return charger


async def make_plant_and_inverter(plant_index, modbus, device_address, plant) -> Tuple[Inverter, PowerPlant]:
    serial, sn = await get_state(InverterSerialNumber(plant_index, device_address), modbus, "inverter")
    if sn in serial_numbers:
        logging.info(f"Inverter serial number {sn} has already been detected - ignoring")
        return None, None

    model, mdl = await get_state(InverterModel(plant_index, device_address), modbus, "inverter")
    device_type = DeviceType.create(mdl)

    firmware, fw = await get_state(InverterFirmwareVersion(plant_index, device_address), modbus, "inverter")
    string_count, strings = await get_state(PVStringCount(plant_index, device_address), modbus, "inverter")

    output_type, ot = await get_state(OutputType(plant_index, device_address), modbus, "plant/inverter", raw=True)
    match ot:
        case 0:  # L/N
            phases = 1
        case 3:  # L1/L2/N
            phases = 2
        case _:
            phases = 3

    if isinstance(device_type, HybridInverter):
        pack_count, batteries = await get_state(PACKBCUCount(plant_index, device_address), modbus, "inverter", default_value=0)
    else:
        pack_count = None
        batteries = 0

    if plant is None:
        # Probe the plant for the supported Modbus Protocol version
        for register, count, version in (  # Must be an input register specific to the version, in descending protocol sequence
            (30284, 2, Protocol.V2_8),  # TotalLoadPower
            (30194, 2, Protocol.V2_7),  # ThirdPartyPVPower
            (30092, 2, Protocol.V2_6),  # TotalLoadDailyConsumption
            (30087, 1, Protocol.V2_5),  # PlantBatterySoH
        ):
            try:
                logging.debug(f"READING modbus://{modbus.comm_params.host}:{modbus.comm_params.port} to see if V{version.value} register {register} exists ({count=} device_id=247)")
                rr = await modbus.read_input_registers(register, count=count, device_id=247)
                if rr.isError():
                    logging.debug(f"FAILURE modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {register=} {count=} device_id=247 -> {rr.exception_code=}")
                else:
                    # No exception, so assign the associated protocol as the real version
                    logging.debug(f"SUCCESS modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {register=} {count=} device_id=247 -> OK protocol=V{version.value}")
                    protocol = version
                    break
            except Exception as e:
                logging.debug(f"FAILURE modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {register=} {count=} device_id=247 -> {e}")
                pass
        else:
            logging.debug(f"DEFAULT modbus://{modbus.comm_params.host}:{modbus.comm_params.port} to Sigenergy Modbus Protocol V1.8")
            protocol = Protocol.V1_8
        logging.info(f"Interrogated modbus://{modbus.comm_params.host}:{modbus.comm_params.port} and found Sigenergy Modbus Protocol V{protocol.value} ({ProtocolApplies(protocol)})")

        if protocol < Protocol.V2_8 and Config.consumption != ConsumptionMethod.CALCULATED:
            logging.warning(f"Resetting consumption configuration to {ConsumptionMethod.CALCULATED.name} because {Config.consumption.name} is not supported on Modbus Protocol V{protocol.value}")
            Config.consumption = ConsumptionMethod.CALCULATED

        if isinstance(device_type, HybridInverter):
            rated_charging_power, rcp = await get_state(PlantRatedChargingPower(plant_index), modbus, "plant", default_value=0.0)
            rated_discharging_power, rdp = await get_state(PlantRatedDischargingPower(plant_index), modbus, "plant", default_value=0.0)
        else:
            rated_charging_power = rated_discharging_power = None
            rcp = rdp = 0.0

        if device_type.has_grid_code_interface and protocol >= Protocol.V2_8:
            rated_frequency, rf = await get_state(GridCodeRatedFrequency(plant_index), modbus, "plant")
        else:
            rated_frequency = rf = None

        plant = PowerPlant(plant_index, device_type, protocol, ot, phases, rcp, rdp, rf, rated_charging_power, rated_discharging_power, rated_frequency)
    else:
        protocol = plant.protocol_version

    inverter = Inverter(plant_index, device_address, protocol, device_type, mdl, sn, fw, batteries, strings, phases, string_count, output_type, firmware, model, serial, pack_count)
    inverter.via_device = plant.unique_id

    serial_numbers.append(sn)

    return inverter, plant


async def test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus: ModbusClient, plant_index, device: PowerPlant | Inverter, *registers: int) -> None:
    device_id: int = device.device_address
    for register in registers:
        sensor: ModbusSensor = device.get_sensor(f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_id:03d}_{register}", search_children=True)
        if sensor and sensor.publishable:
            id = f"{device.name} - {sensor.name} [{sensor['platform']}.{sensor['object_id']}]" if Config.home_assistant.enabled else f"{device.name} - {sensor.name} [{sensor.state_topic}]"
            try:
                if sensor.input_type == InputType.HOLDING:
                    rr = await modbus.read_holding_registers(register, count=sensor.count, device_id=device_id)
                elif sensor.input_type == InputType.INPUT:
                    rr = await modbus.read_input_registers(register, count=sensor.count, device_id=device_id)
                if rr.isError() and rr.exception_code == 0x02:
                    logging.info(f"UNPUBLISHED {id}: ILLEGAL DATA ADDRESS")
                    sensor.publishable = False
            except Exception as e:
                logging.info(f"UNPUBLISHED {id}: {e}")
                sensor.publishable = False
