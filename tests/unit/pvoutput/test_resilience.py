"""PVOutput tasks must survive responses and errors they do not expect."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.pvoutput import service_topics
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.settings import PVOutputSettings
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService


def _response(status: int, headers: dict[str, str] | None = None, body: bytes = b"") -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = body
    if headers:
        response.headers.update(headers)
    return response


class TestRateLimitHeaders:
    def test_missing_headers_are_none(self):
        assert Service("s", "pv_hdr1", "m").get_response_headers(_response(502)) == (None, None, None, None)

    def test_malformed_headers_are_none(self):
        response = _response(200, {"X-Rate-Limit-Limit": "abc", "X-Rate-Limit-Remaining": "", "X-Rate-Limit-Reset": "soon"})
        assert Service("s", "pv_hdr2", "m").get_response_headers(response) == (None, None, None, None)

    def test_present_headers_are_parsed(self):
        response = _response(200, {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": "4102444800"})
        limit, remaining, at, reset = Service("s", "pv_hdr3", "m").get_response_headers(response)
        assert (limit, remaining, at) == (60, 59, 4102444800.0)
        assert reset is not None and reset > 0


class TestUploadPayload:
    @pytest.mark.asyncio
    async def test_gateway_error_without_rate_limit_headers_returns_false(self):
        svc = Service("s", "pv_up1", "m")
        sleep = AsyncMock()
        with (
            patch.object(active_config.pvoutput, "testing", False),
            patch("sigenergy2mqtt.pvoutput.service.requests.post", return_value=_response(502, body=b"Bad Gateway")) as post,
            patch("sigenergy2mqtt.pvoutput.service.asyncio.sleep", sleep),
        ):
            assert await svc.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", {"d": "20260101"}) is False
        assert post.call_count == 3
        assert sleep.await_count == 2, "there is nothing to wait for after the final attempt"

    @pytest.mark.asyncio
    async def test_system_information_without_headers_falls_back_to_defaults(self):
        svc = Service("s", "pv_up2", "m")
        PVOutputSettings.interval_updated = None
        try:
            with patch.object(active_config.pvoutput, "testing", False), patch("sigenergy2mqtt.pvoutput.service.requests.get", return_value=_response(502)):
                seconds, _ = await svc.seconds_until_status_upload()
            assert seconds > 0
        finally:
            PVOutputSettings.interval_updated = None


class TestServiceLoops:
    @pytest.mark.asyncio
    async def test_status_loop_survives_an_unexpected_exception(self):
        svc = PVOutputStatusService({}, {})
        calls = 0

        async def next_upload(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyError("unexpected")
            if calls >= 3:
                svc._online = False
            return 0.0, 0

        svc._online = asyncio.get_running_loop().create_future()
        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=next_upload),
            patch.object(svc, "_refresh_home_assistant_extended_fields", AsyncMock()),
            patch.object(svc, "_create_payload", return_value=({"d": "20260101", "t": "00:00"}, {})),
            patch("sigenergy2mqtt.pvoutput.status.asyncio.sleep", AsyncMock()),
        ):
            await asyncio.wait_for(svc.schedule(None, MagicMock())[0], 10)
        assert calls >= 3, "the loop stopped at the unexpected exception"

    @pytest.mark.asyncio
    async def test_output_loop_survives_an_unexpected_exception(self):
        svc = PVOutputOutputService({})
        calls = 0

        def create_payload(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls >= 2:
                svc._online = False
            raise KeyError("unexpected")

        svc._online = asyncio.get_running_loop().create_future()
        with (
            patch.object(svc, "_next_output_upload", AsyncMock(return_value=0.0)),
            patch.object(svc, "_create_payload", side_effect=create_payload),
            patch("sigenergy2mqtt.pvoutput.output.asyncio.sleep", AsyncMock()),
        ):
            await asyncio.wait_for(svc.schedule(None, MagicMock())[0], 10)
        assert calls >= 2, "the loop stopped at the unexpected exception"

    @pytest.mark.asyncio
    async def test_verify_handles_an_uninterpretable_response_body(self):
        svc = PVOutputOutputService({})
        headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": "4102444800"}
        body = b"20260101,1,2,3,4,not-a-number"
        with (
            patch.object(active_config.pvoutput, "testing", False),
            patch("sigenergy2mqtt.pvoutput.output.requests.get", return_value=_response(200, headers, body)),
            patch("sigenergy2mqtt.pvoutput.output.asyncio.sleep", AsyncMock()),
        ):
            assert await svc._verify({"d": "20260101"}) is False


def test_update_lock_timeout_outlasts_the_system_information_request():
    assert service_topics.UPDATE_LOCK_TIMEOUT > 10
