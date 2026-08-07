"""Lightweight aiohttp-based diagnostics & health-check web server.

Runs inside the app's existing asyncio event loop — no separate process,
thread, or extra server framework needed — alongside the MQTT/Modbus tasks,
following the same ``Device.schedule()`` pattern as :class:`MonitorService`.

Routes:
    GET  /health              Plain status check for Docker HEALTHCHECK / probes.
    GET  /diagnostics         Live dashboard (HTML + WebSocket client).
    GET  /diagnostics/solar   Solar/battery dashboard (shares the same WebSocket feed).
    GET  /diagnostics/ws      WebSocket pushing the full diagnostics payload
                              every ``refresh_interval`` seconds.
    GET  /diagnostics/export  Full diagnostics payload as a downloadable JSON file.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import time
from pathlib import Path
from typing import Any

from aiohttp import WSMsgType, web

from sigenergy2mqtt.config import active_config, is_docker

from .registry import diagnostics_registry

logger = logging.getLogger(__name__)

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
        self._allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._sockets: set[web.WebSocketResponse] = set()
        self._broadcast_task: asyncio.Task | None = None
        self._last_snapshot: dict[str, Any] = {}

    def _configure_routes(self) -> None:
        if self._app is None:
            return
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/diagnostics", self._handle_dashboard_redirect)
        self._app.router.add_get("/diagnostics/", self._handle_dashboard)
        self._app.router.add_get("/diagnostics/solar", self._handle_solar_dashboard)
        self._app.router.add_get("/diagnostics/ws", self._handle_websocket)
        self._app.router.add_get("/diagnostics/export", self._handle_export)
        self._app.router.add_static("/diagnostics/static/", STATIC_DIR, name="static")

    @staticmethod
    def _parse_allowed_networks(raw: list[str] | None) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None:
        """Parse config entries into ``ipaddress`` networks.

        Accepts single IPs (``10.10.2.8``) and CIDR ranges (``10.10.2.0/24``).
        Invalid entries are logged and skipped rather than raising, so a typo
        in the config doesn't take the whole server down.
        """
        if raw is None:
            return None
        networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in raw:
            try:
                networks.append(ipaddress.ip_network(entry.strip(), strict=False))
            except ValueError:
                logger.warning(f"DiagnosticsServer Ignoring invalid allowed_ips entry: {entry!r}")
        return networks

    @web.middleware
    async def _logging_middleware(self, request: web.Request, handler) -> web.StreamResponse:
        """Log every request and its outcome at DEBUG level.

        Runs outermost (registered before ``_ip_filter_middleware``) so it
        also captures requests rejected by the IP filter, and the status
        code it logs is whatever was ultimately returned/raised. For the
        WebSocket route, "response" logging fires only once the socket
        closes, since that's when the handler coroutine returns - the
        connect/disconnect events themselves are already logged separately
        in :meth:`_handle_websocket`.
        """
        if not logger.isEnabledFor(logging.DEBUG):
            return await handler(request)

        started = time.monotonic()
        query = f"?{request.query_string}" if request.query_string else ""
        logger.debug(f"DiagnosticsServer --> {request.method} {request.path}{query} from {request.remote!r}")
        status: int | str = "FAILED"
        try:
            response = await handler(request)
            status = response.status
            return response
        except web.HTTPException as exc:
            # aiohttp uses these to carry non-2xx responses (e.g. our own
            # HTTPForbidden from _ip_filter_middleware) - not a real failure.
            status = exc.status
            raise
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000
            logger.debug(f"DiagnosticsServer <-- {request.method} {request.path}{query} {status} ({elapsed_ms:.1f}ms)")

    @web.middleware
    async def _ip_filter_middleware(self, request: web.Request, handler) -> web.StreamResponse:
        """Reject requests from IPs outside ``self._allowed_networks``.

        A None allow-list means "no restriction" (matches today's default
        behaviour). ``request.remote`` is the directly-connecting peer; if
        this server ever sits behind a reverse proxy, use that proxy's own
        ACLs/allow-list instead of trusting X-Forwarded-For here.
        """
        if is_docker() and request.path == "/health" and request.remote == "127.0.0.1":
            return await handler(request)

        if self._allowed_networks is not None:
            peer = request.remote
            try:
                addr = ipaddress.ip_address(peer) if peer else None
            except ValueError:
                addr = None
            if addr is None or not any(addr in net for net in self._allowed_networks):
                logger.warning(f"DiagnosticsServer Rejected request from disallowed address {peer!r}")
                raise web.HTTPForbidden(text="Forbidden")
        return await handler(request)

    @property
    def last_snapshot(self) -> dict[str, Any] | None:
        """The most recent diagnostics snapshot (cheap, cached; used by /health).

        Returns ``None`` when the cache is empty or the snapshot timestamp is
        older than ``_refresh_interval`` seconds, indicating stale data.
        """
        ts = self._last_snapshot.get("timestamp")
        if ts is None or (time.time() - ts) > self._refresh_interval:
            logger.debug("DiagnosticsServer last_snapshot is stale or empty; returning None")
            return None
        return self._last_snapshot

    async def _fresh_snapshot(self) -> dict[str, Any]:
        """Return a fresh diagnostics snapshot.

        Uses the cached ``_last_snapshot`` when it is still within
        ``_refresh_interval``; otherwise fetches a new snapshot from the
        registry, stores it in the cache, and returns it.
        """
        snapshot = self.last_snapshot
        if snapshot is None:
            logger.debug("DiagnosticsServer fetching fresh snapshot")
            snapshot = self._last_snapshot = await diagnostics_registry.snapshot()
        return snapshot

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Fast health probe. Reuses the cached snapshot rather than recomputing
        checks synchronously — the HTTP round-trip itself already proves the
        event loop is alive and responsive.
        """
        snapshot = await self._fresh_snapshot()
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

    async def _handle_dashboard_redirect(self, request: web.Request) -> web.Response:
        """Redirect ``/diagnostics`` -> ``/diagnostics/``.

        The Location header is deliberately *relative* ("diagnostics/"),
        not absolute ("/diagnostics/"). This server has no idea whether
        it's being hit directly or via Home Assistant's ingress proxy,
        which fronts it behind a per-session prefix such as
        ``/api/hassio_ingress/<token>/``. A relative redirect is resolved
        by the browser against the *externally visible* URL, so it lands
        on the right place either way; an absolute one would drop the
        ingress prefix and 404.
        """
        raise web.HTTPFound(location="diagnostics/")

    async def _handle_dashboard(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "diagnostics.html")

    async def _handle_solar_dashboard(self, request: web.Request) -> web.FileResponse:
        """Solar/battery dashboard — a separate page, but deliberately served
        at ".../diagnostics/solar" (no trailing slash) rather than its own
        top-level route. That makes "solar" the last path segment, so the
        page's relative "ws" WebSocket URL and "static/..." asset paths both
        resolve against ".../diagnostics/" — the exact same /diagnostics/ws
        feed and /diagnostics/static/ assets the main dashboard already uses.
        No second WebSocket route or broadcast loop needed for this page.
        """
        return web.FileResponse(STATIC_DIR / "dashboard.html")

    async def _handle_export(self, request: web.Request) -> web.Response:
        """Full, freshly-collected diagnostics payload as a downloadable file."""
        logger.debug("DiagnosticsServer fetching fresh snapshot for export")
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
        logger.debug(f"DiagnosticsServer WebSocket client connected ({len(self._sockets)} total)")
        try:
            cached = self.last_snapshot
            if cached is not None:
                await ws.send_json(cached)
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    logger.warning(f"DiagnosticsServer WebSocket error: {ws.exception()}")
                # No client->server messages are expected; this loop just
                # keeps the connection open and detects close/error.
        finally:
            self._sockets.discard(ws)
            logger.debug(f"DiagnosticsServer WebSocket client disconnected ({len(self._sockets)} remaining)")
        return ws

    async def _broadcast_loop(self) -> None:
        """Periodically snapshot all providers and push to connected clients."""
        while True:
            try:
                self._last_snapshot = await diagnostics_registry.snapshot()
                logger.debug(f"DiagnosticsServer Snapshot: {self._last_snapshot}")
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
                logger.warning(f"DiagnosticsServer Broadcast loop error: {exc}")
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
        self._allowed_networks = self._parse_allowed_networks(getattr(cfg, "allowed_ips", None))
        if self._allowed_networks is not None:
            logger.info(f"DiagnosticsServer Restricting access to {[str(n) for n in self._allowed_networks]}")

        self._app = web.Application(middlewares=[self._logging_middleware, self._ip_filter_middleware])
        self._configure_routes()

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port, reuse_address=True, reuse_port=True)
        await site.start()
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"DiagnosticsServer Listening on http://{self._host}:{self._port} (dashboard at /diagnostics)")

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
        self._sockets.clear()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        logger.info("DiagnosticsServer Stopped")

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
