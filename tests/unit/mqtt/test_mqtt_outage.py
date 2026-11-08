"""Outage tracking for MQTT broker connections."""

import asyncio
import logging
from unittest.mock import MagicMock

import pytest
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.mqtt.client import MqttClient, _is_failure, on_connect, on_disconnect
from sigenergy2mqtt.mqtt.handler import MqttHandler


def _reason(name: str) -> ReasonCode:
    return ReasonCode(PacketTypes.DISCONNECT, name)


@pytest.fixture
def loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _client(client_id: str, loop) -> tuple[MqttClient, MqttHandler]:
    handler = MqttHandler(client_id, MagicMock(), loop)
    handler.connected = True
    client = MqttClient(client_id, handler)
    client.host = "broker"
    client.port = 1883
    return client, handler


class TestIsFailure:
    def test_reason_codes(self):
        assert _is_failure(_reason("Unspecified error")) is True
        assert _is_failure(_reason("Keep alive timeout")) is True
        assert _is_failure(_reason("Normal disconnection")) is False

    def test_ints(self):
        assert _is_failure(0) is False
        assert _is_failure(7) is True
        assert _is_failure(object()) is False


class TestMqttOutage:
    def test_outage_property_is_shared_per_broker(self, loop):
        a, _ = _client("a", loop)
        b, _ = _client("b", loop)
        assert a.outage is b.outage is outage_tracker("mqtt://broker:1883")

    def test_disconnects_from_several_clients_log_one_outage(self, loop, caplog):
        clients = [_client(cid, loop) for cid in ("a", "b", "c")]
        with caplog.at_level(logging.DEBUG):
            for client, handler in clients:
                on_disconnect(client, handler, None, _reason("Unspecified error"), None)
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert [r.getMessage() for r in warnings] == ["mqtt://broker:1883 outage started: Unspecified error"]
        assert not [r for r in caplog.records if r.levelno == logging.INFO and "Disconnected from" in r.getMessage()]
        assert all(not handler.connected for _, handler in clients)

    def test_outage_ends_when_every_client_reconnects(self, loop, caplog):
        clients = [_client(cid, loop) for cid in ("a", "b")]
        for client, handler in clients:
            on_disconnect(client, handler, None, _reason("Keep alive timeout"), None)
        tracker = outage_tracker("mqtt://broker:1883")
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            on_connect(clients[0][0], clients[0][1], None, 0, None)
            assert tracker.active
            on_connect(clients[1][0], clients[1][1], None, 0, None)
        assert not tracker.active
        ended = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO and "outage ended" in r.getMessage()]
        assert ended == ["mqtt://broker:1883 outage ended after 0s (1 similar messages suppressed)"]

    def test_reconnected_message_demoted_for_tracked_clients(self, loop, caplog):
        client, handler = _client("a", loop)
        handler._topics = {"t": MagicMock()}
        on_disconnect(client, handler, None, _reason("Unspecified error"), None)
        client.subscribe = MagicMock(return_value=(0, 1))
        client.unsubscribe = MagicMock(return_value=(0, 1))
        with caplog.at_level(logging.DEBUG):
            on_connect(client, handler, None, 0, None)
        reconnected = [r for r in caplog.records if "Reconnected to" in r.getMessage()]
        assert reconnected and all(r.levelno == logging.DEBUG for r in reconnected)

    def test_clean_disconnect_is_logged_at_info_without_outage(self, loop, caplog):
        client, handler = _client("a", loop)
        with caplog.at_level(logging.INFO):
            on_disconnect(client, handler, None, _reason("Normal disconnection"), None)
        assert not outage_tracker("mqtt://broker:1883").active
        assert any(r.levelno == logging.INFO and "Disconnected from mqtt://broker:1883" in r.getMessage() for r in caplog.records)

    def test_untracked_client_logs_disconnect_at_info(self, loop, caplog):
        handler = MqttHandler("x", MagicMock(), loop)
        mock_client = MagicMock()
        mock_client.host = "broker"
        mock_client.port = 1883
        with caplog.at_level(logging.INFO):
            on_disconnect(mock_client, handler, None, _reason("Unspecified error"), None)
        assert any("Disconnected from" in r.getMessage() and r.levelno == logging.INFO for r in caplog.records)
        assert not outage_tracker("mqtt://broker:1883").active
