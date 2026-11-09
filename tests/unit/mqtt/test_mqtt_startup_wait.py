"""Waiting for an unreachable MQTT broker at startup."""

import logging
from unittest.mock import MagicMock, patch

import pytest

import sigenergy2mqtt.mqtt as mqtt_module
from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttConnectAborted, _connect_with_retry


@pytest.fixture(autouse=True)
def broker(monkeypatch):
    monkeypatch.setattr(active_config.mqtt, "broker", "10.0.0.2")
    monkeypatch.setattr(active_config.mqtt, "port", 1883)
    monkeypatch.setattr(active_config.mqtt, "retry_delay", 2)
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(mqtt_module, "sleep", fake_sleep)
    mqtt_module.reset_mqtt_reconnection_interrupt()
    return sleeps


def _client(failures: int):
    client = MagicMock()
    client.connect.side_effect = [ConnectionRefusedError(111, "Connection refused")] * failures + [0]
    return client


def _tracker():
    return outage_tracker("mqtt://10.0.0.2:1883")


def _errors(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.asyncio
async def test_waits_until_broker_reachable(caplog, broker):
    client = _client(failures=5)
    with caplog.at_level(logging.DEBUG):
        await _connect_with_retry(client, "c1", max_attempts=None)
    assert client.connect.call_count == 6
    client.loop_start.assert_called_once()
    assert len(broker) == 5 * 2  # 1s sleeps between attempts
    assert _errors(caplog) == ["mqtt://10.0.0.2:1883 outage started: ConnectionRefusedError(111, 'Connection refused')"]
    assert any(r.levelno == logging.INFO and "outage ended" in r.getMessage() for r in caplog.records)
    assert not _tracker().active


@pytest.mark.asyncio
async def test_several_waiting_clients_report_one_outage(caplog):
    a, b = _client(failures=2), _client(failures=3)
    with caplog.at_level(logging.DEBUG):
        a.connect.side_effect = [ConnectionRefusedError(111, "x")] * 2 + [0]
        b.connect.side_effect = [ConnectionRefusedError(111, "x")] * 3 + [0]
        # Interleave the failures of both clients before either recovers
        tracker = _tracker()
        tracker.failure(ConnectionRefusedError(111, "x"), member="b")
        await _connect_with_retry(a, "a", max_attempts=None)
        assert tracker.active  # still waiting for b
        await _connect_with_retry(b, "b", max_attempts=None)
    assert not tracker.active
    assert len([m for m in _errors(caplog) if "outage started" in m]) == 1
    assert len([r for r in caplog.records if "outage ended" in r.getMessage()]) == 1


@pytest.mark.asyncio
async def test_bounded_attempts_give_up_and_stop_counting(caplog):
    client = _client(failures=10)
    with caplog.at_level(logging.DEBUG), pytest.raises(ConnectionRefusedError):
        await _connect_with_retry(client, "persistence", max_attempts=3)
    assert client.connect.call_count == 3
    tracker = _tracker()
    assert tracker.active
    # Another client connecting ends the outage even though "persistence" never recovered
    assert tracker.success(member="Monitor") is True
    assert not [r for r in caplog.records if r.levelno == logging.CRITICAL]


@pytest.mark.asyncio
async def test_stopping_abandons_the_wait():
    client = _client(failures=100)
    calls = {"n": 0}

    def stopping():
        calls["n"] += 1
        return calls["n"] > 3

    with pytest.raises(MqttConnectAborted):
        await _connect_with_retry(client, "c1", max_attempts=None, stopping=stopping)
    tracker = _tracker()
    assert tracker.active
    assert tracker.success(member="other") is True  # the aborted client no longer holds the outage open


@pytest.mark.asyncio
async def test_signal_interrupt_still_raises_keyboard_interrupt():
    client = _client(failures=100)
    mqtt_module.interrupt_mqtt_reconnection()
    try:
        with pytest.raises(KeyboardInterrupt):
            await _connect_with_retry(client, "c1", max_attempts=None)
    finally:
        mqtt_module.reset_mqtt_reconnection_interrupt()


@pytest.mark.asyncio
async def test_mqtt_setup_defaults_to_bounded_attempts():
    with patch.object(mqtt_module, "_connect_with_retry") as connect:
        connect.return_value = None
        await mqtt_module.mqtt_setup("cid", None, MagicMock())
    assert connect.call_args.kwargs == {"max_attempts": 3, "stopping": None}


@pytest.mark.asyncio
async def test_teardown_and_failed_setup_unregister_from_health_registry():
    from unittest.mock import AsyncMock

    from sigenergy2mqtt.mqtt import mqtt_health_registry, mqtt_setup, mqtt_teardown

    with patch.object(mqtt_module, "_connect_with_retry", AsyncMock(side_effect=ConnectionRefusedError(111, "x"))):
        with pytest.raises(ConnectionRefusedError):
            await mqtt_setup("gave_up", None, MagicMock())
    assert "gave_up" not in mqtt_health_registry.snapshot()

    with patch.object(mqtt_module, "_connect_with_retry", AsyncMock()):
        client, handler = await mqtt_setup("closed", None, MagicMock())
    assert "closed" in mqtt_health_registry.snapshot()
    with patch.object(client, "loop_stop"), patch.object(client, "disconnect"), patch.object(handler, "close", AsyncMock()):
        await mqtt_teardown(client, handler)
    assert "closed" not in mqtt_health_registry.snapshot()
