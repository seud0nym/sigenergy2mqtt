import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main.threading import read_and_publish_device_sensors


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

    config.device_init = [device]
    config.devices = [device]

    modbus_client = MagicMock()
    mqtt_client = MagicMock()
    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.threading.ModbusClientFactory.get_client", return_value=modbus_client),
        patch("sigenergy2mqtt.main.threading.mqtt_setup", return_value=(mqtt_client, mqtt_handler)),
        patch.object(Config.home_assistant, "enabled", True),
        patch.object(Config.home_assistant, "discovery_only", False),
        patch.object(Config, "clean", False),
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
    config.device_init = [device]

    mqtt_handler = MagicMock()
    mqtt_handler.wait_for = AsyncMock()
    mqtt_handler.close = AsyncMock()

    with (
        patch("sigenergy2mqtt.main.threading.mqtt_setup", return_value=(MagicMock(), mqtt_handler)),
        patch.object(Config.home_assistant, "enabled", True),
        patch.object(Config.home_assistant, "discovery_only", True),
        patch.object(Config, "clean", True),
    ):
        await read_and_publish_device_sensors(config, asyncio.get_event_loop())
        # discovery_only=True should prevent scheduling tasks
        device.schedule.assert_not_called()
        # clean=True should call wait_for with clean=True
        mqtt_handler.wait_for.assert_any_call(5, "TestDevice", ANY, ANY, clean=True)


def test_run_modbus_event_loop():
    """Hits run_modbus_event_loop logic."""
    from sigenergy2mqtt.main.threading import run_modbus_event_loop

    config = MagicMock()
    loop = MagicMock(spec=asyncio.AbstractEventLoop)

    with patch("sigenergy2mqtt.main.threading.read_and_publish_device_sensors", return_value=AsyncMock()) as mock_read, patch("asyncio.set_event_loop") as mock_set_loop:
        run_modbus_event_loop(config, loop)
        mock_read.assert_called_once()
        loop.run_until_complete.assert_called_once()
        loop.close.assert_called_once()


def test_run_modbus_event_loop_exception(caplog):
    """Hits run_modbus_event_loop exception path."""
    from sigenergy2mqtt.main.threading import run_modbus_event_loop

    config = MagicMock()
    config.description = "CrashedThread"
    loop = MagicMock(spec=asyncio.AbstractEventLoop)
    loop.run_until_complete.side_effect = Exception("loop crash")

    with patch("asyncio.set_event_loop") as mock_set_loop:
        run_modbus_event_loop(config, loop)
    assert "CrashedThread thread crashed !!!" in caplog.text
    loop.close.assert_called_once()


@pytest.mark.asyncio
async def test_start_logic():
    """Hits start function logic."""
    from sigenergy2mqtt.main.threading import start

    config = MagicMock()

    # We need to mock ThreadPoolExecutor to avoid real threads
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor, patch("asyncio.new_event_loop", return_value=MagicMock()):
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
    from sigenergy2mqtt.main.threading import start

    config = MagicMock()

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor, patch("asyncio.new_event_loop", return_value=MagicMock()):
        mock_fut = MagicMock()
        mock_fut.result.side_effect = Exception("future error")
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_fut
        patch_wait = patch("concurrent.futures.wait", return_value=([mock_fut], []))

        with patch_wait:
            await start([config])
            assert "Unhandled exception" in caplog.text
