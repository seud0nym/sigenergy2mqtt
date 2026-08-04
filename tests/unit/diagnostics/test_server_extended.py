import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from sigenergy2mqtt.diagnostics.server import DiagnosticsServer

@pytest.mark.asyncio
async def test_configure_routes_no_app():
    # Covers lines 65-66
    server = DiagnosticsServer()
    server._app = None
    server._configure_routes()  # Should return silently

@pytest.mark.asyncio
async def test_logging_middleware_debug_success(monkeypatch):
    # Covers lines 104-114, 121-122
    server = DiagnosticsServer()
    request = make_mocked_request("GET", "/test?q=1")
    handler = AsyncMock(return_value=web.Response(text="OK", status=200))
    
    monkeypatch.setattr(logging.getLogger("sigenergy2mqtt.diagnostics.server"), "isEnabledFor", lambda level: True)
    
    response = await server._logging_middleware(request, handler)
    assert response.status == 200

@pytest.mark.asyncio
async def test_logging_middleware_debug_exception(monkeypatch):
    # Covers lines 115-119
    server = DiagnosticsServer()
    request = make_mocked_request("GET", "/test")
    handler = AsyncMock(side_effect=web.HTTPForbidden())
    
    monkeypatch.setattr(logging.getLogger("sigenergy2mqtt.diagnostics.server"), "isEnabledFor", lambda level: True)
    
    with pytest.raises(web.HTTPForbidden):
        await server._logging_middleware(request, handler)

@pytest.mark.asyncio
async def test_handle_dashboard_redirect():
    # Covers line 202
    server = DiagnosticsServer()
    request = make_mocked_request("GET", "/diagnostics")
    with pytest.raises(web.HTTPFound) as exc:
        await server._handle_dashboard_redirect(request)
    assert exc.value.location == "diagnostics/"

@pytest.mark.asyncio
async def test_handle_solar_dashboard():
    # Covers line 216
    server = DiagnosticsServer()
    request = make_mocked_request("GET", "/diagnostics/solar")
    response = await server._handle_solar_dashboard(request)
    assert isinstance(response, web.FileResponse)

@pytest.mark.asyncio
async def test_broadcast_loop_dead_socket_runtime_error():
    # specifically tests the dead socket removal which might have been missed
    # Covers lines 261-262
    server = DiagnosticsServer()
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = RuntimeError("Dead socket")
    server._sockets.add(mock_ws)
    server._refresh_interval = 0.01
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snap:
        mock_snap.return_value = {"new": "data"}
        task = asyncio.create_task(server._broadcast_loop())
        # Yield to let it run the loop iteration
        await asyncio.sleep(0.02)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        assert mock_ws not in server._sockets
