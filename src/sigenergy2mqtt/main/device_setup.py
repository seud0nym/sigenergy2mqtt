import asyncio
import logging
import sys
from collections.abc import Mapping
from typing import cast

from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.common import Constants, ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Inverter, PowerPlant, bind_cross_device_sensors
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.sensors.inverter_read_only import RatedActivePower
from sigenergy2mqtt.sensors.plant_read_only import (
    GridStatus,
    SITotalChargedEnergy,
    SITotalDischargedEnergy,
    SITotalEVACChargedEnergy,
    SITotalEVDCChargedEnergy,
    SITotalEVDCDischargedEnergy,
)
from sigenergy2mqtt.sensors.plant_read_write import (
    ActivePowerFixedAdjustmentTargetValue,
    PhaseActivePowerFixedAdjustmentTargetValue,
    PhaseReactivePowerFixedAdjustmentTargetValue,
    ReactivePowerFixedAdjustmentTargetValue,
)

from .device_factories import make_ac_charger, make_dc_charger, make_pid, make_plant_and_inverter, make_pss
from .modbus_helpers import get_state
from .restart import restart_controller
from .thread_config import ThreadConfig, thread_config_registry
from .validation import validate_publishable_sensors

logger = logging.getLogger(__name__)

_GRID_RESTORE_WATCH_TASKS: set[tuple[str, int, int]] = set()


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
                logger.fatal(f"Failed to connect to modbus://{device.host}:{device.port}")
                sys.exit(1)

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
                    inverter_firmware_versions[device_address] = str(inverter["hw"])
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
                    protocol_version=protocol_version,
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
                    protocol_version=protocol_version,
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
                    protocol_version=protocol_version,
                    sequence_start=pss_sequence,
                    total_count=len(device.pss) if device.pss else 0,
                    inverter_firmware_versions=inverter_firmware_versions,
                )

                # Finalise cross-device sensor bindings now that all inverters and chargers are registered
                bind_cross_device_sensors(plant_index)

                # Set the min/max bounds for Active/Reactive Power Fixed Adjustment Target Value
                total_rated_active_power: int = 0
                for i in config.devices:
                    if isinstance(i, Inverter) and i.plant_index == plant_index:
                        sensor = i.get_sensor(RatedActivePower, search_children=True)
                        if sensor is None:
                            logger.warning(f"{i.log_identity} RatedActivePower sensor not found - cannot set bounds for Active/Reactive Power Fixed Adjustment Target Value sensors")
                        else:
                            rap = await get_state(sensor, modbus, "inverter", raw=True)
                            if rap is not None:
                                total_rated_active_power += cast(int, rap)
                            else:
                                logger.warning(f"{i.log_identity} Failed to acquire RatedActivePower")
                if total_rated_active_power > 0:
                    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ActivePowerFixedAdjustmentTargetValue, PhaseActivePowerFixedAdjustmentTargetValue))]:
                        sensor.apply_min_max(-total_rated_active_power, total_rated_active_power)
                    for sensor in [s for s in plant.sensors.values() if isinstance(s, (ReactivePowerFixedAdjustmentTargetValue, PhaseReactivePowerFixedAdjustmentTargetValue))]:
                        sensor.apply_min_max(-60 * total_rated_active_power, 60 * total_rated_active_power)

            logger.debug(f"Disconnecting from modbus://{device.host}:{device.port} - register probing complete")

    return thread_config_registry.get_all(), protocol_version


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
    for device_address in device.dc_chargers:  # type: ignore[reportGeneralTypeIssues]
        if device_address not in inverters:
            logger.warning(f"DC charger at address {device_address} has no associated inverter (inverter may have been skipped as a duplicate) - skipping DC charger")
            continue
        sequence_number += 1
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
    except (TimeoutError, ModbusException) as exc:
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
    finally:
        _GRID_RESTORE_WATCH_TASKS.discard(key)


def _schedule_restart_on_grid_restore(device, plant_index: int) -> None:
    key = (device.host, device.port, plant_index)
    if key in _GRID_RESTORE_WATCH_TASKS:
        return
    _GRID_RESTORE_WATCH_TASKS.add(key)
    logger.info(f"Scheduling grid-restore watcher for modbus://{device.host}:{device.port} plant {plant_index} due to outage-time AC charger skip")
    asyncio.create_task(_watch_grid_restore_and_request_restart(device.host, device.port, device.timeout, device.retries, plant_index))
