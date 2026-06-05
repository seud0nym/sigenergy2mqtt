import asyncio
import logging
import signal
import sys
from datetime import timedelta, timezone
from typing import Any, Tuple, cast

import paho.mqtt.client as paho_mqtt
import requests
from paho.mqtt.enums import CallbackAPIVersion
from pymodbus import pymodbus_apply_logging_config
from pymodbus.pdu import ModbusPDU

from sigenergy2mqtt.common import Constants, ConsumptionMethod, FirmwareVersion, HybridInverter, InputType, Protocol, ProtocolApplies, PVInverter
from sigenergy2mqtt.config import active_config, configure_root_logging, initialize_with_persistence
from sigenergy2mqtt.devices import PID, PSS, ACCharger, DCCharger, Device, Inverter, PowerPlant, bind_cross_device_sensors
from sigenergy2mqtt.influxdb import get_influxdb_services
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.monitor import MonitorService
from sigenergy2mqtt.persistence import state_store
from sigenergy2mqtt.pvoutput import get_pvoutput_services
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, ModbusSensorMixin, WriteOnlySensor
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, InverterModel, InverterSerialNumber, OutputType, PACKBCUCount, RatedActivePower
from sigenergy2mqtt.sensors.pid_read_only import PIDSerialNumber
from sigenergy2mqtt.sensors.plant_ess_preheating_read_write import ESSPreHeatingEnable
from sigenergy2mqtt.sensors.plant_read_only import (
    GridStatus,
    PlantBatterySoH,
    PlantPVTotalGenerationToday,
    SITotalChargedEnergy,
    SITotalDischargedEnergy,
    SITotalEVACChargedEnergy,
    SITotalEVDCChargedEnergy,
    SITotalEVDCDischargedEnergy,
    SystemTimeZone,
    ThirdPartyPVPower,
    TotalLoadDailyConsumption,
    TotalLoadPower,
)
from sigenergy2mqtt.sensors.plant_read_write import (
    ActivePowerFixedAdjustmentTargetValue,
    GridCodeLVRT,
    IndependentPhasePowerControl,
    PhaseActivePowerFixedAdjustmentTargetValue,
    PhaseReactivePowerFixedAdjustmentTargetValue,
    ReactivePowerFixedAdjustmentTargetValue,
)
from sigenergy2mqtt.sensors.pss_read_only import PSSSerialNumber

from .device_thread import start
from .restart import restart_controller
from .thread_config import ThreadConfig, thread_config_registry

_GRID_RESTORE_WATCH_TASKS: set[tuple[str, int, int]] = set()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Configure the root logger with a format appropriate to the runtime environment."""
    # Configure root logger format/level via shared helper so logic is unified
    # with configure_root_logging() performed at import time.
    configure_root_logging(active_config.log_level, active_config.log_fmt)

    _configure_logger("paho.mqtt", active_config.mqtt.log_level)
    _configure_logger("pvoutput", active_config.pvoutput.log_level)
    _configure_logger("pymodbus", active_config.get_modbus_log_level(), propagate=False)
    _configure_logger("sigenergy2mqtt.mqtt.client", active_config.mqtt.log_level)


def _configure_logger(name: str, level: int, *, propagate: bool = True) -> None:
    """Set an individual logger level/propagation and emit transition diagnostics.

    Side effects:

    - Mutates the named logger's effective level.
    - Optionally changes ``logger.propagate`` to control record bubbling.
    - Emits a log entry at the previous level when changing from a non-default level.
    """
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
    """Return a stable ``modbus://host:port`` identifier for logs.

    Falls back to ``modbus://unknown`` if the client does not expose connection
    parameters yet.
    """
    if modbus_client and hasattr(modbus_client, "comm_params"):
        return f"modbus://{modbus_client.comm_params.host}:{modbus_client.comm_params.port}"
    return "modbus://unknown"


async def get_state(sensor: Any, modbus_client: ModbusClient, device: str, default_value: int | float | str | None = None, raw: bool = False) -> int | float | str | None:
    """Read a sensor state for bootstrap/probing while tolerating read failures.

    Returns the sensor value when successful, otherwise ``default_value``.

    Side effects:

    - Performs a Modbus network read through ``sensor.get_state``.
    - Emits debug logs for successful reads and caught failures.
    """
    try:
        state = await sensor.get_state(raw=raw, modbus_client=modbus_client, skip_failure_logging=True)
        logging.debug(
            f"READING {get_modbus_url(modbus_client)} acquired {sensor.__class__.__name__} {'raw ' if raw else ''}{state=} to initialise {device} (idx={sensor.plant_index} id={sensor.device_address} addr={sensor.address})"
        )
    except Exception as e:
        state = default_value
        logging.debug(
            f"FAILURE {get_modbus_url(modbus_client)} acquiring {sensor.__class__.__name__} to initialise {device} (idx={sensor.plant_index} id={sensor.device_address} addr={sensor.address}) -> {e} (returning {default_value=})"
        )
    return state


async def read_registers(modbus_client: ModbusClient, register: int, count: int, device_id: int, input_type: InputType) -> ModbusPDU:
    """Read holding or input registers from a target device.

    ``input_type`` selects the Modbus function code. Raises ``ValueError`` if
    ``modbus_client`` is missing or the input type is unsupported.
    """
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
        (PlantPVTotalGenerationToday.ADDRESS, 2, Protocol.V2_9),
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


async def probe_optional_interface(modbus_client: ModbusClient, register: int, interface_name: str) -> bool:
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


async def make_ac_charger(plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant, sequence_number: int | None = None, total_count: int | None = None) -> ACCharger:
    """Create an AC charger device and link it to the parent plant.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    charger = await ACCharger.create(
        plant_index,
        device_address,
        plant.protocol_version,
        modbus_client,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    charger.via_device = plant.unique_id
    return charger


async def make_dc_charger(plant_index: int, device_address: int, protocol_version: Protocol, inverter_unique_id: str, sequence_number: int | None = None, total_count: int | None = None) -> DCCharger:
    """Create a DC charger device and associate it with its inverter.

    Side effects: performs async device initialisation and sets ``via_device``
    to the owning inverter unique ID.
    """
    charger = await DCCharger.create(
        plant_index,
        device_address,
        protocol_version,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    charger.via_device = inverter_unique_id
    return charger


async def make_pid(
    plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant, seen_serial_numbers: set[str], sequence_number: int | None = None, total_count: int | None = None
) -> PID | None:
    """Create a PID device and link it to the parent plant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    sn = await get_state(PIDSerialNumber(plant_index, device_address), modbus_client, "inverter")
    if sn in seen_serial_numbers:
        logging.info(f"PID {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None

    if sn is not None:
        seen_serial_numbers.add(str(sn))

    pid = await PID.create(
        plant_index,
        device_address,
        plant.protocol_version,
        modbus_client,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    pid.via_device = plant.unique_id
    return pid


async def make_plant_and_inverter(plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant | None, seen_serial_numbers: set[str]) -> Tuple[Inverter | None, PowerPlant | None]:
    """Create an Inverter and, on first call, a PowerPlant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.
    """
    sn = await get_state(InverterSerialNumber(plant_index, device_address), modbus_client, "inverter")
    if sn in seen_serial_numbers:
        logging.info(f"Inverter {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None, None

    mdl = await get_state(InverterModel(plant_index, device_address), modbus_client, "inverter")
    if mdl is None:
        raise ValueError(f"Inverter {sn} Model ID cannot be None (idx={plant_index} id={device_address})")

    batteries = cast(int, await get_state(PACKBCUCount(plant_index, device_address), modbus_client, "plant", default_value=0))
    if batteries == 0:
        device_type = PVInverter()
        logging.debug(f"Inverter {sn} has no batteries - assuming PVInverter (idx={plant_index} id={device_address})")
    else:
        device_type = HybridInverter()
        logging.debug(f"Inverter {sn} has {batteries} batter{'y' if batteries == 1 else 'ies'} - assuming HybridInverter (idx={plant_index} id={device_address})")

    device_type.has_independent_phase_power_control_interface = await probe_optional_interface(modbus_client, IndependentPhasePowerControl.ADDRESS, "Independent Phase Control Interface")
    device_type.has_grid_code_interface = await probe_optional_interface(modbus_client, GridCodeLVRT.ADDRESS, "Grid Code Interface")
    tz = timezone(timedelta(minutes=cast(int, await get_state(SystemTimeZone(plant_index), modbus_client, "plant", raw=True))))

    if plant is None:
        firmware = FirmwareVersion(cast(str, await get_state(InverterFirmwareVersion(plant_index, device_address), modbus_client, "plant/inverter")))
        protocol = await probe_protocol(modbus_client)
        if protocol == Protocol.V2_8 and firmware.service_pack >= 114:
            logging.debug(f"IGNORED {get_modbus_url(modbus_client)} detection of Protocol V{protocol.value} because Firmware {firmware} supports V2.9 features")
            protocol = Protocol.V2_9
        logging.info(f"Interrogated {get_modbus_url(modbus_client)} and found Sigenergy Modbus Protocol V{protocol.value} ({ProtocolApplies(protocol)})")

        if protocol < Protocol.V2_8 and active_config.consumption != ConsumptionMethod.CALCULATED:
            logging.warning(f"Resetting consumption configuration to {ConsumptionMethod.CALCULATED.name} because {active_config.consumption.name} is not supported on Modbus Protocol V{protocol.value}")
            active_config.consumption = ConsumptionMethod.CALCULATED

        ot = await get_state(OutputType(plant_index, device_address), modbus_client, "plant/inverter", raw=True)
        if ot is None:
            raise ValueError(f"Inverter {sn} OutputType cannot be None — cannot create PowerPlant (idx={plant_index} id={device_address})")

        pre_heating = await get_state(ESSPreHeatingEnable(plant_index), modbus_client, "plant/inverter")

        plant = await PowerPlant.create(plant_index, device_type, firmware, protocol, tz, cast(int, ot), pre_heating is not None, modbus_client)
    else:
        protocol = plant.protocol_version

    inverter = await Inverter.create(plant_index, device_address, device_type, protocol, tz, modbus_client)
    inverter.via_device = plant.unique_id

    if sn is not None:
        seen_serial_numbers.add(str(sn))

    return inverter, plant


async def make_pss(
    plant_index: int, modbus_client: ModbusClient, device_address: int, plant: PowerPlant, seen_serial_numbers: set[str], sequence_number: int | None = None, total_count: int | None = None
) -> PSS | None:
    """Create a PSS device and link it to the parent plant.

    ``seen_serial_numbers`` is updated in-place to guard
    against duplicate serial numbers.

    Side effects: performs async device initialisation reads and sets
    ``via_device`` to the plant unique ID for topology/discovery metadata.
    """
    sn = await get_state(PSSSerialNumber(plant_index, device_address), modbus_client, "inverter")
    if sn in seen_serial_numbers:
        logging.info(f"PSS {sn} has already been detected - ignoring (idx={plant_index} id={device_address})")
        return None

    if sn is not None:
        seen_serial_numbers.add(str(sn))

    pss = await PSS.create(
        plant_index,
        device_address,
        plant.protocol_version,
        modbus_client,
        sequence_number=sequence_number,
        total_count=total_count,
    )
    pss.via_device = plant.unique_id
    return pss


# ---------------------------------------------------------------------------
# Top-level setup helpers
# ---------------------------------------------------------------------------


async def setup_devices(seen_serial_numbers: set[str]) -> tuple[list[ThreadConfig], Protocol | None]:
    """Iterate over all configured Modbus hosts, probe registers, and populate ThreadConfigs."""
    protocol_version: Protocol | None = None
    devices = active_config.modbus
    total_ac_chargers = sum(len(d.ac_chargers) if d.ac_chargers else 0 for d in devices)  # type: ignore[reportGeneralTypeIssues]
    total_dc_chargers = sum(len(d.dc_chargers) if d.dc_chargers else 0 for d in devices)  # type: ignore[reportGeneralTypeIssues]
    ac_charger_sequence = 0
    dc_charger_sequence = 0
    pid_sequence = 0
    pss_sequence = 0

    for plant_index, device in enumerate(devices):
        if not (device.registers.read_only or device.registers.read_write or device.registers.write_only):
            logging.info(f"Ignored Modbus host {device.host} (device index {plant_index}): all registers are disabled (read-only=false read-write=false write-only=false)")
            continue

        config: ThreadConfig = ThreadConfig.create(device.host, device.port, device.timeout, device.retries)
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
                    await validate_publishable_sensors(modbus, plant)

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
                    await validate_publishable_sensors(modbus, inverter)

            if plant is not None:
                dc_charger_sequence = await _setup_dc_chargers(
                    plant_index,
                    device,
                    plant,
                    modbus,
                    inverters,
                    config,
                    dc_charger_sequence,
                    total_dc_chargers,
                )
                ac_charger_sequence = await _setup_ac_chargers(
                    plant_index,
                    device,
                    plant,
                    modbus,
                    config,
                    protocol_version,
                    ac_charger_sequence,
                    total_ac_chargers,
                )
                pid_sequence = await _setup_pid(
                    plant_index,
                    device,
                    plant,
                    seen_serial_numbers,
                    modbus,
                    config,
                    protocol_version,
                    pid_sequence,
                    len(device.pid) if device.pid else 0,
                )
                pss_sequence = await _setup_pss(
                    plant_index,
                    device,
                    plant,
                    seen_serial_numbers,
                    modbus,
                    config,
                    protocol_version,
                    pss_sequence,
                    len(device.pss) if device.pss else 0,
                )

                # Finalise cross-device sensor bindings now that all inverters and chargers are registered
                bind_cross_device_sensors(plant_index)

                # Set the min/max bounds for Active/Reactive Power Fixed Adjustment Target Value
                total_rated_active_power: int = 0
                for i in config.devices:
                    if isinstance(i, Inverter) and i.plant_index == plant_index:
                        sensor = i.get_sensor(RatedActivePower, search_children=True)
                        if sensor is None:
                            logging.warning(f"{i.log_identity} RatedActivePower sensor not found - cannot set bounds for Active/Reactive Power Fixed Adjustment Target Value sensors")
                        else:
                            rap = await get_state(sensor, modbus, "inverter", raw=True)
                            if rap is not None:
                                total_rated_active_power += cast(int, rap)
                            else:
                                logging.warning(f"{i.log_identity} Failed to acquire RatedActivePower")
                if total_rated_active_power > 0:
                    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ActivePowerFixedAdjustmentTargetValue, PhaseActivePowerFixedAdjustmentTargetValue))]:
                        sensor.apply_min_max(-total_rated_active_power, total_rated_active_power)
                    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ReactivePowerFixedAdjustmentTargetValue, PhaseReactivePowerFixedAdjustmentTargetValue))]:
                        sensor.apply_min_max(-60 * total_rated_active_power, 60 * total_rated_active_power)

            logging.info(f"Disconnecting from modbus://{device.host}:{device.port} - register probing complete")

    return thread_config_registry.get_all(), protocol_version


def setup_services(configs: list[ThreadConfig], protocol_version: Protocol | None) -> list[ThreadConfig]:
    """Attach optional service/monitor threads to the discovered device configs.

    Side effects:

    - Mutates ``configs`` in-place by inserting a ``Services`` thread at index 0
      and/or appending a debug ``Monitor`` thread.
    - Instantiates integration services that may later make outbound API/network
      calls (PVOutput/InfluxDB/Metrics) once started.
    """
    svc_thread_cfg = ThreadConfig.create(name="Services", host=None, port=None)

    if active_config.metrics_enabled:
        svc_thread_cfg.add_device(MetricsService(protocol_version if protocol_version is not None else Protocol.N_A))

    if active_config.pvoutput.enabled and not active_config.clean:
        for service in get_pvoutput_services(configs):
            svc_thread_cfg.add_device(service)

    if active_config.influxdb.enabled and not active_config.clean:
        for service in get_influxdb_services():
            svc_thread_cfg.add_device(service)

    if svc_thread_cfg.has_devices:
        configs.insert(0, svc_thread_cfg)
    else:
        logging.info("No services configured - skipping service thread")

    mon_thread_cfg = ThreadConfig.create(name="Monitor", host=None, port=None)
    mon_thread_cfg.add_device(MonitorService([d for c in configs for d in c.devices]))
    configs.append(mon_thread_cfg)

    return configs


def setup_signals(configs: list[ThreadConfig]) -> None:
    """Register process-level handlers for shutdown, reload, and restart signals.

    Side effects:

    - Installs handlers for ``SIGINT``, ``SIGTERM``, ``SIGHUP``, and ``SIGUSR1``.
    - On termination paths, marks all thread configs offline.
    - On restart path, suppresses Home Assistant availability-offline publication.
    """

    def configure_for_restart(caught, frame):
        """Handle SIGUSR1 by suppressing HA and initiating a graceful shutdown."""
        logging.info(f"Signal {caught} received - reconfiguring for restart")
        # Suppress the HA offline availability message since we intend to restart.
        active_config.home_assistant.enabled = False
        exit_on_signal(caught, frame)

    def exit_on_signal(caught, frame):
        """Handle termination signals by setting all active thread configs to offline."""
        logging.info(f"Signal {caught} received - Shutdown commenced")
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        for config in configs:
            config.offline()

    def reload_on_signal(caught=None, frame=None):
        """Handle SIGHUP by reloading config/logging and requesting restart."""
        logging.info("Signal SIGHUP received - Reloading configuration")
        try:
            active_config.reload()
        except Exception as e:
            logging.error(f"SIGHUP reload failed: {e}")

        restart_controller.request("signal SIGHUP")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    signal.signal(signal.SIGINT, exit_on_signal)
    signal.signal(signal.SIGTERM, exit_on_signal)
    signal.signal(signal.SIGUSR1, configure_for_restart)
    signal.signal(signal.SIGHUP, reload_on_signal)

    if loop:
        try:
            loop.add_signal_handler(signal.SIGHUP, reload_on_signal)
        except (NotImplementedError, AttributeError):
            pass


async def _setup_ac_chargers(plant_index: int, device, plant: PowerPlant, modbus_client: ModbusClient, config: ThreadConfig, protocol_version: Protocol | None, sequence_start: int, total_count: int) -> int:
    if not device.ac_chargers:
        logging.debug(f"No AC chargers defined for plant {device.host}:{device.port} - disabling AC charger statistics interface sensors")
        si_sensor = plant.get_sensor(
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_247_{SITotalEVACChargedEnergy.ADDRESS}",
            search_children=True,
        )
        if si_sensor:
            si_sensor.publishable = False
        return sequence_start

    if protocol_version is not None and protocol_version < Protocol.V2_0:
        logging.warning(f"AC Chargers are not supported on Sigenergy Modbus Protocol V{protocol_version.value} - skipping AC Charger device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.ac_chargers:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            charger = await make_ac_charger(
                plant_index,
                modbus_client,
                device_address,
                plant,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            config.add_device(charger)
            await validate_publishable_sensors(modbus_client, charger)
        except Exception as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logging.warning(f"AC charger at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logging.error(f"Failed to initialize AC charger at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _setup_dc_chargers(plant_index: int, device, plant: PowerPlant, modbus_client: ModbusClient, inverters: dict[int, str], config: ThreadConfig, sequence_start: int, total_count: int) -> int:
    if not device.dc_chargers:
        logging.debug(f"No DC chargers defined for plant {device.host}:{device.port} - disabling DC charger statistics interface sensors")
        for register in (SITotalEVDCChargedEnergy.ADDRESS, SITotalEVDCDischargedEnergy.ADDRESS):
            si_sensor = plant.get_sensor(
                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{Constants.PLANT_DEVICE_ADDRESS}_{register}",
                search_children=True,
            )
            if si_sensor:
                si_sensor.publishable = False
        return sequence_start

    sequence_number = sequence_start
    for device_address in device.dc_chargers:  # type: ignore[reportGeneralTypeIssues]
        if device_address not in inverters:
            logging.warning(f"DC charger at address {device_address} has no associated inverter (inverter may have been skipped as a duplicate) - skipping DC charger")
            continue
        sequence_number += 1
        charger = await make_dc_charger(
            plant_index,
            device_address,
            plant.protocol_version,
            inverters[device_address],
            sequence_number=sequence_number,
            total_count=total_count,
        )
        config.add_device(charger)
        await validate_publishable_sensors(modbus_client, charger)

    return sequence_number


async def _setup_pid(
    plant_index: int, device, plant: PowerPlant, seen_serial_numbers: set[str], modbus_client: ModbusClient, config: ThreadConfig, protocol_version: Protocol | None, sequence_start: int, total_count: int
) -> int:
    if not device.pid:
        return sequence_start

    if protocol_version is not None and protocol_version < Protocol.V2_9:
        logging.warning(f"PID devices are not supported on Sigenergy Modbus Protocol V{protocol_version.value} - skipping PID device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.pid:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            pid = await make_pid(
                plant_index,
                modbus_client,
                device_address,
                plant,
                seen_serial_numbers,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            if pid is not None:
                config.add_device(pid)
                await validate_publishable_sensors(modbus_client, pid)
        except Exception as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logging.warning(f"PID device at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logging.error(f"Failed to initialize PID device at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _setup_pss(
    plant_index: int, device, plant: PowerPlant, seen_serial_numbers: set[str], modbus_client: ModbusClient, config: ThreadConfig, protocol_version: Protocol | None, sequence_start: int, total_count: int
) -> int:
    if not device.pss:
        return sequence_start

    if protocol_version is not None and protocol_version < Protocol.V2_9:
        logging.warning(f"PSS devices are not supported on Sigenergy Modbus Protocol V{protocol_version.value} - skipping PSS device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.pss:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            pss = await make_pss(
                plant_index,
                modbus_client,
                device_address,
                plant,
                seen_serial_numbers,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            if pss is not None:
                config.add_device(pss)
                await validate_publishable_sensors(modbus_client, pss)
        except Exception as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logging.warning(f"PSS device at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logging.error(f"Failed to initialize PSS device at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _is_grid_outage(plant_index: int, modbus_client: ModbusClient) -> bool | None:
    """Return True when grid is unavailable, False when on-grid, None when probe fails."""
    grid_status = GridStatus(plant_index)
    try:
        raw_status = await grid_status.get_state(raw=True, modbus_client=modbus_client)
    except Exception as exc:
        logging.debug(f"Unable to probe GridStatus for outage detection: {exc}")
        return None

    if raw_status is None:
        return None

    try:
        return int(raw_status) != 0
    except (TypeError, ValueError):
        logging.debug(f"Unexpected GridStatus raw value for outage detection: {raw_status}")
        return None


async def _watch_grid_restore_and_request_restart(host: str, port: int, timeout: float, retries: int, plant_index: int) -> None:
    """Watch GridStatus and request runtime restart once grid returns on-line."""
    key = (host, port, plant_index)
    try:
        while True:
            modbus = ModbusClient(host, port=port, timeout=timeout, retries=retries)
            async with modbus:
                if modbus.connected:
                    is_outage = await _is_grid_outage(plant_index, modbus)
                    if is_outage is False:
                        restart_controller.request(f"grid restored for AC charger setup on modbus://{host}:{port} plant {plant_index}")
                        return
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        raise
    finally:
        _GRID_RESTORE_WATCH_TASKS.discard(key)


def _schedule_restart_on_grid_restore(device, plant_index: int) -> None:
    key = (device.host, device.port, plant_index)
    if key in _GRID_RESTORE_WATCH_TASKS:
        return
    _GRID_RESTORE_WATCH_TASKS.add(key)
    logging.info(f"Scheduling grid-restore watcher for modbus://{device.host}:{device.port} plant {plant_index} due to outage-time AC charger skip")
    asyncio.create_task(_watch_grid_restore_and_request_restart(device.host, device.port, device.timeout, device.retries, plant_index))


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


async def _validate_modbus_connections() -> None:
    """Verify that each configured Modbus endpoint accepts a TCP connection.

    Opens a short-lived client for every configured host/port, attempts to
    connect, validates the connected state, logs success, and then closes the
    socket. No register reads or writes are performed.
    """
    for index, modbus in enumerate(active_config.modbus):
        client = ModbusClient(modbus.host, port=modbus.port, timeout=modbus.timeout, retries=modbus.retries)
        try:
            await client.connect()
            if not client.connected:
                raise ConnectionError(f"Unable to connect to modbus://{modbus.host}:{modbus.port}")
            logging.info(f"Validated Modbus connection to modbus://{modbus.host}:{modbus.port} (device #{index})")
        finally:
            client.close()


def _validate_mqtt_connection(show_credentials: bool) -> None:
    """Validate MQTT broker reachability and authentication only.

    Establishes a temporary MQTT session using the configured transport/TLS and
    optional credentials, waits for a successful CONNACK, then disconnects.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    client_id = f"{active_config.mqtt.client_id_prefix}_validate"
    client = paho_mqtt.Client(CallbackAPIVersion.VERSION2, client_id=client_id, protocol=paho_mqtt.MQTTv311, transport=active_config.mqtt.transport)

    if active_config.mqtt.tls:
        import ssl

        ssl_context = ssl.create_default_context()
        if active_config.mqtt.tls_insecure:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(ssl_context)

    url = f"mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}"
    try:
        if active_config.mqtt.anonymous:
            logging.info(f"Validating MQTT connection to {url} anonymously")
        else:
            if show_credentials:
                logging.info(f"Validating MQTT connection to {url} with username={active_config.mqtt.username!r} password={active_config.mqtt.password!r}")
            else:
                logging.info(f"Validating MQTT connection to {url} with username={active_config.mqtt.username!r} password='[REDACTED]'")
            client.username_pw_set(active_config.mqtt.username, active_config.mqtt.password)

        client.connect(active_config.mqtt.broker, port=active_config.mqtt.port, keepalive=active_config.mqtt.keepalive)

        connected = False
        for _ in range(10):
            rc = client.loop(timeout=1.0)
            if client.is_connected():
                connected = True
                break
            if rc not in (paho_mqtt.MQTT_ERR_SUCCESS, paho_mqtt.MQTT_ERR_NO_CONN):
                raise ConnectionError(f"MQTT broker connection failed with rc={rc}")

        if not connected:
            raise TimeoutError("Timed out waiting for MQTT CONNACK")

        logging.info(f"Validated MQTT connection/authentication to {url}")
    finally:
        try:
            client.disconnect()
            client.loop(timeout=0.1)
        except Exception:
            pass


def _validate_influxdb_connection(show_credentials: bool) -> None:
    """Validate InfluxDB connectivity/authentication via read-only HTTP calls.

    For v2 config (token+org), performs a GET against the buckets endpoint.
    For v1 config (username+password), performs a read-only query endpoint
    request. No write endpoint is called.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    if not active_config.influxdb.enabled:
        return

    base = f"http://{active_config.influxdb.host}:{active_config.influxdb.port}"
    timeout = max(active_config.influxdb.write_timeout, 5.0)

    if active_config.influxdb.token and active_config.influxdb.org:
        headers = {"Authorization": f"Token {active_config.influxdb.token}"}
        if show_credentials:
            logging.info(f"Validating InfluxDB v2 credentials for {base}: token={active_config.influxdb.token!r} org={active_config.influxdb.org!r}")
        else:
            logging.info(f"Validating InfluxDB v2 credentials for {base}: token='[REDACTED]' org={active_config.influxdb.org!r}")
        response = requests.get(f"{base}/api/v2/buckets", params={"org": active_config.influxdb.org, "limit": 1}, headers=headers, timeout=timeout)
    else:
        auth = (active_config.influxdb.username, active_config.influxdb.password)
        if show_credentials:
            logging.info(f"Validating InfluxDB v1 credentials for {base}: username={active_config.influxdb.username!r} password={active_config.influxdb.password!r}")
        else:
            logging.info(f"Validating InfluxDB v1 credentials for {base}: username={active_config.influxdb.username!r} password='[REDACTED]'")
        response = requests.get(f"{base}/query", params={"q": "SHOW DATABASES"}, auth=auth, timeout=timeout)

    response.raise_for_status()
    logging.info(f"Validated InfluxDB connection/authentication to {base}")


def _validate_pvoutput_connection(show_credentials: bool) -> None:
    """Validate PVOutput endpoint reachability and API authentication.

    Calls PVOutput's system-info API with configured API key/system ID and
    requires a successful HTTP response. No upload API endpoint is used.

    When ``pvoutput.testing`` is enabled, this probe is skipped to match
    runtime behaviour, which intentionally avoids outbound PVOutput requests
    in testing mode.

    Args:
        show_credentials: When ``True``, include raw configured credentials in
            log output for troubleshooting.
    """
    if not active_config.pvoutput.enabled:
        return

    if active_config.pvoutput.testing:
        logging.info("Skipping PVOutput connection/authentication probe because pvoutput.testing is enabled")
        return

    headers = {
        "X-Pvoutput-Apikey": active_config.pvoutput.api_key,
        "X-Pvoutput-SystemId": active_config.pvoutput.system_id,
        "X-Rate-Limit": "1",
    }
    if show_credentials:
        logging.info(f"Validating PVOutput credentials with api_key={active_config.pvoutput.api_key!r} system_id={active_config.pvoutput.system_id!r}")
    else:
        logging.info(f"Validating PVOutput credentials with api_key='[REDACTED]' system_id={active_config.pvoutput.system_id!r}")

    response = requests.get("https://pvoutput.org/service/r2/getsystem.jsp?donations=1", headers=headers, timeout=10)
    response.raise_for_status()
    logging.info("Validated PVOutput connection/authentication")


async def validate_connections(show_credentials: bool = False) -> None:
    """Run all configured connection/authentication checks for ``--validate``.

    Executes Modbus, MQTT, InfluxDB, and PVOutput validation checks in
    sequence. Intended for one-shot startup validation mode, not steady-state
    runtime.

    Args:
        show_credentials: When ``True``, validation logs include raw
            credentials where applicable.
    """
    await _validate_modbus_connections()
    _validate_mqtt_connection(show_credentials)
    _validate_influxdb_connection(show_credentials)
    _validate_pvoutput_connection(show_credentials)


async def validate_publishable_sensors(modbus_client: ModbusClient, device: Device) -> None:
    """Validate all publishable sensors for illegal data addresses.

    Scans all publishable ModbusSensorMixin sensors that are not not WriteOnlySensors that
    have not been previously probed (state_count == 0) and marks those returning Modbus
    0x02 ILLEGAL_DATA_ADDRESS as unpublishable before scan groups are created.

    This comprehensive approach detects all illegal addresses on the device, eliminating
    the risk of data corruption from multi-register reads spanning unknown illegal addresses.

    Args:
        modbus_client: Modbus client for reads
        device: Device to validate (and children recursively)
    """
    ###### CHECK ALARM SENSORS !!!!! ######
    sensors_to_test = [s for s in device.get_all_sensors(search_children=True).values() if isinstance(s, ModbusSensorMixin) and not isinstance(s, WriteOnlySensor) and s.publishable and s.state_count == 0]

    if not sensors_to_test:
        return

    logging.debug(f"{device.log_identity} Validating {len(sensors_to_test)} sensor{'s' if len(sensors_to_test) != 1 else ''} addresses")

    # Test each sensor for illegal address exceptions
    for sensor in sensors_to_test:
        for s in sensor.alarms if isinstance(sensor, AlarmCombinedSensor) else [sensor]:
            try:
                rr = await read_registers(modbus_client, s.address, s.count, s.device_address, s.input_type)
                if rr and rr.isError() and rr.exception_code == 0x02:
                    logging.info(f"{s.log_identity} not supported on this device/firmware: ILLEGAL DATA ADDRESS {s.address} (count={s.count} type={s.input_type} protocol=V{s.protocol_version.value})")
                    s.publishable = False
            except Exception as e:
                # Log but don't suppress sensor on transient errors (only explicit 0x02)
                if "0x02 ILLEGAL DATA ADDRESS" in str(e):
                    logging.debug(f"{s.log_identity}: Validation detected illegal address: {e}")
                else:
                    logging.debug(f"{s.log_identity}: Validation read failed: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def async_main() -> None:
    """Run the main lifecycle loop, supporting clean shutdown and controlled restart.

    Side effects:

    - Reconfigures global logging (including pymodbus integration).
    - Rebuilds thread registry/config state and registers signal handlers.
    - Probes Modbus devices/services (network I/O) and starts worker threads.
    - Reloads runtime configuration after restart requests.
    """
    while True:
        # Configure logging before pymodbus so basicConfig wins the handler race.
        configure_logging()
        pymodbus_apply_logging_config(active_config.get_modbus_log_level())

        restart_controller.reset()
        thread_config_registry.clear()

        # Initialise StateStore with dedicated MQTT connection + sentinel-based warming
        if active_config.persistence.mqtt_redundancy or not active_config.clean:
            await state_store.initialise(
                active_config.persistent_state_path,
                active_config.persistence,
            )

        # Phase 2 config load — StateStore now available for auto-discovery fallback
        await initialize_with_persistence()

        seen_serial_numbers: set[str] = set()
        configs, protocol_version = await setup_devices(seen_serial_numbers)
        configs = setup_services(configs, protocol_version)

        setup_signals(configs)

        await start(configs)

        # Shutdown StateStore
        state_store.shutdown()

        if not restart_controller.requested:
            logging.info(f"Shutdown of Release {active_config.version} completed")
            return
        else:
            await active_config.reload_async()

        logging.info("Restarting runtime")
