"""Thread-safe registry of MQTT client health state.

External monitoring classes should call :meth:`MqttHealthRegistry.snapshot`
to obtain a point-in-time copy of all client states — safe to read from any
thread with no locking required on the caller's side.
"""

import copy
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MqttClientHealth:
    """Observed health state for a single MQTT client."""

    client_id: str
    connected: bool = False
    last_connected_at: Optional[float] = None
    last_disconnected_at: Optional[float] = None
    last_message_at: Optional[float] = None
    last_publish_ack_at: Optional[float] = None
    connect_count: int = 0
    disconnect_count: int = 0


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
        self._clients: Dict[str, MqttClientHealth] = {}

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

    def mark_disconnected(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry is None:
                return
            entry.connected = False
            entry.last_disconnected_at = time.monotonic()
            entry.disconnect_count += 1

    def record_message(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry:
                entry.last_message_at = time.monotonic()

    def record_publish_ack(self, client_id: str) -> None:
        with self._lock:
            entry = self._clients.get(client_id)
            if entry:
                entry.last_publish_ack_at = time.monotonic()

    # ------------------------------------------------------------------
    # Read-only interface for external consumers
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, MqttClientHealth]:
        """Return a shallow copy of all client states.

        Safe to iterate without holding any lock.  Each :class:`ClientHealth`
        value is itself a copy — mutating it has no effect on the registry.
        """
        with self._lock:
            return {cid: copy.copy(h) for cid, h in self._clients.items()}

    def is_connected(self, client_id: str) -> Optional[bool]:
        """Return the current connection state, or *None* if unknown."""
        with self._lock:
            entry = self._clients.get(client_id)
            return entry.connected if entry else None

    def __repr__(self) -> str:
        with self._lock:
            states = {cid: ("up" if h.connected else "down") for cid, h in self._clients.items()}
        return f"MqttHealthRegistry({states})"
