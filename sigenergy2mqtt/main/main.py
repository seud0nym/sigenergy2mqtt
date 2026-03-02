import logging
import os
import signal
import sys
from pathlib import Path
from typing import Tuple, cast

from pymodbus import pymodbus_apply_logging_config
from pymodbus.pdu import ModbusPDU

from sigenergy2mqtt.common import Constants, ConsumptionMethod, HybridInverter, InputType, Protocol, ProtocolApplies, PVInverter
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import ACCharger, DCCharger, Inverter, PowerPlant
from sigenergy2mqtt.influxdb import get_influxdb_services
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.monitor import MonitorService
from sigenergy2mqtt.pvoutput import get_pvoutput_services
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, Sensor
from sigenergy2mqtt.sensors.inverter_read_only import InverterMaxCellVoltage, InverterMinCellVoltage, InverterModel, InverterSerialNumber, OutputType
from sigenergy2mqtt.sensors.plant_read_only import (
    Alarm7,
    CurrentControlCommandValue,
    PlantBatterySoH,
    PlantRatedChargingPower,
    PlantRatedDischargingPower,
    SITotalChargedEnergy,
    SITotalDischargedEnergy,
    SITotalEVACChargedEnergy,
    SITotalEVDCChargedEnergy,
    SITotalEVDCDischargedEnergy,
    ThirdPartyPVPower,
    TotalLoadDailyConsumption,
    TotalLoadPower,
)
from sigenergy2mqtt.sensors.plant_read_write import ActivePowerRegulationGradient, GridCodeLVRT, IndependentPhasePowerControl

from .device_thread import start
from .thread_config import ThreadConfig, thread_config_registry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Configure the root logger with a format appropriate to the runtime environment.

    Three formats are used:

    - **TTY**: includes timestamp and ``sigenergy2mqtt:`` prefix — for interactive use.
    - **Docker**: includes timestamp but no prefix — for structured container log collectors.
    - **Other**: no timestamp — for init systems (systemd, etc.) that add their own.
    """
    if os.isatty(sys.stdout.fileno()):
        fmt = "{asctime} {levelname:<8} sigenergy2mqtt:{module:.<15.15}{lineno:04d} {message}"
    else:
        cgroup = Path("/proc/self/cgroup")
        in_docker = Path("/.dockerenv").is_file() or (cgroup.is_file() and "docker" in cgroup.read_text())
        fmt = "{asctime} {levelname:<8} {module:.<15.15}{lineno:04d} {message}" if in_docker else "{levelname:<8} {module:.<15.15}{lineno:04d} {message}"

    # basicConfig is a no-op if handlers already exist; force our format by
    # removing any pre-existing handlers first (e.g. added by pymodbus).
    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()
    logging.basicConfig(format=fmt, level=active_config.log_level, style="{")

    _configure_logger("pymodbus", active_config.get_modbus_log_level(), propagate=False)
    _configure_logger("paho.mqtt", active_config.mqtt.log_level)
    _configure_logger("pvoutput", active_config.pvoutput.log_level)


def _configure_logger(name: str, level: int, *, propagate: bool = True) -> None:
    logger = logging.getLogger(name)
    if logger.level != level:
        if logger.level not in (logging.NOTSET, level):
            logger.log(logger.level, f"{name} log-level changed to {logging.getLevelName(level)}")
        logger.setLevel(level)
    logger.propagate = propagate


# ---------------------------------------------------------------------------
# Modbus helpers
# ---------------------------------------------------------------------------


def get_modbus_url(modbus_client: ModbusClient) -> str:
    if modbus_client and hasattr(modbus_client, "comm_params"):
        return f"modbus://{modbus_client.comm_params.host}:{modbus_client.comm_params.port}"
    return "modbus://unknown"


async def get_state(
    sensor: Sensor,
    modbus_client: ModbusClient,
    device: str,
    default_value: int | float | str | None = None,
    raw: bool = False,
) -> int | float | str | None:
    try:
        state = await sensor.get_state(raw=raw, modbus_client=modbus_client)
        logging.debug(f"READING {get_modbus_url(modbus_client)} - Acquiring {sensor.__class__.__name__} {'raw ' if raw else ''}{state=} to initialise {device}")
    except Exception as e:
        state = default_value
        logging.debug(f"FAILURE {get_modbus_url(modbus_client)} - Acquiring {sensor.__class__.__name__} to initialise {device} -> {e} (returning {default_value=})")
    return state


async def read_registers(
    modbus_client: ModbusClient,
    register: int,
    count: int,
    device_id: int,
    input_type: InputType,
) -> ModbusPDU:
    if modbus_client is None:
        raise ValueError("modbus_client cannot be None")
    if input_type == InputType.HOLDING:
        return await modbus_client.read_holding_registers(register, count=count, device_id=device_id)
    if input_type == InputType.INPUT:
        return await modbus_client.read_input_registers(register, count=count, device_id=device_id)
    raise ValueError(f"Unknown input type '{input_type}'")


# ---------------------------------------------------------------------------
# Protocol probing
# ---------------------------------------------------------------------------


async def probe_protocol(modbus_client: ModbusClient) -> Protocol:
    """Interrogate the plant to determine the highest supported Modbus protocol version.

    Registers are probed in descending version order; the first successful read
    determines the protocol.  Falls back to V1.8 if none respond.
    """
    # Tuples of (register, count, protocol_version) — must be input registers
    # unique to each version, listed from newest to oldest.
    candidates = [
        (TotalLoadPower.ADDRESS, 2, Protocol.V2_8),
        (ThirdPartyPVPower.ADDRESS, 2, Protocol.V2_7),
        (TotalLoadDailyConsumption.ADDRESS, 2, Protocol.V2_6),
        (PlantBatterySoH.ADDRESS, 1, Protocol.V2_5),
    ]
    for register, count, version in candidates:
        logging.debug(f"READING {get_modbus_url(modbus_client)} to probe V{version.value} register {register} ({count=} device_id={Constants.PLANT_DEVICE_ADDRESS})")
        try:
            rr = await read_registers(modbus_client, register, count=count, device_id=Constants.PLANT_DEVICE_ADDRESS, input_type=InputType.INPUT)
            if rr.isError():
                logging.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> {rr.exception_code=}")
            else:
                logging.debug(f"SUCCESS {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> OK protocol=V{version.value}")
                return version
        except Exception as e:
            logging.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} {count=} device_id={Constants.PLANT_DEVICE_ADDRESS} -> {e}")

    logging.debug(f"DEFAULT {get_modbus_url(modbus_client)} to Sigenergy Modbus Protocol V1.8")
    return Protocol.V1_8


async def probe_optional_interface(
    modbus_client: ModbusClient,
    register: int,
    interface_name: str,
) -> bool:
    """Return True if the device responds successfully to a holding-register read."""
    try:
        rr = await read_registers(modbus_client, register, count=1, device_id=Constants.PLANT_DEVICE_ADDRESS, input_type=InputType.HOLDING)
        if rr.isError():
            logging.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> {rr.exception_code=} : NO {interface_name}")
            return False
        logging.debug(f"SUCCESS {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> HAS {interface_name}")
        return True
    except Exception as e:
        logging.debug(f"FAILURE {get_modbus_url(modbus_client)} {register=} count=1 device_id={Constants.PLANT_DEVICE_ADDRESS} -> {e} : NO {interface_name}")
        return False


# ---------------------------------------------------------------------------
# Device factories
# ---------------------------------------------------------------------------


async def make_ac_charger(
    plant_index: int,
    modbus_client: ModbusClient,
    device_address: int,
    plant: PowerPlant,
) -> ACCharger:
    charger = await ACCharger.create(plant_index, device_address, plant.protocol_version, modbus_client)
    charger.via_device = plant.unique_id
    return charger


async def make_dc_charger(
    plant_index: int,
    device_address: int,
    protocol_version: Protocol,
    inverter_unique_id: str,
) -> DCCharger:
    charger = await DCCharger.create(plant_index, device_address, protocol_version)
    charger.via_device = inverter_unique_id
    return charger


async def make_plant_and_inverter(
    plant_index: int,
    modbus_client: ModbusClient,
    device_address: int,
    plant: PowerPlant | None,
    seen_serial_numbers: set[str],
) -> Tuple[Inverter | None, PowerPlant | None]:
    """Create an Inverter and, on first call, a PowerPlant.

    ``seen_serial_numbers`` is updated in-place to guard against duplicate
    inverters across multiple Modbus hosts.
    """
    sn = await get_state(InverterSerialNumber(plant_index, device_address), modbus_client, "inverter")
    if sn in seen_serial_numbers:
        logging.info(f"Inverter {sn} has already been detected - ignoring")
        return None, None

    mdl = await get_state(InverterModel(plant_index, device_address), modbus_client, "inverter")
    if mdl is None:
        raise ValueError("Model ID cannot be None")

    rcp = await get_state(PlantRatedChargingPower(plant_index), modbus_client, "plant")
    rdp = await get_state(PlantRatedDischargingPower(plant_index), modbus_client, "plant")
    if rcp is None or rdp is None:
        logging.debug(f"Inverter {sn} does not support charging or discharging - assuming PVInverter")
        device_type = PVInverter()
        rcp = rdp = 0.0
    else:
        logging.debug(f"Inverter {sn} supports charging and discharging - assuming HybridInverter")
        device_type = HybridInverter()

    device_type.has_independent_phase_power_control_interface = await probe_optional_interface(modbus_client, IndependentPhasePowerControl.ADDRESS, "Independent Phase Control Interface")
    device_type.has_grid_code_interface = await probe_optional_interface(modbus_client, GridCodeLVRT.ADDRESS, "Grid Code Interface")

    if plant is None:
        protocol = await probe_protocol(modbus_client)
        logging.info(f"Interrogated {get_modbus_url(modbus_client)} and found Sigenergy Modbus Protocol V{protocol.value} ({ProtocolApplies(protocol)})")

        if protocol < Protocol.V2_8 and active_config.consumption != ConsumptionMethod.CALCULATED:
            logging.warning(f"Resetting consumption configuration to {ConsumptionMethod.CALCULATED.name} because {active_config.consumption.name} is not supported on Modbus Protocol V{protocol.value}")
            active_config.consumption = ConsumptionMethod.CALCULATED

        ot = await get_state(OutputType(plant_index, device_address), modbus_client, "plant/inverter", raw=True)
        if ot is None:
            raise ValueError("OutputType cannot be None — cannot create PowerPlant")
        plant = await PowerPlant.create(plant_index, device_type, protocol, int(ot), modbus_client)
    else:
        protocol = plant.protocol_version

    inverter = await Inverter.create(plant_index, device_address, device_type, protocol, modbus_client)
    inverter.via_device = plant.unique_id

    if sn is not None:
        seen_serial_numbers.add(str(sn))

    return inverter, plant


async def test_for_0x02_ILLEGAL_DATA_ADDRESS(
    modbus_client: ModbusClient,
    plant_index: int,
    device: PowerPlant | Inverter,
    *registers: int,
) -> None:
    device_id: int = device.device_address
    for register in registers:
        sensor: Sensor = cast(
            Sensor,
            device.get_sensor(
                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{device_id:03d}_{register}",
                search_children=True,
            ),
        )
        if not (sensor and sensor.publishable):
            continue
        id = f"{device.name} - {sensor.name} [{sensor['platform']}.{sensor['object_id']}]" if active_config.home_assistant.enabled else f"{device.name} - {sensor.name} [{sensor.state_topic}]"
        if isinstance(sensor, ModbusSensorMixin):
            try:
                rr = await read_registers(modbus_client, register, sensor.count, device_id, sensor.input_type)
                if rr and rr.isError() and rr.exception_code == 0x02:
                    logging.info(f"Unpublishing {id}: ILLEGAL DATA ADDRESS")
                    sensor.publishable = False
            except Exception as e:
                logging.info(f"Unpublishing {id}: {e}")
                sensor.publishable = False


# ---------------------------------------------------------------------------
# Top-level setup helpers
# ---------------------------------------------------------------------------


async def setup_devices(seen_serial_numbers: set[str]) -> tuple[list[ThreadConfig], Protocol | None]:
    """Iterate over all configured Modbus hosts, probe registers, and populate ThreadConfigs."""
    protocol_version: Protocol | None = None

    for plant_index in range(len(active_config.modbus)):
        device = active_config.modbus[plant_index]
        if not (device.registers.read_only or device.registers.read_write or device.registers.write_only):
            logging.info(f"Ignored Modbus host {device.host} (device index {plant_index}): all registers are disabled (read-only=false read-write=false write-only=false)")
            continue

        config: ThreadConfig = thread_config_registry.get_config(device.host, device.port, device.timeout, device.retries)
        modbus = ModbusClient(device.host, port=device.port, timeout=device.timeout, retries=device.retries)

        async with modbus:
            if not modbus.connected:
                logging.fatal(f"Failed to connect to modbus://{device.host}:{device.port}")
                sys.exit(1)

            logging.info(f"Connected to modbus://{device.host}:{device.port} for register probing")

            plant: PowerPlant | None = None
            inverters: dict[int, str] = {}

            for device_address in device.inverters:  # type: ignore[reportGeneralTypeIssues]
                inverter, plant_tmp = await make_plant_and_inverter(plant_index, modbus, device_address, plant, seen_serial_numbers)

                if plant is None and plant_tmp is not None:
                    plant = plant_tmp

                    config.add_device(plant)
                    await test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus, plant_index, plant, CurrentControlCommandValue.ADDRESS, Alarm7.ADDRESS, ActivePowerRegulationGradient.ADDRESS)

                    if plant.protocol_version is not None:
                        protocol_version = plant.protocol_version if protocol_version is None or protocol_version < plant.protocol_version else protocol_version

                    if not plant.has_battery:
                        logging.debug(f"No battery modules attached to plant {device.host}:{device.port} - disabling charging/discharging statistics interface sensors")
                        for register in (SITotalChargedEnergy.ADDRESS, SITotalDischargedEnergy.ADDRESS):
                            si_sensor = plant.get_sensor(
                                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{Constants.PLANT_DEVICE_ADDRESS}_{register}",
                                search_children=True,
                            )
                            if si_sensor:
                                si_sensor.publishable = False

                if inverter is not None:
                    inverters[device_address] = inverter.unique_id
                    config.add_device(inverter)
                    await test_for_0x02_ILLEGAL_DATA_ADDRESS(modbus, plant_index, inverter, InverterMaxCellVoltage.ADDRESS, InverterMinCellVoltage.ADDRESS)

            if plant is not None:
                await _setup_dc_chargers(plant_index, device, plant, inverters, config)
                await _setup_ac_chargers(plant_index, device, plant, modbus, config, protocol_version)

            logging.info(f"Disconnecting from modbus://{device.host}:{device.port} - register probing complete")

    return thread_config_registry.get_all(), protocol_version


async def _setup_dc_chargers(
    plant_index: int,
    device,
    plant: PowerPlant,
    inverters: dict[int, str],
    config: ThreadConfig,
) -> None:
    if not device.dc_chargers:
        logging.debug(f"No DC chargers defined for plant {device.host}:{device.port} - disabling DC charger statistics interface sensors")
        for register in (SITotalEVDCChargedEnergy.ADDRESS, SITotalEVDCDischargedEnergy.ADDRESS):
            si_sensor = plant.get_sensor(
                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{Constants.PLANT_DEVICE_ADDRESS}_{register}",
                search_children=True,
            )
            if si_sensor:
                si_sensor.publishable = False
        return

    for device_address in device.dc_chargers:  # type: ignore[reportGeneralTypeIssues]
        if device_address not in inverters:
            logging.warning(f"DC charger at address {device_address} has no associated inverter (inverter may have been skipped as a duplicate) - skipping DC charger")
            continue
        charger = await make_dc_charger(plant_index, device_address, plant.protocol_version, inverters[device_address])
        config.add_device(charger)


async def _setup_ac_chargers(
    plant_index: int,
    device,
    plant: PowerPlant,
    modbus_client: ModbusClient,
    config: ThreadConfig,
    protocol_version: Protocol | None,
) -> None:
    if not device.ac_chargers:
        logging.debug(f"No AC chargers defined for plant {device.host}:{device.port} - disabling AC charger statistics interface sensors")
        si_sensor = plant.get_sensor(
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_247_{SITotalEVACChargedEnergy.ADDRESS}",
            search_children=True,
        )
        if si_sensor:
            si_sensor.publishable = False
        return

    if protocol_version is not None and protocol_version < Protocol.V2_0:
        logging.warning(f"AC Chargers are not supported on Sigenergy Modbus Protocol V{protocol_version.value} - skipping AC Charger device creation for modbus://{device.host}:{device.port}")
        return

    for device_address in device.ac_chargers:  # type: ignore[reportGeneralTypeIssues]
        charger = await make_ac_charger(plant_index, modbus_client, device_address, plant)
        config.add_device(charger)


def setup_services(configs: list[ThreadConfig], protocol_version: Protocol | None) -> list[ThreadConfig]:
    """Build and return the full list of ThreadConfigs, prepending any service threads."""
    svc_thread_cfg = ThreadConfig(name="Services", host=None, port=None)

    if active_config.metrics_enabled:
        svc_thread_cfg.add_device(MetricsService(protocol_version if protocol_version is not None else Protocol.N_A))

    if active_config.pvoutput.enabled and not active_config.clean:
        for service in get_pvoutput_services(configs):
            svc_thread_cfg.add_device(service)

    if active_config.influxdb.enabled and not active_config.clean:
        for service in get_influxdb_services(configs):
            svc_thread_cfg.add_device(service)

    if svc_thread_cfg.has_devices:
        configs.insert(0, svc_thread_cfg)
    else:
        logging.info("No services configured - skipping service thread")

    if active_config.log_level == logging.DEBUG:
        mon_thread_cfg = ThreadConfig(name="Monitor", host=None, port=None)
        mon_thread_cfg.add_device(MonitorService([d for c in configs for d in c.devices]))
        configs.append(mon_thread_cfg)

    return configs


def setup_signals(configs: list[ThreadConfig]) -> None:
    """Register OS signal handlers for graceful shutdown, reload, and restart."""

    def configure_for_restart(caught, frame):
        logging.info(f"Signal {caught} received - reconfiguring for restart")
        # Suppress the HA offline availability message since we intend to restart.
        active_config.home_assistant.enabled = False
        exit_on_signal(caught, frame)

    def exit_on_signal(caught, frame):
        logging.info(f"Signal {caught} received - Shutdown commenced")
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        for config in configs:
            config.offline()

    def reload_on_signal(caught, frame):
        logging.info(f"Signal {caught} received - Reloading configuration")
        active_config.reload()
        configure_logging()
        for config in configs:
            config.reapply_sensor_overrides()

    signal.signal(signal.SIGINT, exit_on_signal)
    signal.signal(signal.SIGHUP, reload_on_signal)
    signal.signal(signal.SIGTERM, exit_on_signal)
    signal.signal(signal.SIGUSR1, configure_for_restart)


def check_upgrade() -> bool:
    """Return True if a version change is detected, writing the new version to disk."""
    if not active_config.home_assistant.enabled:
        return False

    current_version_file = Path(active_config.persistent_state_path, ".current-version")
    current_version: str | None = None

    if current_version_file.exists():
        try:
            with current_version_file.open("r") as f:
                current_version = f.read()
            logging.debug(f"Loaded '{current_version}' from {current_version_file}")
        except Exception as error:
            logging.error(f"Failed to read {current_version_file}: {error}")

    if current_version == active_config.version():
        return False

    if current_version:
        logging.info(f"Upgrade to '{active_config.version()}' from '{current_version}' detected")
    else:
        logging.info(f"Upgrade to '{active_config.version()}' detected")

    logging.debug(f"Writing '{active_config.version()}' to {current_version_file}")
    try:
        with current_version_file.open("w") as f:
            f.write(active_config.version())
    except Exception as error:
        logging.error(f"Failed to write to {current_version_file}: {error}")

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def async_main() -> None:
    # Configure logging before pymodbus so basicConfig wins the handler race.
    configure_logging()
    pymodbus_apply_logging_config(active_config.get_modbus_log_level())

    seen_serial_numbers: set[str] = set()
    configs, protocol_version = await setup_devices(seen_serial_numbers)
    configs = setup_services(configs, protocol_version)

    setup_signals(configs)
    check_upgrade()

    await start(configs)
    logging.info("Shutdown completed")
