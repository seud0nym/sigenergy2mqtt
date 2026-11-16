"""Last Will, refused connections, handler failures and teardown draining."""

import asyncio
import json
import logging
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt import mqtt as mqtt_package
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import client as client_module
from sigenergy2mqtt.mqtt.client import (
    MqttClient,
    connection_refused,
    on_connect,
    reset_connection_refused,
    status_topic_for,
)
from sigenergy2mqtt.mqtt.handler import MqttHandler
from sigenergy2mqtt.sensors.plant.read_only import PlantPVPower


@pytest.fixture(autouse=True)
def clear_refused_flag():
    reset_connection_refused()
    yield
    reset_connection_refused()


def _client(client_id: str = "sigenergy2mqtt_test") -> tuple[MqttClient, MqttHandler]:
    handler = MqttHandler(client_id, None, MagicMock())
    client = MqttClient(client_id=client_id, userdata=handler)
    client._host = "broker"
    client._port = 1883
    return client, handler


def _published(info_published: bool) -> mqtt.MQTTMessageInfo:
    info = mqtt.MQTTMessageInfo(1)
    info.rc = mqtt.MQTT_ERR_SUCCESS
    info._published = info_published
    return info


class TestLastWill:
    def test_client_registers_a_retained_offline_will(self):
        client, _ = _client("sigenergy2mqtt_abc")
        assert client.status_topic == status_topic_for("sigenergy2mqtt_abc") == "sigenergy2mqtt/status/sigenergy2mqtt_abc"
        assert client._will_topic == client.status_topic.encode()
        assert client._will_payload == b"offline"
        assert client._will_retain is True
        assert client._will_qos == 1

    def test_online_status_is_published_on_every_successful_connect(self):
        client, handler = _client()
        with patch.object(mqtt.Client, "publish", return_value=_published(True)) as publish:
            on_connect(client, handler, None, 0, None)
            handler.connected = False
            on_connect(client, handler, None, 0, None)
        status = [c for c in publish.call_args_list if c.args[0] == client.status_topic]
        assert len(status) == 2
        assert all(c.kwargs["payload"] == "online" for c in status)
        assert all(c.kwargs["retain"] is True for c in status)

    def test_discovery_availability_includes_the_publishing_clients_status_topic(self):
        with patch.object(active_config.home_assistant, "enabled", True):
            device = Device("Test Device", 0, f"{active_config.home_assistant.unique_id_prefix}_0_will_test", "mf", "mdl", ProtocolVersion.V2_4)
            sensor = PlantPVPower(0)
            assert device._add_sensor(sensor)
            own_availability = list(sensor["availability"])

            mqtt_client = MagicMock()
            mqtt_client.status_topic = "sigenergy2mqtt/status/thread"
            device.publish_discovery(mqtt_client, clean=False)

        payloads = [c.args[1] for c in mqtt_client.publish.call_args_list if c.args[0].endswith("/config")]
        component = json.loads(payloads[0])["cmps"][sensor.unique_id]
        assert component["availability"] == [*own_availability, {"topic": "sigenergy2mqtt/status/thread"}]
        assert component["availability_mode"] == "all"
        assert sensor["availability"] == own_availability, "the sensor's own list must not grow on every discovery"


class TestRefusedConnection:
    def test_first_connection_refused_shuts_down_with_failure_flag(self):
        client, handler = _client()
        with patch.object(client_module._thread, "interrupt_main") as interrupt:
            on_connect(client, handler, None, 5, None)
        interrupt.assert_called_once()
        assert connection_refused() is True

    def test_refusal_after_a_successful_connection_is_an_outage_not_a_shutdown(self):
        client, handler = _client("sigenergy2mqtt_refused_later")
        with patch.object(mqtt.Client, "publish", return_value=_published(True)):
            client._connection_started = 1.0
            on_connect(client, handler, None, 0, None)
        assert client._has_connected is True

        with patch.object(client_module._thread, "interrupt_main") as interrupt:
            on_connect(client, handler, None, 3, None)
        interrupt.assert_not_called()
        assert connection_refused() is False
        assert outage_tracker("mqtt://broker:1883").active is True


class TestHandlerFailureLogging:
    @pytest.mark.asyncio
    async def test_exception_in_command_handler_is_logged(self, caplog):
        handler = MqttHandler("c", None, asyncio.get_running_loop())

        async def bad(*args):
            raise ValueError("boom")

        client = MagicMock()
        handler.register(client, "t/set", bad)
        with caplog.at_level(logging.ERROR, logger="paho.mqtt"):
            await asyncio.to_thread(handler.on_message, client, "t/set", "1")
            await handler.close()
            await asyncio.sleep(0)

        failures = [r for r in caplog.records if "failed" in r.getMessage() and "boom" in r.getMessage()]
        assert len(failures) == 1
        assert failures[0].exc_info is not None

    @pytest.mark.asyncio
    async def test_successful_handler_logs_nothing(self, caplog):
        handler = MqttHandler("c", None, asyncio.get_running_loop())

        async def good(*args):
            return True

        client = MagicMock()
        handler.register(client, "t/set", good)
        with caplog.at_level(logging.ERROR, logger="paho.mqtt"):
            await asyncio.to_thread(handler.on_message, client, "t/set", "1")
            await handler.close()
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


class TestTeardownDrain:
    def test_unacknowledged_publishes_counts_only_pending_qos_messages(self):
        client, _ = _client()
        pending, done = _published(False), _published(True)
        with patch.object(mqtt.Client, "publish", side_effect=[done, pending, _published(False)]):
            client.publish("a", "1", qos=1)
            client.publish("b", "1", qos=2)
            client.publish("c", "1", qos=0)
        assert client.unacknowledged_publishes() == 1
        pending._published = True
        assert client.unacknowledged_publishes() == 0

    @pytest.mark.asyncio
    async def test_teardown_waits_for_acknowledgement_before_stopping_the_loop(self):
        client, handler = _client()
        pending = _published(False)
        order: list[str] = []

        def acknowledge_soon():
            pending._published = True
            order.append("acknowledged")

        with (
            patch.object(mqtt.Client, "publish", return_value=pending),
            patch.object(client, "is_connected", return_value=True),
            patch.object(client, "loop_stop", side_effect=lambda: order.append("loop_stop")),
            patch.object(client, "disconnect"),
            patch.object(client, "unsubscribe"),
        ):
            client.publish("availability", "offline", qos=2, retain=True)
            asyncio.get_running_loop().call_later(0.2, acknowledge_soon)
            await mqtt_package.mqtt_teardown(client, handler)

        assert order == ["acknowledged", "loop_stop"]

    @pytest.mark.asyncio
    async def test_drain_gives_up_after_the_timeout(self):
        client, _ = _client()
        with patch.object(mqtt.Client, "publish", return_value=_published(False)), patch.object(client, "is_connected", return_value=True):
            client.publish("availability", "offline", qos=2, retain=True)
            await asyncio.wait_for(mqtt_package._drain_publishes(client, timeout=0.2), 2)
        assert client.unacknowledged_publishes() == 1
