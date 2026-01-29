import asyncio
import logging
import time

import pytest
import requests

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.pvoutput.service import Service


def make_service():
    logger = logging.getLogger("test-pvoutput")
    return Service("pvtest", "pvtest", "pvmodel", logger)


def test_get_response_headers_and_reset(monkeypatch):
    svc = make_service()
    # freeze time to make reset calculation deterministic
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    resp = requests.Response()
    resp.status_code = 200
    resp.headers = {
        "X-Rate-Limit-Limit": "60",
        "X-Rate-Limit-Remaining": "58",
        "X-Rate-Limit-Reset": "1060.0",
    }
    limit, remaining, at, reset = svc.get_response_headers(resp)
    assert limit == 60
    assert remaining == 58
    assert at == 1060.0
    assert isinstance(reset, int)


@pytest.mark.asyncio
async def test_seconds_until_status_upload_testing(monkeypatch):
    svc = make_service()
    # Ensure testing path is taken
    orig = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = True
        seconds, next_time = await svc.seconds_until_status_upload(rand_min=1, rand_max=1)
        # In testing mode seconds_until_status_upload returns 60
        assert seconds == 60
        assert isinstance(next_time, int)
        # Service._interval should be set to 5 in testing mode
        assert svc._interval == 5
    finally:
        Config.pvoutput.testing = orig


@pytest.mark.asyncio
async def test_upload_payload_testing_mode(monkeypatch):
    svc = make_service()
    orig = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = True
        uploaded = await svc.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", {"d": "20250101"})
        assert uploaded is True
    finally:
        Config.pvoutput.testing = orig


@pytest.mark.asyncio
async def test_upload_payload_http_error_bad_request(monkeypatch):
    svc = make_service()
    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        # make requests.post raise HTTPError with response containing status_code 400
        resp = requests.Response()
        cid = requests.structures.CaseInsensitiveDict()
        cid["X-Rate-Limit-Remaining"] = "5"
        cid["X-Rate-Limit-Limit"] = "60"
        cid["X-Rate-Limit-Reset"] = "1100.0"
        resp.status_code = 400
        resp.reason = "Bad Request"
        resp.headers = cid
        resp._content = b"Bad Request"

        def fake_post(*a, **k):
            raise requests.exceptions.HTTPError(response=resp)

        monkeypatch.setattr(requests, "post", fake_post)

        # avoid real sleeps
        async def no_sleep(x):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_sleep)

        uploaded = await svc.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", {"d": "20250101"})
        assert uploaded is False
    finally:
        Config.pvoutput.testing = orig_testing
