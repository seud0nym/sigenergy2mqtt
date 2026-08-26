"""Extensible diagnostics provider registry.

Any component that wants to surface data on the diagnostics page or in the
JSON export registers itself here as a named provider. The web layer
(``server.py``) knows nothing about MQTT, Modbus, InfluxDB, metrics, etc. —
it only ever asks the registry for "whatever providers exist right now".

To add a new diagnostics section later, a component just needs to call::

    from sigenergy2mqtt.diagnostics.registry import diagnostics_registry

    diagnostics_registry.register("my_subsystem", my_collect_fn)

``my_collect_fn`` is a zero-argument callable (sync or async) returning a
JSON-serialisable dict. No changes to the web server are required.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

logger = logging.getLogger(__name__)

CollectFn = Callable[[], "Awaitable[dict[str, Any]] | dict[str, Any]"]


@runtime_checkable
class DiagnosticsProvider(Protocol):
    """Anything that can contribute a named section to the diagnostics payload.

    Implementing this Protocol is optional — ``register()`` accepts any
    zero-arg callable — but it documents the expected shape for providers
    that prefer a class-based implementation over a bound method.
    """

    name: str

    async def collect(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of this provider's current state."""
        ...


@dataclass
class _RegisteredProvider:
    name: str
    collect: CollectFn


class DiagnosticsRegistry:
    """Process-wide registry of diagnostics providers.

    Providers are collected concurrently and defensively: a failing provider
    produces an ``{"error": ...}`` entry rather than aborting the whole
    snapshot, so one broken subsystem never blanks the entire dashboard.
    """

    def __init__(self) -> None:
        self._providers: dict[str, _RegisteredProvider] = {}
        self._lock = asyncio.Lock()

    def clear(self) -> None:
        """Clear all registered providers.

        This is useful for resetting the registry during restarts or cleanup.
        """
        self._providers.clear()
        logger.debug("DiagnosticsRegistry cleared")

    def register(self, name: str, collect: CollectFn) -> None:
        """Register (or replace) a provider under ``name``.

        Args:
            name: Top-level JSON key the provider's data will appear under
                on the dashboard and in the ``/diagnostics/export`` payload.
            collect: Zero-arg callable (sync or async) returning a dict.
        """
        self._providers[name] = _RegisteredProvider(name, collect)
        logger.debug(f"DiagnosticsRegistry Registered provider '{name}'")

    def unregister(self, name: str) -> None:
        """Remove a previously registered provider, if present."""
        if self._providers.pop(name, None) is not None:
            logger.debug(f"DiagnosticsRegistry Unregistered provider '{name}'")

    async def snapshot(self) -> dict[str, Any]:
        """Collect every registered provider's data into one payload."""

        async def _run(p: _RegisteredProvider) -> tuple[str, dict[str, Any]]:
            logger.debug(f"DiagnosticsRegistry Collecting from provider '{p.name}'")
            try:
                raw = p.collect()
                data: dict[str, Any] = await raw if inspect.isawaitable(raw) else cast("dict[str, Any]", raw)
                return p.name, data
            except Exception as exc:  # noqa: BLE001 - providers are arbitrary user-registered callables; any of them can raise anything, and one must not take down the whole snapshot
                logger.warning(f"DiagnosticsRegistry Provider '{p.name}' failed: {exc}")
                return p.name, {"error": str(exc)}

        async with self._lock:
            providers = list(self._providers.values())

        results = await asyncio.gather(*(_run(p) for p in providers)) if providers else []

        payload: dict[str, Any] = {"timestamp": int(time.time())}
        payload.update({name: data for name, data in results})
        return payload


# Single process-wide instance. Import this, don't instantiate DiagnosticsRegistry yourself.
diagnostics_registry = DiagnosticsRegistry()
