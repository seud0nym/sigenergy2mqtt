import asyncio
import json
import time

import pytest
import requests

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.topic import Topic


def test_topic_json_roundtrip():
    now = time.localtime()
    t = Topic(topic="a/b", scan_interval=60, gain=2.0, precision=1, state=3.5, timestamp=now)
    # encode via json_encoder
    encoded = json.dumps(t, default=Topic.json_encoder)
    # decode via json_decoder
    decoded = json.loads(encoded, object_hook=Topic.json_decoder)
    assert isinstance(decoded, Topic)
    assert decoded.topic == t.topic
    assert decoded.gain == t.gain
    assert decoded.state == t.state
    assert decoded.restore_timestamp is not None


def test_get_response_headers_parsing():
    svc = Service("n", "uid", "model", __import__("logging").getLogger("pvout"))

    class Dummy:
        headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 30)}

    limit, remaining, at, reset = svc.get_response_headers(Dummy())
    assert limit == 60
    assert remaining == 59
    assert isinstance(at, float)
    assert isinstance(reset, int)


def test_json_decoder_handles_list_timestamps():
    # create a dict as if read from JSON where timestamps are lists
    now = time.localtime()
    ts_list = list(now)
    obj = {"topic": "x", "scan_interval": 10, "gain": 1.0, "precision": None, "state": 2.0, "timestamp": ts_list, "previous_state": None, "previous_timestamp": None}
    topic = Topic.json_decoder(obj)
    assert isinstance(topic, Topic)
    assert isinstance(topic.timestamp, time.struct_time)
    assert topic.restore_timestamp is not None


def test_json_encoder_raises_on_non_dataclass():
    with pytest.raises(TypeError):
        Topic.json_encoder(123)


@pytest.mark.asyncio
async def test_upload_payload_retries_and_http400(monkeypatch):
    svc = Service("n", "uid", "model", __import__("logging").getLogger("pvout"))

    # avoid sleeping delays
    async def no_sleep(*a, **k):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(Config.pvoutput, "testing", False)

    # Case A: first attempt raises ConnectionError, second succeeds
    calls = {"count": 0}

    class RespCM:
        def __init__(self, status=200):
            self.status_code = status
            self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 30)}
            self.text = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            if self.status_code != 200:
                err = requests.exceptions.HTTPError("status")
                err.response = self
                raise err

    def fake_post(url, headers=None, data=None, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return RespCM(500)
        return RespCM(200)

    monkeypatch.setattr("requests.post", fake_post)
    ok = await svc.upload_payload("u", {"d": "20250101"})
    assert ok is True

    # Case B: HTTP 400 -> should return False
    def fake_post_400(url, headers=None, data=None, timeout=None):
        class R:
            status_code = 400
            headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 30)}
            text = "bad"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                err = requests.exceptions.HTTPError("bad")
                err.response = self
                raise err

        return R()

    monkeypatch.setattr("requests.post", fake_post_400)
    ok2 = await svc.upload_payload("u", {"d": "20250101"})
    assert ok2 is False

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_non_testing(monkeypatch):
        svc = Service("n", "uid", "model", __import__("logging").getLogger("pvout"))
        # ensure not testing
        orig_testing = Config.pvoutput.testing
        orig_interval = Service._interval
        orig_donator = Service._donator
        try:
            Config.pvoutput.testing = False

            # craft response with section[0] having 16 comma-separated fields, index 15 is interval
            section0 = ",".join(["0"] * 15 + ["12"])  # interval=12
            text = f"{section0};unused;1"

            class DummyResp:
                def __init__(self, text):
                    self.text = text
                    self.status_code = 200
                    self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 60)}

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            def fake_get(url, headers=None, timeout=None):
                return DummyResp(text)

            monkeypatch.setattr("requests.get", fake_get)

            seconds, next_time = await svc.seconds_until_status_upload()
            assert isinstance(seconds, float)
            assert Service._interval == 12
            assert Service._donator is True
        finally:
            Config.pvoutput.testing = orig_testing
            Service._interval = orig_interval
            Service._donator = orig_donator
