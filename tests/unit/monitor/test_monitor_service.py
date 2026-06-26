import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.monitor.monitor_service import MonitorService
from sigenergy2mqtt.mqtt.registry import MqttClientHealth

# Helper fake MQTT client
class FakeMqttClient:
    def __init__(self, client_id: bytes = b'test_client'):
        self._client_id = client_id
        self.published = []
        self.publish = MagicMock(side_effect=self._publish)

    def _publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        info = MagicMock()
        info.rc = 0
        info.wait_for_publish = MagicMock()
        return info

# Helper fake Modbus client
class FakeModbusClient:
    def __init__(self, client_id='modbus1'):
        self.client_id = client_id
        self.connected = True
        self.last_read_at = time.monotonic()
        self.connect_count = 1
        self.close_count = 0
        self.snapshot = MagicMock(return_value=self)

# Fake sensor for subscribe tests
class DummySensor:
    def __init__(self, name, topic, scan_interval=10, publishable=True):
        self._log_identity = name
        self.scan_interval = scan_interval
        self.state_topic = topic
        self.publishable = publishable
        self.last_seen = None
        self.notified = False

    @property
    def log_identity(self):
        return self._log_identity

# Fake device containing sensors
class DummyDevice:
    def __init__(self, sensors):
        self._log_identity = "Device1"
        self.sensors = sensors

    @property
    def log_identity(self):
        return self._log_identity

    def get_all_sensors(self):
        return {s.state_topic: s for s in self.sensors}

@pytest.fixture
def fake_mqtt_client():
    return FakeMqttClient()

def test_check_modbus_no_clients(monkeypatch):
    monkeypatch.setattr('sigenergy2mqtt.modbus.ModbusClientFactory._clients', {}, raising=False)
    svc = MonitorService([])
    assert svc._check_modbus() is False

def test_check_modbus_healthy(monkeypatch):
    fake_client = FakeModbusClient()
    monkeypatch.setattr('sigenergy2mqtt.modbus.ModbusClientFactory._clients', {'c1': fake_client}, raising=False)
    svc = MonitorService([])
    assert svc._check_modbus() is True

def test_check_mqtt_no_snapshot(monkeypatch):
    monkeypatch.setattr('sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot', lambda: {}, raising=False)
    svc = MonitorService([])
    fake_client = FakeMqttClient()
    assert svc._check_mqtt(fake_client) is False

def test_check_mqtt_healthy(monkeypatch, fake_mqtt_client):
    health = MqttClientHealth(client_id='test_client', connected=True, last_publish_ack_at=time.monotonic(), last_message_at=time.monotonic(), connect_count=1)
    monkeypatch.setattr('sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot', lambda: {'test_client': health}, raising=False)
    svc = MonitorService([])
    assert svc._check_mqtt(fake_mqtt_client) is True

def test_on_topic_update(monkeypatch):
    sensor = DummySensor(name='temp', topic='home/temp')
    device = DummyDevice([sensor])
    svc = MonitorService([device])
    # Populate topics dict as subscribe would
    from sigenergy2mqtt.monitor.monitored_sensor import MonitoredSensor
    svc._topics['home/temp'] = MonitoredSensor('Device1', 'temp', 10)
    result = asyncio.run(svc.on_topic_update(None, FakeMqttClient(), '23', 'home/temp', None))
    assert result is True
    ms = svc._topics['home/temp']
    assert ms.last_seen is not None
    assert ms.notified is False

def test_clean_removes_file_and_topics(monkeypatch, tmp_path):
    svc = MonitorService([])
    temp_file = tmp_path / 'health.json'
    svc._health_file = Path(str(temp_file))
    temp_file.write_text(json.dumps({"status": "healthy"}), encoding='utf-8')
    mock_client = MagicMock()
    mock_client.publish.return_value = MagicMock(rc=0)
    mock_handler = MagicMock()
    async def fake_setup(*args, **kwargs):
        return mock_client, mock_handler
    monkeypatch.setattr('sigenergy2mqtt.monitor.monitor_service.mqtt_setup', fake_setup)
    async def run_clean():
        await MonitorService.clean()
    asyncio.run(run_clean())
    assert not temp_file.exists()
    assert mock_client.publish.call_count == 2

def test_publish_health_writes_file_and_mqtt(monkeypatch, fake_mqtt_client, tmp_path):
    svc = MonitorService([])
    health_path = tmp_path / 'health.json'
    svc._health_file = health_path
    monkeypatch.setattr(svc, '_check_modbus', lambda: True)
    monkeypatch.setattr(svc, '_check_mqtt', lambda client: True)
    monkeypatch.setattr(svc, '_check_topic_health', AsyncMock(return_value=0))
    asyncio.run(svc._publish_health(fake_mqtt_client))
    data = json.loads(health_path.read_text())
    assert data['status'] == 'healthy'
    published_topics = [call[0][0] for call in fake_mqtt_client.publish.call_args_list]
    assert svc._health_state_topic in published_topics
    assert svc._health_attributes_topic in published_topics
