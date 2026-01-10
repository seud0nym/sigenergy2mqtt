import asyncio
import time

import pytest

from sigenergy2mqtt.monitor.monitor_service import MonitorService
from sigenergy2mqtt.monitor.monitored_sensor import MonitoredSensor
from sigenergy2mqtt.sensors.base import ReadableSensorMixin


class DummyReadable(ReadableSensorMixin):
    def __init__(self, *, name: str, scan_interval: int, state_topic: str, publishable: bool = True):
        # Do not call base class __init__ to avoid heavy Sensor setup
        self.name = name
        self.scan_interval = scan_interval
        self["state_topic"] = state_topic
        self._publishable = publishable


class DummyDevice:
    def __init__(self, name: str, sensors: dict):
        self.name = name
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
async def test_monitor_marks_overdue_and_stops():
    svc = MonitorService([])
    topic = "topic/overdue"
    # make last_seen well in the past so it's overdue
    ms = MonitoredSensor("Dev", "S", 1, last_seen=time.time() - 100)
    svc._topics[topic] = ms

    # mark service as online by providing a Future
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    svc.online = fut

    task = asyncio.create_task(svc._monitor(None, None))

    # let the monitor run one iteration
    await asyncio.sleep(0.2)

    # stop the service (this cancels the future and stops the loop)
    svc.online = False
    await task

    assert ms.notified is True
