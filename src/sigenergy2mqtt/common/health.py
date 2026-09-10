"""Registry for tracking third-party service health status."""

from __future__ import annotations

import threading


class ServiceHealthRegistry:
    """Thread-safe registry for managing service health states."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, bool] = {}

    def set_health(self, service_name: str, healthy: bool) -> None:
        """Set the health status for a given service."""
        with self._lock:
            self._states[service_name] = bool(healthy)

    def get_health(self, service_name: str, default: bool = True) -> bool:
        """Get the health status for a given service, returning default if unrecorded."""
        with self._lock:
            return self._states.get(service_name, default)

    def snapshot(self) -> dict[str, bool]:
        """Return a snapshot of all registered service health states."""
        with self._lock:
            return self._states.copy()

    def clear(self) -> None:
        """Clear all registered service health states."""
        with self._lock:
            self._states.clear()

    def __repr__(self) -> str:
        with self._lock:
            return f"ServiceHealthRegistry({self._states})"


service_health_registry = ServiceHealthRegistry()
