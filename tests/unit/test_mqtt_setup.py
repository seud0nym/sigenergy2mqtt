import asyncio

import pytest

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.mqtt import mqtt_setup


def test_mqtt_setup_retries_then_succeeds(monkeypatch):
    # Make sleep a no-op to avoid delays
    import sigenergy2mqtt.mqtt.__init__ as mqtt_init
    monkeypatch.setattr(mqtt_init, "sleep", lambda s: None)

    # Prepare Config
    Config.mqtt.broker = "localhost"
    Config.mqtt.port = 1883
    Config.mqtt.keepalive = 10
    Config.mqtt.anonymous = False
    Config.mqtt.username = "user"
    Config.mqtt.password = "pass"

    # Monkeypatch paho Client methods to simulate connect failing once then succeeding
    import paho.mqtt.client as paho
    side = {"calls": 0}

    def fake_connect(self, broker, port=1883, keepalive=60):
        side["calls"] += 1
        if side["calls"] == 1:
            raise Exception("connect failed")
        return 0

    def fake_loop_start(self):
        setattr(self, "loop_started", True)

    def fake_username_pw_set(self, u, p):
        setattr(self, "_user", u)
        setattr(self, "_pw", p)

    monkeypatch.setattr(paho.Client, "connect", fake_connect, raising=True)
    monkeypatch.setattr(paho.Client, "loop_start", fake_loop_start, raising=True)
    monkeypatch.setattr(paho.Client, "username_pw_set", fake_username_pw_set, raising=True)

    loop = asyncio.new_event_loop()
    try:
        client, handler = mqtt_setup("cid", None, loop)
    finally:
        loop.close()

    assert getattr(client, "loop_started", False) is True
    assert getattr(client, "_user") == "user"
    assert getattr(client, "_pw") == "pass"


def test_mqtt_setup_fails_after_retries(monkeypatch):
    import sigenergy2mqtt.mqtt.__init__ as mqtt_init
    monkeypatch.setattr(mqtt_init, "sleep", lambda s: None)

    Config.mqtt.broker = "localhost"
    Config.mqtt.port = 1883
    Config.mqtt.keepalive = 10
    Config.mqtt.anonymous = True

    import paho.mqtt.client as paho

    def always_fail_connect(self, broker, port=1883, keepalive=60):
        raise Exception("boom")

    monkeypatch.setattr(paho.Client, "connect", always_fail_connect, raising=True)

    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(Exception):
            mqtt_setup("cid2", None, loop)
    finally:
        loop.close()
