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
import json
import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from sigenergy2mqtt.config.models.persistence import PersistenceConfig


# Sentinel sub-topic appended to the state prefix during cache warming.
_SENTINEL_SUFFIX = "_sentinel"

# Key embedded in every persisted payload.
_PAYLOAD_VALUE_KEY = "v"
_PAYLOAD_TS_KEY = "ts"
_PAYLOAD_VER_KEY = "ver"


class Category(str, Enum):
    SENSOR = "sensor"
    PVOUTPUT = "pvoutput"
    CONFIG = "config"


def _make_envelope(value: str, version: str) -> str:
    """Return a JSON-encoded persistence envelope for *value*."""
    return json.dumps(
        {
            _PAYLOAD_VALUE_KEY: value,
            _PAYLOAD_TS_KEY: int(time.time()),
            _PAYLOAD_VER_KEY: version,
        }
    )


def _parse_envelope(raw: str, *, fallback_ts: int | None = None) -> tuple[str, int, bool] | None:
    """Parse a persistence envelope, returning ``(value, ts, was_legacy)`` or ``None`` on error.

    If *raw* is not valid JSON or lacks the expected keys it is treated as a
    legacy raw value and wrapped automatically.  ``fallback_ts`` is used as the
    timestamp when migrating legacy content (typically the file's ``st_mtime``).
    """
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and _PAYLOAD_VALUE_KEY in obj and _PAYLOAD_TS_KEY in obj:
            return str(obj[_PAYLOAD_VALUE_KEY]), int(obj[_PAYLOAD_TS_KEY]), False
    except (json.JSONDecodeError, ValueError, TypeError):
        logging.debug("StateStore: invalid envelope detected, treating as legacy value")

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

    def _path_for(self, category: str, key: str) -> Path:
        return self._state_path / category / key

    def save(self, category: str, key: str, value: str, debug: bool = True) -> None:
        """Write *value* to disk under ``{state_path}/{category}/{key}``."""
        path = self._path_for(category, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = _make_envelope(value, self._version)
        path.write_text(envelope, encoding="utf-8")
        if debug:
            logging.debug(f"DiskBackend.save {category}/{key}")

    def load(self, category: str, key: str, debug: bool = True) -> tuple[str, int] | None:
        """Read and return ``(value, ts)`` from disk, or ``None`` if absent.

        Legacy files containing raw (non-JSON-envelope) content are migrated
        automatically on first read.  Legacy files from the root state directory
        are also moved into their respective category subdirectories.
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
                return None
            value, ts, was_legacy = result

            # We migrate if:
            # 1. The content was legacy (non-envelope)
            # 2. OR the file was picked up from the root directory instead of the category dir.
            if was_legacy or found_in_root:
                if debug:
                    logging.debug(f"DiskBackend.load migrating legacy file {category}/{key}")
                self.save(category, key, value, debug=debug)

                # If we've successfully migrated it from the root, remove the old one.
                if found_in_root:
                    try:
                        path.unlink()
                        if debug:
                            logging.debug(f"DiskBackend.load deleted migrated root file {key}")
                    except OSError as exc:
                        logging.warning(f"DiskBackend.load failed to delete migrated root file {key}: {exc}")

            return value, ts
        except OSError as exc:
            logging.warning(f"DiskBackend.load failed for {category}/{key}: {exc}")
            return None

    def delete(self, category: str, key: str, debug: bool = True) -> None:
        """Remove the state file for *category*/*key* if it exists."""
        path = self._path_for(category, key)
        try:
            path.unlink(missing_ok=True)
            if debug:
                logging.debug(f"DiskBackend.delete {category}/{key}")
        except OSError as exc:
            logging.warning(f"DiskBackend.delete failed for {category}/{key}: {exc}")

    def all_keys(self) -> list[tuple[str, str]]:
        """Return all ``(category, key)`` pairs currently on disk."""
        results: list[tuple[str, str]] = []
        if not self._state_path.is_dir():
            return results

        # Include legacy root files
        for file in self._state_path.iterdir():
            if file.is_file():
                results.append(("__root__", file.name))

        for category_dir in self._state_path.iterdir():
            if category_dir.is_dir():
                for file in category_dir.iterdir():
                    if file.is_file():
                        results.append((category_dir.name, file.name))

        return results


# ---------------------------------------------------------------------------
# MqttBackend
# ---------------------------------------------------------------------------


class _MqttBackend:
    """In-memory MQTT cache populated from retained broker messages."""

    def __init__(self) -> None:
        # Maps (category, key) -> (value, ts)
        self._cache: dict[tuple[str, str], tuple[str, int]] = {}
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
            logging.warning("MqttBackend: dropping message after %d retries", attempt)
            return
        delay = self._base_delay * (2**attempt)
        self._retry_queue.append((time.time() + delay, attempt + 1, fn, args))

    def _drain_retries(self, client) -> None:
        now = time.time()
        for _ in range(len(self._retry_queue)):
            ts, attempt, fn, args = self._retry_queue[0]
            if ts > now:
                break
            self._retry_queue.popleft()
            try:
                fn(client, *args, _attempt=attempt)
            except Exception:
                pass

    def _topic_to_key(self, topic: str) -> tuple[str, str] | None:
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
        return category, key

    def _key_to_topic(self, category: str, key: str) -> str:
        return f"{self._prefix}/{category}/{key}"

    def on_message(self, client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        """Handle an incoming MQTT message — either retained state or the sentinel."""
        if msg.topic == self._sentinel_topic:
            logging.debug("MqttBackend: sentinel received — cache warming complete")
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

            show = True
            if category == Category.SENSOR:
                show = active_config.sensor_debug_logging
            elif category == Category.PVOUTPUT:
                show = active_config.pvoutput.log_level == logging.DEBUG

            if show:
                logging.debug(f"MqttBackend: cached {category}/{key} (ts={ts})")

    def publish(self, client: mqtt.Client, category: str, key: str, value: str, debug: bool = True, _attempt: int = 0) -> None:
        """Publish a retained state message."""
        self._drain_retries(client)
        topic = self._key_to_topic(category, key)
        envelope = _make_envelope(value, self._version)
        try:
            info = client.publish(topic, envelope, qos=2, retain=True)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(info.rc)
        except Exception:
            self._schedule_retry(_attempt, self.publish, category, key, value, debug)
            return
        if debug:
            logging.debug(f"MqttBackend.publish {category}/{key}")

    def publish_delete(self, client: mqtt.Client, category: str, key: str, debug: bool = True, _attempt: int = 0) -> None:
        """Clear a retained message by publishing an empty payload."""
        self._drain_retries(client)
        topic = self._key_to_topic(category, key)
        try:
            info = client.publish(topic, b"", qos=2, retain=True)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(info.rc)
        except Exception:
            self._schedule_retry(_attempt, self.publish_delete, category, key, debug)
            return

        with self._lock:
            self._cache.pop((category, key), None)

        if debug:
            logging.debug(f"MqttBackend.publish_delete {category}/{key}")

    def load(self, category: str, key: str) -> tuple[str, int] | None:
        """Return cached ``(value, ts)`` or ``None``."""
        with self._lock:
            return self._cache.get((category, key))

    def all_known_keys(self) -> list[tuple[str, str]]:
        """All ``(category, key)`` pairs currently held in the in-memory cache."""
        with self._lock:
            return list(self._cache.keys())

    def publish_sentinel(self, client: mqtt.Client) -> None:
        """Publish the non-retained sentinel to trigger end-of-retained-messages."""
        info = client.publish(self._sentinel_topic, b"1", qos=2, retain=False)
        info.wait_for_publish(timeout=5.0)
        logging.debug("MqttBackend: sentinel published")

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
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread_id: int | None = None
        self._disk_primary: bool = True
        self._version: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialised(self) -> bool:
        """True once :meth:`initialise` has completed (sentinel received or timed out)."""
        return self._initialised

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialise(
        self,
        state_path: Path,
        persistence_config: "PersistenceConfig",
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

        self._version = _ver.__version__

        self._loop = asyncio.get_running_loop()
        self._loop_thread_id = threading.get_ident()
        self._disk = _DiskBackend(state_path, self._version)
        self._mqtt_enabled = persistence_config.mqtt_redundancy
        self._disk_primary = persistence_config.disk_primary
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="persistence")

        if not self._mqtt_enabled:
            logging.info("StateStore: MQTT redundancy disabled — disk only")
            self._initialised = True
            return

        prefix = persistence_config.mqtt_state_prefix
        timeout = persistence_config.cache_warmup_timeout
        self._mqtt.configure(prefix, self._version)

        # Build a dedicated MQTT client for persistence traffic.
        from sigenergy2mqtt.config import active_config
        from sigenergy2mqtt.mqtt import mqtt_setup

        try:
            client_id = f"{active_config.mqtt.client_id_prefix}_persistence"
            client, _ = await mqtt_setup(client_id, None, self._loop)
            client.on_message = self._mqtt.on_message
        except Exception as exc:
            logging.warning(f"StateStore: MQTT connection failed ({exc}) — disk only")
            self._initialised = True
            return

        self._client = client

        # Subscribe to the full state namespace.
        client.subscribe(f"{prefix}/#", qos=2)

        # Publish sentinel and wait for it to come back, guaranteeing all
        # retained messages have been delivered first.
        logging.debug(f"StateStore: publishing sentinel, waiting up to {timeout:.1f}s for cache warm-up")
        self._mqtt.publish_sentinel(client)

        # Wait in a thread so as not to block the asyncio event loop.
        received = await self._loop.run_in_executor(None, lambda: self._mqtt.wait_for_sentinel(timeout))

        if received:
            logging.info(f"StateStore: cache warm-up complete ({len(self._mqtt.all_known_keys())} entries)")
        else:
            logging.warning(f"StateStore: cache warm-up timed out after {timeout:.1f}s — some MQTT state may be unavailable. Disk fallback will be used where possible.")

        self._initialised = True

    def shutdown(self, timeout: float = 1.0) -> None:
        """Flush pending writes, disconnect the persistence MQTT client, and stop the executor.

        Args:
            timeout: Seconds to wait for in-flight background tasks to complete.
        """
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None

        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as exc:
                logging.debug(f"StateStore: error during MQTT disconnect: {exc}")
            self._client = None

        self._initialised = False
        logging.info("StateStore: shutdown complete")

    # ------------------------------------------------------------------
    # Core async API
    # ------------------------------------------------------------------

    async def save(
        self,
        category: str,
        key: str,
        value: str,
        *,
        stale_after: timedelta | None = None,
        debug: bool = True,
    ) -> None:
        """Persist *value* to both disk and MQTT (fire-and-forget via executor).

        Args:
            category:    Logical grouping (e.g. ``"sensor"``, ``"pvoutput"``, ``"config"``).
            key:         File/topic name within the category.
            value:       String value to persist.
            stale_after: Unused on save; present for API symmetry with :meth:`load`.
            debug:       If False, suppresses debug logging for this operation.
        """
        if not self._initialised or self._executor is None:
            if debug:
                logging.debug(f"StateStore.save called before initialise — skipping {category}/{key}")
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._save_sync_impl, category, key, value, debug)

    async def load(
        self,
        category: str,
        key: str,
        *,
        stale_after: timedelta | None = None,
        validator: Callable[[str], bool] | None = None,
        debug: bool = True,
    ) -> str | None:
        """Load a persisted value, applying staleness check and optional validator.

        Tries disk first (if ``disk_primary`` is True, which is the default),
        then falls back to the MQTT retained-message cache.  If MQTT is the
        primary, the order is reversed.

        Args:
            category:    Logical grouping.
            key:         File/topic name within the category.
            stale_after: If set, values older than this timedelta are discarded.
            validator:   Optional callable that asserts the loaded value is valid;
                         returns False to discard the value.
            debug:       If False, suppresses debug logging for this operation.

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
            debug,
        )

    async def delete(self, category: str, key: str, debug: bool = True) -> None:
        """Remove *category*/*key* from both backends.

        MQTT removal is achieved by publishing an empty retained message,
        which instructs the broker to clear the retained payload.
        """
        if not self._initialised or self._executor is None:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._delete_sync_impl, category, key, debug)

    async def clean_all(self) -> None:
        """Clear all persisted state from both backends.

        Called when ``active_config.clean`` is ``True``.  Removes every disk
        file under ``state_path`` and publishes empty retained messages to every
        topic in the MQTT backend cache.
        """
        if not self._initialised or self._executor is None:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._clean_all_sync_impl)

    # ------------------------------------------------------------------
    # Synchronous wrappers (for use from Config.reload() sync context)
    # ------------------------------------------------------------------

    def save_sync(self, category: str, key: str, value: str, debug: bool = True) -> None:
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
            future = asyncio.run_coroutine_threadsafe(self.save(category, key, value, debug=debug), loop)
            try:
                future.result(timeout=5.0)
            except Exception as exc:
                logging.warning(f"StateStore.save_sync failed for {category}/{key}: {repr(exc)}")
        else:
            self._save_sync_impl(category, key, value, debug)

    def load_sync(
        self,
        category: str,
        key: str,
        *,
        stale_after: timedelta | None = None,
        validator: Callable[[str], bool] | None = None,
        debug: bool = True,
    ) -> str | None:
        """Synchronous wrapper for :meth:`load`.

        Uses :func:`asyncio.run_coroutine_threadsafe` when called from a
        synchronous context inside a running event loop.
        """
        if not self._initialised or self._disk is None:
            return None
        loop = self._loop
        if loop is not None and loop.is_running() and threading.get_ident() != self._loop_thread_id:
            future = asyncio.run_coroutine_threadsafe(self.load(category, key, stale_after=stale_after, validator=validator, debug=debug), loop)
            try:
                return future.result(timeout=5.0)
            except Exception as exc:
                logging.warning(f"StateStore.load_sync failed for {category}/{key}: {repr(exc)}")
                return None
        else:
            return self._load_sync_impl(category, key, stale_after, validator, debug)

    def delete_sync(self, category: str, key: str, debug: bool = True) -> None:
        """Synchronous wrapper for :meth:`delete`."""
        if not self._initialised or self._executor is None:
            return
        loop = self._loop
        if loop is not None and loop.is_running() and threading.get_ident() != self._loop_thread_id:
            future = asyncio.run_coroutine_threadsafe(self.delete(category, key, debug=debug), loop)
            try:
                future.result(timeout=5.0)
            except Exception as exc:
                logging.warning(f"StateStore.delete_sync failed for {category}/{key}: {repr(exc)}")
        else:
            self._delete_sync_impl(category, key, debug)

    # ------------------------------------------------------------------
    # Internal synchronous implementations (run in executor)
    # ------------------------------------------------------------------

    def _save_sync_impl(self, category: str, key: str, value: str, debug: bool = True) -> None:
        """Write to disk and MQTT; called from the ThreadPoolExecutor."""
        assert self._disk is not None
        try:
            self._disk.save(category, key, value, debug=debug)
        except Exception as exc:
            logging.warning(f"StateStore: disk save failed for {category}/{key}: {exc}")

        if self._mqtt_enabled and self._client is not None:
            try:
                self._mqtt.publish(self._client, category, key, value, debug=debug)
            except Exception as exc:
                logging.warning(f"StateStore: MQTT publish failed for {category}/{key}: {exc}")

    def _load_sync_impl(
        self,
        category: str,
        key: str,
        stale_after: timedelta | None,
        validator: Callable[[str], bool] | None,
        debug: bool = True,
    ) -> str | None:
        """Read from backends in priority order; called from the ThreadPoolExecutor."""
        assert self._disk is not None

        cutoff: int | None = None
        if stale_after is not None:
            cutoff = int(time.time() - stale_after.total_seconds())

        def _accept(value: str, ts: int) -> bool:
            if cutoff is not None and ts < cutoff:
                if debug:
                    logging.debug(f"StateStore: discarding stale value for {category}/{key} (ts={ts} cutoff={cutoff})")
                return False
            if validator is not None and not validator(value):
                if debug:
                    logging.debug(f"StateStore: validator rejected value for {category}/{key}")
                return False
            return True

        # Determine backend order.
        backends_primary_first: list[str] = (
            ["disk", "mqtt"]
            if not self._mqtt_enabled or self._disk_primary
            else ["mqtt", "disk"]
        )

        for backend in backends_primary_first:
            result: tuple[str, int] | None = None
            if backend == "disk":
                result = self._disk.load(category, key)
            elif backend == "mqtt" and self._mqtt_enabled:
                result = self._mqtt.load(category, key)

            if result is not None:
                value, ts = result
                if _accept(value, ts):
                    if debug:
                        logging.debug(f"StateStore.load {category}/{key} from {backend} (ts={ts})")
                    return value

        return None

    def _delete_sync_impl(self, category: str, key: str, debug: bool = True) -> None:
        """Remove from disk and MQTT; called from the ThreadPoolExecutor."""
        assert self._disk is not None
        self._disk.delete(category, key, debug=debug)

        if self._mqtt_enabled and self._client is not None:
            try:
                self._mqtt.publish_delete(self._client, category, key, debug=debug)
            except Exception as exc:
                logging.warning(f"StateStore: MQTT delete failed for {category}/{key}: {exc}")

    def _clean_all_sync_impl(self) -> None:
        """Clear all state from both backends; called from the ThreadPoolExecutor."""
        assert self._disk is not None
        disk_keys = self._disk.all_keys()
        for category, key in disk_keys:
            self._disk.delete(category, key)

        if self._mqtt_enabled and self._client is not None:
            # Clear any keys known from the MQTT cache (may include entries with
            # no matching disk file on this host, e.g. restored from another machine).
            mqtt_keys = self._mqtt.all_known_keys()
            for category, key in mqtt_keys:
                try:
                    self._mqtt.publish_delete(self._client, category, key)
                except Exception as exc:
                    logging.warning(f"StateStore: MQTT clean failed for {category}/{key}: {exc}")

        logging.info(f"StateStore: clean_all removed {len(disk_keys)} disk entries and cleared MQTT retained state")
