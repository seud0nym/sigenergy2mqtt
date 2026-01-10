import asyncio
import logging
import time

import pytest

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.config.pvoutput_config import OutputField
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.topic import Topic


def test_create_payload_and_is_changed(monkeypatch):
    svc = PVOutputOutputService(logging.getLogger("pvout"), {})
    # ensure peak power topic is enabled by default
    topic = Topic(topic="peak", state=123.0, timestamp=time.localtime())
    svc._service_topics[OutputField.PEAK_POWER].register(topic)

    now_struct = time.localtime()
    payload = svc._create_payload(now_struct, 1440)
    assert payload.get("d") is not None
    # 'pp' is peak power value key
    assert payload.get("pp") == round(123.0)

    # test _is_payload_changed
    svc._previous_payload = payload.copy()
    assert svc._is_payload_changed(payload) is False
    payload2 = payload.copy()
    payload2["pp"] = payload2["pp"] + 1
    assert svc._is_payload_changed(payload2) is True


@pytest.mark.asyncio
async def test_next_output_upload_uses_seconds_until_status(monkeypatch):
    svc = PVOutputOutputService(logging.getLogger("pvout"), {})

    async def fake_seconds(rand_min=1, rand_max=1):
        return 5, 12345

    monkeypatch.setattr(svc, "seconds_until_status_upload", fake_seconds)
    # set output_hour to -1 to force using seconds_until_status_upload
    orig = Config.pvoutput.output_hour
    try:
        Config.pvoutput.output_hour = -1
        nxt = await svc._next_output_upload()
        assert isinstance(nxt, float)
    finally:
        Config.pvoutput.output_hour = orig


@pytest.mark.asyncio
async def test_upload_sets_previous_payload_when_output_hour_minus1(monkeypatch):
    svc = PVOutputOutputService(logging.getLogger("pvout"), {})
    payload = {"d": "20250101", "pp": 50}

    # ensure changed (previous None)
    svc._previous_payload = None

    async def fake_upload(url, pl):
        return True

    async def fake_verify(pl, force=False):
        return True

    monkeypatch.setattr(svc, "upload_payload", fake_upload)
    monkeypatch.setattr(svc, "_verify", fake_verify)

    orig = Config.pvoutput.output_hour
    try:
        Config.pvoutput.output_hour = -1
        await svc._upload(payload, last_upload_of_day=False)
        assert svc._previous_payload == payload
    finally:
        Config.pvoutput.output_hour = orig


@pytest.mark.asyncio
async def test_verify_in_testing_mode(monkeypatch):
    svc = PVOutputOutputService(logging.getLogger("pvout"), {})
    payload = {"d": "20250101", "g": 10}

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = True
        # avoid actual sleep delays
        async def no_sleep(*a, **k):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_sleep)

        # not forced -> verify_retries == 1 -> should return False
        res = await svc._verify(payload, force=False)
        assert res is False

        # forced -> should return True because testing mode simulates success on 2nd attempt
        res2 = await svc._verify(payload, force=True)
        assert res2 is True
    finally:
        Config.pvoutput.testing = orig_testing
