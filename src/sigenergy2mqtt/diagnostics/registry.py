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
        self._revisions: dict[str, int] = {}
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

    def bump_revision(self, name: str) -> int:
        """Atomically advance and return the revision counter for a named section.

        Used by write endpoints (e.g. the debug-logging and runtime-config
        HTTP handlers) to give clients a total order for "did a write I sent
        actually take effect, and is it still the most recent thing that's
        happened" — independent of HTTP response arrival order or WS
        broadcast timing.

        Deliberately synchronous and lock-free: callers must invoke this
        immediately after ``await``-ing the value's actual commit, with no
        further ``await`` in between. asyncio only switches tasks at await
        points, so that gap-free sequence is what guarantees a broadcast can
        never observe the new value with a stale revision (or vice versa).
        Wrapping this in ``asyncio.Lock`` would require ``async with``,
        reintroducing an await point and the exact race this exists to close.
        """
        self._revisions[name] = self._revisions.get(name, 0) + 1
        return self._revisions[name]

    def revision(self, name: str) -> int:
        """Current revision counter for a named section (0 if never bumped)."""
        return self._revisions.get(name, 0)

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

        # Snapshot revisions BEFORE collecting provider data, not after. A
        # write that commits (and bumps its revision — see bump_revision)
        # while the gather below is in flight will have already committed
        # its value by then; that provider's collect() call will see the new
        # value even though this "_revisions" dict, captured earlier, won't
        # yet include the bump. That's a safe kind of staleness — a lower
        # revision number paired with a value that's actually already
        # current — and self-corrects via the write's own HTTP response.
        # The reverse ordering (revisions captured after data) can instead
        # pair a *newer* revision with a *stale* value when a write commits
        # mid-gather, which a client's "revision > lastKnownRevision" check
        # would wrongly trust as authoritative.
        revisions = dict(self._revisions)

        results = await asyncio.gather(*(_run(p) for p in providers)) if providers else []

        payload: dict[str, Any] = {"timestamp": int(time.time())}
        payload["_revisions"] = revisions
        payload.update({name: data for name, data in results})
        return payload


# Single process-wide instance. Import this, don't instantiate DiagnosticsRegistry yourself.
diagnostics_registry = DiagnosticsRegistry()