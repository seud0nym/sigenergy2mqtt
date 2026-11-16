import logging

from sigenergy2mqtt.common import service_health_registry
from sigenergy2mqtt.common.outage import clear_outage_trackers
from sigenergy2mqtt.config import (
    ConfigurationError,
    active_config,
    auto_discovery,
    initialize_async,
)
from sigenergy2mqtt.devices import DeviceRegistry as device_registry
from sigenergy2mqtt.devices.base.child_devices import child_device_migration
from sigenergy2mqtt.diagnostics import diagnostics_registry
from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory
from sigenergy2mqtt.monitor import MonitorService
from sigenergy2mqtt.mqtt import mqtt_health_registry, mqtt_reconnection_interrupted
from sigenergy2mqtt.persistence import Category, state_store

from .device_setup import cancel_grid_restore_watchers, setup_devices
from .device_thread import start
from .logging_setup import configure_logging
from .restart import restart_controller
from .service_setup import setup_init_signals, setup_services, setup_signals
from .thread_config import thread_config_registry

logger = logging.getLogger(__name__)

_INSTALLATION_COHORT_KEY = "installation-cohort"
_INSTALLATION_COHORTS = {"legacy", "fresh"}


async def _ensure_installation_cohort() -> str | None:
    """Persist whether the existing state store predates child-device discovery."""
    cohort = await state_store.load(Category.CONFIG, _INSTALLATION_COHORT_KEY)
    if cohort in _INSTALLATION_COHORTS:
        return cohort

    has_prior_state = state_store.has_persisted_entries()
    if has_prior_state is None:
        logger.warning("Installation cohort could not be determined because persisted state is unavailable; leaving the marker unset")
        return None

    cohort = "legacy" if has_prior_state else "fresh"
    await state_store.save(Category.CONFIG, _INSTALLATION_COHORT_KEY, cohort)
    logger.info(f"Recorded installation cohort: {cohort}")
    return cohort


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _shutdown_signalled() -> bool:
    """Whether a termination signal has been received during this runtime cycle."""
    return mqtt_reconnection_interrupted() or auto_discovery._interrupted


async def async_main() -> int:
    """Run the main lifecycle loop, supporting clean shutdown and controlled restart.

    Side effects:

    - Reconfigures global logging (including pymodbus integration).
    - Rebuilds thread registry/config state and registers signal handlers.
    - Probes Modbus devices/services (network I/O) and starts worker threads.
    - Reloads runtime configuration after restart requests.

    Returns:
        The process exit status: ``0`` after an orderly shutdown, ``1`` if a
        worker thread crashed or the configuration could not be reloaded for a
        restart. A service manager can then tell a failure from a requested stop.
    """
    while True:
        configure_logging()

        # A termination signal can arrive at any point of the initialisation below, before
        # there are thread configs for setup_signals() to take offline. These handlers record
        # it, and it is checked between the phases. The flags are never reset: once a
        # termination signal has been received, the process exits rather than restarts.
        setup_init_signals()

        restart_controller.reset()
        cancel_grid_restore_watchers()
        thread_config_registry.clear()
        device_registry.clear()
        mqtt_health_registry.clear()
        # Outages are tracked per runtime: a restart changes the MQTT client IDs (and a reload
        # may change hosts), so members or resources of a previous runtime could otherwise keep
        # an outage open forever, suppressing its logging and deferring every later restart.
        clear_outage_trackers()
        ModbusLockFactory.clear()
        service_health_registry.clear()
        diagnostics_registry.clear()

        # Phase 2 config load — must run before StateStore so that the correct
        # MQTT broker address (and other settings) from the YAML config file are
        # available when StateStore opens its dedicated MQTT connection.
        # Note: _restore_discovery_from_mqtt inside initialize_async() already
        # guards against StateStore not yet being initialised, so ordering here
        # is safe.
        await initialize_async()

        # Reconfigure logging with the authoritative resolved settings (CLI/YAML/env).
        # The configure_logging() call at the top of the loop uses the import-time
        # Settings() which pre-dates CLI→env promotion, so levels may be incorrect
        # (e.g. --log-level=DEBUG not yet applied). This second call corrects that.
        configure_logging()

        if _shutdown_signalled():
            logger.info("Shutdown signal received during initialisation - exiting")
            return 0

        # Initialise StateStore with dedicated MQTT connection + sentinel-based warming
        await state_store.initialise(
            active_config.persistent_state_path,
            active_config.persistence,
        )
        crashed = False
        try:
            installation_cohort = await _ensure_installation_cohort()

            seen_serial_numbers: set[str] = set()
            configs, protocol_version = await setup_devices(seen_serial_numbers)
            configs = setup_services(configs, protocol_version)

            # Must run before any discovery is published: a failed preflight falls back to
            # the legacy via_device payloads without having changed anything.
            await child_device_migration.prepare(device_registry.all())

            setup_signals(configs)

            if _shutdown_signalled():
                # Received while the devices were being created, when nothing could act on it
                logger.info("Shutdown signal received during initialisation - exiting")
                return 0

            crashed = await start(configs)

            if active_config.clean:
                await state_store.clean()
                if installation_cohort is not None:
                    await state_store.save(Category.CONFIG, _INSTALLATION_COHORT_KEY, installation_cohort)
                await MonitorService.clean()
        finally:
            # Shutdown StateStore
            state_store.shutdown()

        if crashed and not restart_controller.requested:
            logger.critical(f"Release {active_config.version} stopped because a worker thread crashed")
            return 1

        if not restart_controller.requested or _shutdown_signalled():
            # A termination signal takes precedence over a restart that was already under way
            logger.info(f"Shutdown of Release {active_config.version} completed")
            return 0

        # From here the previous cycle's handlers would act on thread configs that no longer exist
        setup_init_signals()
        try:
            await active_config.reload()
        except ConfigurationError as e:
            logger.critical(f"Configuration error: {e} - unable to restart")
            return 1

        logger.info("Restarting runtime")
