import asyncio
import logging
import signal

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import SettingsService, active_config, is_docker
from sigenergy2mqtt.diagnostics import DiagnosticsService
from sigenergy2mqtt.influxdb import get_influxdb_services
from sigenergy2mqtt.metrics import Metrics, MetricsService
from sigenergy2mqtt.monitor import MonitorService
from sigenergy2mqtt.mqtt import interrupt_mqtt_reconnection
from sigenergy2mqtt.pvoutput import get_pvoutput_services

from .restart import restart_controller
from .thread_config import ThreadConfig

logger = logging.getLogger(__name__)


def setup_services(configs: list[ThreadConfig], protocol_version: ProtocolVersion | None) -> list[ThreadConfig]:
    """Attach optional service/monitor threads to the discovered device configs.

    Side effects:

    - Mutates ``configs`` in-place by inserting a ``Monitor`` thread at index 0
      and/or appending a ``Services`` thread.
    - Instantiates integration services that may later make outbound API/network
      calls (PVOutput/InfluxDB/Metrics) once started.
    """
    if not active_config.clean:
        mon_thread_cfg = ThreadConfig.create(name="Monitor", host=None, port=None)
        mon_thread_cfg.add_device(MonitorService([d for c in configs for d in c.devices]))
        configs.insert(0, mon_thread_cfg)

    svc_thread_cfg = ThreadConfig.create(name="Services", host=None, port=None)

    svc_thread_cfg.add_device(SettingsService())

    if active_config.diagnostics.enabled or is_docker():
        svc_thread_cfg.add_device(DiagnosticsService())

    Metrics.commence()
    if active_config.metrics_enabled:
        svc_thread_cfg.add_device(MetricsService(protocol_version if protocol_version is not None else ProtocolVersion.N_A))

    if active_config.pvoutput.enabled and not active_config.clean:
        for service in get_pvoutput_services(configs):
            svc_thread_cfg.add_device(service)

    if active_config.influxdb.enabled and not active_config.clean:
        for service in get_influxdb_services():
            svc_thread_cfg.add_device(service)

    if svc_thread_cfg.has_devices:
        configs.append(svc_thread_cfg)
    else:
        logger.debug("No services configured - skipping service thread")

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
        logger.info(f"Signal {caught} received - reconfiguring for restart")
        # Suppress the HA offline availability message since we intend to restart.
        active_config.home_assistant.enabled = False
        exit_on_signal(caught, frame)

    def exit_on_signal(caught, frame):
        """Handle termination signals by setting all active thread configs to offline."""
        logger.info(f"Signal {caught} received - Shutdown commenced")
        interrupt_mqtt_reconnection()
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        for config in configs:
            config.offline()

    def reload_on_signal(caught=None, frame=None):
        """Handle SIGHUP by reloading config/logging and requesting restart."""
        logger.info("Signal SIGHUP received - Reloading configuration")

        async def _reload_and_restart():
            try:
                await active_config.reload()
            except (ValueError, OSError, RuntimeError) as e:
                logger.error(f"SIGHUP reload failed: {e}")
            finally:
                restart_controller.request("signal SIGHUP")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_reload_and_restart())
        except RuntimeError:
            logger.error("No running event loop to handle SIGHUP reload")

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
