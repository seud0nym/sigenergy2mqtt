"""Thread-safe registry of MQTT client health state.

External monitoring classes should call :meth:`MqttHealthRegistry.snapshot`
to obtain a point-in-time copy of all client states — safe to read from any
thread with no locking required on the caller's side.
"""

import copy
import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MqttClientHealth:
    """Observed health state for a single MQTT client."""

    client_id: str
    connected: bool = False
    last_connected_at: float | None = None
    last_disconnected_at: float | None = None
    last_message_at: float | None = None
    last_publish_at: float | None = None
    last_publish_ack_at: float | None = None
    oldest_pending_publish_at: float | None = None
    connect_count: int = 0
    disconnect_count: int = 0
    _pending_publishes: dict[int, float] = field(default_factory=dict, repr=False)
    _seen_ack_mids: set[int] = field(default_factory=set, repr=False)


class MqttHealthRegistry:
    """Tracks liveness and activity timestamps for registered MQTT clients.

    Designed to be shared across the callback module and any external
    monitoring class.  All mutations are serialised with an :class:`RLock`;
    :meth:`snapshot` returns a shallow copy so callers never hold the lock.

    Usage::

        registry = MqttHealthRegistry()
        client = MqttClient("my-client", handler, registry=registry)

        # from a monitoring thread or class:
        for cid, health in registry.snapshot().items():
            if not health.connected:
                alert(f"{cid} is down")
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._clients: dict[str, MqttClientHealth] = {}

    def clear(self) -> None:
        """Clear the registry."""
        with self._lock:
            self._clients.clear()

    # ------------------------------------------------------------------
    # Registration (called once per client at startup)
    # ------------------------------------------------------------------

    def register(self, client_id: str) -> None:
        """Add *client_id* to the registry with a default-disconnected state."""
        with self._lock:
            if client_id not in self._clients:
                self._clients[client_id] = MqttClientHealth(client_id=client_id)

    # ------------------------------------------------------------------
    # Mutation helpers (called from MQTT callbacks)
    # ------------------------------------------------------------------

    def mark_connected(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry is None:
                return
            entry.connected = True
            entry.last_connected_at = time.monotonic()
            entry.connect_count += 1
            entry._pending_publishes.clear()
            entry._seen_ack_mids.clear()
            entry.oldest_pending_publish_at = None

    def mark_disconnected(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry is None:
                return
            entry.connected = False
            entry.last_disconnected_at = time.monotonic()
            entry.disconnect_count += 1
            entry._pending_publishes.clear()
            entry._seen_ack_mids.clear()
            entry.oldest_pending_publish_at = None

    def record_message(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry:
                entry.last_message_at = time.monotonic()
                # if last_message_at is later than last_connected_at, then the client must be connected
                if not entry.connected and entry.last_message_at and entry.last_connected_at and entry.last_message_at > entry.last_connected_at:
                    logger.info(f"MQTT client {client_id} currently marked as disconnected but message received so assume it IS connected")
                    entry.connected = True
                    entry.connect_count += 2

    def record_publish(self, client_id: str, mid: int | None = None) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry:
                now = time.monotonic()
                entry.last_publish_at = now
                if mid is not None:
                    if mid in entry._seen_ack_mids:
                        entry._seen_ack_mids.remove(mid)
                    else:
                        entry._pending_publishes[mid] = now
                    entry.oldest_pending_publish_at = (
                        min(entry._pending_publishes.values())
                        if entry._pending_publishes
                        else None
                    )
                else:
                    if entry.oldest_pending_publish_at is None:
                        entry.oldest_pending_publish_at = now

    def record_publish_ack(self, client_id: str, mid: int | None = None) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry:
                now = time.monotonic()
                entry.last_publish_ack_at = now
                if mid is not None:
                    if mid in entry._pending_publishes:
                        entry._pending_publishes.pop(mid, None)
                    else:
                        entry._seen_ack_mids.add(mid)
                        if len(entry._seen_ack_mids) > 1000:
                            entry._seen_ack_mids.clear()
                    entry.oldest_pending_publish_at = (
                        min(entry._pending_publishes.values())
                        if entry._pending_publishes
                        else None
                    )
                else:
                    entry._pending_publishes.clear()
                    entry._seen_ack_mids.clear()
                    entry.oldest_pending_publish_at = None
                # if last_publish_ack_at is later than last_connected_at, then the client must be connected
                if not entry.connected and entry.last_publish_ack_at and entry.last_connected_at and entry.last_publish_ack_at > entry.last_connected_at:
                    logger.info(f"MQTT client {client_id} currently marked as disconnected but publish ACK received so assume it IS connected")
                    entry.connected = True
                    entry.connect_count += 2

    # ------------------------------------------------------------------
    # Read-only interface for external consumers
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, MqttClientHealth]:
        """Return a shallow copy of all client states.

        Safe to iterate without holding any lock.  Each :class:`ClientHealth`
        value is itself a copy — mutating it has no effect on the registry.
        """
        with self._lock:
            return {cid: copy.copy(h) for cid, h in self._clients.items()}

    def is_connected(self, client_id: str) -> bool | None:
        """Return the current connection state, or *None* if unknown."""
        with self._lock:
            entry = self._clients.get(client_id)
            return entry.connected if entry else None

    def __repr__(self) -> str:
        with self._lock:
            states = {cid: ("up" if h.connected else "down") for cid, h in self._clients.items()}
        return f"MqttHealthRegistry({states})"
