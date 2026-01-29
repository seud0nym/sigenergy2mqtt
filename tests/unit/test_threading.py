import asyncio
import logging
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.main import threading as threading_mod
from sigenergy2mqtt.main.thread_config import ThreadConfig


class DummyMQTTClient:
    def __init__(self):
        self.loop_stopped = False
        self.disconnected = False

    def loop_stop(self):
        self.loop_stopped = True

    def disconnect(self):
        self.disconnected = True


class DummyMQTTHandler:
    async def wait_for(self, timeout, name, method, mqtt_client, **kwargs):
        # call the device method synchronously (it may be sync in tests)
        try:
            # method signature may be (mqtt_client, clean=...)
            method(mqtt_client, **kwargs)
        except TypeError:
            # fallback: call without kwargs
            method(mqtt_client)


class DummyDevice:
    def __init__(self, name="dev"):
        self.name = name
        self.sensors = {}
        self._subscribed = False
        self._availability = []

    def publish_discovery(self, mqtt_client, clean: bool = False):
        return None

    def publish_attributes(self, mqtt_client, clean: bool = False):
        return None

    def subscribe(self, mqtt_client, mqtt_handler):
        self._subscribed = True

    def publish_availability(self, mqtt_client, ha_state: str | None):
        self._availability.append(ha_state)

    def schedule(self, modbus_client, mqtt_client):
        # return a coroutine (awaitable) so gather() will run it
        async def _coro():
            await asyncio.sleep(0)

        return [_coro()]


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_no_modbus(monkeypatch):
    # Config: clean True should prevent modbus usage
    monkeypatch.setattr(Config, "clean", True)
    monkeypatch.setattr(Config, "home_assistant", type("HA", (), {"enabled": False}))
    # Prepare ThreadConfig with no host
    cfg = ThreadConfig(None, None, name="Test")
    cfg.add_device(0, DummyDevice("dev1"))

    # Patch mqtt_setup to return dummy client and handler
    mqtt_client = DummyMQTTClient()
    mqtt_handler = DummyMQTTHandler()

    monkeypatch.setattr(threading_mod, "mqtt_setup", lambda cid, mb, loop: (mqtt_client, mqtt_handler))
    # Ensure ModbusFactory isn't called
    monkeypatch.setattr(threading_mod, "ModbusClientFactory", type("M", (), {"get_client": lambda *a, **k: asyncio.sleep(0)}))

    loop = asyncio.new_event_loop()
    orig_name = threading.current_thread().name
    try:
        await threading_mod.read_and_publish_device_sensors(cfg, loop=loop)
    finally:
        loop.close()
        threading.current_thread().name = orig_name

    assert mqtt_client.loop_stopped is True
    assert mqtt_client.disconnected is True


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_with_modbus_and_tasks(monkeypatch):
    # Config: not clean, HA disabled
    monkeypatch.setattr(Config, "clean", False)
    monkeypatch.setattr(Config, "home_assistant", type("HA", (), {"enabled": False}))

    # Create ThreadConfig with host so Modbus client is used
    cfg = ThreadConfig("127.0.0.1", 502, name="TestHost")
    cfg.add_device(0, DummyDevice("dev2"))

    # Mock Modbus client
    class MockModbus:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    async def fake_get_client(host, port, timeout, retries):
        return MockModbus()

    monkeypatch.setattr(threading_mod.ModbusClientFactory, "get_client", fake_get_client)

    mqtt_client = DummyMQTTClient()
    mqtt_handler = DummyMQTTHandler()
    monkeypatch.setattr(threading_mod, "mqtt_setup", lambda cid, mb, loop: (mqtt_client, mqtt_handler))

    loop = asyncio.new_event_loop()
    orig_name = threading.current_thread().name
    try:
        await threading_mod.read_and_publish_device_sensors(cfg, loop=loop)
    finally:
        loop.close()
        threading.current_thread().name = orig_name

    assert mqtt_client.loop_stopped is True
    assert mqtt_client.disconnected is True


def test_run_modbus_event_loop_and_start_exception_handling(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)

    # Patch read_and_publish_device_sensors to raise an exception when awaited
    async def raise_corr(config, upgrade, loop):
        raise RuntimeError("boom")

    monkeypatch.setattr(threading_mod, "read_and_publish_device_sensors", raise_corr)

    # Prepare a ThreadConfig
    cfg = ThreadConfig(None, None, name="Runner")
    # run_modbus_event_loop should catch and log the exception
    loop = asyncio.new_event_loop()
    orig_name = threading.current_thread().name
    try:
        threading_mod.run_modbus_event_loop(cfg, loop)
    finally:
        threading.current_thread().name = orig_name

    # Now test start() handling when run_modbus_event_loop raises in worker
    def bad_runner(cfg, upgrade, loop):
        raise ValueError("bad")

    monkeypatch.setattr(threading_mod, "run_modbus_event_loop", bad_runner)

    # start should not raise
    asyncio.run(threading_mod.start([cfg]))
    # asyncio.run() closes the running loop; restore a default loop for remaining tests
    asyncio.set_event_loop(asyncio.new_event_loop())


@pytest.mark.asyncio
async def test_read_and_publish_device_sensors_discovery_only(monkeypatch):
    """Verify that discovery_only mode doesn't schedule tasks but still connects to modbus."""
    monkeypatch.setattr(Config, "clean", False)
    monkeypatch.setattr(Config, "home_assistant", type("HA", (), {"enabled": True, "discovery_only": True}))
    monkeypatch.setattr(Config.mqtt, "client_id_prefix", "sigen")
    monkeypatch.setattr(Config.mqtt, "broker", "localhost")
    monkeypatch.setattr(Config.mqtt, "port", 1883)

    cfg = ThreadConfig("127.0.0.1", 502, name="DiscoveryOnly")
    mock_device = DummyDevice("disc_only")
    mock_device.schedule = MagicMock(return_value=[])
    cfg.add_device(0, mock_device)

    mock_mqtt_client = DummyMQTTClient()
    mock_mqtt_handler = DummyMQTTHandler()
    monkeypatch.setattr(threading_mod, "mqtt_setup", lambda cid, mb, loop: (mock_mqtt_client, mock_mqtt_handler))

    # Mock Modbus
    mock_modbus = MagicMock()
    monkeypatch.setattr(threading_mod.ModbusClientFactory, "get_client", AsyncMock(return_value=mock_modbus))

    loop = asyncio.new_event_loop()
    orig_name = threading.current_thread().name
    try:
        await threading_mod.read_and_publish_device_sensors(cfg, loop=loop)
    finally:
        loop.close()
        threading.current_thread().name = orig_name

    # Should NOT have scheduled tasks
    mock_device.schedule.assert_not_called()
    # Should have closed MQTT
    assert mock_mqtt_client.loop_stopped is True
