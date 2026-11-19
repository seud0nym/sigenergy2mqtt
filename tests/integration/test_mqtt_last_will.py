"""Last Will behavior against an independently running MQTT broker.

Set ``SIGENERGY_TEST_MQTT_BROKER`` to the broker hostname to run this test. The
broker must allow anonymous clients; ``SIGENERGY_TEST_MQTT_PORT`` defaults to
1883.
"""

import asyncio
import os
import socket
import threading
import time
import uuid

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.mqtt.client import STATUS_OFFLINE, STATUS_ONLINE, MqttClient
from sigenergy2mqtt.mqtt.handler import MqttHandler


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("SIGENERGY_TEST_MQTT_BROKER"), reason="requires SIGENERGY_TEST_MQTT_BROKER")
def test_broker_publishes_retained_will_after_ungraceful_disconnect():
    host = os.environ["SIGENERGY_TEST_MQTT_BROKER"]
    port = int(os.getenv("SIGENERGY_TEST_MQTT_PORT", "1883"))
    suffix = uuid.uuid4().hex
    topic = f"sigenergy2mqtt/test/{suffix}/status"
    subscriber_connected = threading.Event()
    publisher_connected = threading.Event()
    subscribed = threading.Event()
    received_offline = threading.Event()
    payloads: list[bytes] = []

    subscriber = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"se2m-sub-{suffix}")
    # Use the application's own client so its Will configuration is what is under test
    loop = asyncio.new_event_loop()
    publisher_id = f"se2m-pub-{suffix}"
    publisher = MqttClient(publisher_id, MqttHandler(publisher_id, None, loop), status_topic=topic)

    def on_subscriber_connect(client, userdata, flags, reason_code, properties):
        assert reason_code == 0
        subscriber_connected.set()
        client.subscribe(topic, qos=1)

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    def on_message(client, userdata, message):
        payloads.append(message.payload)
        if message.payload == STATUS_OFFLINE.encode():
            received_offline.set()

    def on_publisher_connect(client, userdata, flags, reason_code, properties):
        assert reason_code == 0
        publisher_connected.set()

    subscriber.on_connect = on_subscriber_connect
    subscriber.on_subscribe = on_subscribe
    subscriber.on_message = on_message
    publisher.on_connect = on_publisher_connect

    try:
        subscriber.connect(host, port, keepalive=10)
        subscriber.loop_start()
        assert subscriber_connected.wait(10), "subscriber did not connect"
        assert subscribed.wait(10), "subscriber did not subscribe"

        publisher.connect(host, port, keepalive=10)
        publisher.loop_start()
        assert publisher_connected.wait(10), "publisher did not connect"
        publisher.publish_status(STATUS_ONLINE).wait_for_publish(timeout=5)
        deadline = time.monotonic() + 5
        while STATUS_ONLINE.encode() not in payloads and time.monotonic() < deadline:
            time.sleep(0.01)
        assert STATUS_ONLINE.encode() in payloads

        # Stop Paho's reconnect loop, then close the underlying TCP socket without
        # an MQTT DISCONNECT packet so the broker must publish the configured Will.
        publisher.loop_stop()
        sock = publisher._sock
        assert sock is not None
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        publisher._sock = None

        assert received_offline.wait(15), "broker did not publish the retained Last Will"
        retained = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"se2m-check-{suffix}")
        retained_message = threading.Event()
        retained_payload: list[bytes] = []

        def on_retained_connect(client, userdata, flags, reason_code, properties):
            assert reason_code == 0
            client.subscribe(topic, qos=1)

        def on_retained_message(client, userdata, message):
            if message.retain:
                retained_payload.append(message.payload)
                retained_message.set()

        retained.on_connect = on_retained_connect
        retained.on_message = on_retained_message
        retained.connect(host, port, keepalive=10)
        retained.loop_start()
        try:
            assert retained_message.wait(10), "broker did not retain the Last Will"
            assert retained_payload == [STATUS_OFFLINE.encode()]
        finally:
            retained.loop_stop()
            retained.disconnect()
    finally:
        if publisher._sock is not None:
            publisher.loop_stop()
            publisher.disconnect()
        subscriber.loop_stop()
        subscriber.disconnect()
        loop.close()
