import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.monitor.service import MonitorService
from sigenergy2mqtt.mqtt.registry import MqttClientHealth


class FakeMqttClient:
    def __init__(self, client_id: bytes = b"test_client"):
        self._client_id = client_id
        self.published = []
        self.publish = MagicMock(side_effect=self._publish)

    def _publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        info = MagicMock()
        info.rc = 0
        info.wait_for_publish = MagicMock()
        return info


class FakeModbusClient:
    def __init__(self, client_id="modbus1"):
        self.client_id = client_id
        self.connected = True
        self.last_read_at = time.monotonic()
        self.connect_count = 1
        self.close_count = 0
        self.snapshot = MagicMock(return_value=self)


@pytest.mark.asyncio
async def test_monitor_cancelled_error(caplog):
    """Handle asyncio.CancelledError during initial sleep."""
    import logging

    with _swap_active_config(Config()) as cfg:
        cfg.diagnostics.log_level = logging.DEBUG
        caplog.set_level(logging.DEBUG)
        svc = MonitorService([])

        # We want to mock asyncio.sleep to raise CancelledError
        with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
            await svc._monitor(FakeMqttClient())

        assert "sleep interrupted" in caplog.text


def test_check_modbus_no_reads(monkeypatch, caplog):
    """Modbus connected but no reads."""
    fake_client = FakeModbusClient()
    # Set last_read_at way in the past so it triggers "no reads for X s"
    fake_client.last_read_at = time.monotonic() - 10000
    monkeypatch.setattr("sigenergy2mqtt.modbus.ModbusClientFactory._clients", {"c1": fake_client}, raising=False)

    svc = MonitorService([])
    result = svc._check_modbus()

    assert "connected but no reads for" in caplog.text
    assert result[0] is False


def test_check_mqtt_disconnected(monkeypatch, caplog):
    """MQTT Client disconnected."""
    health = MqttClientHealth(client_id="test_client", connected=False, last_publish_ack_at=time.monotonic(), last_message_at=time.monotonic(), connect_count=1, disconnect_count=5)
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"test_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    assert "disconnected (5x total)" in caplog.text
    assert result[0] is False


def test_check_mqtt_no_ack_no_msg(monkeypatch, caplog):
    """MQTT connected but no ack and/or no msg."""
    health = MqttClientHealth(client_id="other_client", connected=True, last_publish_ack_at=time.monotonic() - 10000, last_message_at=time.monotonic() - 10000, connect_count=1)
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    assert "connected but no publish acknowledgement received" in caplog.text
    assert result[0] is False


def test_check_mqtt_healthy_ack_msg(monkeypatch, caplog):
    """MQTT healthy branch."""
    import logging

    with _swap_active_config(Config()) as cfg:
        cfg.diagnostics.log_level = logging.DEBUG
        caplog.set_level(logging.DEBUG)
        health = MqttClientHealth(client_id="other_client", connected=True, last_publish_ack_at=time.monotonic(), last_message_at=time.monotonic(), connect_count=3)
        monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

        svc = MonitorService([])
        result = svc._check_mqtt(FakeMqttClient())

        assert "healthy (connected 3x" in caplog.text
        assert result[0] is True


@pytest.mark.asyncio
async def test_on_ha_state_change():
    """on_ha_state_change returns True."""
    svc = MonitorService([])
    result = await svc.on_ha_state_change(None, FakeMqttClient(), "payload", "source", None)
    assert result is True


@pytest.mark.asyncio
async def test_clean_oserror_tmp_dir(monkeypatch, caplog):
    """OSError when deleting from /tmp."""
    mock_path = MagicMock()
    mock_path.unlink.side_effect = OSError("Permission denied")

    mock_tmp = MagicMock()
    mock_tmp.rglob.return_value = [mock_path]

    # We also mock mqtt_setup to avoid real connection attempts during clean
    monkeypatch.setattr("sigenergy2mqtt.monitor.service.mqtt_setup", AsyncMock(return_value=(MagicMock(), MagicMock())))
    monkeypatch.setattr("sigenergy2mqtt.monitor.service.mqtt_teardown", AsyncMock())

    await MonitorService.clean()

    assert "Failed to clean topic" in caplog.text
