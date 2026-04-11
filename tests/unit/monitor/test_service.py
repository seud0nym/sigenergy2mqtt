import asyncio
import time

import pytest

from sigenergy2mqtt.monitor.monitor_service import MonitorService
from sigenergy2mqtt.monitor.monitored_sensor import MonitoredSensor
from sigenergy2mqtt.sensors.base import ReadableSensorMixin
from sigenergy2mqtt.config import active_config


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


def test_subscribe_registers_topics():
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
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    s = DummyReadable(name="sensor1", scan_interval=5, state_topic="topic/1", publishable=True)
    d = DummyDevice("Device1", {"s1": s})
    handler = FakeMqttHandler()
    svc = MonitorService([d])

    svc.subscribe(None, handler)

    assert handler.registered == []
    assert svc._topics == {}


def test_schedule_returns_no_tasks_when_repeated_negative(monkeypatch):
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    svc = MonitorService([])

    assert svc.schedule(None, None) == []


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
    topic = "topic/overdue"
    # make last_seen well in the past so it's overdue
    ms = MonitoredSensor("Dev", "S", 1, last_seen=time.time() - 100)
    svc._topics[topic] = ms

    # mark service as online by providing a Future
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    svc.online = fut

    task = asyncio.create_task(svc._monitor(None, None))

    # let the monitor run one iteration
    await original_sleep(0.2)

    # stop the service (this cancels the future and stops the loop)
    svc.online = False
    await task

    assert ms.notified is True
