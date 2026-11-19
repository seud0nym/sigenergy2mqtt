"""Exit status, signals during initialisation, and device-creation consistency."""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ModbusException

from sigenergy2mqtt.config import ConfigurationError, auto_discovery
from sigenergy2mqtt.main import device_setup, device_thread, service_setup
from sigenergy2mqtt.main import main as main_module
from sigenergy2mqtt.main.restart import restart_controller
from sigenergy2mqtt.main.thread_config import ThreadConfig, thread_config_registry
from sigenergy2mqtt.mqtt import (
    mqtt_reconnection_interrupted,
    reset_mqtt_reconnection_interrupt,
)
from sigenergy2mqtt.sensors.base.sanity_check import SanityCheckException


@pytest.fixture(autouse=True)
def restore_process_state():
    """Signal handlers and interruption flags are process-wide: put them back."""
    signals = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGUSR1]
    saved = {s: signal.getsignal(s) for s in signals}
    interrupted = auto_discovery._interrupted
    reset_mqtt_reconnection_interrupt()
    thread_config_registry.clear()
    restart_controller.reset()
    yield
    for s, handler in saved.items():
        signal.signal(s, handler)
    auto_discovery._interrupted = interrupted
    reset_mqtt_reconnection_interrupt()
    thread_config_registry.clear()
    restart_controller.reset()
    device_setup._GRID_RESTORE_WATCH_TASKS.clear()


# ---------------------------------------------------------------------------
# Exit status
# ---------------------------------------------------------------------------


class TestStartReportsCrash:
    @pytest.mark.asyncio
    async def test_returns_true_when_a_thread_crashes(self):
        config = ThreadConfig.create(None, None, name="Boom")

        async def boom(*args, **kwargs):
            raise AssertionError("thread failure")

        with patch.object(device_thread, "read_and_publish_device_sensors", boom):
            assert await device_thread.start([config]) is True

    @pytest.mark.asyncio
    async def test_returns_false_after_an_orderly_finish(self):
        config = ThreadConfig.create(None, None, name="Fine")

        async def fine(*args, **kwargs):
            return None

        with patch.object(device_thread, "read_and_publish_device_sensors", fine):
            assert await device_thread.start([config]) is False


def _patched_async_main(start_result=False, start_side_effect=None):
    """Patch everything async_main touches so that only its control flow runs."""
    start = AsyncMock(return_value=start_result, side_effect=start_side_effect)
    state_store = MagicMock()
    state_store.initialise = AsyncMock()
    state_store.load = AsyncMock(return_value="fresh")
    state_store.save = AsyncMock()
    state_store.clean = AsyncMock()
    config = MagicMock()
    config.clean = False
    config.reload = AsyncMock()
    patches = [
        patch.object(main_module, "configure_logging"),
        patch.object(main_module, "initialize_async", AsyncMock()),
        patch.object(main_module, "state_store", state_store),
        patch.object(main_module, "setup_devices", AsyncMock(return_value=([], None))),
        patch.object(main_module, "setup_services", return_value=[]),
        patch.object(main_module, "setup_signals"),
        patch.object(main_module, "setup_init_signals"),
        patch.object(main_module.child_device_migration, "prepare", AsyncMock()),
        patch.object(main_module, "start", start),
        patch.object(main_module, "active_config", config),
    ]
    return patches, start, state_store, config


class TestAsyncMainExitStatus:
    @pytest.mark.asyncio
    async def test_orderly_shutdown_returns_zero(self):
        patches, start, state_store, _ = _patched_async_main(start_result=False)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 0
        start.assert_awaited_once()
        state_store.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_crashed_thread_returns_one(self):
        patches, _, state_store, _ = _patched_async_main(start_result=True)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 1
        state_store.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_during_device_setup_exits_without_starting_threads(self):
        patches, start, state_store, _ = _patched_async_main()

        async def setup_devices(seen):
            service_setup.interrupt_mqtt_reconnection()  # what the initialisation handler does
            return [], None

        with patches[0], patches[1], patches[2], patch.object(main_module, "setup_devices", setup_devices), patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 0
        start.assert_not_awaited()
        state_store.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_during_slow_device_probe_is_not_lost(self):
        """A signal received while setup_devices is suspended must stop before start()."""
        patches, start, state_store, _ = _patched_async_main()
        probe_entered = asyncio.Event()
        finish_probe = asyncio.Event()

        async def slow_probe(seen):
            probe_entered.set()
            await finish_probe.wait()
            return [], None

        with (
            patches[0],
            patches[1],
            patches[2],
            patch.object(main_module, "setup_devices", slow_probe),
            patches[4],
            patches[5],
            patches[7],
            patches[8],
            patches[9],
        ):
            task = asyncio.create_task(main_module.async_main())
            await probe_entered.wait()
            # async_main installed the initialization handler before awaiting the probe.
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            finish_probe.set()
            assert await task == 0

        start.assert_not_awaited()
        state_store.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_during_configuration_load_exits_before_the_state_store(self):
        patches, start, state_store, _ = _patched_async_main()

        async def initialize():
            auto_discovery._interrupted = True

        with patches[0], patch.object(main_module, "initialize_async", initialize), patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 0
        state_store.initialise.assert_not_awaited()
        start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_restart_reloads_once_and_runs_another_cycle(self):
        cycles = 0

        async def start(configs):
            nonlocal cycles
            cycles += 1
            if cycles == 1:
                restart_controller._requested = True
            return False

        patches, _, _, config = _patched_async_main(start_side_effect=start)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 0
        assert cycles == 2
        config.reload.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_termination_signal_wins_over_a_pending_restart(self):
        async def start(configs):
            restart_controller._requested = True
            service_setup.interrupt_mqtt_reconnection()
            return False

        patches, _, _, config = _patched_async_main(start_side_effect=start)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 0
        config.reload.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_configuration_on_restart_returns_one(self):
        async def start(configs):
            restart_controller._requested = True
            return False

        patches, _, _, config = _patched_async_main(start_side_effect=start)
        config.reload = AsyncMock(side_effect=ConfigurationError("bad yaml"))
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
            assert await main_module.async_main() == 1


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestInitSignals:
    def test_first_signal_sets_the_interruption_flags(self):
        auto_discovery._interrupted = False
        service_setup.setup_init_signals()
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        assert mqtt_reconnection_interrupted() is True
        assert auto_discovery._interrupted is True

    def test_second_signal_forces_exit(self):
        service_setup.setup_init_signals()
        handler = signal.getsignal(signal.SIGTERM)
        with patch.object(service_setup.os, "_exit") as force_exit:
            handler(signal.SIGTERM, None)
            force_exit.assert_not_called()
            handler(signal.SIGTERM, None)
        force_exit.assert_called_once_with(128 + signal.SIGTERM)

    def test_sighup_is_ignored_while_initialising(self):
        service_setup.setup_init_signals()
        signal.getsignal(signal.SIGHUP)(signal.SIGHUP, None)
        assert restart_controller.requested is False
        assert mqtt_reconnection_interrupted() is False

    def test_replaces_the_previous_cycles_handlers(self):
        stale = MagicMock()
        service_setup.setup_signals([stale])
        service_setup.setup_init_signals()
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        stale.offline.assert_not_called()


    def test_signal_during_initialisation_counts_towards_the_forced_exit_at_runtime(self):
        """The first signal arrives during device setup, the second after setup_signals()."""
        service_setup.setup_init_signals()
        with patch.object(service_setup.os, "_exit") as force_exit:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            config = MagicMock()
            service_setup.setup_signals([config])
            force_exit.assert_not_called()
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        force_exit.assert_called_once_with(128 + signal.SIGTERM)

    def test_signal_at_runtime_counts_towards_the_forced_exit_during_a_restart(self):
        config = MagicMock()
        service_setup.setup_signals([config])
        with patch.object(service_setup.os, "_exit") as force_exit:
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
            service_setup.setup_init_signals()
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        force_exit.assert_called_once_with(128 + signal.SIGINT)


class TestRuntimeSignals:
    def test_second_termination_signal_forces_exit(self):
        config = MagicMock()
        service_setup.setup_signals([config])
        handler = signal.getsignal(signal.SIGTERM)
        with patch.object(service_setup.os, "_exit") as force_exit:
            handler(signal.SIGTERM, None)
            config.offline.assert_called_once()
            force_exit.assert_not_called()
            handler(signal.SIGINT, None)
        force_exit.assert_called_once_with(128 + signal.SIGINT)

    def test_sigusr1_does_not_count_towards_the_forced_exit(self):
        config = MagicMock()
        with patch.object(service_setup, "active_config", MagicMock()):
            service_setup.setup_signals([config])
            with patch.object(service_setup.os, "_exit") as force_exit:
                signal.getsignal(signal.SIGUSR1)(signal.SIGUSR1, None)
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        force_exit.assert_not_called()
        assert config.offline.call_count == 2

    def test_sighup_requests_a_restart_without_reloading_live_configuration(self):
        config = MagicMock()
        fake_config = MagicMock()
        fake_config.reload = AsyncMock()
        with patch.object(service_setup, "active_config", fake_config), patch.object(service_setup.restart_controller, "request") as request:
            service_setup.setup_signals([config])
            signal.getsignal(signal.SIGHUP)(signal.SIGHUP, None)
        request.assert_called_once_with("signal SIGHUP")
        fake_config.reload.assert_not_called()


# ---------------------------------------------------------------------------
# Worker thread start-up
# ---------------------------------------------------------------------------


class TestThreadStartup:
    @pytest.mark.asyncio
    async def test_shutdown_requested_before_tasks_commence_is_honoured(self):
        config = ThreadConfig.create(None, None, name="Late")
        ran = False

        async def poll():
            nonlocal ran
            ran = True

        device = MagicMock()
        device.name = "device"
        device.log_identity = "Device"

        def schedule(transport, mqtt_client):
            config.offline()  # the signal arrives while this thread is still starting
            return [poll()]

        device.schedule.side_effect = schedule
        config.add_device(device)
        handler = MagicMock()
        handler.wait_for = AsyncMock()
        fake_config = MagicMock()
        fake_config.clean = False
        fake_config.home_assistant.enabled = True
        fake_config.home_assistant.discovery_only = False
        with (
            patch.object(device_thread, "mqtt_setup", AsyncMock(return_value=(MagicMock(), handler))),
            patch.object(device_thread, "mqtt_teardown", AsyncMock()),
            patch.object(device_thread, "active_config", fake_config),
        ):
            await device_thread.read_and_publish_device_sensors(config, asyncio.get_running_loop())

        assert ran is False
        assert config.shutdown_requested is True
        device.on_commencement.assert_not_called()
        assert device.publish_availability.call_args_list[-1].args[1] == "offline"

    @pytest.mark.asyncio
    async def test_failed_task_is_reported_while_the_others_keep_running(self, caplog):
        config = ThreadConfig.create(None, None, name="Mixed")
        release = asyncio.Event()
        reported_before_shutdown = False

        async def dies():
            raise KeyError("early")

        async def keeps_running():
            nonlocal reported_before_shutdown
            await asyncio.sleep(0.1)
            reported_before_shutdown = "a scheduled task raised an exception" in caplog.text
            release.set()

        device = MagicMock()
        device.name = "device"
        device.log_identity = "Device"
        device.schedule.return_value = [dies(), keeps_running()]
        config.add_device(device)
        handler = MagicMock()
        handler.wait_for = AsyncMock()
        fake_config = MagicMock()
        fake_config.clean = False
        fake_config.home_assistant.enabled = False
        with (
            patch.object(device_thread, "mqtt_setup", AsyncMock(return_value=(MagicMock(), handler))),
            patch.object(device_thread, "mqtt_teardown", AsyncMock()),
            patch.object(device_thread, "active_config", fake_config),
        ):
            await device_thread.read_and_publish_device_sensors(config, asyncio.get_running_loop())

        assert release.is_set()
        assert reported_before_shutdown is True
        assert caplog.text.count("a scheduled task raised an exception") == 1, "the failure must not be reported a second time at shutdown"

    @pytest.mark.asyncio
    async def test_thread_stops_cleanly_when_abandoning_the_wait_for_modbus(self):
        config = ThreadConfig.create("192.0.2.1", 502)
        mqtt_setup = AsyncMock()
        with (
            patch.object(device_thread.ModbusClientFactory, "get_client", AsyncMock(side_effect=device_thread.ModbusConnectAborted("stop"))),
            patch.object(device_thread, "mqtt_setup", mqtt_setup),
        ):
            await device_thread.read_and_publish_device_sensors(config, asyncio.get_running_loop())
        mqtt_setup.assert_not_awaited()


# ---------------------------------------------------------------------------
# Device creation
# ---------------------------------------------------------------------------


class TestDeviceCreation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [SanityCheckException("bad"), OSError("down"), RuntimeError("x"), ModbusException("m"), TimeoutError()])
    async def test_grid_outage_probe_never_raises(self, error):
        with patch.object(device_setup.GridStatus, "get_state", AsyncMock(side_effect=error)):
            assert await device_setup._is_grid_outage(0, MagicMock()) is None

    @pytest.mark.asyncio
    async def test_failing_dc_charger_is_skipped_like_the_other_device_types(self):
        device = MagicMock()
        device.dc_chargers = [1, 2]
        config = MagicMock()
        charger = MagicMock()
        with (
            patch.object(device_setup, "make_dc_charger", AsyncMock(side_effect=[ModbusException("no response"), charger])),
            patch.object(device_setup, "validate_publishable_sensors", AsyncMock()),
            patch.object(device_setup, "_is_grid_outage", AsyncMock(return_value=False)),
        ):
            sequence = await device_setup._setup_dc_chargers(
                plant_index=0, device=device, plant=MagicMock(), modbus_client=MagicMock(), inverters={1: "a", 2: "b"}, config=config, sequence_start=0, total_count=2
            )
        assert sequence == 2
        config.add_device.assert_called_once_with(charger)

    @pytest.mark.asyncio
    async def test_dc_charger_skipped_during_grid_outage_schedules_a_restart(self):
        device = MagicMock()
        device.dc_chargers = [1]
        with (
            patch.object(device_setup, "make_dc_charger", AsyncMock(side_effect=TimeoutError())),
            patch.object(device_setup, "_is_grid_outage", AsyncMock(return_value=True)),
            patch.object(device_setup, "_schedule_restart_on_grid_restore") as schedule,
        ):
            await device_setup._setup_dc_chargers(plant_index=0, device=device, plant=MagicMock(), modbus_client=MagicMock(), inverters={1: "a"}, config=MagicMock(), sequence_start=0, total_count=1)
        schedule.assert_called_once_with(device, 0)

    @pytest.mark.asyncio
    async def test_watcher_is_referenced_and_cancelled_with_the_cycle(self):
        device = MagicMock(host="192.0.2.1", port=502, timeout=1.0, retries=1)
        started = asyncio.Event()

        async def watch(*args):
            started.set()
            await asyncio.sleep(60)

        with patch.object(device_setup, "_watch_grid_restore_and_request_restart", watch):
            device_setup._schedule_restart_on_grid_restore(device, 0)
            device_setup._schedule_restart_on_grid_restore(device, 0)  # no duplicate
            assert len(device_setup._GRID_RESTORE_WATCH_TASKS) == 1
            task = next(iter(device_setup._GRID_RESTORE_WATCH_TASKS.values()))
            await started.wait()
            device_setup.cancel_grid_restore_watchers()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert device_setup._GRID_RESTORE_WATCH_TASKS == {}

    @pytest.mark.asyncio
    async def test_watcher_keeps_watching_when_the_host_is_unreachable(self):
        probes = 0

        class Client:
            connected = True

            def __init__(self, *args, **kwargs):
                nonlocal probes
                probes += 1
                if probes == 1:
                    raise OSError("unreachable")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        with (
            patch.object(device_setup, "ModbusClient", Client),
            patch.object(device_setup, "_is_grid_outage", AsyncMock(return_value=False)),
            patch.object(device_setup.asyncio, "sleep", AsyncMock()),
            patch.object(device_setup.restart_controller, "request") as request,
        ):
            await asyncio.wait_for(device_setup._watch_grid_restore_and_request_restart("192.0.2.1", 502, 1.0, 1, 0), 5)
        assert probes == 2
        request.assert_called_once()
