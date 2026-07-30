"""Schedulable wrapper that starts/stops the diagnostics web server.

Deliberately separate from MonitorService: MonitorService's job is producing
health data (it registers the "monitor" diagnostics_registry entry regardless
of whether a web server exists to expose it). This class's only job is
hosting that data over HTTP/WebSocket — it's a "service" in the same sense as
MetricsService, the PVOutput services, and the InfluxDB services, and is
attached to the Services thread alongside them in `setup_services()`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device

from .server import diagnostics_server

logger = logging.getLogger("sigenergy2mqtt")


class DiagnosticsService(Device):
    """Starts/stops :data:`diagnostics_server` alongside the other optional services."""

    def __init__(self) -> None:
        super().__init__(
            "Diagnostics",
            -1,
            f"{active_config.home_assistant.unique_id_prefix}_diagnostics",
            "sigenergy2mqtt",
            "Diagnostics",
            Protocol.N_A,
        )

    def schedule(self, modbus_client: Any, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Return the single long-running coroutine that owns the web server's lifecycle."""
        return [self._run_without_crashing_the_thread()]

    async def _run_without_crashing_the_thread(self) -> None:
        """Run the diagnostics server, but never let a startup/bind failure escape.

        This coroutine is gathered alongside MetricsService/PVOutput/InfluxDB
        inside the Services thread's event loop. `run_modbus_event_loop` only
        sets `stop_event` (and thus triggers the app-wide crash/offline
        cascade) for `(ValueError, TypeError, RuntimeError)` — an `OSError`
        from a failed `bind()` (port already in use, permission denied on a
        privileged port, etc.) is *not* in that tuple, so left unhandled it
        would instead surface unnoticed as an exception on this thread's
        Future and only blow up later, uncaught, in `start()`'s final
        `fut.result()` loop — taking down the whole app over what should be
        a non-fatal diagnostics failure.

        Catches only the exceptions a bind/lifecycle failure can actually
        raise; anything else (a genuine bug) is left to propagate rather than
        being silently swallowed.
        """
        try:
            await diagnostics_server.run()
        except asyncio.CancelledError:
            raise  # cooperative shutdown must still propagate
        except (OSError, RuntimeError):
            logger.exception("DiagnosticsService Web server failed to start — diagnostics will be unavailable, but continuing without it")
