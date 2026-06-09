import asyncio
import logging
import time

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.monitor.monitor_service import MonitorService
from sigenergy2mqtt.monitor.monitored_sensor import MonitoredSensor
from sigenergy2mqtt.sensors.base import ReadableSensorMixin


class DummyReadable(ReadableSensorMixin):
    def __init__(self, *, name: str, scan_interval: int, state_topic: str, publishable: bool = True):
        # Do not call base class __init__ to avoid heavy Sensor setup
        self.name = name
        self._log_identity = name
        self.scan_interval = scan_interval
        self["state_topic"] = state_topic
        self._publishable = publishable


class DummyDevice:
    def __init__(self, name: str, sensors: dict):
        self.name = name
        self.log_identity = name
        self._sensors = sensors

    def get_all_sensors(self):
        return self._sensors


class FakeMqttHandler:
    def __init__(self):
        self.registered = []

    def register(self, mqtt_client, topic, handler=None):
        self.registered.append((mqtt_client, topic, handler))


class FakeMqttClient:
    def __init__(self, connected: bool = True):
        self._connected = connected
        self.published = []

    def is_connected(self):
        return self._connected

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


def test_subscribe_registers_topics():
    active_config.log_level = logging.DEBUG
    s = DummyReadable(name="sensor1", scan_interval=5, state_topic="topic/1", publishable=True)
    d = DummyDevice("Device1", {"s1": s})
    handler = FakeMqttHandler()
    svc = MonitorService([d])

    svc.subscribe(None, handler)

    assert (None, "topic/1", svc.on_topic_update) in handler.registered
    assert "topic/1" in svc._topics
    ms = svc._topics["topic/1"]
    assert isinstance(ms, MonitoredSensor)
    assert ms.device_name == "Device1"
    assert ms.sensor_name == "sensor1"


def test_subscribe_skips_registration_when_repeated_negative(monkeypatch):
    monkeypatch.setattr(active_config, "log_level", logging.DEBUG)
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    s = DummyReadable(name="sensor1", scan_interval=5, state_topic="topic/1", publishable=True)
    d = DummyDevice("Device1", {"s1": s})
    handler = FakeMqttHandler()
    svc = MonitorService([d])

    svc.subscribe(None, handler)

    assert handler.registered == []
    assert svc._topics == {}


def test_schedule_returns_monitor_task_when_repeated_negative(monkeypatch):
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    svc = MonitorService([])

    tasks = svc.schedule(None, None)
    assert len(tasks) == 1
    tasks[0].close()


def test_monitored_sensor_last_seen_uses_creation_time_default():
    first = MonitoredSensor("Dev", "S1", 5)
    time.sleep(0.01)
    second = MonitoredSensor("Dev", "S2", 5)

    assert second.last_seen > first.last_seen


def test_monitored_sensor_is_overdue_uses_repeated_state_publish_interval_when_larger(monkeypatch):
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", 60)
    ms = MonitoredSensor("Dev", "S", 5, last_seen=time.time() - 20)

    # Would be overdue with scan_interval (5*3=15), but should not be overdue when
    # repeated_state_publish_interval is larger (60*3=180).
    assert ms.is_overdue is False


def test_monitored_sensor_is_overdue_uses_scan_interval_when_repeated_disabled(monkeypatch):
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", 0)
    ms = MonitoredSensor("Dev", "S", 5, last_seen=time.time() - 20)

    assert ms.is_overdue is True


def test_monitored_sensor_is_overdue_disabled_when_repeated_negative(monkeypatch):
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    ms = MonitoredSensor("Dev", "S", 1, last_seen=time.time() - 10_000)

    assert ms.is_overdue is False


@pytest.mark.asyncio
async def test_on_topic_update_known_and_unknown():
    svc = MonitorService([])
    topic = "topic/known"
    ms = MonitoredSensor("Dev", "S", 5)
    ms.notified = True
    old_last_seen = ms.last_seen
    svc._topics[topic] = ms

    # known topic
    res = await svc.on_topic_update(None, None, "val", topic, None)
    assert res is True
    assert ms.notified is False
    assert ms.last_seen >= old_last_seen

    # unknown topic
    res2 = await svc.on_topic_update(None, None, "val", "topic/unknown", None)
    assert res2 is False


@pytest.mark.asyncio
async def test_monitor_marks_overdue_and_stops(monkeypatch):
    monkeypatch.setattr(active_config, "log_level", logging.DEBUG)
    # Track sleep calls to allow first 30s sleep, then mock subsequent 1s sleeps
    original_sleep = asyncio.sleep
    sleep_count = 0

    async def mock_sleep(duration):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 1:
            # First call is the 30s startup delay - skip it
            await original_sleep(0)
        else:
            # Let the 1s loop sleep run briefly
            await original_sleep(0.05)

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    svc = MonitorService([])
    svc._started = 0
    topic = "topic/overdue"
    # make last_seen well in the past so it's overdue
    ms = MonitoredSensor("Dev", "S", 1, last_seen=time.time() - 100)
    svc._topics[topic] = ms

    # mark service as online by providing a Future
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    svc.online = fut

    task = asyncio.create_task(svc._monitor(FakeMqttClient()))

    # let the monitor run one iteration
    await original_sleep(0.2)

    # stop the service (this cancels the future and stops the loop)
    svc.online = False
    await task

    assert ms.notified is True


@pytest.mark.asyncio
async def test_publish_health_includes_modbus_and_mqtt_connectivity(monkeypatch, tmp_path):
    svc = MonitorService([])
    svc._health_file = tmp_path / "health.json"
    mqtt_client = FakeMqttClient(connected=True)

    class MockHealth:
        client_id = "127.0.0.1"
        close_count = 0
        connect_count = 1
        last_read_at = time.monotonic()

    class Modbus:
        connected = True

        def snapshot(self):
            return MockHealth()

    monkeypatch.setattr(ModbusClientFactory, "_clients", {("127.0.0.1", 502): Modbus()})

    await svc._publish_health(mqtt_client)

    assert svc._health_file.exists()
    content = svc._health_file.read_text(encoding="utf-8")
    assert '"modbus_connected": true' in content
    assert '"mqtt_connected": true' in content
    assert any(t[0] == "sigenergy2mqtt/health/state" for t in mqtt_client.published)
    assert any(t[0] == "sigenergy2mqtt/health/attributes" for t in mqtt_client.published)


@pytest.mark.asyncio
async def test_publish_health_considers_all_modbus_clients(monkeypatch, tmp_path):
    svc = MonitorService([])
    svc._health_file = tmp_path / "health.json"
    mqtt_client = FakeMqttClient(connected=True)

    class MockHealth1:
        client_id = "127.0.0.1"
        close_count = 0
        connect_count = 1
        last_read_at = time.monotonic()

    class MockHealth2:
        client_id = "192.168.0.2"
        close_count = 1
        connect_count = 0
        last_read_at = time.monotonic()

    class ConnectedModbus:
        connected = True

        def snapshot(self):
            return MockHealth1()

    class DisconnectedModbus:
        connected = False

        def snapshot(self):
            return MockHealth2()

    monkeypatch.setattr(
        ModbusClientFactory,
        "_clients",
        {
            ("127.0.0.1", 502): ConnectedModbus(),
            ("192.168.0.2", 502): DisconnectedModbus(),
        },
    )

    await svc._publish_health(mqtt_client)

    content = svc._health_file.read_text(encoding="utf-8")
    assert '"modbus_connected": false' in content
    assert '"mqtt_connected": true' in content
    assert any(t[0] == "sigenergy2mqtt/health/state" for t in mqtt_client.published)
    assert any(t[0] == "sigenergy2mqtt/health/attributes" for t in mqtt_client.published)
