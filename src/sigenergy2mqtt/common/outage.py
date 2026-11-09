"""Outage tracking to collapse floods of similar error messages.

When a shared resource (the MQTT broker, a Modbus host, ...) becomes
unavailable, every sensor and scan group that depends on it fails at once and
logs its own error.  An :class:`OutageTracker` turns that flood into:

* one ``ERROR`` when the outage starts,
* one ``ERROR`` the first time a *different kind* of error is seen,
* an optional periodic ``ERROR`` reminder while the outage continues, and
* one ``INFO`` when the outage ends, reporting the duration and how many
  messages were suppressed.

Everything else that would have been logged is demoted to ``DEBUG``.

Trackers are shared per resource name via :func:`outage_tracker`, so every
component that talks to the same resource reports into the same outage.  All
methods are thread-safe because paho callbacks run on paho's network thread
while the pollers run on the asyncio loop.
"""

from __future__ import annotations

import logging
import threading
import time

__all__ = ["OutageTracker", "active_outages", "clear_outage_trackers", "format_duration", "outage_tracker"]

DEFAULT_REMINDER_INTERVAL = 300.0
"""Seconds between "outage continuing" reminders (``0`` disables reminders)."""

_DEFAULT_MEMBER = "*"

logger = logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """Format *seconds* as a compact human-readable duration (e.g. ``4m 12s``)."""
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _error_kind(error: BaseException | str) -> str:
    """Return the key used to decide whether an error is "new" for an outage.

    Exceptions are grouped by class so that messages differing only in
    transaction ids or retry counts are not reported as new errors.
    """
    if isinstance(error, BaseException):
        return type(error).__name__
    return str(error)


def _describe(error: BaseException | str) -> str:
    return repr(error) if isinstance(error, BaseException) else str(error)


class OutageTracker:
    """Track the outage state of a single shared resource.

    An outage may involve several *members* (e.g. the individual MQTT client
    connections to one broker).  The outage starts when the first member fails
    and ends once every failing member has recovered.  Callers that do not
    care about members can ignore the argument entirely.

    Args:
        resource: Human-readable resource name used as the log message prefix,
            e.g. ``mqtt://10.0.0.2:1883``.
        reminder_interval: Seconds between "outage continuing" reminders while
            failures keep occurring; ``0`` disables reminders.
        log: Logger used for outage messages (defaults to this module's logger).
    """

    def __init__(self, resource: str, reminder_interval: float = DEFAULT_REMINDER_INTERVAL, log: logging.Logger | None = None) -> None:
        self.resource = resource
        self.reminder_interval = reminder_interval
        self._logger = log or logger
        self._lock = threading.RLock()
        self._members: set[str] = set()
        self._kinds: set[str] = set()
        self._started: float | None = None
        self._last_reminder: float = 0.0
        self._suppressed = 0
        self._first_error = ""

    # ------------------------------------------------------------------ state

    @property
    def active(self) -> bool:
        """``True`` while an outage is in progress."""
        with self._lock:
            return self._started is not None

    @property
    def suppressed(self) -> int:
        """Number of messages demoted to DEBUG during the current outage."""
        with self._lock:
            return self._suppressed

    @property
    def duration(self) -> float:
        """Seconds since the current outage started (``0`` when not active)."""
        with self._lock:
            return 0.0 if self._started is None else time.monotonic() - self._started

    # ---------------------------------------------------------------- updates

    def failure(self, error: BaseException | str, *, member: str | None = None, detail: str | None = None) -> bool:
        """Record a failure of the resource.

        Args:
            error: The exception (or error text) that occurred.
            member: Optional member that failed (e.g. an MQTT client id).
            detail: Optional caller-specific message; it is logged at DEBUG
                whenever this failure does not produce an ERROR of its own.

        Returns:
            ``True`` if this failure was logged at ERROR (outage start or a
            new kind of error); ``False`` if it was suppressed to DEBUG.
        """
        kind = _error_kind(error)
        description = _describe(error)
        now = time.monotonic()
        with self._lock:
            self._members.add(member or _DEFAULT_MEMBER)
            if self._started is None:
                self._started = now
                self._last_reminder = now
                self._suppressed = 0
                self._kinds = {kind}
                self._first_error = description
                self._logger.error(f"{self.resource} outage started: {description}")
                if detail:
                    self._logger.debug(detail)
                return True
            if kind not in self._kinds:
                self._kinds.add(kind)
                self._logger.error(f"{self.resource} outage continuing with a new error after {format_duration(now - self._started)}: {description}")
                if detail:
                    self._logger.debug(detail)
                return True
            self._suppressed += 1
            if detail:
                self._logger.debug(detail)
            if self.reminder_interval > 0 and now - self._last_reminder >= self.reminder_interval:
                self._last_reminder = now
                self._logger.error(f"{self.resource} outage continuing for {format_duration(now - self._started)} ({self._suppressed} similar messages suppressed): {self._first_error}")
            return False

    def suppress(self, detail: str | None = None) -> bool:
        """Demote a message caused by an ongoing outage.

        Returns ``True`` (and logs *detail* at DEBUG) if an outage is active, so
        the caller knows not to log the message itself; ``False`` otherwise.
        """
        with self._lock:
            if self._started is None:
                return False
            self._suppressed += 1
            if detail:
                self._logger.debug(detail)
            return True

    def success(self, *, member: str | None = None) -> bool:
        """Record that the resource (or one *member* of it) is working again.

        With no *member*, every failing member is treated as recovered.

        Returns:
            ``True`` if this call ended the outage.
        """
        with self._lock:
            if self._started is None:
                return False
            if member is None:
                self._members.clear()
            else:
                self._members.discard(member)
            if self._members:
                return False
            duration = time.monotonic() - self._started
            suppressed = self._suppressed
            self._started = None
            self._kinds = set()
            self._suppressed = 0
            self._first_error = ""
        self._logger.info(f"{self.resource} outage ended after {format_duration(duration)} ({suppressed} similar messages suppressed)")
        return True

    def __repr__(self) -> str:
        return f"OutageTracker(resource={self.resource!r}, active={self.active}, suppressed={self.suppressed})"


_trackers: dict[str, OutageTracker] = {}
_trackers_lock = threading.Lock()


def outage_tracker(resource: str) -> OutageTracker:
    """Return the shared :class:`OutageTracker` for *resource*, creating it on first use."""
    with _trackers_lock:
        tracker = _trackers.get(resource)
        if tracker is None:
            tracker = _trackers[resource] = OutageTracker(resource)
        return tracker


def active_outages(prefix: str = "") -> list[OutageTracker]:
    """Return the trackers whose resource starts with *prefix* and have an active outage."""
    with _trackers_lock:
        trackers = [t for r, t in _trackers.items() if r.startswith(prefix)]
    return [t for t in trackers if t.active]


def clear_outage_trackers() -> None:
    """Forget all trackers (intended for tests)."""
    with _trackers_lock:
        _trackers.clear()
