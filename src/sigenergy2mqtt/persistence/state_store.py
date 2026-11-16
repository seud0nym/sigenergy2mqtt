"""StateStore — centralised state persistence with disk + MQTT redundancy.

Architecture
------------
All persisted values are stored in a unified JSON envelope format::

    {"v": "<value>", "ts": <unix_timestamp>, "ver": "<app_version>"}

Both the ``DiskBackend`` and ``MqttBackend`` use this same envelope, enabling
seamless migration between backends and consistent staleness checking via the
``ts`` field rather than filesystem metadata.

Cache warming
-------------
On :meth:`StateStore.initialise`, a dedicated MQTT client subscribes to the
configured state prefix and uses a **sentinel message** to guarantee all
retained messages are received before the method returns:

1. Subscribe to ``{prefix}/#``
2. Publish a non-retained sentinel to ``{prefix}/_sentinel``
3. MQTT guarantees ordering within a single connection — the sentinel arrives
   *after* all retained messages
4. When the sentinel is received, the in-memory cache is complete

The ``cache_warmup_timeout`` setting is a safety limit for degraded broker
conditions; under normal circumstances the sentinel arrives within milliseconds.

Atomic disk writes
------------------
The ``DiskBackend`` never writes a state file in place.  The envelope is
written to a temporary file in the same directory, flushed and ``fsync``-ed,
and then moved over the target with :func:`os.replace`, so an interruption
leaves either the previous content or the new content - never an empty or
partial file.  The parent directory is then synced (best effort) so that the
completed rename itself survives a power cut.  A file that is nevertheless empty or holds a truncated envelope
is treated as absent, so that the other backend is consulted.

Throttled saves
---------------
Callers that persist very frequently (accumulation sensors persist on every
source update) may pass ``min_interval`` to :meth:`StateStore.save`.  A save
that arrives within ``min_interval`` seconds of the previous write for the
same key is held in memory instead of being written; it is returned by
:meth:`StateStore.load`, superseded by the next save, and written when the
interval ends (a timer is armed for that) or by :meth:`StateStore.shutdown`,
whichever comes first.  An unclean exit can therefore lose at most the last
``min_interval`` seconds of such a value, even if no further save arrives.

Legacy migration
----------------
Disk files written by earlier versions of sigenergy2mqtt contain raw values
(plain floats or strings) rather than JSON envelopes.  On load, the
``DiskBackend`` detects these files, reads the raw value, and wraps it in the
current envelope format, using the file's ``st_mtime`` as the timestamp.  The
migrated envelope is written back to disk transparently.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException

if TYPE_CHECKING:
    from sigenergy2mqtt.config.models.persistence import PersistenceConfig


# Sentinel sub-topic appended to the state prefix during cache warming.
_SENTINEL_SUFFIX = "_sentinel"

# Key embedded in every persisted payload.
_PAYLOAD_VALUE_KEY = "v"
_PAYLOAD_TS_KEY = "ts"
_PAYLOAD_VER_KEY = "ver"

logger = logging.getLogger(__name__)


class Category(StrEnum):
    _ROOT = "__root__"
    CONFIG = "config"
    PVOUTPUT = "pvoutput"
    SENSOR = "sensor"


def _make_envelope(value: str, version: str, ts: int | None = None) -> str:
    """Return a JSON-encoded persistence envelope for *value*.

    *ts* is the time the value was produced; it defaults to now.
    """
    return json.dumps({
        _PAYLOAD_VALUE_KEY: value,
        _PAYLOAD_TS_KEY: int(time.time()) if ts is None else int(ts),
        _PAYLOAD_VER_KEY: version,
    })


def _is_same_local_day(ts: float, now: float | None = None) -> bool:
    """Return True when *ts* falls on the same local calendar day as *now*."""
    then = time.localtime(ts)
    today = time.localtime(time.time() if now is None else now)
    return (then.tm_year, then.tm_yday) == (today.tm_year, today.tm_yday)


def _parse_envelope(raw: str, *, fallback_ts: int | None = None) -> tuple[str, int, bool] | None:
    """Parse a persistence envelope, returning ``(value, ts, was_legacy)`` or ``None`` on error.

    If *raw* is not valid JSON or lacks the expected keys it is treated as a
    legacy raw value and wrapped automatically.  ``fallback_ts`` is used as the
    timestamp when migrating legacy content (typically the file's ``st_mtime``).

    ``None`` is returned for content that cannot be a value at all: an empty
    (or whitespace/NUL-only) payload, as left behind by an interrupted write,
    or a truncated JSON object.  Callers treat that as "absent".
    """
    stripped = raw.strip().strip("\x00").strip()
    if not stripped:
        logger.debug("StateStore: empty payload detected, treating as absent")
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and _PAYLOAD_VALUE_KEY in obj and _PAYLOAD_TS_KEY in obj:
            return str(obj[_PAYLOAD_VALUE_KEY]), int(obj[_PAYLOAD_TS_KEY]), False
    except (json.JSONDecodeError, ValueError, TypeError):
        if stripped.startswith("{"):
            # Legacy values are plain numbers/strings; an undecodable JSON object is a truncated envelope
            logger.debug("StateStore: truncated envelope detected, treating as absent")
            return None
        logger.debug("StateStore: invalid envelope detected, treating as legacy value")

    # Legacy / raw value — treat the whole string as the value.
    ts = fallback_ts if fallback_ts is not None else int(time.time())
    return raw.strip(), ts, True


# ---------------------------------------------------------------------------
# DiskBackend
# ---------------------------------------------------------------------------


class _DiskBackend:
    """Filesystem-backed persistence using the unified JSON envelope format."""

    def __init__(self, state_path: Path, version: str) -> None:
        self._state_path = state_path
        self._version = version
        self._write_lock = threading.Lock()

    @staticmethod
    def _temp_path_for(path: Path) -> Path:
        return path.with_name(f".{path.name}.tmp")

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Best-effort ``fsync`` of *directory* so a completed rename is durable.

        Not every platform or filesystem can open or sync a directory; the
        write itself has already succeeded, so failures are ignored.
        """
        try:
            fd = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)

    @staticmethod
    def _is_temp_file(path: Path) -> bool:
        return path.name.startswith(".") and path.name.endswith(".tmp")

    def _path_for(self, category: Category | str, key: str) -> Path:
        if ".." in str(category) or ".." in key:
            raise ValueError(f"Invalid category or key: {category}/{key}")
        return self._state_path / str(category) / key

    def save(self, category: Category | str, key: str, value: str, ts: int | None = None) -> None:
        """Atomically write *value* to disk under ``{state_path}/{category}/{key}``.

        The envelope is written to a temporary file in the same directory,
        synced, and then renamed over the target, so a crash or power loss
        mid-write cannot leave an empty or partial state file.
        """
        from sigenergy2mqtt.config import active_config

        path = self._path_for(category, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = _make_envelope(value, self._version, ts)
        tmp = self._temp_path_for(path)
        with self._write_lock:
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(envelope)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
                self._sync_directory(path.parent)
            except BaseException:
                with contextlib.suppress(OSError):
                    tmp.unlink(missing_ok=True)
                raise
        if active_config.persistence_debug:
            logger.debug(f"DiskBackend.save {category}/{key}")

    def load(self, category: Category | str, key: str) -> tuple[str, int, bool, bool] | None:
        """Read and return ``(value, ts, was_legacy, found_in_root)`` from disk, or ``None`` if absent.

        Legacy files containing raw (non-JSON-envelope) content are migrated
        automatically on first read.  Legacy files from the root state directory
        are also moved into their respective category subdirectories.

        An empty or truncated file is reported as absent (``None``) so that the
        caller falls back to the other backend.
        """
        path = self._path_for(category, key)
        found_in_root = False
        if not path.is_file():
            # Try falling back to the root state directory (the legacy structure)
            # if we don't have a file in the category-prefixed path yet.
            root_path = self._state_path / key
            if root_path.is_file():
                path = root_path
                found_in_root = True
            else:
                return None

        try:
            raw = path.read_text(encoding="utf-8")
            mtime = int(path.stat().st_mtime)
            result = _parse_envelope(raw, fallback_ts=mtime)
            if result is None:
                logger.warning(f"DiskBackend.load ignored empty or corrupt state file for {category}/{key}")
                return None
            value, ts, was_legacy = result

            return value, ts, was_legacy, found_in_root
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(f"DiskBackend.load failed for {category}/{key}: {exc}")
            return None

    def delete(self, category: Category | str, key: str) -> None:
        """Remove the state file for *category*/*key* if it exists, including legacy root positions."""
        from sigenergy2mqtt.config import active_config

        # Remove from the category subdirectory
        path = self._path_for(category, key)
        try:
            path.unlink(missing_ok=True)
            if active_config.persistence_debug:
                logger.debug(f"DiskBackend.delete {category}/{key} successful")
        except OSError as exc:
            logger.error(f"DiskBackend.delete failed for {category}/{key}: {exc}")

        # Also remove from the legacy root state directory if present
        root_path = self._state_path / key
        if root_path.is_file():
            try:
                root_path.unlink()
                if active_config.persistence_debug:
                    logger.debug(f"DiskBackend.delete legacy root file {key}")
            except OSError as exc:
                logger.warning(f"DiskBackend.delete failed for legacy root file {key}: {exc}")

    def delete_root_legacy(self, key: str) -> None:
        """Explicitly remove a legacy file from the root state path."""
        root_path = self._state_path / key
        try:
            root_path.unlink(missing_ok=True)
        except OSError:
            pass

    def all_keys(self) -> list[tuple[Category | str, str]]:
        """Return all ``(category, key)`` pairs currently on disk."""
        results: list[tuple[Category | str, str]] = []
        if not self._state_path.is_dir():
            return results

        # Include legacy root files
        for file in self._state_path.iterdir():
            if file.is_file() and not self._is_temp_file(file):
                results.append((Category._ROOT, file.name))

        for category_dir in self._state_path.iterdir():
            if category_dir.is_dir():
                name = category_dir.name
                try:
                    category = Category(name)
                except ValueError:
                    category = name
                for file in category_dir.iterdir():
                    if file.is_file() and not self._is_temp_file(file):
                        results.append((category, file.name))

        return results


# ---------------------------------------------------------------------------
# MqttBackend
# ---------------------------------------------------------------------------


class _MqttBackend:
    """In-memory MQTT cache populated from retained broker messages."""

    def __init__(self) -> None:
        # Maps (category, key) -> (value, ts)
        self._cache: dict[tuple[Category | str, str], tuple[str, int]] = {}
        self._lock = threading.Lock()

        self._retry_queue = deque()
        self._max_retries = 3
        self._base_delay = 0.5

        self._prefix = ""
        self._sentinel_topic = ""
        self._sentinel_event = threading.Event()
        self._version: str = ""

    def configure(self, prefix: str, version: str) -> None:
        self._prefix = prefix
        self._sentinel_topic = f"{prefix}/{_SENTINEL_SUFFIX}"
        self._version = version

    def _schedule_retry(self, attempt, fn, *args) -> None:
        if attempt >= self._max_retries:
            logger.warning("MqttBackend: dropping message after %d retries", attempt)
            return
        delay = self._base_delay * (2**attempt)
        self._retry_queue.append((time.time() + delay, attempt + 1, fn, args))

    def _drain_retries(self, client) -> None:
        now = time.time()
        while self._retry_queue:
            ts, attempt, fn, args = self._retry_queue[0]
            if ts > now:
                break
            self._retry_queue.popleft()
            try:
                fn(client, *args, _attempt=attempt)
            except (ValueError, TypeError, RuntimeError):
                arg_desc = "/".join(str(a) for a in args) if args else "unknown"
                logger.warning("MqttBackend: retry failed for %s on attempt %d", arg_desc, attempt)

    def _topic_to_key(self, topic: str) -> tuple[Category | str, str] | None:
        """Convert an MQTT topic to ``(category, key)`` or ``None`` if not ours."""
        if not topic.startswith(self._prefix + "/"):
            return None
        rest = topic[len(self._prefix) + 1 :]
        parts = rest.split("/", 1)
        if len(parts) != 2:
            return None
        category, key = parts
        if key == _SENTINEL_SUFFIX:
            return None  # ignore the sentinel itself
        try:
            return Category(category), key
        except ValueError:
            return category, key

    def _key_to_topic(self, category: Category | str, key: str) -> str:
        return f"{self._prefix}/{category!s}/{key}"

    def on_message(self, client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        """Handle an incoming MQTT message — either retained state or the sentinel."""
        if msg.topic == self._sentinel_topic:
            logger.debug("MqttBackend: sentinel received — cache warming complete")
            self._sentinel_event.set()
            return

        key_pair = self._topic_to_key(msg.topic)
        if key_pair is None:
            return

        category, key = key_pair
        if not msg.payload:
            # Empty payload = delete
            with self._lock:
                self._cache.pop(key_pair, None)
            return

        raw = msg.payload.decode("utf-8", errors="replace")
        result = _parse_envelope(raw)
        if result is not None:
            value, ts, _ = result
            with self._lock:
                self._cache[key_pair] = (value, ts)
            from sigenergy2mqtt.config import active_config

            if active_config.persistence_debug:
                logger.debug(f"MqttBackend: cached {category}/{key} (ts={ts})")

    def publish(self, client: mqtt.Client, category: Category | str, key: str, value: str, ts: int | None = None, _attempt: int = 0) -> None:
        """Publish a retained state message."""
        from sigenergy2mqtt.config import active_config

        self._drain_retries(client)
        topic = self._key_to_topic(category, key)
        envelope = _make_envelope(value, self._version, ts)
        try:
            info = client.publish(topic, envelope, qos=2, retain=True)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(info.rc)
        except RuntimeError:
            self._schedule_retry(_attempt, self.publish, category, key, value, ts)
            return
        if active_config.persistence_debug:
            logger.debug(f"MqttBackend.publish {category}/{key}")

    def publish_delete(self, client: mqtt.Client, category: Category | str, key: str, _attempt: int = 0) -> None:
        """Clear a retained message by publishing an empty payload."""
        from sigenergy2mqtt.config import active_config

        self._drain_retries(client)
        topic = self._key_to_topic(category, key)
        try:
            info = client.publish(topic, b"", qos=1, retain=True)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(info.rc)
            info.wait_for_publish(timeout=5.0)
            if active_config.persistence_debug:
                logger.debug(f"MqttBackend.publish_delete {topic} successful")
        except RuntimeError as error:
            logger.error(f"MqttBackend.publish_delete {topic} rescheduled after failing on attempt {_attempt}: {error}")
            self._schedule_retry(_attempt, self.publish_delete, category, key)
            return

        with self._lock:
            self._cache.pop((category, key), None)

        if active_config.persistence_debug:
            logger.debug(f"MqttBackend.publish_delete {category}/{key}")

    def load(self, category: Category | str, key: str) -> tuple[str, int] | None:
        """Return cached ``(value, ts)`` or ``None``."""
        with self._lock:
            return self._cache.get((category, key))

    def all_known_keys(self) -> list[tuple[Category | str, str]]:
        """All ``(category, key)`` pairs currently held in the in-memory cache."""
        with self._lock:
            return list(self._cache.keys())

    def publish_sentinel(self, client: mqtt.Client) -> None:
        """Publish the non-retained sentinel to trigger end-of-retained-messages."""
        info = client.publish(self._sentinel_topic, b"1", qos=2, retain=False)
        info.wait_for_publish(timeout=5.0)
        logger.debug("MqttBackend: sentinel published")

    def wait_for_sentinel(self, timeout: float) -> bool:
        """Block until sentinel received or *timeout* seconds elapse.

        Returns True if the sentinel was received within the timeout.
        """
        return self._sentinel_event.wait(timeout=timeout)


# ---------------------------------------------------------------------------
# StateStore
# ---------------------------------------------------------------------------


class StateStore:
    """Centralised state persistence with disk + MQTT redundancy.

    Provides a unified interface for saving, loading and deleting persisted
    state.  Writes are dispatched to a background ``ThreadPoolExecutor``
    (``max_workers=1``) so they never block the asyncio event loop, mirroring
    the pattern used by :class:`~sigenergy2mqtt.metrics.metrics.Metrics`.

    The store is **degradation-safe**: if the MQTT backend is unavailable,
    disk operations continue normally.  If both are unavailable, operations
    are logged as warnings and silently skipped.
    """

    def __init__(self) -> None:
        self._disk: _DiskBackend | None = None
        self._mqtt: _MqttBackend = _MqttBackend()
        self._client: mqtt.Client | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._initialised: bool = False
        self._mqtt_enabled: bool = False
        self._mqtt_cache_warmed: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread_id: int | None = None
        self._disk_primary: bool = False
        self._version: str = ""
        self._sync_timeout: float = 5.0
        # Throttled saves: (category, key) -> (value, ts) held in memory until the next write or shutdown
        self._deferred: dict[tuple[str, str], tuple[str, int]] = {}
        self._last_write: dict[tuple[str, str], float] = {}
        self._flush_timers: dict[tuple[str, str], threading.Timer] = {}
        # Bumped whenever a key is written immediately or deleted, so a queued timer write that
        # has been overtaken can tell. A save that is merely held back does NOT bump it: its
        # value is not written yet, so the queued (older) write must still go ahead.
        self._generation: dict[tuple[str, str], int] = {}
        self._deferred_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialised(self) -> bool:
        """True once :meth:`initialise` has completed (sentinel received or timed out)."""
        return self._initialised

    def has_persisted_entries(self) -> bool | None:
        """Return whether prior state exists, or None if the MQTT cache is uncertain.

        The auto-discovery YAML file is generated during configuration loading,
        before this store is initialised, so it is excluded from installation
        cohort detection.
        """
        if not self._initialised or self._disk is None:
            return None

        mqtt_keys = self._mqtt.all_known_keys() if self._mqtt_enabled else []
        try:
            disk_keys = [key for key in self._disk.all_keys() if key != (Category._ROOT, "auto-discovery.yaml")]
        except OSError as exc:
            logger.warning(f"DiskBackend.all_keys failed during persisted-state detection: {exc}")
            # An unreadable directory makes the disk result inconclusive. MQTT
            # can still prove prior state, but an empty cache cannot prove its absence.
            return True if mqtt_keys else None

        if disk_keys or mqtt_keys:
            return True
        if self._mqtt_enabled and not self._mqtt_cache_warmed:
            return None
        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialise(
        self,
        state_path: Path,
        persistence_config: PersistenceConfig,
    ) -> None:
        """Connect the persistence MQTT client, warm the in-memory cache, then return.

        After this method returns, :attr:`is_initialised` is ``True`` and all
        retained state previously published to the broker is available via
        :meth:`load`.

        Args:
            state_path:         Root directory for disk-based state files.
            persistence_config: Persistence-specific settings.
        """
        # Capture the version string here to avoid circular imports at module level.
        from sigenergy2mqtt.config import version as _ver

        self._mqtt_cache_warmed = False
        self._version = _ver.__version__
        with self._deferred_lock:
            self._clear_deferred_locked()

        self._loop = asyncio.get_running_loop()
        self._loop_thread_id = threading.get_ident()
        self._disk = _DiskBackend(state_path, self._version)
        self._mqtt_enabled = persistence_config.mqtt_redundancy
        self._disk_primary = persistence_config.disk_primary
        self._sync_timeout = persistence_config.sync_timeout
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="persistence")

        if not self._mqtt_enabled:
            logger.info("StateStore: MQTT redundancy disabled — disk only")
            self._mqtt_cache_warmed = True
            self._initialised = True
            return

        prefix = persistence_config.mqtt_state_prefix
        timeout = persistence_config.cache_warmup_timeout
        self._mqtt.configure(prefix, self._version)

        # Build a dedicated MQTT client for persistence traffic.
        # (Lazy import to prevent circular references)
        from sigenergy2mqtt.config import active_config
        from sigenergy2mqtt.mqtt import mqtt_setup

        try:
            client_id = f"{active_config.mqtt.client_id_prefix}_persistence"
            # Wait for the broker: nothing can be published until it is reachable anyway, and
            # giving up would leave persistence without MQTT redundancy for the whole runtime
            client, _ = await mqtt_setup(client_id, None, self._loop, max_attempts=None)
            client.on_message = self._mqtt.on_message
        except (MQTTException, ValueError, OSError, RuntimeError) as exc:
            logger.warning(f"StateStore: MQTT connection failed ({exc}) — disk only")
            self._initialised = True
            return

        self._client = client

        # Subscribe to the full state namespace.
        client.subscribe(f"{prefix}/#", qos=2)

        # Publish sentinel and wait for it to come back, guaranteeing all
        # retained messages have been delivered first.
        logger.debug(f"StateStore: publishing sentinel, waiting up to {timeout:.1f}s for cache warm-up")
        self._mqtt.publish_sentinel(client)

        # Wait in a thread so as not to block the asyncio event loop.
        received = await self._loop.run_in_executor(None, lambda: self._mqtt.wait_for_sentinel(timeout))
        self._mqtt_cache_warmed = received

        if received:
            logger.info(f"StateStore: cache warm-up complete ({len(self._mqtt.all_known_keys())} entries)")
        else:
            logger.warning(f"StateStore: cache warm-up timed out after {timeout:.1f}s — some MQTT state may be unavailable. Disk fallback will be used where possible.")

        self._initialised = True

    def shutdown(self) -> None:
        """Flush pending writes, disconnect the persistence MQTT client, and stop the executor."""
        # Stop the flush timers and wait for any callback that has already
        # started: it has taken its value and is queuing the write, which the
        # executor shutdown below must not miss.
        with self._deferred_lock:
            timers = list(self._flush_timers.values())
            for timer in timers:
                timer.cancel()
            self._flush_timers.clear()
        for timer in timers:
            if timer.is_alive() and timer is not threading.current_thread():
                timer.join(timeout=self._sync_timeout)

        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None

        # Write out throttled saves only after the executor has drained, so
        # that a queued older value cannot overwrite the newer deferred one.
        with self._deferred_lock:
            pending = list(self._deferred.items())
            self._clear_deferred_locked()
        if pending and self._disk is not None:
            for (category, key), (value, ts) in pending:
                self._save_sync_impl(category, key, value, ts)
            logger.debug(f"StateStore: flushed {len(pending)} deferred entries")

        if self._client:
            try:
                from sigenergy2mqtt.config import active_config

                if active_config.clean and hasattr(self._client, "publish_status"):
                    try:
                        # Leave nothing retained behind
                        self._client.publish_status("").wait_for_publish(timeout=2.0)  # type: ignore[attr-defined]
                    except (RuntimeError, ValueError) as exc:
                        logger.debug(f"StateStore: unable to clear the connection status topic: {exc}")
                self._client.loop_stop()
                self._client.disconnect()
            except RuntimeError as exc:
                logger.debug(f"StateStore: error during MQTT disconnect: {exc}")
            self._client = None

        self._initialised = False
        logger.info("StateStore: shutdown complete")

    # ------------------------------------------------------------------
    # Core async API
    # ------------------------------------------------------------------

    def _defer_or_claim(self, category: Category | str, key: str, value: str, min_interval: float | None) -> bool:
        """Return True if *value* was held back because the key was written less than *min_interval* seconds ago.

        Otherwise the caller must write *value* now: the key's last-write time
        is updated and any older deferred value is discarded.
        """
        k = (str(category), key)
        now = time.monotonic()
        with self._deferred_lock:
            last = self._last_write.get(k)
            if min_interval is not None and min_interval > 0 and last is not None and (now - last) < min_interval:
                self._deferred[k] = (value, int(time.time()))
                if k not in self._flush_timers:
                    # Make sure the held-back value is written when the interval
                    # ends, even if no further save arrives for this key.
                    timer = threading.Timer(min_interval - (now - last), self._flush_deferred, args=(k,))
                    timer.daemon = True
                    self._flush_timers[k] = timer
                    timer.start()
                return True
            self._last_write[k] = now
            self._generation[k] = self._generation.get(k, 0) + 1
            self._deferred.pop(k, None)
            self._cancel_flush_timer_locked(k)
            return False

    def _cancel_flush_timer_locked(self, k: tuple[str, str]) -> None:
        timer = self._flush_timers.pop(k, None)
        if timer is not None:
            timer.cancel()

    def _clear_deferred_locked(self) -> None:
        for timer in self._flush_timers.values():
            timer.cancel()
        self._flush_timers.clear()
        self._deferred.clear()
        self._last_write.clear()
        for k in self._generation:
            self._generation[k] += 1  # invalidate any timer write already queued

    def _flush_deferred(self, k: tuple[str, str]) -> None:
        """Write the value held back for *k*; runs on a timer thread when its interval ends.

        The value is taken and its write queued while holding the lock that
        every save and delete takes first, so a reset or deletion that arrives
        later is always queued behind this write, never ahead of it.
        """
        with self._deferred_lock:
            self._flush_timers.pop(k, None)
            entry = self._deferred.pop(k, None)
            if entry is None or self._disk is None:
                return
            self._last_write[k] = time.monotonic()
            generation = self._generation.get(k, 0)
            value, ts = entry
            try:
                if self._executor is None:
                    raise RuntimeError("executor stopped")
                self._executor.submit(self._write_flushed, k, value, ts, generation)
                return
            except RuntimeError:
                # Shutting down: put the value back for shutdown() to write
                self._deferred[k] = entry

    def _write_flushed(self, k: tuple[str, str], value: str, ts: int, generation: int) -> None:
        """Write a timer-flushed value unless a newer save or delete has overtaken it."""
        with self._deferred_lock:
            if self._generation.get(k, 0) != generation:
                return
        self._save_sync_impl(k[0], k[1], value, ts)

    def _discard_deferred(self, category: Category | str, key: str) -> None:
        k = (str(category), key)
        with self._deferred_lock:
            self._generation[k] = self._generation.get(k, 0) + 1
            self._deferred.pop(k, None)
            self._last_write.pop(k, None)
            self._cancel_flush_timer_locked(k)

    async def save(self, category: Category | str, key: str, value: str, *, stale_after: timedelta | None = None, min_interval: float | None = None) -> None:
        """Persist *value* to both disk and MQTT (fire-and-forget via executor).

        Args:
            category:     Logical grouping (e.g. ``"sensor"``, ``"pvoutput"``, ``"config"``).
            key:          File/topic name within the category.
            value:        String value to persist.
            stale_after:  Unused on save; present for API symmetry with :meth:`load`.
            min_interval: If set, write this key at most once per this many seconds.
                          A save inside the interval is held in memory (still visible
                          to :meth:`load`) and written by a later save or by
                          :meth:`shutdown`.
        """
        from sigenergy2mqtt.config import active_config

        if not self._initialised or self._executor is None:
            if active_config.persistence_debug:
                logger.debug(f"StateStore.save called before initialise — skipping {category}/{key}")
            return
        if self._defer_or_claim(category, key, value, min_interval):
            if active_config.persistence_debug:
                logger.debug(f"StateStore.save deferred {category}/{key} ({min_interval=})")
            return
        # Stamp the value with the time the save was requested, not the time the
        # queued write happens to run: a total saved just before midnight must
        # not be dated the next day.
        ts = int(time.time())
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._save_sync_impl, category, key, value, ts)

    async def load(
        self,
        category: Category | str,
        key: str,
        *,
        stale_after: timedelta | None = None,
        validator: Callable[[str], bool] | None = None,
        same_local_day: bool = False,
    ) -> str | None:
        """Load a persisted value, applying staleness check and optional validator.

        Tries disk first (if ``disk_primary`` is True),then falls back to
        the MQTT retained-message cache.  If MQTT is the primary, the order
        is reversed.

        Args:
            category:    Logical grouping.
            key:         File/topic name within the category.
            stale_after: If set, values older than this timedelta are discarded.
            validator:   Optional callable that asserts the loaded value is valid;
                         returns False to discard the value.
            same_local_day: If True, values not written on the current local
                         calendar day are discarded.

        Returns:
            The persisted value string, or ``None`` if absent/stale/invalid.
        """
        if not self._initialised or self._disk is None:
            return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._load_sync_impl,
            category,
            key,
            stale_after,
            validator,
            same_local_day,
        )

    async def delete(self, category: Category | str, key: str) -> None:
        """Remove *category*/*key* from both backends.

        MQTT removal is achieved by publishing an empty retained message,
        which instructs the broker to clear the retained payload.
        """
        if not self._initialised or self._executor is None:
            return
        self._discard_deferred(category, key)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._delete_sync_impl, category, key)

    async def clean(self) -> None:
        """Clear all persisted state from both backends.

        Called when ``active_config.clean`` is ``True``.  Removes every disk
        file under ``state_path`` and publishes empty retained messages to every
        topic in the MQTT backend cache.
        """
        if not self._initialised or self._executor is None:
            return
        with self._deferred_lock:
            self._clear_deferred_locked()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._clean_all_sync_impl)

    # ------------------------------------------------------------------
    # Synchronous wrappers (for use from Config.reload() sync context)
    # ------------------------------------------------------------------

    def save_sync(self, category: Category | str, key: str, value: str) -> None:
        """Synchronous wrapper for :meth:`save`.

        When called from a synchronous context while an asyncio event loop is
        running (e.g. from :meth:`~sigenergy2mqtt.config.config.Config.reload`),
        uses :func:`asyncio.run_coroutine_threadsafe` to submit the work.
        Otherwise falls back to direct execution.
        """
        if not self._initialised or self._executor is None:
            return
        loop = self._loop
        if loop is not None and loop.is_running() and threading.get_ident() != self._loop_thread_id:
            future = asyncio.run_coroutine_threadsafe(self.save(category, key, value), loop)
            try:
                future.result(timeout=self._sync_timeout)
            except TimeoutError as exc:
                future.cancel()
                logger.warning(f"StateStore.save_sync failed for {category}/{key}: {exc!r}")
        else:
            self._defer_or_claim(category, key, value, None)
            self._save_sync_impl(category, key, value, int(time.time()))

    def load_sync(
        self,
        category: Category | str,
        key: str,
        *,
        stale_after: timedelta | None = None,
        validator: Callable[[str], bool] | None = None,
        same_local_day: bool = False,
    ) -> str | None:
        """Synchronous wrapper for :meth:`load`.

        Uses :func:`asyncio.run_coroutine_threadsafe` when called from a
        synchronous context inside a running event loop.
        """
        if not self._initialised or self._disk is None:
            return None
        loop = self._loop
        if loop is not None and loop.is_running() and threading.get_ident() != self._loop_thread_id:
            future = asyncio.run_coroutine_threadsafe(self.load(category, key, stale_after=stale_after, validator=validator, same_local_day=same_local_day), loop)
            try:
                return future.result(timeout=self._sync_timeout)
            except TimeoutError as exc:
                future.cancel()
                logger.warning(f"StateStore.load_sync failed for {category}/{key}: {exc!r}")
                return None
        else:
            return self._load_sync_impl(category, key, stale_after, validator, same_local_day)

    def delete_sync(self, category: Category | str, key: str) -> None:
        """Synchronous wrapper for :meth:`delete`."""
        if not self._initialised or self._executor is None:
            return
        loop = self._loop
        if loop is not None and loop.is_running() and threading.get_ident() != self._loop_thread_id:
            future = asyncio.run_coroutine_threadsafe(self.delete(category, key), loop)
            try:
                future.result(timeout=self._sync_timeout)
            except TimeoutError as exc:
                future.cancel()
                logger.warning(f"StateStore.delete_sync failed for {category}/{key}: {exc!r}")
        else:
            self._discard_deferred(category, key)
            self._delete_sync_impl(category, key)

    def _accept(self, value: str, ts: int, cutoff: int | None, validator: Callable[[str], bool] | None, same_local_day: bool = False) -> bool:
        from sigenergy2mqtt.config import active_config

        if same_local_day and not _is_same_local_day(ts):
            if active_config.persistence_debug:
                logger.debug(f"StateStore: discarding value from a previous day (ts={ts})")
            return False
        if cutoff is not None and ts < cutoff:
            if active_config.persistence_debug:
                logger.debug(f"StateStore: discarding stale value (ts={ts} cutoff={cutoff})")
            return False
        if validator is not None and not validator(value):
            if active_config.persistence_debug:
                logger.debug("StateStore: validator rejected value")
            return False
        return True

    def _load_from_backend(self, backend: str, category: Category | str, key: str) -> tuple[str, int, bool, bool] | None:
        if backend == "disk":
            assert self._disk is not None
            return self._disk.load(category, key)
        elif backend == "mqtt" and self._mqtt_enabled:
            res = self._mqtt.load(category, key)
            if res is not None:
                value, ts = res
                return value, ts, False, False
        return None

    def _fire_metric(self, method_name: str, *args) -> None:
        """Schedule a :class:`~sigenergy2mqtt.metrics.Metrics` coroutine from any thread.

        Called from the ThreadPoolExecutor so we cannot ``await`` directly.
        Instead we use :func:`asyncio.run_coroutine_threadsafe` to post the
        coroutine back onto the owning event loop. The future is intentionally
        dropped — metrics are fire-and-forget.
        """
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        try:
            from sigenergy2mqtt.metrics import Metrics

            coro_fn = getattr(Metrics, method_name, None)
            if coro_fn is None:
                return
            asyncio.run_coroutine_threadsafe(coro_fn(*args), loop)
        except (AttributeError, RuntimeError):
            pass

    def _save_sync_impl(self, category: Category | str, key: str, value: str, ts: int | None = None) -> None:
        """Write to disk and MQTT; called from the ThreadPoolExecutor.

        *ts* is the time the value was produced. Both backends (and any MQTT
        retry) carry the same timestamp.
        """
        assert self._disk is not None
        if ts is None:
            ts = int(time.time())
        t0 = time.perf_counter()
        error = False
        try:
            self._disk.save(category, key, value, ts)
        except (OSError, ValueError) as exc:
            error = True
            logger.warning(f"StateStore: disk save failed for {category}/{key}: {exc}")

        if self._mqtt_enabled and self._client is not None:
            try:
                self._mqtt.publish(self._client, category, key, value, ts)
            except (RuntimeError, ValueError) as exc:
                error = True
                logger.warning(f"StateStore: MQTT publish failed for {category}/{key}: {exc}")

        elapsed = time.perf_counter() - t0
        if error:
            self._fire_metric("state_store_save_error")
        else:
            self._fire_metric("state_store_save", elapsed)

    def _load_sync_impl(
        self,
        category: Category | str,
        key: str,
        stale_after: timedelta | None,
        validator: Callable[[str], bool] | None,
        same_local_day: bool = False,
    ) -> str | None:
        """Read from backends in priority order; called from the ThreadPoolExecutor."""
        from sigenergy2mqtt.config import active_config

        assert self._disk is not None

        cutoff: int | None = None
        if stale_after is not None:
            cutoff = int(time.time() - stale_after.total_seconds())

        # A throttled save that has not been written yet is newer than either backend.
        with self._deferred_lock:
            deferred = self._deferred.get((str(category), key))
        if deferred is not None and self._accept(deferred[0], deferred[1], cutoff, validator, same_local_day):
            self._fire_metric("state_store_load", True)
            return deferred[0]

        # Determine backend order.
        backends_primary_first: list[str] = ["disk", "mqtt"] if not self._mqtt_enabled or self._disk_primary else ["mqtt", "disk"]

        for backend in backends_primary_first:
            result = self._load_from_backend(backend, category, key)
            if result is not None:
                value, ts, was_legacy, found_in_root = result
                if self._accept(value, ts, cutoff, validator, same_local_day):
                    if was_legacy or found_in_root:
                        if active_config.persistence_debug:
                            logger.debug(f"StateStore.load migrating legacy file {category}/{key}")
                        self._save_sync_impl(category, key, value, ts)  # keep the original time
                        if found_in_root:
                            self._disk.delete_root_legacy(key)

                    if active_config.persistence_debug:
                        logger.debug(f"StateStore.load {category}/{key} from {backend} (ts={ts})")
                    self._fire_metric("state_store_load", True)
                    return value

        self._fire_metric("state_store_load", False)
        return None

    def _delete_sync_impl(self, category: Category | str, key: str) -> None:
        """Remove from disk and MQTT; called from the ThreadPoolExecutor."""
        assert self._disk is not None
        error = False
        self._disk.delete(category, key)

        if self._mqtt_enabled and self._client is not None:
            try:
                self._mqtt.publish_delete(self._client, category, key)
            except (RuntimeError, ValueError) as exc:
                error = True
                logger.warning(f"StateStore: MQTT delete failed for {category}/{key}: {exc}")

        self._fire_metric("state_store_delete_error" if error else "state_store_delete")

    def _clean_all_sync_impl(self) -> None:
        """Clear all state from both backends; called from the ThreadPoolExecutor."""
        assert self._disk is not None
        disk_keys = self._disk.all_keys()
        logger.debug(f"StateStore: Removing {len(disk_keys)} disk entries")
        for category, key in disk_keys:
            self._disk.delete(category, key)
        logger.info(f"StateStore: Cleaned {len(disk_keys)} disk entries")

        if self._mqtt_enabled and self._client is not None:
            # Clear any keys known from the MQTT cache (may include entries with
            # no matching disk file on this host, e.g. restored from another machine).
            mqtt_keys = self._mqtt.all_known_keys()
            logger.debug(f"StateStore: Removing {len(mqtt_keys)} MQTT entries")
            removed: int = 0
            for category, key in mqtt_keys:
                try:
                    self._mqtt.publish_delete(self._client, category, key)
                    removed += 1
                except (RuntimeError, ValueError) as exc:
                    logger.warning(f"StateStore: MQTT clean failed for {category}/{key}: {exc}")
            logger.info(f"StateStore: Cleaned {removed} MQTT entries")
        else:
            logger.info("StateStore: MQTT not enabled, skipping MQTT clean")
