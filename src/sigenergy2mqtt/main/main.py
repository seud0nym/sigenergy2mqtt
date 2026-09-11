import logging

from sigenergy2mqtt.common import service_health_registry
from sigenergy2mqtt.config import active_config, initialize_async
from sigenergy2mqtt.devices import DeviceRegistry as device_registry
from sigenergy2mqtt.diagnostics import diagnostics_registry
from sigenergy2mqtt.monitor import MonitorService
from sigenergy2mqtt.mqtt import mqtt_health_registry, reset_mqtt_reconnection_interrupt
from sigenergy2mqtt.persistence import state_store

from .device_setup import setup_devices
from .device_thread import start
from .logging_setup import configure_logging
from .restart import restart_controller
from .service_setup import setup_services, setup_signals
from .thread_config import thread_config_registry

logger = logging.getLogger(__name__)


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
        configure_logging()
        reset_mqtt_reconnection_interrupt()

        restart_controller.reset()
        thread_config_registry.clear()
        device_registry.clear()
        mqtt_health_registry.clear()
        service_health_registry.clear()
        diagnostics_registry.clear()

        # Phase 2 config load — must run before StateStore so that the correct
        # MQTT broker address (and other settings) from the YAML config file are
        # available when StateStore opens its dedicated MQTT connection.
        # Note: _restore_discovery_from_mqtt inside initialize_async() already
        # guards against StateStore not yet being initialised, so ordering here
        # is safe.
        await initialize_async()

        # Initialise StateStore with dedicated MQTT connection + sentinel-based warming
        await state_store.initialise(
            active_config.persistent_state_path,
            active_config.persistence,
        )

        seen_serial_numbers: set[str] = set()
        configs, protocol_version = await setup_devices(seen_serial_numbers)
        configs = setup_services(configs, protocol_version)

        setup_signals(configs)

        await start(configs)

        if active_config.clean:
            await state_store.clean()
            await MonitorService.clean()

        # Shutdown StateStore
        state_store.shutdown()

        if not restart_controller.requested:
            logger.info(f"Shutdown of Release {active_config.version} completed")
            return
        else:
            await active_config.reload()

        logger.info("Restarting runtime")
