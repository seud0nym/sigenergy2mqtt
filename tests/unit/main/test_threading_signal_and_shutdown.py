import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.main.device_thread import read_and_publish_device_sensors


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_ha_enabled_and_cancel():
    """Hits HA availability and CancelledError paths in threading.py."""
    config = MagicMock()
    config.description = "TestDescription"
    config.host = "1.2.3.4"
    config.port = 502
    config.timeout = 1
    config.retries = 1
    config.url = "modbus://1.2.3.4:502"

    device = MagicMock()
    device.name = "TestDevice"
    device.publish_discovery = AsyncMock()
    device.publish_availability = MagicMock()
    device.schedule.return_value = [asyncio.sleep(10)]  # Long task to be cancelled

    config.devices = [device]
    config.devices = [device]

    modbus_client = MagicMock()
    mqtt_client = MagicMock()
    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.ModbusClientFactory.get_client", return_value=modbus_client),
        patch("sigenergy2mqtt.main.device_thread.mqtt_setup", return_value=(mqtt_client, mqtt_handler)),
        patch.object(active_config.home_assistant, "enabled", True),
        patch.object(active_config.home_assistant, "discovery_only", False),
        patch.object(active_config, "clean", False),
    ):
        task = asyncio.create_task(read_and_publish_device_sensors(config, asyncio.get_event_loop()))
        await asyncio.sleep(0.1)

        # Verify online availability was called
        device.publish_availability.assert_any_call(mqtt_client, "online")

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify offline availability was called after cancellation/exit
        device.publish_availability.assert_any_call(mqtt_client, "offline")
        modbus_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_clean_and_discovery_only():
    """Hits clean=True and discovery_only=True paths."""
    config = MagicMock()
    config.description = "TestClean"
    config.host = None
    config.url = "None"

    device = MagicMock()
    device.name = "TestDevice"
    device.publish_discovery = AsyncMock()
    config.devices = [device]

    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.mqtt_setup", return_value=(MagicMock(), mqtt_handler)),
        patch.object(active_config.home_assistant, "enabled", True),
        patch.object(active_config.home_assistant, "discovery_only", True),
        patch.object(active_config, "clean", True),
    ):
        await read_and_publish_device_sensors(config, asyncio.get_event_loop())
        # discovery_only=True should prevent scheduling tasks
        device.schedule.assert_not_called()
        # clean=True should call wait_for with clean=True
        mqtt_handler.wait_for.assert_any_call(5, "TestDevice", ANY, ANY, clean=True)


def test_run_modbus_event_loop():
    """Hits run_modbus_event_loop logic."""
    from sigenergy2mqtt.main.device_thread import run_modbus_event_loop

    config = MagicMock()
    loop = MagicMock(spec=asyncio.AbstractEventLoop)

    with patch("sigenergy2mqtt.main.device_thread.read_and_publish_device_sensors", new_callable=MagicMock, return_value=None) as mock_read, patch("asyncio.set_event_loop"):
        run_modbus_event_loop(config, loop)
        mock_read.assert_called_once()
        loop.run_until_complete.assert_called_once()
        loop.close.assert_called_once()


def test_run_modbus_event_loop_exception(caplog):
    """Hits run_modbus_event_loop exception path."""
    from sigenergy2mqtt.main.device_thread import run_modbus_event_loop

    config = MagicMock()
    config.description = "CrashedThread"
    loop = MagicMock(spec=asyncio.AbstractEventLoop)
    loop.run_until_complete.side_effect = Exception("loop crash")

    with patch("sigenergy2mqtt.main.device_thread.read_and_publish_device_sensors", new_callable=MagicMock, return_value=None), patch("asyncio.set_event_loop"):
        run_modbus_event_loop(config, loop)
    assert "CrashedThread thread crashed !!!" in caplog.text
    loop.close.assert_called_once()


@pytest.mark.asyncio
async def test_start_logic():
    """Hits start function logic."""
    from sigenergy2mqtt.main.device_thread import start

    config = MagicMock()

    # We need to mock ThreadPoolExecutor to avoid real threads
    # Also mock run_modbus_event_loop to avoid creating unawaited coroutines
    mock_loop = MagicMock()
    with (
        patch("sigenergy2mqtt.main.device_thread.run_modbus_event_loop", MagicMock()),
        patch("concurrent.futures.ThreadPoolExecutor") as mock_executor,
        patch("asyncio.new_event_loop", return_value=mock_loop),
    ):
        # Setup mock executor to return a finished future
        mock_fut = MagicMock()
        mock_fut.result.return_value = None
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_fut
        patch_wait = patch("concurrent.futures.wait", return_value=([mock_fut], []))

        with patch_wait:
            await start([config])
            mock_executor.return_value.__enter__.return_value.submit.assert_called_once()


@pytest.mark.asyncio
async def test_start_logic_with_exception(caplog):
    """Hits start function exception path."""
    from sigenergy2mqtt.main.device_thread import start

    config = MagicMock()

    # Also mock run_modbus_event_loop to avoid creating unawaited coroutines
    mock_loop = MagicMock()
    with (
        patch("sigenergy2mqtt.main.device_thread.run_modbus_event_loop", MagicMock()),
        patch("concurrent.futures.ThreadPoolExecutor") as mock_executor,
        patch("asyncio.new_event_loop", return_value=mock_loop),
    ):
        mock_fut = MagicMock()
        mock_fut.result.side_effect = Exception("future error")
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_fut
        patch_wait = patch("concurrent.futures.wait", return_value=([mock_fut], []))

        with patch_wait:
            await start([config])
            assert "Unhandled exception" in caplog.text


@pytest.mark.asyncio
async def test_start_logic_keyboard_interrupt_sets_offline_and_reraises():
    """Ensures Ctrl-C in main thread triggers cooperative shutdown then re-raises."""
    from sigenergy2mqtt.main.device_thread import start

    config = MagicMock()
    mock_loop = MagicMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.run_modbus_event_loop", MagicMock()),
        patch("concurrent.futures.ThreadPoolExecutor") as mock_executor,
        patch("asyncio.new_event_loop", return_value=mock_loop),
        patch("asyncio.sleep", side_effect=[KeyboardInterrupt()]),
        patch(
            "concurrent.futures.wait",
            return_value=([MagicMock()], []),
        ) as mock_wait,
    ):
        mock_fut = MagicMock()
        mock_fut.done.side_effect = [False, False, True, True, True, True]
        mock_fut.result.return_value = None
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_fut

        with pytest.raises(KeyboardInterrupt):
            await start([config])

        # One call from the exception handler to drain the futures.
        assert mock_wait.call_count == 1
        config.offline.assert_called_once()


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_on_commencement_exception(caplog):
    """Cover exception path in on_commencement (lines 100-101)."""
    config = MagicMock()
    config.description = "TestCommencementCrash"
    config.host = None
    config.url = "None"

    async def fake_task():
        pass

    device = MagicMock()
    device.name = "TestDevice"
    device.publish_discovery = AsyncMock()
    device.schedule.return_value = [fake_task()]
    device.on_commencement.side_effect = Exception("commencement failed")
    config.devices = [device]

    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.mqtt_setup", return_value=(MagicMock(), mqtt_handler)),
        patch.object(active_config.home_assistant, "enabled", True),
        patch.object(active_config.home_assistant, "discovery_only", False),
        patch.object(active_config, "clean", False),
    ):
        await read_and_publish_device_sensors(config, asyncio.get_event_loop())
        assert "on commencement failed" in caplog.text


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_on_completion_exception(caplog):
    """Cover exception path in on_completion (lines 122-123)."""
    config = MagicMock()
    config.description = "TestCompletionCrash"
    config.host = None
    config.url = "None"

    async def fake_task():
        pass

    device = MagicMock()
    device.name = "TestDevice"
    device.publish_discovery = AsyncMock()
    device.schedule.return_value = [fake_task()]
    device.on_completion.side_effect = Exception("completion failed")
    config.devices = [device]

    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.mqtt_setup", return_value=(MagicMock(), mqtt_handler)),
        patch.object(active_config.home_assistant, "enabled", True),
        patch.object(active_config.home_assistant, "discovery_only", False),
        patch.object(active_config, "clean", False),
    ):
        await read_and_publish_device_sensors(config, asyncio.get_event_loop())
        assert "on completion failed" in caplog.text


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_task_exception(caplog):
    """Cover exception path in task gathering (line 114)."""
    config = MagicMock()
    config.description = "TestTaskCrash"
    config.host = None
    config.url = "None"

    async def raise_error():
        raise ValueError("task failed")

    device = MagicMock()
    device.name = "TestDevice"
    device.publish_discovery = AsyncMock()
    device.schedule.return_value = [raise_error()]
    config.devices = [device]

    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.device_thread.mqtt_setup", return_value=(MagicMock(), mqtt_handler)),
        patch.object(active_config.home_assistant, "enabled", True),
        patch.object(active_config.home_assistant, "discovery_only", False),
        patch.object(active_config, "clean", False),
    ):
        await read_and_publish_device_sensors(config, asyncio.get_event_loop())
        assert "a scheduled task raised an exception" in caplog.text


def test_run_modbus_event_loop_stop_event_set():
    """Cover run_modbus_event_loop exception with stop_event.set() (line 162)."""
    from sigenergy2mqtt.main.device_thread import run_modbus_event_loop
    import threading

    config = MagicMock()
    config.description = "CrashedThreadStopEvent"
    loop = MagicMock(spec=asyncio.AbstractEventLoop)
    loop.run_until_complete.side_effect = Exception("loop crash")
    stop_event = threading.Event()

    with (
        patch("sigenergy2mqtt.main.device_thread.read_and_publish_device_sensors", return_value=None),
        patch("asyncio.set_event_loop")
    ):
        run_modbus_event_loop(config, loop, stop_event)
        assert stop_event.is_set()


@pytest.mark.asyncio
async def test_start_logic_sibling_thread_crashed():
    """Cover start logic when a sibling thread crashed (lines 200-207)."""
    from sigenergy2mqtt.main.device_thread import start
    import time

    cfg_crasher = MagicMock()
    cfg_crasher.description = "crasher"
    cfg_pending = MagicMock()
    cfg_pending.description = "pending"

    # We want a real thread pool executor, but we patch run_modbus_event_loop
    # to control its behavior and stop_event.
    def fake_run_modbus_event_loop(config, loop, stop_event):
        loop.close()  # close the loop as run_modbus_event_loop would do in finally
        if config.description == "crasher":
            stop_event.set()
        else:
            time.sleep(0.5)

    with patch("sigenergy2mqtt.main.device_thread.run_modbus_event_loop", side_effect=fake_run_modbus_event_loop):
        await start([cfg_crasher, cfg_pending])

    cfg_crasher.offline.assert_called_once()
    cfg_pending.offline.assert_called_once()

