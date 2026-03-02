import asyncio

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import mqtt_setup


@pytest.mark.asyncio
async def test_mqtt_setup_retries_then_succeeds(monkeypatch):
    async def _fake_sleep(s):
        pass

    monkeypatch.setitem(mqtt_setup.__globals__, "sleep", _fake_sleep)

    # Prepare Config
    active_config.mqtt.broker = "localhost"
    active_config.mqtt.port = 1883
    active_config.mqtt.keepalive = 10
    active_config.mqtt.anonymous = False
    active_config.mqtt.username = "user"
    active_config.mqtt.password = "pass"

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
        client, handler = await mqtt_setup("cid", None, loop)
    finally:
        loop.close()

    assert getattr(client, "loop_started", False) is True
    assert getattr(client, "_user") == "user"
    assert getattr(client, "_pw") == "pass"


@pytest.mark.asyncio
async def test_mqtt_setup_fails_after_retries(monkeypatch):
    async def _fake_sleep(s):
        pass

    monkeypatch.setitem(mqtt_setup.__globals__, "sleep", _fake_sleep)

    active_config.mqtt.broker = "localhost"
    active_config.mqtt.port = 1883
    active_config.mqtt.keepalive = 10
    active_config.mqtt.anonymous = True

    import paho.mqtt.client as paho

    def always_fail_connect(self, broker, port=1883, keepalive=60):
        raise Exception("boom")

    monkeypatch.setattr(paho.Client, "connect", always_fail_connect, raising=True)

    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(Exception):
            await mqtt_setup("cid2", None, loop)
    finally:
        loop.close()
