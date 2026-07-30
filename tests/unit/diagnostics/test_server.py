import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, PropertyMock

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
        "timestamp": time.time(),
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
    now = time.time()
    server._last_snapshot = {"test": 1, "timestamp": now}
    assert server.last_snapshot == {"test": 1, "timestamp": now}


def test_stale_last_snapshot_property(server: DiagnosticsServer) -> None:
    server._last_snapshot = {"test": 1, "timestamp": time.time() - server._refresh_interval - 0.001}
    assert server.last_snapshot is None


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
        server._last_snapshot = {"pre": "loaded", "timestamp": time.time()}
        
        ws_res = await server._handle_websocket(request)
        
        assert ws_res is mock_ws
        mock_ws.prepare.assert_called_once_with(request)
        mock_ws.send_json.assert_called_once_with(server._last_snapshot)
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


def test_parse_allowed_networks() -> None:
    import ipaddress
    # Test None
    assert DiagnosticsServer._parse_allowed_networks(None) is None
    
    # Test empty
    assert DiagnosticsServer._parse_allowed_networks([]) == []
    
    # Test valid networks
    networks = DiagnosticsServer._parse_allowed_networks(["192.168.1.1", "10.0.0.0/24"])
    assert networks is not None
    assert len(networks) == 2
    assert ipaddress.ip_network("192.168.1.1") in networks
    assert ipaddress.ip_network("10.0.0.0/24") in networks
    
    # Test invalid networks (should be ignored, not crash)
    networks_with_invalid = DiagnosticsServer._parse_allowed_networks(["192.168.1.1", "invalid_ip"])
    assert networks_with_invalid is not None
    assert len(networks_with_invalid) == 1
    assert ipaddress.ip_network("192.168.1.1") in networks_with_invalid

    # Test only invalid networks (should return [])
    assert DiagnosticsServer._parse_allowed_networks(["invalid_ip"]) == []


@pytest.mark.asyncio
async def test_ip_filter_middleware_allow_all(server: DiagnosticsServer) -> None:
    server._allowed_networks = None
    
    request = make_mocked_request("GET", "/diagnostics")
    handler = AsyncMock(return_value=web.Response(text="OK"))
    
    response = await server._ip_filter_middleware(request, handler)
    assert response.text == "OK"
    handler.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_ip_filter_middleware_empty_list_denies(server: DiagnosticsServer) -> None:
    server._allowed_networks = []
    
    request = make_mocked_request("GET", "/diagnostics")
    handler = AsyncMock()
    
    with pytest.raises(web.HTTPForbidden):
        await server._ip_filter_middleware(request, handler)
        
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_ip_filter_middleware_allowed_ip(server: DiagnosticsServer) -> None:
    import ipaddress
    from unittest.mock import PropertyMock
    server._allowed_networks = [ipaddress.ip_network("192.168.1.0/24")]
    
    request = make_mocked_request("GET", "/diagnostics")
    with patch.object(type(request), 'remote', new_callable=PropertyMock, return_value="192.168.1.100"):
        handler = AsyncMock(return_value=web.Response(text="OK"))
        response = await server._ip_filter_middleware(request, handler)
        assert response.text == "OK"


@pytest.mark.asyncio
async def test_ip_filter_middleware_denied_ip(server: DiagnosticsServer) -> None:
    import ipaddress
    from unittest.mock import PropertyMock
    server._allowed_networks = [ipaddress.ip_network("192.168.1.0/24")]
    
    request = make_mocked_request("GET", "/diagnostics")
    with patch.object(type(request), 'remote', new_callable=PropertyMock, return_value="10.0.0.5"):
        handler = AsyncMock()
        with pytest.raises(web.HTTPForbidden):
            await server._ip_filter_middleware(request, handler)


@pytest.mark.asyncio
async def test_ip_filter_middleware_invalid_remote(server: DiagnosticsServer) -> None:
    import ipaddress
    from unittest.mock import PropertyMock
    server._allowed_networks = [ipaddress.ip_network("192.168.1.0/24")]
    
    request = make_mocked_request("GET", "/diagnostics")
    with patch.object(type(request), 'remote', new_callable=PropertyMock, return_value="invalid"):
        handler = AsyncMock()
        with pytest.raises(web.HTTPForbidden):
            await server._ip_filter_middleware(request, handler)


@pytest.mark.asyncio
async def test_ip_filter_middleware_health_exempt_in_docker(server: DiagnosticsServer) -> None:
    server._allowed_networks = []  # Empty list normally denies all
    
    request = make_mocked_request("GET", "/health")
    type(request).remote = PropertyMock(return_value="127.0.0.1")
    handler = AsyncMock(return_value=web.Response(text="OK"))
    
    with patch("sigenergy2mqtt.diagnostics.server.is_docker", return_value=True):
        response = await server._ip_filter_middleware(request, handler)
        
    assert response.text == "OK"
    handler.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_ip_filter_middleware_health_not_exempt_outside_docker(server: DiagnosticsServer) -> None:
    server._allowed_networks = []  # Empty list normally denies all
    
    request = make_mocked_request("GET", "/health")
    handler = AsyncMock()
    
    with patch("sigenergy2mqtt.diagnostics.server.is_docker", return_value=False):
        with pytest.raises(web.HTTPForbidden):
            await server._ip_filter_middleware(request, handler)
            
    handler.assert_not_called()
