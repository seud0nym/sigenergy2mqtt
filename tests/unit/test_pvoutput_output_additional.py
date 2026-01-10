import asyncio
import time
import types

import pytest

from sigenergy2mqtt.config import Config, OutputField
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 60)}
        self.reason = "OK"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_verify_parses_remote_response(monkeypatch):
    svc = PVOutputOutputService(__import__("logging").getLogger("pvout"), {})
    # ensure non-testing mode
    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False
        # set exports/imports flags so parsing maps fields
        orig_exports = Config.pvoutput.exports
        orig_imports = Config.pvoutput.imports
        Config.pvoutput.exports = True
        Config.pvoutput.imports = True

        payload = {"d": "20250101", "pp": 10, "ep": 0}

        # craft response text where v[5] -> pp (index 5), v[14] -> ep
        # ensure all other indices are 'NaN' to avoid int('') parsing errors
        parts = ["NaN"] * 18
        parts[0] = "20250101"
        parts[5] = "10"
        parts[14] = "0"
        text = ",".join(parts)

        def fake_get(url, headers=None, timeout=None):
            return DummyResponse(text)

        monkeypatch.setattr("requests.get", fake_get)

        # avoid real sleeps
        async def no_sleep(*a, **k):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_sleep)

        res = await svc._verify(payload, force=False)
        assert res is True

    finally:
        Config.pvoutput.testing = orig_testing
        Config.pvoutput.exports = orig_exports
        Config.pvoutput.imports = orig_imports


@pytest.mark.asyncio
async def test_next_output_upload_rolls_over_to_tomorrow():
    svc = PVOutputOutputService(__import__("logging").getLogger("pvout"), {})
    # ensure not testing
    orig_testing = Config.pvoutput.testing
    orig_hour = Config.pvoutput.output_hour
    try:
        Config.pvoutput.testing = False
        # set output_hour to an earlier hour to force next <= now
        now = time.localtime()
        past_hour = now.tm_hour - 1 if now.tm_hour > 0 else 0
        Config.pvoutput.output_hour = past_hour
        nxt = await svc._next_output_upload(minute=0)
        assert nxt > time.time()
        # should be roughly at least 1 hour ahead (tomorrow)
        assert nxt - time.time() > 3500
    finally:
        Config.pvoutput.testing = orig_testing
        Config.pvoutput.output_hour = orig_hour
