"""Lightweight aiohttp-based diagnostics & health-check web server.

Runs inside the app's existing asyncio event loop — no separate process,
thread, or extra server framework needed — alongside the MQTT/Modbus tasks,
following the same ``Device.schedule()`` pattern as :class:`MonitorService`.

Routes:
    GET  /health              Plain status check for Docker HEALTHCHECK / probes.
    GET  /diagnostics         Live dashboard (HTML + WebSocket client).
    GET  /diagnostics/ws      WebSocket pushing the full diagnostics payload
                              every ``refresh_interval`` seconds.
    GET  /diagnostics/export  Full diagnostics payload as a downloadable JSON file.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from sigenergy2mqtt.config import active_config, is_docker

from .registry import diagnostics_registry

logger = logging.getLogger("sigenergy2mqtt")

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_PORT = 8502


class DiagnosticsServer:
    """Owns the aiohttp app/runner lifecycle and the WebSocket broadcast loop."""

    def __init__(self) -> None:
        """Initialise the server.

        Host/port/refresh-interval are deliberately *not* fixed here — they're
        read from ``active_config.diagnostics`` inside :meth:`start`, each time
        it's called. This instance is a long-lived singleton, but it's expected
        to be stopped and restarted alongside the rest of the app's services on
        every restart cycle (see ``MonitorService.schedule()``), including
        after ``active_config.reload()`` — so a changed port in the config
        file takes effect on the next cycle rather than being frozen at
        whatever it was when the process first imported this module.
        """
        self._host = "127.0.0.1"
        self._port = DEFAULT_PORT
        self._refresh_interval = 5.0
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._sockets: set[web.WebSocketResponse] = set()
        self._broadcast_task: asyncio.Task | None = None
        self._last_snapshot: dict[str, Any] = {}
        self._configure_routes()

    def _configure_routes(self) -> None:
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/diagnostics", self._handle_dashboard)
        self._app.router.add_get("/diagnostics/ws", self._handle_websocket)
        self._app.router.add_get("/diagnostics/export", self._handle_export)
        self._app.router.add_static("/diagnostics/static/", STATIC_DIR, name="static")

    @property
    def last_snapshot(self) -> dict[str, Any]:
        """The most recent diagnostics snapshot (cheap, cached; used by /health)."""
        return self._last_snapshot

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Fast health probe. Reuses the cached snapshot rather than recomputing
        checks synchronously — the HTTP round-trip itself already proves the
        event loop is alive and responsive.
        """
        snapshot = self._last_snapshot or await diagnostics_registry.snapshot()
        monitor = snapshot.get("monitor", {})
        status = monitor.get("status", "unknown")
        code = 200 if status == "healthy" else 503
        return web.json_response(
            {
                "status": status,
                "timestamp": snapshot.get("timestamp"),
                "mqtt_connected": monitor.get("mqtt_connected"),
                "modbus_connected": monitor.get("modbus_connected"),
            },
            status=code,
        )

    async def _handle_dashboard(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "dashboard.html")

    async def _handle_export(self, request: web.Request) -> web.Response:
        """Full, freshly-collected diagnostics payload as a downloadable file."""
        snapshot = await diagnostics_registry.snapshot()
        body = json.dumps(snapshot, indent=2, default=str)
        return web.Response(
            body=body,
            content_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sigenergy2mqtt-diagnostics.json"'},
        )

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._sockets.add(ws)
        logger.debug(f"DiagnosticsServer: WebSocket client connected ({len(self._sockets)} total)")
        try:
            if self._last_snapshot:
                await ws.send_json(self._last_snapshot)
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    logger.warning(f"DiagnosticsServer: WebSocket error: {ws.exception()}")
                # No client->server messages are expected; this loop just
                # keeps the connection open and detects close/error.
        finally:
            self._sockets.discard(ws)
            logger.debug(f"DiagnosticsServer: WebSocket client disconnected ({len(self._sockets)} remaining)")
        return ws

    async def _broadcast_loop(self) -> None:
        """Periodically snapshot all providers and push to connected clients."""
        while True:
            try:
                self._last_snapshot = await diagnostics_registry.snapshot()
                # logger.debug(f"DiagnosticsServer: Snapshot: {self._last_snapshot}")
                if self._sockets:
                    dead: set[web.WebSocketResponse] = set()
                    for ws in self._sockets:
                        try:
                            await ws.send_json(self._last_snapshot)
                        except (ConnectionResetError, RuntimeError):
                            dead.add(ws)
                    self._sockets -= dead
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - this loop must survive indefinitely; a provider or send_json failure here must never kill the only task pushing live diagnostics
                logger.warning(f"DiagnosticsServer: Broadcast loop error: {exc}")
            await asyncio.sleep(self._refresh_interval)

    async def start(self) -> None:
        """Bind the socket and start the background broadcast loop.

        Reads ``active_config.diagnostics`` fresh on every call — this runs
        once per restart cycle (see ``MonitorService.schedule()``), so a
        config reload that changed the port/host/refresh interval is picked
        up here rather than being stuck with whatever was set at import time.
        """
        cfg = active_config.diagnostics
        self._host = getattr(cfg, "host", self._host)
        self._port = DEFAULT_PORT if is_docker() else getattr(cfg, "port", self._port)
        self._refresh_interval = getattr(cfg, "refresh_interval", self._refresh_interval)

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"DiagnosticsServer: Listening on http://{self._host}:{self._port} (dashboard at /diagnostics)")

    async def stop(self) -> None:
        """Cancel the broadcast loop, close sockets, and tear down the runner."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        for ws in list(self._sockets):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()
        logger.info("DiagnosticsServer: Stopped")

    async def run(self) -> None:
        """Start the server and block until cancelled.

        Matches the shape expected by ``Device.schedule()`` — a single
        awaitable that runs for the lifetime of the service, e.g.::

            def schedule(self, modbus_client, mqtt_client) -> list[Awaitable[None]]:
                return [self._monitor(mqtt_client), diagnostics_server.run()]
        """
        await self.start()
        try:
            await asyncio.Event().wait()  # sleeps forever until the task is cancelled
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


# Module-level singleton. Deliberately constructed with no config-derived
# arguments — see the note in __init__/start() for why.
diagnostics_server = DiagnosticsServer()
