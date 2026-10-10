from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.diagnostics.collectors import DiagnosticsCollectors
from sigenergy2mqtt.metrics import Metrics, MetricsService
from sigenergy2mqtt.mqtt.client import MqttClient, on_connect, on_disconnect


@pytest.fixture
async def clean_metrics():
    await Metrics.reset()
    await Metrics.drain()
    yield
    await Metrics.reset()
    await Metrics.drain()


@pytest.mark.asyncio
async def test_connection_outcomes_and_exposure(clean_metrics):
    handler = MagicMock()
    client = MqttClient("metrics-test", handler)
    # A success, a reconnect and a transport failure take 100, 300 and 200 ms.
    with patch.object(mqtt.Client, "reconnect", return_value=mqtt.MQTT_ERR_SUCCESS), patch(
        "sigenergy2mqtt.mqtt.client.time.monotonic", side_effect=[1.0, 1.1, 2.0, 2.3, 3.0, 3.2]
    ):
        client.reconnect()
        on_connect(client, handler, None, 0, None)
        on_disconnect(client, handler, None, 0, None)
        client.reconnect()
        on_connect(client, handler, None, 0, None)
        with patch.object(mqtt.Client, "reconnect", side_effect=OSError("unreachable")):
            with pytest.raises(OSError):
                client.reconnect()
    await Metrics.drain()
    values = {
        "connection_attempts": 3,
        "connections": 2,
        "connection_errors": 1,
        "connection_max": 300,
        "connection_mean": 200,
        "connection_min": 100,
        "reconnections": 1,
    }
    service = MetricsService(ProtocolVersion.N_A)
    for suffix, expected in values.items():
        assert getattr(Metrics, f"sigenergy2mqtt_mqtt_{suffix}") == pytest.approx(expected)
        sensor = next(s for s in service.read_sensors.values() if s._attribute == f"sigenergy2mqtt_mqtt_{suffix}")
        await sensor._update_internal_state()
        assert sensor.latest_raw_state == pytest.approx(expected)
        assert sensor.state_topic == f"sigenergy2mqtt/metrics/mqtt_{suffix}"
    diagnostics = await DiagnosticsCollectors._diagnostics_collect_mqtt_metrics()
    assert diagnostics["Connection Attempts"] == 3
    assert diagnostics["Successful Connections"] == 2
    assert diagnostics["Connection Errors"] == 1
    assert diagnostics["Reconnections"] == 1
    for label, expected in [("Max", 300), ("Mean", 200), ("Min", 100)]:
        assert diagnostics[f"Connection {label}_ms"] == pytest.approx(expected)


@pytest.mark.asyncio
async def test_refusal_counts_once_and_reset(clean_metrics):
    client = MqttClient("metrics-test", MagicMock())
    with patch.object(mqtt.Client, "reconnect", return_value=mqtt.MQTT_ERR_SUCCESS):
        client.reconnect()
    with patch("sigenergy2mqtt.mqtt.client._thread.interrupt_main"):
        on_connect(client, MagicMock(), None, 5, None)
    on_disconnect(client, MagicMock(), None, 5, None)
    await Metrics.drain()
    assert Metrics.sigenergy2mqtt_mqtt_connection_attempts == 1
    assert Metrics.sigenergy2mqtt_mqtt_connection_errors == 1
    assert Metrics.sigenergy2mqtt_mqtt_connections == 0
    await Metrics.reset()
    await Metrics.drain()
    diagnostics = await DiagnosticsCollectors._diagnostics_collect_mqtt_metrics()
    assert diagnostics["Connection Attempts"] == 0
    assert diagnostics["Connection Min_ms"] == 0.0
    assert Metrics.sigenergy2mqtt_mqtt_connection_min == float("inf")


class BrokerSocket:
    """Socket-only fake delivering a real MQTT 3.1.1 CONNACK, then EOF."""

    def __init__(self, reason_code=0):
        self.incoming = bytearray([0x20, 0x02, 0x00, reason_code])
        self.sent = bytearray()

    def setblocking(self, blocking):
        pass

    def send(self, data):
        self.sent.extend(data)
        return len(data)

    def recv(self, size):
        data = bytes(self.incoming[:size])
        del self.incoming[:size]
        return data

    def close(self):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("socket_failure", [False, True])
async def test_connect_routes_through_metrics_and_real_connack(clean_metrics, socket_failure):
    handler = MagicMock()
    client = MqttClient("metrics-connect-path", handler)
    sock = BrokerSocket()
    with patch.object(client, "_create_socket", side_effect=OSError("unreachable") if socket_failure else None, return_value=sock):
        if socket_failure:
            with pytest.raises(OSError, match="unreachable"):
                client.connect("broker.test", port=1883, keepalive=60)
        else:
            assert client.connect("broker.test", port=1883, keepalive=60) == mqtt.MQTT_ERR_SUCCESS
        await Metrics.drain()
        assert Metrics.sigenergy2mqtt_mqtt_connection_attempts == 1
        assert Metrics.sigenergy2mqtt_mqtt_connections == 0
        assert Metrics.sigenergy2mqtt_mqtt_connection_errors == int(socket_failure)
        if not socket_failure:
            # Let Paho parse the wire response and dispatch its configured callback.
            client.loop_read()
    await Metrics.drain()
    if not socket_failure:
        assert sock.sent[0] == 0x10  # Paho sent CONNECT.
    assert Metrics.sigenergy2mqtt_mqtt_connection_attempts == 1
    assert Metrics.sigenergy2mqtt_mqtt_connections == int(not socket_failure)
    assert Metrics.sigenergy2mqtt_mqtt_connection_errors == int(socket_failure)
    assert Metrics.sigenergy2mqtt_mqtt_reconnections == 0
    client.disconnect()


@pytest.mark.asyncio
async def test_paho_automatic_retries_record_attempts_and_results(clean_metrics):
    handler = MagicMock()
    client = MqttClient("metrics-automatic-retry", handler)
    client.reconnect_delay_set(min_delay=0, max_delay=0)
    first_socket = BrokerSocket()
    retry_socket = BrokerSocket()

    def stop_after_reconnection(connected_client):
        if handler.on_reconnect.call_count == 2:
            connected_client.disconnect()

    handler.on_reconnect.side_effect = stop_after_reconnection

    # Only socket creation and socket readiness are replaced. Paho sends CONNECT,
    # parses CONNACK, detects EOF, handles the failed retry, and retries again.
    with patch.object(
        client, "_create_socket", side_effect=[first_socket, OSError("broker unavailable"), retry_socket]
    ) as create_socket, patch(
        "paho.mqtt.client.select.select",
        side_effect=lambda readers, writers, errors, timeout: ([client.socket()] if client.socket() else [], writers, []),
    ):
        client.connect("broker.test", port=1883, keepalive=60)
        client.loop_forever(timeout=0)
    await Metrics.drain()
    assert create_socket.call_count == 3
    assert handler.on_reconnect.call_count == 2
    assert first_socket.sent[0] == retry_socket.sent[0] == 0x10
    assert Metrics.sigenergy2mqtt_mqtt_connection_attempts == 3
    assert Metrics.sigenergy2mqtt_mqtt_connections == 2
    assert Metrics.sigenergy2mqtt_mqtt_connection_errors == 1
    assert Metrics.sigenergy2mqtt_mqtt_reconnections == 1
