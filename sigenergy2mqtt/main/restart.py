import logging
import threading

from sigenergy2mqtt.config import active_config

from .thread_config import thread_config_registry


class RestartController:
    """Coordinates a full runtime restart across threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requested = False

    def reset(self) -> None:
        """Clear restart-request state for a newly initialized runtime cycle."""
        with self._lock:
            self._requested = False

    @property
    def requested(self) -> bool:
        """Whether a restart has been requested for the active runtime cycle."""
        with self._lock:
            return self._requested

    def request(self, reason: str) -> None:
        """Request a coordinated full-runtime restart.

        On the first request only, Home Assistant publishing is temporarily
        disabled to suppress controlled-restart offline availability messages,
        and all active thread configs are offlined.

        Args:
            reason: Human-readable restart reason for logs.
        """
        should_offline = False
        with self._lock:
            if not self._requested:
                self._requested = True
                if active_config.home_assistant.enabled:
                    active_config.home_assistant.enabled = False
                should_offline = True

        if should_offline:
            logging.info(f"Restart requested: {reason}")
            for config in thread_config_registry.get_all():
                config.offline()


restart_controller = RestartController()
