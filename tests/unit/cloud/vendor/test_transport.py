"""Transport response handling tests."""

import aiohttp
import pytest
from aioresponses import aioresponses

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
    auth = OAuthSession()
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
            assert await transport.data(session, "GET", "device/example") == {
                "ok": True
            }
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
async def test_maps_http_status_to_typed_error(
    status: int, error_type: type[Exception]
) -> None:
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
