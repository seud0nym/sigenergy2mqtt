import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from sigenergy2mqtt.diagnostics.server import DiagnosticsServer


@pytest.fixture
def server() -> DiagnosticsServer:
    return DiagnosticsServer()


@pytest.mark.asyncio
async def test_handle_health_healthy(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/health")
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snapshot:
        mock_snapshot.return_value = {
            "timestamp": 12345,
            "monitor": {
                "status": "healthy",
                "mqtt_connected": True,
                "modbus_connected": True
            }
        }
        response = await server._handle_health(request)
        
        assert response.status == 200
        body = json.loads(response.body)
        assert body["status"] == "healthy"
        assert body["mqtt_connected"] is True


@pytest.mark.asyncio
async def test_handle_health_unhealthy(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/health")
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snapshot:
        mock_snapshot.return_value = {
            "timestamp": 12345,
            "monitor": {
                "status": "unhealthy",
                "mqtt_connected": False,
                "modbus_connected": True
            }
        }
        response = await server._handle_health(request)
        
        assert response.status == 503
        body = json.loads(response.body)
        assert body["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_handle_health_uses_cached_snapshot(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/health")
    
    server._last_snapshot = {
        "timestamp": 999,
        "monitor": {"status": "healthy"}
    }
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snapshot:
        response = await server._handle_health(request)
        
        assert response.status == 200
        mock_snapshot.assert_not_called()


@pytest.mark.asyncio
async def test_handle_export(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/diagnostics/export")
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snapshot:
        mock_snapshot.return_value = {"system": "ok"}
        
        response = await server._handle_export(request)
        
        assert response.status == 200
        assert response.content_type == "application/json"
        
        body = json.loads(response.text)
        assert body == {"system": "ok"}


@pytest.mark.asyncio
async def test_start_and_stop(server: DiagnosticsServer) -> None:
    with patch("sigenergy2mqtt.diagnostics.server.web.TCPSite") as mock_site:
        with patch("sigenergy2mqtt.diagnostics.server.web.AppRunner") as mock_runner:
            mock_runner_instance = mock_runner.return_value
            mock_runner_instance.setup = AsyncMock()
            mock_runner_instance.cleanup = AsyncMock()
            
            mock_site_instance = mock_site.return_value
            mock_site_instance.start = AsyncMock()
            
            await server.start()
            
            mock_runner_instance.setup.assert_called_once()
            mock_site_instance.start.assert_called_once()
            
            assert server._broadcast_task is not None
            assert not server._broadcast_task.done()
            
            await server.stop()
            
            assert server._broadcast_task.cancelled() or server._broadcast_task.done()
            mock_runner_instance.cleanup.assert_called_once()


def test_last_snapshot_property(server: DiagnosticsServer) -> None:
    server._last_snapshot = {"test": 1}
    assert server.last_snapshot == {"test": 1}


@pytest.mark.asyncio
async def test_handle_dashboard(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/diagnostics")
    response = await server._handle_dashboard(request)
    assert isinstance(response, web.FileResponse)


@pytest.mark.asyncio
async def test_handle_websocket(server: DiagnosticsServer) -> None:
    request = make_mocked_request("GET", "/diagnostics/ws")
    
    class MockWS:
        def __init__(self):
            self.prepare = AsyncMock()
            self.send_json = AsyncMock()
            self.exception = lambda: Exception("Test error")
        async def __aiter__(self):
            msg = type("Msg", (), {"type": web.WSMsgType.ERROR})()
            yield msg
            
    mock_ws = MockWS()
    
    with patch("sigenergy2mqtt.diagnostics.server.web.WebSocketResponse", return_value=mock_ws):
        server._last_snapshot = {"pre": "loaded"}
        
        ws_res = await server._handle_websocket(request)
        
        assert ws_res is mock_ws
        mock_ws.prepare.assert_called_once_with(request)
        mock_ws.send_json.assert_called_once_with({"pre": "loaded"})
        assert mock_ws not in server._sockets  # discarded in finally


@pytest.mark.asyncio
async def test_broadcast_loop_dead_sockets(server: DiagnosticsServer) -> None:
    mock_ws = AsyncMock()
    mock_ws.send_json.side_effect = ConnectionResetError("Dead")
    server._sockets.add(mock_ws)
    server._refresh_interval = 0.01
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snap:
        mock_snap.return_value = {"new": "data"}
        task = asyncio.create_task(server._broadcast_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        assert mock_ws not in server._sockets


@pytest.mark.asyncio
async def test_run(server: DiagnosticsServer) -> None:
    with patch.object(server, "start", new_callable=AsyncMock) as mock_start, \
         patch.object(server, "stop", new_callable=AsyncMock) as mock_stop:
         
        task = asyncio.create_task(server.run())
        await asyncio.sleep(0.01)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        mock_start.assert_called_once()
        mock_stop.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_loop(server: DiagnosticsServer) -> None:
    mock_ws = AsyncMock()
    server._sockets.add(mock_ws)
    
    server._refresh_interval = 0.01
    
    with patch("sigenergy2mqtt.diagnostics.server.diagnostics_registry.snapshot", new_callable=AsyncMock) as mock_snap:
        mock_snap.return_value = {"new": "data"}
        
        task = asyncio.create_task(server._broadcast_loop())
        
        # let it run a bit
        await asyncio.sleep(0.05)
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        mock_ws.send_json.assert_called_with({"new": "data"})
