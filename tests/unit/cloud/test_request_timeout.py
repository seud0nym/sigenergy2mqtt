"""Cloud API requests must time out promptly instead of hanging for aiohttp's 5-minute default."""

import asyncio
import time

import aiohttp
import pytest
from aiohttp import web

from sigenergy2mqtt.cloud import mysigen_adapter
from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.cloud.mysigen_adapter import REQUEST_TIMEOUT, MySigenCloudAdapter, _error_text
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import SigenergyCloudClient
from sigenergy2mqtt.config import active_config


@pytest.fixture
async def stalled_server():
    """An HTTP server that accepts requests and never answers them."""
    release = asyncio.Event()

    async def hang(_request):
        await release.wait()
        return web.Response(text="too late")

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", hang)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
    yield f"http://127.0.0.1:{port}/"
    release.set()
    await runner.cleanup()


def test_adapter_sets_a_request_timeout():
    assert REQUEST_TIMEOUT.total is not None and REQUEST_TIMEOUT.total <= 60
    assert REQUEST_TIMEOUT.sock_connect is not None and REQUEST_TIMEOUT.sock_connect <= REQUEST_TIMEOUT.total
    adapter = MySigenCloudAdapter("user@example.com", "secret", "eu")
    assert adapter._client._timeout is REQUEST_TIMEOUT


async def test_vendored_client_session_uses_timeout():
    timeout = aiohttp.ClientTimeout(total=7)
    client = SigenergyCloudClient("user@example.com", "secret", region="eu", timeout=timeout)
    try:
        session = await client._http_session()
        assert session.timeout.total == 7
    finally:
        await client.close()


async def test_vendored_client_without_timeout_keeps_aiohttp_default():
    client = SigenergyCloudClient("user@example.com", "secret", region="eu")
    try:
        session = await client._http_session()
        assert session.timeout == aiohttp.ClientTimeout(total=300, sock_connect=30)
    finally:
        await client.close()


async def test_stalled_request_fails_promptly_with_a_message(stalled_server, monkeypatch):
    timeout = aiohttp.ClientTimeout(total=1, sock_connect=1)
    monkeypatch.setattr(mysigen_adapter, "REQUEST_TIMEOUT", timeout)
    monkeypatch.setattr(active_config.cloud, "testing_url", stalled_server)
    adapter = MySigenCloudAdapter("user@example.com", "secret", "testing")
    started = time.monotonic()
    try:
        with pytest.raises(CloudControlUnavailableError) as excinfo:
            await adapter.connect()
    finally:
        await adapter.close()
    assert time.monotonic() - started < 5
    assert str(excinfo.value) == "no response within 1s"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), f"no response within {REQUEST_TIMEOUT.total:.0f}s"),
        (asyncio.TimeoutError(), f"no response within {REQUEST_TIMEOUT.total:.0f}s"),
        (aiohttp.ConnectionTimeoutError("Connection timeout to host x"), "Connection timeout to host x"),
        (aiohttp.ServerDisconnectedError(), "Server disconnected"),
        (OSError(), "OSError"),
        (ValueError("bad"), "bad"),
    ],
)
def test_error_text_is_never_empty(error, expected):
    assert _error_text(error) == expected
