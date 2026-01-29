import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.main import threading as threading_mod
from sigenergy2mqtt.main.thread_config import ThreadConfig


@pytest.mark.asyncio
async def test_main_clean_disables_pvoutput(monkeypatch):
    """Verify that --clean disables PVOutput services in async_main."""
    monkeypatch.setattr(Config, "modbus", [], raising=False)
    monkeypatch.setattr(Config.pvoutput, "enabled", True, raising=False)
    monkeypatch.setattr(Config, "clean", True, raising=False)
    monkeypatch.setattr(Config, "metrics_enabled", False, raising=False)
    monkeypatch.setattr(Config, "validate", classmethod(lambda cls: None), raising=False)
    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: logging.INFO), raising=False)

    mock_get_pvoutput = MagicMock(return_value=[MagicMock()])
    monkeypatch.setattr(main_mod, "get_pvoutput_services", mock_get_pvoutput)

    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(main_mod, "configure_logging", lambda: None)
    monkeypatch.setattr(main_mod, "pymodbus_apply_logging_config", lambda *a: None)
    monkeypatch.setattr(main_mod, "signal", MagicMock())

    await main_mod.async_main()

    # get_pvoutput_services should NOT have been called because clean is True
    mock_get_pvoutput.assert_not_called()


@pytest.mark.asyncio
async def test_threading_clean_effect(monkeypatch):
    """Verify that --clean prevents modbus client creation and skips task scheduling."""
    monkeypatch.setattr(Config, "clean", True)
    monkeypatch.setattr(Config, "home_assistant", type("HA", (), {"enabled": True, "discovery_only": False}))
    monkeypatch.setattr(Config.mqtt, "client_id_prefix", "sigen")
    monkeypatch.setattr(Config.mqtt, "broker", "localhost")
    monkeypatch.setattr(Config.mqtt, "port", 1883)

    cfg = ThreadConfig("127.0.0.1", 502, name="Test")
    mock_device = MagicMock()
    mock_device.name = "TestDevice"
    mock_device.publish_discovery = MagicMock()
    cfg.add_device(0, mock_device)

    mock_mqtt_client = MagicMock()
    mock_mqtt_handler = AsyncMock()
    monkeypatch.setattr(threading_mod, "mqtt_setup", lambda cid, mb, loop: (mock_mqtt_client, mock_mqtt_handler))

    mock_modbus_factory = MagicMock()
    monkeypatch.setattr(threading_mod, "ModbusClientFactory", mock_modbus_factory)

    import asyncio

    loop = asyncio.get_event_loop()

    await threading_mod.read_and_publish_device_sensors(cfg, loop)

    # Modbus client should NOT be created because clean is True
    mock_modbus_factory.get_client.assert_not_called()

    # Discovery should be called with clean=True
    # wait_for(5, device.name, method, mqtt_client, clean=True)
    mock_mqtt_handler.wait_for.assert_any_call(5, "TestDevice", mock_device.publish_discovery, mock_mqtt_client, clean=True)

    # Tasks should NOT be scheduled
    mock_device.schedule.assert_not_called()


@pytest.mark.asyncio
async def test_threading_discovery_only_effect(monkeypatch):
    """Verify that --hass-discovery-only skips task scheduling."""
    monkeypatch.setattr(Config, "clean", False)
    monkeypatch.setattr(Config, "home_assistant", type("HA", (), {"enabled": True, "discovery_only": True}))
    monkeypatch.setattr(Config.mqtt, "client_id_prefix", "sigen")
    monkeypatch.setattr(Config.mqtt, "broker", "localhost")
    monkeypatch.setattr(Config.mqtt, "port", 1883)

    cfg = ThreadConfig("127.0.0.1", 502, name="TestHost")
    mock_device = MagicMock()
    mock_device.name = "TestDevice"
    mock_device.publish_discovery = MagicMock()
    cfg.add_device(0, mock_device)

    mock_mqtt_client = MagicMock()
    mock_mqtt_handler = AsyncMock()
    monkeypatch.setattr(threading_mod, "mqtt_setup", lambda cid, mb, loop: (mock_mqtt_client, mock_mqtt_handler))

    # Mock modbus client to avoid actual connection
    mock_modbus = MagicMock()
    monkeypatch.setattr(threading_mod.ModbusClientFactory, "get_client", AsyncMock(return_value=mock_modbus))

    import asyncio

    loop = asyncio.get_event_loop()

    await threading_mod.read_and_publish_device_sensors(cfg, loop)

    # Discovery should be called with clean=False
    mock_mqtt_handler.wait_for.assert_any_call(5, "TestDevice", mock_device.publish_discovery, mock_mqtt_client, clean=False)

    # Tasks should NOT be scheduled
    mock_device.schedule.assert_not_called()
