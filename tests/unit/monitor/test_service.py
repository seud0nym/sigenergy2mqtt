import asyncio
import logging
import time
from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.common import service_health_registry
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.influx_base import InfluxBase
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.monitor.monitor_service import MonitorService
from sigenergy2mqtt.monitor.monitored_sensor import MonitoredSensor
from sigenergy2mqtt.pvoutput.service import Service as PvOutputService
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
        self._client_id = str("fake").encode("utf-8")

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


def test_subscribe_registers_topics_even_when_repeated_negative(monkeypatch):
    monkeypatch.setattr(active_config, "log_level", logging.DEBUG)
    monkeypatch.setattr(active_config, "repeated_state_publish_interval", -1)
    s = DummyReadable(name="sensor1", scan_interval=5, state_topic="topic/1", publishable=True)
    d = DummyDevice("Device1", {"s1": s})
    handler = FakeMqttHandler()
    svc = MonitorService([d])

    svc.subscribe(None, handler)

    assert (None, "topic/1", svc.on_topic_update) in handler.registered
    assert "topic/1" in svc._topics


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

    class MockMqttHealth:
        connected = True
        last_message_at = time.monotonic()
        last_publish_ack_at = time.monotonic()
        connect_count = 1
        disconnect_count = 0

    monkeypatch.setattr("sigenergy2mqtt.monitor.monitor_service.mqtt_health_registry.snapshot", lambda: {"fake": MockMqttHealth()})

    await svc._publish_health(mqtt_client, is_docker_env=False)

    assert svc._health_file.exists()
    content = svc._health_file.read_text(encoding="utf-8")
    assert '"modbus_connected": true' in content
    assert '"mqtt_connected": true' in content
    assert any(t[0] == "sigenergy2mqtt/health/state" for t in mqtt_client.published)
    assert any(t[0] == "sigenergy2mqtt/health/attributes" for t in mqtt_client.published)


@pytest.mark.asyncio
async def test_pvoutput_upload_failure_marks_health_unhealthy(monkeypatch):
    monkeypatch.setattr(active_config.pvoutput, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.pvoutput, "health_monitoring", True, raising=False)
    service_health_registry.set_health("pvoutput", True)
    monkeypatch.setattr(active_config.pvoutput, "testing", False, raising=False)

    class FakeResponse:
        status_code = 500
        reason = "Internal Server Error"
        text = "failed"
        headers = {
            "X-Rate-Limit-Limit": "60",
            "X-Rate-Limit-Remaining": "59",
            "X-Rate-Limit-Reset": str(int(time.time()) + 60),
        }

        def raise_for_status(self):
            raise Exception("boom")

    monkeypatch.setattr("sigenergy2mqtt.pvoutput.service.requests.post", lambda *args, **kwargs: FakeResponse())

    service = PvOutputService("pvoutput", "pvoutput", "PVOutput", logging.getLogger("test"))
    uploaded = await service.upload_payload("https://example.test", {"d": "20240101"})

    assert uploaded is False
    assert service_health_registry.get_health("pvoutput") is False


@pytest.mark.asyncio
async def test_influxdb_write_failure_marks_health_unhealthy(monkeypatch):
    monkeypatch.setattr(active_config.influxdb, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.influxdb, "health_monitoring", True, raising=False)
    service_health_registry.set_health("influxdb_0", True)

    service = InfluxBase("influx", 0, "unique", "manufacturer", "model", logging.getLogger("test"))
    loop = asyncio.get_running_loop()
    service.online = loop.create_future()
    service._writer_type = "v1_http"
    service._write_url = "https://example.test/write"
    service._write_auth = None

    class FakeResponse:
        status_code = 500
        text = "failed"

    monkeypatch.setattr(service._session, "post", lambda *args, **kwargs: FakeResponse())

    result = await service.execute_write(b"state value=1")

    assert result is False
    assert service_health_registry.get_health("influxdb_0") is False


@pytest.mark.asyncio
async def test_multi_plant_influxdb_health_isolation(monkeypatch):
    monkeypatch.setattr(active_config.influxdb, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.influxdb, "health_monitoring", True, raising=False)
    monkeypatch.setattr(active_config, "modbus", [MagicMock(host="host1"), MagicMock(host="host2")])
    service_health_registry.clear()

    plant0_service = InfluxBase("influx0", 0, "unique0", "manufacturer", "model", logging.getLogger("test0"))
    plant1_service = InfluxBase("influx1", 1, "unique1", "manufacturer", "model", logging.getLogger("test1"))

    loop = asyncio.get_running_loop()
    plant0_service.online = loop.create_future()
    plant1_service.online = loop.create_future()

    plant0_service._writer_type = "v1_http"
    plant0_service._write_url = "https://example.test/write"
    plant1_service._writer_type = "v1_http"
    plant1_service._write_url = "https://example.test/write"

    # Plant 0 fails write
    monkeypatch.setattr(plant0_service._session, "post", lambda *args, **kwargs: MagicMock(status_code=500, text="error"))
    res0 = await plant0_service.execute_write(b"state value=1")
    assert res0 is False
    assert service_health_registry.get_health("influxdb_0") is False

    # Plant 1 succeeds write
    monkeypatch.setattr(plant1_service._session, "post", lambda *args, **kwargs: MagicMock(status_code=204))
    res1 = await plant1_service.execute_write(b"state value=1")
    assert res1 is True
    assert service_health_registry.get_health("influxdb_1") is True

    # Plant 0 should STILL be unhealthy despite plant 1 succeeding
    assert service_health_registry.get_health("influxdb_0") is False

    monitor = MonitorService([])
    healthy, contributors = monitor._check_service_health()
    assert healthy is False
    assert contributors == {"influxdb_0": False, "influxdb_1": True}


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

    class MockMqttHealth:
        connected = True
        last_message_at = time.monotonic()
        last_publish_ack_at = time.monotonic()
        connect_count = 1
        disconnect_count = 0

    monkeypatch.setattr("sigenergy2mqtt.monitor.monitor_service.mqtt_health_registry.snapshot", lambda: {"fake": MockMqttHealth()})

    await svc._publish_health(mqtt_client, is_docker_env=False)

    content = svc._health_file.read_text(encoding="utf-8")
    assert '"modbus_connected": false' in content
    assert '"mqtt_connected": true' in content
    assert any(t[0] == "sigenergy2mqtt/health/state" for t in mqtt_client.published)
    assert any(t[0] == "sigenergy2mqtt/health/attributes" for t in mqtt_client.published)


@pytest.mark.asyncio
async def test_influxdb_init_failure_registers_unhealthy(monkeypatch):
    """async_init must write health=False when the connection probe raises.

    Without this the ServiceHealthRegistry has no entry for the key and
    get_health(key, default=True) returns True, making a totally broken
    InfluxDB service look healthy and preventing the recovery restart.
    """
    monkeypatch.setattr(active_config.influxdb, "enabled", True, raising=False)
    monkeypatch.setattr(active_config.influxdb, "health_monitoring", True, raising=False)
    monkeypatch.setattr(active_config, "modbus", [MagicMock(host="host0")], raising=False)
    service_health_registry.clear()

    service = InfluxBase("influx", 0, "unique", "manufacturer", "model", logging.getLogger("test"))

    # Make _init_connection raise unconditionally (simulates a completely
    # unreachable InfluxDB host).
    monkeypatch.setattr(service, "_init_connection", lambda: (_ for _ in ()).throw(RuntimeError("connection refused")))

    result = await service.async_init()

    assert result is False
    # The key must be present and explicitly False — not missing (which would
    # cause get_health to return the True default and hide the outage).
    assert service_health_registry.get_health("influxdb_0") is False

    # Confirm the monitor service sees the plant as unhealthy.
    monitor = MonitorService([])
    healthy, contributors = monitor._check_service_health()
    assert healthy is False
    assert contributors.get("influxdb_0") is False

