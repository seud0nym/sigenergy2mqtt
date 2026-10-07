"""Transport response handling tests."""

import logging

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.auth import OAuthSession
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.errors import (
    SigenergyCloudAPIError,
    SigenergyCloudAuthError,
    SigenergyCloudRateLimitError,
)
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.transport import (
    CloudTransport,
)


async def _authed_transport() -> tuple[aiohttp.ClientSession, CloudTransport]:
    session = aiohttp.ClientSession()
    auth = OAuthSession("eu")
    with aioresponses() as mocked:
        mocked.post(
            "https://api-eu.sigencloud.com/auth/oauth/token",
            payload={
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
            },
        )
        await auth.authenticate(
            session,
            "https://api-eu.sigencloud.com/",
            "user",
            "encrypted",
        )
        (request,) = mocked.requests[("POST", URL("https://api-eu.sigencloud.com/auth/oauth/token"))]
        assert request.kwargs["headers"] == {"Authorization": aiohttp.encode_basic_auth("sigen", "sigen")}
        assert "auth" not in request.kwargs
    return session, CloudTransport("https://api-eu.sigencloud.com/", auth)


@pytest.mark.asyncio
async def test_returns_data_from_successful_envelope() -> None:
    session, transport = await _authed_transport()
    try:
        with aioresponses() as mocked:
            mocked.get(
                "https://api-eu.sigencloud.com/device/example",
                payload={"code": 0, "data": {"ok": True}},
            )
            assert await transport.data(session, "GET", "device/example") == {"ok": True}
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_maps_api_error_code_to_exception() -> None:
    session, transport = await _authed_transport()
    try:
        with aioresponses() as mocked:
            mocked.get(
                "https://api-eu.sigencloud.com/device/example",
                payload={"code": 123, "msg": "bad"},
            )
            with pytest.raises(SigenergyCloudAPIError, match="bad"):
                await transport.data(session, "GET", "device/example")
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, SigenergyCloudAuthError), (429, SigenergyCloudRateLimitError)],
)
async def test_maps_http_status_to_typed_error(status: int, error_type: type[Exception]) -> None:
    session, transport = await _authed_transport()
    try:
        with aioresponses() as mocked:
            mocked.get(
                "https://api-eu.sigencloud.com/device/example",
                status=status,
                payload={"msg": "nope"},
            )
            with pytest.raises(error_type, match="nope"):
                await transport.data(session, "GET", "device/example")
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_debug_logs_request_and_response(caplog: pytest.LogCaptureFixture) -> None:
    """Transport logs the HTTP response status, method, and URL at DEBUG."""
    session, transport = await _authed_transport()
    try:
        with aioresponses() as mocked:
            mocked.get(
                "https://api-eu.sigencloud.com/device/example",
                payload={"code": 0, "data": {"ok": True}},
            )
            with caplog.at_level(logging.DEBUG, logger="sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.transport"):
                await transport.data(session, "GET", "device/example")

        response_records = [r for r in caplog.records if "Cloud API response" in r.message]
        assert len(response_records) >= 1, "Expected at least one Cloud API response log"
        assert "get" in response_records[0].message
        assert "device/example" in response_records[0].message
        assert "200" in response_records[0].message
    finally:
        await session.close()
