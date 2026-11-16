import asyncio
import logging
import os
import signal

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import (
    SettingsService,
    active_config,
    auto_discovery,
    is_docker,
)
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

    # Keep the settings sensors available to diagnostics and retain the device
    # for clearing old discovery, even when MQTT publishing is disabled.
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


def _exit_status(signum: int) -> int:
    """Conventional exit status for a process ended by *signum* (128 + signal number)."""
    return 128 + int(signum)


def setup_init_signals() -> None:
    """Install the signal handlers used while a runtime cycle is being initialised.

    Between the start of a cycle and :func:`setup_signals` there are no thread
    configs to take offline, so a termination signal can only be recorded. It
    is recorded in the shared interruption flags, which the startup waits and
    :func:`~sigenergy2mqtt.main.main.async_main` check between phases. Without
    this, the handlers of the *previous* cycle (bound to its thread configs)
    would stay installed during a restart and the signal would be lost.

    A second termination signal forces an immediate exit.

    Side effects:

    - Installs handlers for ``SIGINT``, ``SIGTERM`` and ``SIGUSR1`` (shutdown)
      and ``SIGHUP`` (ignored: the configuration is being loaded anyway).
    """
    signalled = False

    def stop_initialising(caught, frame):
        nonlocal signalled
        if signalled and caught in (signal.SIGINT, signal.SIGTERM):
            # Not responding quickly enough: bypass any blocked threads
            os._exit(_exit_status(caught))
        signalled = True
        auto_discovery._interrupted = True
        interrupt_mqtt_reconnection()

    def ignore_reload(caught=None, frame=None):
        logger.info("Signal SIGHUP ignored - configuration is already being loaded")

    signal.signal(signal.SIGINT, stop_initialising)
    signal.signal(signal.SIGTERM, stop_initialising)
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, stop_initialising)
    if hasattr(signal, "SIGHUP"):
        try:
            # setup_signals() registers SIGHUP with the event loop, which would otherwise
            # keep dispatching it to the previous cycle's handler
            asyncio.get_running_loop().remove_signal_handler(signal.SIGHUP)
        except (RuntimeError, NotImplementedError, AttributeError, ValueError):
            pass
        signal.signal(signal.SIGHUP, ignore_reload)


def setup_signals(configs: list[ThreadConfig]) -> None:
    """Register process-level handlers for shutdown, reload, and restart signals.

    Side effects:

    - Installs handlers for ``SIGINT``, ``SIGTERM``, ``SIGHUP``, and ``SIGUSR1``.
    - On termination paths, marks all thread configs offline. A second
      ``SIGINT``/``SIGTERM`` forces an immediate exit.
    - On restart path, suppresses Home Assistant availability-offline publication.
    """
    terminations = 0

    def configure_for_restart(caught, frame):
        """Handle SIGUSR1 by suppressing HA and initiating a graceful shutdown."""
        logger.info(f"Signal {caught} received - reconfiguring for restart")
        # Suppress the HA offline availability message since we intend to restart.
        active_config.home_assistant.enabled = False
        shutdown(caught)

    def shutdown(caught) -> None:
        logger.info(f"Signal {caught} received - Shutdown commenced")
        interrupt_mqtt_reconnection()
        logging.getLogger("asyncio").setLevel(logging.ERROR)
        for config in configs:
            config.offline()

    def exit_on_signal(caught, frame):
        """Handle termination signals by setting all active thread configs to offline."""
        nonlocal terminations
        terminations += 1
        if terminations > 1:
            # The graceful shutdown is not completing: bypass any blocked threads
            os._exit(_exit_status(caught))
        shutdown(caught)

    def reload_on_signal(caught=None, frame=None):
        """Handle SIGHUP by requesting a restart, which reloads the configuration.

        The configuration is deliberately not reloaded here: doing so would
        replace the live settings underneath the running threads. The restart
        takes them offline first, and :func:`~sigenergy2mqtt.main.main.async_main`
        then reloads once before the next cycle.
        """
        logger.info("Signal SIGHUP received - Reloading configuration")
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
            # Run the SIGHUP handler as a loop callback rather than inside the signal handler
            loop.add_signal_handler(signal.SIGHUP, reload_on_signal)
        except (NotImplementedError, AttributeError):
            pass
