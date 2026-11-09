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
    """MQTT connected with a pending publish that is overdue."""
    now = time.monotonic()
    health = MqttClientHealth(
        client_id="other_client",
        connected=True,
        last_publish_at=now - 10000,
        last_publish_ack_at=now - 20000,
        oldest_pending_publish_at=now - 10000,
        connect_count=1,
    )
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    assert "connected but no publish acknowledgement received" in caplog.text
    assert result[0] is False


def test_check_mqtt_legacy_fallback_when_attribute_absent(monkeypatch, caplog):
    """When oldest_pending_publish_at attribute is absent entirely, fall back to last_publish_at comparison."""
    class LegacyHealthMock:
        connected = True
        disconnect_count = 0
        connect_count = 1
        last_publish_at = time.monotonic() - 10000
        last_publish_ack_at = time.monotonic() - 20000

    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"legacy_client": LegacyHealthMock()}, raising=False)

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
        health = MqttClientHealth(
            client_id="other_client",
            connected=True,
            last_publish_at=time.monotonic(),
            last_publish_ack_at=time.monotonic(),
            connect_count=3,
        )
        monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

        svc = MonitorService([])
        result = svc._check_mqtt(FakeMqttClient())

        assert "healthy (connected 3x" in caplog.text
        assert result[0] is True


def test_check_mqtt_inbound_message_after_ack_does_not_degrade(monkeypatch, caplog):
    """Regression: inbound message (e.g. HA offline/online status) received after the
    last publish was acknowledged must NOT trigger the 'no publish acknowledgement'
    warning.  Before the fix, last_message_at (inbound) was used as the 'sent-at'
    reference, so receiving an HA status topic update advanced the window and made
    the health check falsely report the connection as degraded.
    """
    now = time.monotonic()
    health = MqttClientHealth(
        client_id="other_client",
        connected=True,
        # Simulates receiving an HA status message 55 s ago (after the last publish ack).
        last_message_at=now - 55,
        # The last publish was acknowledged 60 s ago — before the inbound message.
        last_publish_at=now - 70,
        last_publish_ack_at=now - 60,
        connect_count=1,
    )
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    # The publish was acknowledged (last_publish_ack_at > last_publish_at is False here, so
    # the pending-ack check should NOT fire).  Wait — last_publish_ack_at=now-60 and
    # last_publish_at=now-70, so ack IS newer than publish: no warning expected.
    assert "connected but no publish acknowledgement received" not in caplog.text
    assert result[0] is True


def test_check_mqtt_repeated_publishes_do_not_postpone_timeout(monkeypatch, caplog):
    """If an earlier publish is unacknowledged, newer publishes must not postpone the timeout."""
    now = time.monotonic()
    health = MqttClientHealth(
        client_id="other_client",
        connected=True,
        # A newer publish happened recently (10s ago, well within the 30s interval):
        last_publish_at=now - 10,
        last_publish_ack_at=now - 200,
        # But the oldest unacknowledged publish happened 100s ago (> 30s timeout):
        oldest_pending_publish_at=now - 100,
        connect_count=1,
    )
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    assert "connected but no publish acknowledgement received for 100" in caplog.text
    assert result[0] is False


def test_check_mqtt_no_fallback_when_oldest_pending_is_none(monkeypatch, caplog):
    """When oldest_pending_publish_at is explicitly None (e.g. ACK arrived before publish returned),
    the monitor must NOT use the timestamp fallback even if last_publish_ack_at < last_publish_at.
    """
    now = time.monotonic()
    health = MqttClientHealth(
        client_id="other_client",
        connected=True,
        # ACK arrived before publish() returned:
        last_publish_ack_at=now - 100.1,
        last_publish_at=now - 100.0,
        # But all messages were acknowledged, so oldest_pending_publish_at is explicitly None:
        oldest_pending_publish_at=None,
        connect_count=1,
    )
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"other_client": health}, raising=False)

    svc = MonitorService([])
    result = svc._check_mqtt(FakeMqttClient())

    assert "connected but no publish acknowledgement received" not in caplog.text
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


def test_check_modbus_disconnected_reports_observed_disconnects(monkeypatch, caplog):
    from sigenergy2mqtt.modbus.client import ModbusClientHealth

    fake_client = FakeModbusClient()
    fake_client.connected = False
    fake_client.snapshot = MagicMock(return_value=ModbusClientHealth("modbus://h:502", disconnect_count=2, close_count=0))
    monkeypatch.setattr("sigenergy2mqtt.modbus.ModbusClientFactory._clients", {"c1": fake_client}, raising=False)

    assert MonitorService([])._check_modbus()[0] is False
    assert "disconnected (2x total)" in caplog.text


def test_check_modbus_disconnected_during_outage_is_debug(monkeypatch, caplog):
    import logging

    from sigenergy2mqtt.common.outage import outage_tracker

    fake_client = FakeModbusClient()
    fake_client.connected = False
    fake_client.outage = outage_tracker("modbus://h:502")
    fake_client.outage.failure("unreachable")
    monkeypatch.setattr("sigenergy2mqtt.modbus.ModbusClientFactory._clients", {"c1": fake_client}, raising=False)

    svc = MonitorService([])
    with caplog.at_level(logging.DEBUG):
        assert svc._check_modbus()[0] is False
    records = [r for r in caplog.records if "Modbus connection" in r.getMessage()]
    assert records and all(r.levelno == logging.DEBUG for r in records)


def test_check_mqtt_disconnected_during_outage_is_debug(monkeypatch, caplog):
    import logging

    from sigenergy2mqtt.common.outage import outage_tracker

    outage_tracker("mqtt://broker:1883").failure("Keep alive timeout")
    health = MqttClientHealth(client_id="test_client", connected=False, connect_count=1, disconnect_count=1)
    monkeypatch.setattr("sigenergy2mqtt.mqtt.mqtt_health_registry.snapshot", lambda: {"test_client": health}, raising=False)

    svc = MonitorService([])
    with caplog.at_level(logging.DEBUG):
        assert svc._check_mqtt(FakeMqttClient())[0] is False
    records = [r for r in caplog.records if "disconnected (1x total)" in r.getMessage()]
    assert records and all(r.levelno == logging.DEBUG for r in records)


@pytest.mark.asyncio
async def test_overdue_topics_during_outage_are_debug(caplog):
    import logging

    from sigenergy2mqtt.common.outage import outage_tracker

    svc = MonitorService([])
    svc._monitor_topic_updates = True
    svc._started = time.monotonic() - 1000
    sensor = MagicMock(is_overdue=True, notified=False, overdue=120, scan_interval=5)
    sensor.name = "Plant Power"
    svc._topics = {"t/1": sensor}

    outage_tracker("modbus://h:502").failure("unreachable")
    with caplog.at_level(logging.DEBUG):
        assert await svc._check_topic_health() == 1
    records = [r for r in caplog.records if "has not been seen" in r.getMessage()]
    assert records and all(r.levelno == logging.DEBUG for r in records)
