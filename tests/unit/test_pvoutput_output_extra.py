import asyncio
import time
from datetime import datetime

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService


class DummyLogger:
    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def test_create_payload_and_change_detection():
    svc = PVOutputOutputService(DummyLogger(), {})
    # fixed struct for date
    now_struct = time.localtime(1700000000)
    payload = svc._create_payload(now_struct, 1440)
    assert "d" in payload
    # when previous payload equals current, _is_payload_changed should return False
    svc._previous_payload = dict(payload)
    assert svc._is_payload_changed(payload) is False
    # modified payload triggers change
    payload2 = dict(payload)
    payload2["g"] = 100
    assert svc._is_payload_changed(payload2) is True


@pytest.mark.asyncio
async def test_next_output_upload_testing_mode(monkeypatch):
    orig = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = True
        svc = PVOutputOutputService(DummyLogger(), {})
        Config.pvoutput.output_hour = 3
        n = await svc._next_output_upload()
        # testing mode should schedule ~now + 60 seconds
        assert n - time.time() <= 65
    finally:
        Config.pvoutput.testing = orig


@pytest.mark.asyncio
async def test_verify_in_testing_mode_returns_true(monkeypatch):
    orig = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = True
        svc = PVOutputOutputService(DummyLogger(), {})
        payload = {"d": datetime.utcnow().strftime("%Y%m%d"), "g": 1}
        # when forced verification (multiple retries) testing mode should succeed
        ok = await svc._verify(payload, force=True)
        assert ok is True
    finally:
        Config.pvoutput.testing = orig


@pytest.mark.asyncio
async def test_upload_skips_unchanged_and_verifies(monkeypatch):
    svc = PVOutputOutputService(DummyLogger(), {})
    payload = {"d": datetime.utcnow().strftime("%Y%m%d"), "g": 1}
    svc._previous_payload = dict(payload)

    called = {"upload": False, "verify": False}

    async def fake_upload(url, pl):
        called["upload"] = True
        return True

    async def fake_verify(pl, force=False):
        called["verify"] = True
        return True

    monkeypatch.setattr(svc, "upload_payload", fake_upload)
    monkeypatch.setattr(svc, "_verify", fake_verify)

    await svc._upload(payload, last_upload_of_day=False)
    # upload should be skipped because unchanged, but verify still called
    assert called["upload"] is False
    assert called["verify"] is True
