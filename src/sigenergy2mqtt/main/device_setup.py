import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.cloud.registry import cloud_control_registry
from sigenergy2mqtt.common import Constants, ProtocolVersion
from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.config import active_config, auto_discovery
from sigenergy2mqtt.devices import (
    CloudControl,
    DeviceRegistry,
    Inverter,
    PowerPlant,
    bind_cross_device_sensors,
)
from sigenergy2mqtt.devices.cloud import (
    CloudDiscovery,
    discover_cloud,
    discover_dc_chargers,
    discover_operational_modes,
)
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.modbus.client import CONNECTIVITY
from sigenergy2mqtt.mqtt import mqtt_reconnection_interrupted
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.cloud.read_write import GatewayGridConnectionControl
from sigenergy2mqtt.sensors.inverter.read_only import RatedActivePower
from sigenergy2mqtt.sensors.plant.read_only import (
    GridStatus,
    SITotalChargedEnergy,
    SITotalDischargedEnergy,
    SITotalEVACChargedEnergy,
    SITotalEVDCChargedEnergy,
    SITotalEVDCDischargedEnergy,
)
from sigenergy2mqtt.sensors.plant.read_write import (
    ActivePowerFixedAdjustmentTargetValue,
    PhaseActivePowerFixedAdjustmentTargetValue,
    PhaseReactivePowerFixedAdjustmentTargetValue,
    ReactivePowerFixedAdjustmentTargetValue,
)

from .device_factories import (
    make_ac_charger,
    make_dc_charger,
    make_pid,
    make_plant_and_inverter,
    make_pss,
)
from .modbus_helpers import get_state
from .restart import restart_controller
from .thread_config import ThreadConfig, thread_config_registry
from .validation import validate_publishable_sensors

logger = logging.getLogger(__name__)

# Backoff between attempts to reach a Modbus host at startup
STARTUP_CONNECT_INITIAL_DELAY = 5.0
STARTUP_CONNECT_MAX_DELAY = 60.0


async def _wait_for_modbus(modbus: ModbusClient, host: str, port: int) -> None:
    """Wait until *modbus* is connected, retrying with backoff.

    Devices can only be created by probing the inverter's registers, so startup
    cannot continue without Modbus. Rather than exiting (which would kill the
    process after an automatic restart, or crash-loop a container) the attempt
    is retried until the host is reachable. The wait is reported as a single
    outage of the host, and ends as soon as a connection is made. A shutdown
    signal interrupts the wait (raising ``KeyboardInterrupt``, as the MQTT
    startup wait does), because the runtime signal handlers are not yet
    installed while devices are being created.
    """
    outage = outage_tracker(f"modbus://{host}:{port}")
    delay = STARTUP_CONNECT_INITIAL_DELAY
    while not modbus.connected:
        outage.failure(
            "unable to connect; retrying until it is available (check the configured host and port if this persists)",
            kind=CONNECTIVITY,
            detail=f"Failed to connect to modbus://{host}:{port}; retrying in {delay:.0f}s",
        )
        for _ in range(int(delay)):
            if mqtt_reconnection_interrupted() or auto_discovery._interrupted:
                logger.info(f"Waiting for modbus://{host}:{port} interrupted by signal")
                raise KeyboardInterrupt("Modbus startup wait interrupted by signal")
            await asyncio.sleep(1)
        delay = min(delay * 2, STARTUP_CONNECT_MAX_DELAY)
        await modbus.connect()
    outage.success()

_GRID_RESTORE_WATCH_TASKS: dict[tuple[str, int, int], asyncio.Task] = {}


def _cloud_control_plant_index(device_list: list[dict[str, Any]]) -> int | None:
    """Find the local plant containing an inverter reported by the cloud."""
    cloud_logger = logging.getLogger("sigenergy2mqtt.cloud")
    cloud_serial_numbers = {
        str(device.get("serialNumber") or device.get("serial_number") or device.get("sn"))
        for device in device_list
        if device.get("deviceType") in ("Aio", "Inverter") and (device.get("serialNumber") or device.get("serial_number") or device.get("sn"))
    }
    plants_with_unreadable_serials: set[int] = set()
    for device in DeviceRegistry.all():
        if not isinstance(device, Inverter):
            continue
        serial_number = device.get("sn") or device.get("serial_number")
        if serial_number is None:
            plants_with_unreadable_serials.add(device.plant_index)
            continue
        if str(serial_number) in cloud_serial_numbers:
            cloud_logger.info(f"Cloud inverter serial number {serial_number} matched local inverter at plant index {device.plant_index}; Cloud API enabled")
            return device.plant_index

    if plants_with_unreadable_serials:
        cloud_logger.warning(f"Local inverter serial numbers are unavailable for plant indexes {sorted(plants_with_unreadable_serials)}; Cloud API cannot be matched safely and will be disabled")
        return None

    cloud_logger.warning("No cloud inverter matched a local inverter; Cloud API disabled")
    return None


def _plant_grid_status(plant_index: int) -> Sensor | None:
    """Return the plant's published Modbus GridStatus sensor, if it has one."""
    for device in DeviceRegistry.all():
        if device.plant_index == plant_index and (sensor := device.get_sensor(GridStatus, search_children=True)) is not None and sensor.publishable:
            return sensor
    return None


async def _setup_cloud_control() -> None:
    """Discover, match, and configure the optional cloud control device.

    A single cloud connection is established for the full discovery sequence
    (device list, gateway info, operational modes) and closed once at the end.
    The transport_factory used by the polling thread will re-authenticate in
    its own event loop, creating a fresh HTTP session bound to that loop.
    """
    cloud_control_registry.configure(active_config.cloud)
    if (cloud_port := cloud_control_registry.active) is None:
        return

    discovery: CloudDiscovery | None = None
    plant_index: int | None = None
    close_failed = False
    try:
        if (discovery := await discover_cloud(cloud_port)) is not None:
            plant_index = _cloud_control_plant_index(discovery.device_list)
            if plant_index is not None:
                discovery = await discover_operational_modes(cloud_port, discovery)
                discovery = await discover_dc_chargers(cloud_port, discovery)
    finally:
        try:
            await cloud_port.close()
        except Exception:
            close_failed = True
            logger.exception("Failed to close cloud adapter after discovery; Cloud API will be disabled for this run")

    if discovery is None or plant_index is None or close_failed:
        return

    cloud_config = ThreadConfig.create(host=None, port=None, name="Cloud")
    cloud_config.transport_factory = cloud_control_registry.transport_factory
    cloud_control = CloudControl(plant_index, cloud_port, discovery)
    grid_connection_control = cloud_control.get_sensor(GatewayGridConnectionControl, search_children=True)
    if isinstance(grid_connection_control, GatewayGridConnectionControl):
        grid_connection_control.set_plant_grid_status(_plant_grid_status(plant_index))
    cloud_config.add_device(cloud_control)


async def setup_devices(seen_serial_numbers: set[str]) -> tuple[list[ThreadConfig], ProtocolVersion | None]:
    """Iterate over all configured Modbus hosts, probe registers, and populate ThreadConfigs."""
    protocol_version: ProtocolVersion | None = None
    devices = active_config.modbus
    total_ac_chargers = sum(len(d.ac_chargers) if d.ac_chargers else 0 for d in devices)  # type: ignore[reportGeneralTypeIssues]
    total_dc_chargers = sum(len(d.dc_chargers) if d.dc_chargers else 0 for d in devices)  # type: ignore[reportGeneralTypeIssues]
    ac_charger_sequence = 0
    dc_charger_sequence = 0
    pid_sequence = 0
    pss_sequence = 0

    if devices and devices[0].registers.read_only is True and devices[0].registers.read_write is False and devices[0].registers.write_only is False:
        # registers is a single entity that is propagated to all devices (sigenergy2mqtt.config.merge.propagate_to_all_devices), so we only need to check the first device
        logger.warning("Read-only mode enabled: No write operations can be performed.")

    for plant_index, device in enumerate(devices):
        if not (device.registers.read_only or device.registers.read_write or device.registers.write_only):
            logger.info(f"Ignored modbus://{device.host}:{device.port} (Plant Index = {plant_index}): All registers are disabled (read-only=false read-write=false write-only=false)")
            continue
        if device.pss or device.pid:
            logger.info(
                f"Creating devices from modbus://{device.host}:{device.port} (Plant: {plant_index}, Device IDs: Inverter={device.inverters} AC Charger={device.ac_chargers} DC Charger={device.dc_chargers} PSS={device.pss} PID={device.pid})"
            )
        else:
            logger.info(
                f"Creating devices from modbus://{device.host}:{device.port} (Plant: {plant_index}, Device IDs: Inverter={device.inverters} AC Charger={device.ac_chargers} DC Charger={device.dc_chargers})"
            )

        config: ThreadConfig = ThreadConfig.create(device.host, device.port, device.timeout, device.retries)
        modbus = ModbusClient(device.host, port=device.port, timeout=device.timeout, retries=device.retries)

        async with modbus:
            if not modbus.connected:
                await _wait_for_modbus(modbus, device.host, device.port)

            logger.debug(f"Connected to modbus://{device.host}:{device.port} for register probing")

            plant: PowerPlant | None = None
            inverters: dict[int, str] = {}
            inverter_devices: list[Inverter] = []
            inverter_firmware_versions: dict[int, str] = {}

            for device_address in device.inverters:  # type: ignore[reportGeneralTypeIssues]
                inverter, plant_tmp = await make_plant_and_inverter(plant_index, modbus, device_address, plant, seen_serial_numbers)

                if plant is None and plant_tmp is not None:
                    plant = plant_tmp

                    config.add_device(plant)

                    if plant.protocol_version is not None:
                        protocol_version = plant.protocol_version if protocol_version is None or protocol_version < plant.protocol_version else protocol_version

                    if not plant.has_battery:
                        logger.debug(f"No battery modules attached to plant {device.host}:{device.port} - disabling charging/discharging statistics interface sensors")
                        for register in (SITotalChargedEnergy.ADDRESS, SITotalDischargedEnergy.ADDRESS):
                            si_sensor = plant.get_sensor(
                                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{Constants.PLANT_DEVICE_ADDRESS}_{register}",
                                search_children=True,
                            )
                            if si_sensor:
                                si_sensor.publishable = False

                if inverter is not None:
                    inverters[device_address] = inverter.unique_id
                    inverter_devices.append(inverter)
                    inverter_firmware_versions[device_address] = str(inverter["sw"])
                    config.add_device(inverter)

            if plant is not None:
                await validate_publishable_sensors(modbus, plant, inverter_firmware_versions)
                for inverter in inverter_devices:
                    await validate_publishable_sensors(modbus, inverter, inverter_firmware_versions)

                dc_charger_sequence = await _setup_dc_chargers(
                    plant_index=plant_index,
                    device=device,
                    plant=plant,
                    modbus_client=modbus,
                    inverters=inverters,
                    config=config,
                    sequence_start=dc_charger_sequence,
                    total_count=total_dc_chargers,
                    inverter_firmware_versions=inverter_firmware_versions,
                )
                ac_charger_sequence = await _setup_ac_chargers(
                    plant_index=plant_index,
                    device=device,
                    plant=plant,
                    modbus_client=modbus,
                    config=config,
                    protocol_version=plant.protocol_version,
                    sequence_start=ac_charger_sequence,
                    total_count=total_ac_chargers,
                    inverter_firmware_versions=inverter_firmware_versions,
                )
                pid_sequence = await _setup_pid(
                    plant_index=plant_index,
                    device=device,
                    plant=plant,
                    seen_serial_numbers=seen_serial_numbers,
                    modbus_client=modbus,
                    config=config,
                    protocol_version=plant.protocol_version,
                    sequence_start=pid_sequence,
                    total_count=len(device.pid) if device.pid else 0,
                    inverter_firmware_versions=inverter_firmware_versions,
                )
                pss_sequence = await _setup_pss(
                    plant_index=plant_index,
                    device=device,
                    plant=plant,
                    seen_serial_numbers=seen_serial_numbers,
                    modbus_client=modbus,
                    config=config,
                    protocol_version=plant.protocol_version,
                    sequence_start=pss_sequence,
                    total_count=len(device.pss) if device.pss else 0,
                    inverter_firmware_versions=inverter_firmware_versions,
                )

                # Finalise cross-device sensor bindings now that all inverters and chargers are registered
                bind_cross_device_sensors(plant_index)

                # Set the min/max bounds for Active/Reactive Power Fixed Adjustment Target Value
                await _apply_power_adjustment_bounds(plant_index, plant, modbus, config)

            logger.debug(f"Disconnecting from modbus://{device.host}:{device.port} - register probing complete")

    await _setup_cloud_control()

    return thread_config_registry.get_all(), protocol_version


# Protocol register 40003: "Range: [-60.00 * base value, 60.00 * base value]", where the
# base value is the rated power and the multiplier is a percentage (maintainer decision 2026-11-16).
REACTIVE_POWER_ADJUSTMENT_RATIO: float = 0.6


async def _apply_power_adjustment_bounds(plant_index: int, plant: PowerPlant, modbus_client: ModbusClient, config: ThreadConfig) -> None:
    """Bound the fixed power adjustment targets by the plant's total rated active power.

    Active targets are limited to ±rated kW and reactive targets to ±60 % of
    rated power (in kvar). ``apply_min_max`` takes display units and applies the
    sensor gain itself, so the rated power is read as a display value (kW)
    rather than as the raw register value (W).

    The protocol gives no separate base value for the per-phase targets, so they
    get the plant total as well: no single phase can exceed it.

    The limits are only applied when the rated power of every inverter in the
    plant is known. A partial total would under-state the plant's capability and
    reject valid commands, so in that case the sensors keep their existing ranges.
    """
    total_rated_active_power: float = 0.0
    complete = True
    for i in config.devices:
        if isinstance(i, Inverter) and i.plant_index == plant_index:
            sensor = i.get_sensor(RatedActivePower, search_children=True)
            if sensor is None:
                logger.warning(f"{i.log_identity} RatedActivePower sensor not found - cannot set bounds for Active/Reactive Power Fixed Adjustment Target Value sensors")
                complete = False
            else:
                rap = await get_state(sensor, modbus_client, "inverter")
                if isinstance(rap, (int, float)) and not isinstance(rap, bool):
                    total_rated_active_power += float(rap)
                else:
                    logger.warning(f"{i.log_identity} Failed to acquire RatedActivePower")
                    complete = False
    if not complete:
        logger.warning(f"Plant {plant_index} total rated active power is incomplete - leaving the Active/Reactive Power Fixed Adjustment Target Value bounds unchanged")
        return
    if total_rated_active_power <= 0:
        return
    active_limit = round(total_rated_active_power, 3)
    reactive_limit = round(total_rated_active_power * REACTIVE_POWER_ADJUSTMENT_RATIO, 3)
    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ActivePowerFixedAdjustmentTargetValue, PhaseActivePowerFixedAdjustmentTargetValue))]:
        sensor.apply_min_max(-active_limit, active_limit)
    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ReactivePowerFixedAdjustmentTargetValue, PhaseReactivePowerFixedAdjustmentTargetValue))]:
        sensor.apply_min_max(-reactive_limit, reactive_limit)


async def _setup_ac_chargers(
    plant_index: int,
    device,
    plant: PowerPlant,
    modbus_client: ModbusClient,
    config: ThreadConfig,
    protocol_version: ProtocolVersion | None,
    sequence_start: int,
    total_count: int,
    inverter_firmware_versions: Mapping[int, str] | None = None,
) -> int:
    if not device.ac_chargers:
        logger.debug(f"No AC chargers defined for plant {device.host}:{device.port} - disabling AC charger statistics interface sensors")
        si_sensor = plant.get_sensor(
            f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_247_{SITotalEVACChargedEnergy.ADDRESS}",
            search_children=True,
        )
        if si_sensor:
            si_sensor.publishable = False
        return sequence_start

    if protocol_version is not None and protocol_version < ProtocolVersion.V2_0:
        logger.warning(f"AC Chargers are not supported on Sigenergy Modbus ProtocolVersion V{protocol_version.value} - skipping AC Charger device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.ac_chargers:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            charger = await make_ac_charger(
                plant_index=plant_index,
                device_address=device_address,
                modbus_client=modbus_client,
                plant=plant,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            config.add_device(charger)
            await validate_publishable_sensors(modbus_client, charger, inverter_firmware_versions)
        except (TimeoutError, ModbusException, ValueError, OSError, RuntimeError) as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logger.warning(f"AC charger at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logger.error(f"Failed to initialize AC charger at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _setup_dc_chargers(
    plant_index: int,
    device,
    plant: PowerPlant,
    modbus_client: ModbusClient,
    inverters: dict[int, str],
    config: ThreadConfig,
    sequence_start: int,
    total_count: int,
    inverter_firmware_versions: Mapping[int, str] | None = None,
) -> int:
    if not device.dc_chargers:
        logger.debug(f"No DC chargers defined for plant {device.host}:{device.port} - disabling DC charger statistics interface sensors")
        for register in (SITotalEVDCChargedEnergy.ADDRESS, SITotalEVDCDischargedEnergy.ADDRESS):
            si_sensor = plant.get_sensor(
                f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{Constants.PLANT_DEVICE_ADDRESS}_{register}",
                search_children=True,
            )
            if si_sensor:
                si_sensor.publishable = False
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.dc_chargers:  # type: ignore[reportGeneralTypeIssues]
        if device_address not in inverters:
            logger.warning(f"DC charger at address {device_address} has no associated inverter (inverter may have been skipped as a duplicate) - skipping DC charger")
            continue
        sequence_number += 1
        try:
            charger = await make_dc_charger(
                plant_index=plant_index,
                device_address=device_address,
                modbus_client=modbus_client,
                plant=plant,
                inverter_unique_id=inverters[device_address],
                sequence_number=sequence_number,
                total_count=total_count,
            )
            config.add_device(charger)
            await validate_publishable_sensors(modbus_client, charger, inverter_firmware_versions)
        except (TimeoutError, ModbusException, ValueError, OSError, RuntimeError) as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logger.warning(f"DC charger at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logger.error(f"Failed to initialize DC charger at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _setup_pid(
    plant_index: int,
    device,
    plant: PowerPlant,
    seen_serial_numbers: set[str],
    modbus_client: ModbusClient,
    config: ThreadConfig,
    protocol_version: ProtocolVersion | None,
    sequence_start: int,
    total_count: int,
    inverter_firmware_versions: Mapping[int, str] | None = None,
) -> int:
    if not device.pid:
        return sequence_start

    if protocol_version is not None and protocol_version < ProtocolVersion.V2_9:
        logger.warning(f"PID devices are not supported on Sigenergy Modbus ProtocolVersion V{protocol_version.value} - skipping PID device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.pid:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            pid = await make_pid(
                plant_index=plant_index,
                modbus_client=modbus_client,
                device_address=device_address,
                plant=plant,
                seen_serial_numbers=seen_serial_numbers,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            if pid is not None:
                config.add_device(pid)
                await validate_publishable_sensors(modbus_client, pid, inverter_firmware_versions)
        except (TimeoutError, ModbusException, ValueError, OSError, RuntimeError) as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logger.warning(f"PID device at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logger.error(f"Failed to initialize PID device at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _setup_pss(
    plant_index: int,
    device,
    plant: PowerPlant,
    seen_serial_numbers: set[str],
    modbus_client: ModbusClient,
    config: ThreadConfig,
    protocol_version: ProtocolVersion | None,
    sequence_start: int,
    total_count: int,
    inverter_firmware_versions: Mapping[int, str] | None = None,
) -> int:
    if not device.pss:
        return sequence_start

    if protocol_version is not None and protocol_version < ProtocolVersion.V2_9:
        logger.warning(f"PSS devices are not supported on Sigenergy Modbus ProtocolVersion V{protocol_version.value} - skipping PSS device creation for modbus://{device.host}:{device.port}")
        return sequence_start

    sequence_number = sequence_start
    skipped_due_to_outage = False
    for device_address in device.pss:  # type: ignore[reportGeneralTypeIssues]
        sequence_number += 1
        try:
            pss = await make_pss(
                plant_index=plant_index,
                device_address=device_address,
                modbus_client=modbus_client,
                plant=plant,
                seen_serial_numbers=seen_serial_numbers,
                sequence_number=sequence_number,
                total_count=total_count,
            )
            if pss is not None:
                config.add_device(pss)
                await validate_publishable_sensors(modbus_client, pss, inverter_firmware_versions)
        except (TimeoutError, ModbusException, ValueError, OSError, RuntimeError) as exc:
            is_outage = await _is_grid_outage(plant_index, modbus_client)
            if is_outage is True:
                logger.warning(f"PSS device at address {device_address} initialization failed during grid outage; skipping this startup pass so other devices continue: {exc}")
                skipped_due_to_outage = True
                continue

            logger.error(f"Failed to initialize PSS device at address {device_address}; skipping: {exc}")

    if skipped_due_to_outage:
        _schedule_restart_on_grid_restore(device, plant_index)

    return sequence_number


async def _is_grid_outage(plant_index: int, modbus_client: ModbusClient) -> bool | None:
    """Return True when grid is unavailable, False when on-grid, None when probe fails."""
    grid_status = GridStatus(plant_index)
    try:
        raw_status = await grid_status.get_state(raw=True, modbus_client=modbus_client)
    except (TimeoutError, ModbusException, OSError, ValueError, RuntimeError) as exc:
        # Called while handling another failure, so no error here may escape (ValueError
        # includes a reading rejected by the sanity check)
        logger.debug(f"Unable to probe GridStatus for outage detection: {exc}")
        return None

    if raw_status is None:
        return None

    try:
        return int(raw_status) != 0
    except (TypeError, ValueError):
        logger.debug(f"Unexpected GridStatus raw value for outage detection: {raw_status}")
        return None


async def _watch_grid_restore_and_request_restart(host: str, port: int, timeout: float, retries: int, plant_index: int) -> None:
    """Watch GridStatus and request runtime restart once grid returns on-line."""
    while True:
        try:
            modbus = ModbusClient(host, port=port, timeout=timeout, retries=retries)
            async with modbus:
                if modbus.connected:
                    is_outage = await _is_grid_outage(plant_index, modbus)
                    if is_outage is False:
                        restart_controller.request(f"grid restored for skipped device setup on modbus://{host}:{port} plant {plant_index}")
                        return
        except (ModbusException, OSError, RuntimeError) as exc:
            # The host is often unreachable during the outage being watched: keep watching
            logger.debug(f"Grid-restore watcher for modbus://{host}:{port} plant {plant_index} failed to probe: {exc!r}")
        await asyncio.sleep(10)


def _schedule_restart_on_grid_restore(device, plant_index: int) -> None:
    key = (device.host, device.port, plant_index)
    if key in _GRID_RESTORE_WATCH_TASKS:
        return
    logger.info(f"Scheduling grid-restore watcher for modbus://{device.host}:{device.port} plant {plant_index} because device setup was skipped during a grid outage")
    # The event loop only keeps a weak reference to a task, so hold one here
    task = asyncio.create_task(_watch_grid_restore_and_request_restart(device.host, device.port, device.timeout, device.retries, plant_index))
    _GRID_RESTORE_WATCH_TASKS[key] = task

    def finished(done: asyncio.Task) -> None:
        if _GRID_RESTORE_WATCH_TASKS.get(key) is done:
            del _GRID_RESTORE_WATCH_TASKS[key]
        if not done.cancelled() and (error := done.exception()) is not None:
            logger.error(f"Grid-restore watcher for modbus://{key[0]}:{key[1]} plant {plant_index} failed; the skipped devices will not be set up until the next restart", exc_info=error)

    task.add_done_callback(finished)


def cancel_grid_restore_watchers() -> None:
    """Cancel the grid-restore watchers of a previous runtime cycle.

    A watcher left running across a restart would request another, redundant,
    restart as soon as it saw the grid; the new cycle schedules its own if it
    still needs one.
    """
    for task in list(_GRID_RESTORE_WATCH_TASKS.values()):
        task.cancel()
    _GRID_RESTORE_WATCH_TASKS.clear()
