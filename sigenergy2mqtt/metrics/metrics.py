"""
Centralised runtime metrics store for sigenergy2mqtt.

All mutable state is protected by a :class:`threading.Lock`. Callers should
use the async helper methods rather than mutating class attributes directly.
Timing values are stored in milliseconds unless noted otherwise.

Call :meth:`Metrics.commence` from the service ``on_commencement`` handler to
initialise the time-sensitive ``_started`` and ``sigenergy2mqtt_started``
fields at actual service start rather than at module-import time.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

from sigenergy2mqtt.config import active_config


class Metrics:
    """
    Class-level store for all sigenergy2mqtt operational metrics.

    Attributes are class variables so they can be read cheaply from anywhere
    without an instance. All writes go through the provided async helper
    methods, which acquire the internal :class:`threading.Lock` before mutating
    state, preventing TOCTOU races.
    """

    _lock: threading.Lock = threading.Lock()
    _pending_lock: threading.Lock = threading.Lock()
    _executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="metrics")
    _pending_updates: list[Future] = []

    _started: float = 0.0
    """Monotonic reference timestamp set by :meth:`commence`. Used for rate calculations."""

    # ------------------------------------------------------------------
    # Modbus read metrics
    # ------------------------------------------------------------------

    sigenergy2mqtt_modbus_cache_fill_reads: int = 0
    """Number of reads that triggered a physical cache-fill."""

    sigenergy2mqtt_modbus_cache_hit_percentage: float = 0.0
    """Percentage of modbus reads satisfied from cache."""

    sigenergy2mqtt_modbus_reads: int = 0
    """Total number of modbus read calls."""

    sigenergy2mqtt_modbus_register_reads: int = 0
    """Total number of individual registers read across all calls."""

    sigenergy2mqtt_modbus_read_total: float = 0.0
    """Cumulative elapsed time of all modbus reads, in milliseconds."""

    sigenergy2mqtt_modbus_read_max: float = 0.0
    """Maximum single modbus read duration, in milliseconds."""

    sigenergy2mqtt_modbus_read_mean: float = 0.0
    """Mean modbus read duration per register read, in milliseconds."""

    sigenergy2mqtt_modbus_read_min: float = float("inf")
    """Minimum single modbus read duration, in milliseconds."""

    sigenergy2mqtt_modbus_read_errors: int = 0
    """Number of modbus read errors."""

    sigenergy2mqtt_modbus_physical_read_percentage: float = 0.0
    """Percentage of modbus reads that resulted in a physical bus read."""

    # ------------------------------------------------------------------
    # MQTT publish metrics
    # ------------------------------------------------------------------

    sigenergy2mqtt_mqtt_publish_attempts: int = 0
    """Total number of logical MQTT state publish attempts."""

    sigenergy2mqtt_mqtt_publish_failures: int = 0
    """Number of MQTT state publish attempts that failed."""

    sigenergy2mqtt_mqtt_physical_publishes: int = 0
    """Number of attempts that resulted in an actual MQTT state publish."""

    sigenergy2mqtt_mqtt_physical_publish_percentage: float = 0.0
    """Percentage of publish attempts that resulted in physical publishes."""

    # ------------------------------------------------------------------
    # Modbus write metrics
    # ------------------------------------------------------------------

    sigenergy2mqtt_modbus_writes: int = 0
    """Total number of modbus write calls."""

    sigenergy2mqtt_modbus_write_total: float = 0.0
    """Cumulative elapsed time of all modbus writes, in milliseconds."""

    sigenergy2mqtt_modbus_write_max: float = 0.0
    """Maximum single modbus write duration, in milliseconds."""

    sigenergy2mqtt_modbus_write_mean: float = 0.0
    """Mean modbus write duration per write call, in milliseconds."""

    sigenergy2mqtt_modbus_write_min: float = float("inf")
    """Minimum single modbus write duration, in milliseconds."""

    sigenergy2mqtt_modbus_write_errors: int = 0
    """Number of modbus write errors."""

    # ------------------------------------------------------------------
    # InfluxDB metrics
    # ------------------------------------------------------------------

    sigenergy2mqtt_influxdb_writes: int = 0
    """Total number of InfluxDB write operations."""

    sigenergy2mqtt_influxdb_write_errors: int = 0
    """Number of InfluxDB write errors."""

    sigenergy2mqtt_influxdb_write_total: float = 0.0
    """Cumulative elapsed time of all InfluxDB writes, in milliseconds."""

    sigenergy2mqtt_influxdb_write_max: float = 0.0
    """Maximum single InfluxDB write duration, in milliseconds."""

    sigenergy2mqtt_influxdb_write_mean: float = 0.0
    """Mean InfluxDB write duration per write call, in milliseconds."""

    sigenergy2mqtt_influxdb_write_min: float = float("inf")
    """Minimum single InfluxDB write duration, in milliseconds."""

    sigenergy2mqtt_influxdb_queries: int = 0
    """Total number of InfluxDB query operations."""

    sigenergy2mqtt_influxdb_query_errors: int = 0
    """Number of InfluxDB query errors."""

    sigenergy2mqtt_influxdb_retries: int = 0
    """Number of InfluxDB retry attempts."""

    sigenergy2mqtt_influxdb_rate_limit_waits: int = 0
    """Number of times execution was paused due to InfluxDB rate limiting."""

    sigenergy2mqtt_influxdb_batch_total: int = 0
    """Total number of data points written to InfluxDB across all batches."""

    # ------------------------------------------------------------------
    # Service identity
    # ------------------------------------------------------------------

    sigenergy2mqtt_started: str = ""
    """ISO-8601 wall-clock timestamp of service commencement, set by :meth:`commence`."""

    # ------------------------------------------------------------------
    # Class-level defaults for int/float metrics (used by :meth:`reset`)
    # ------------------------------------------------------------------

    _defaults: dict[str, int | float] = {}

    @classmethod
    async def reset(cls) -> None:
        """Reset all public int and float metrics class fields to their default values."""

        def _update() -> None:
            def _operation() -> None:
                for name, default in cls._defaults.items():
                    setattr(cls, name, default)

            cls._update_with_lock(_operation, "metrics reset")

        cls._submit(_update)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    @asynccontextmanager
    async def lock(cls, timeout: float | None = 1.0):
        """
        Async context manager that acquires the internal :class:`threading.Lock`.

        ``threading.Lock`` is used deliberately: this app runs one asyncio
        event loop per thread, so an ``asyncio.Lock`` would be loop-bound and
        unsafe across threads (modbus and InfluxDB writers run in separate
        threads). The GIL ensures that the non-blocking ``acquire(timeout=…)``
        call is safe to issue from any thread without stalling the event loop.

        Args:
            timeout: Maximum seconds to wait for the lock. Raises
                :class:`TimeoutError` if the lock cannot be acquired in time.
                Pass ``None`` to wait indefinitely.

        Raises:
            TimeoutError: When ``timeout`` is set and the lock is not acquired
                within that period.
        """
        acquired: bool = False
        try:
            if timeout is None:
                acquired = cls._lock.acquire()
            else:
                acquired = cls._lock.acquire(timeout=timeout)
                if not acquired:
                    raise TimeoutError("Failed to acquire Metrics lock within the timeout period.")
            yield
        finally:
            if acquired:
                cls._lock.release()

    @classmethod
    def commence(cls) -> None:
        """
        Initialise time-sensitive fields at actual service start.

        Must be called from the service ``on_commencement`` handler so that
        ``_started`` and ``sigenergy2mqtt_started`` reflect the real service
        start time rather than the earlier module-import time.

        This is intentionally synchronous. It is called before any async
        workers are running, so no lock is required — direct assignment is
        both safe and necessary to avoid the ``run_until_complete`` /
        running-loop conflict that arises when a synchronous
        ``on_commencement`` handler tries to drive an async coroutine inside
        an already-running event loop.
        """
        cls._started = time.monotonic()
        cls.sigenergy2mqtt_started = datetime.now().astimezone().isoformat()

    @classmethod
    def _metrics_enabled(cls) -> bool:
        """Return True when metrics recording is enabled in configuration."""
        return bool(getattr(active_config, "metrics_enabled", True))

    @classmethod
    def _submit(cls, operation: Callable[[], None]) -> None:
        """Queue a metric update to the internal worker and return immediately."""
        if not cls._metrics_enabled():
            return

        future = cls._executor.submit(operation)
        with cls._pending_lock:
            cls._pending_updates.append(future)

        def _cleanup(completed: Future) -> None:
            with cls._pending_lock:
                if completed in cls._pending_updates:
                    cls._pending_updates.remove(completed)

        future.add_done_callback(_cleanup)

    @classmethod
    def _update_with_lock(cls, operation: Callable[[], None], warning: str) -> None:
        """Run a metric update while holding the class lock."""
        acquired = False
        try:
            if not cls._metrics_enabled():
                return

            acquired = cls._lock.acquire(timeout=1)
            if not acquired:
                raise TimeoutError("Failed to acquire Metrics lock within the timeout period.")
            operation()
        except Exception as exc:
            logging.warning(f"Error during {warning}: {repr(exc)}")
        finally:
            if acquired:
                cls._lock.release()

    @classmethod
    async def drain(cls, timeout: float | None = 1.0) -> None:
        """Await completion of queued metrics updates. Primarily intended for tests."""
        with cls._pending_lock:
            pending = list(cls._pending_updates)
        if not pending:
            return
        done, not_done = await asyncio.to_thread(wait, pending, timeout=timeout)
        if not_done:
            raise TimeoutError(f"Timed out waiting for {len(not_done)} metrics updates to finish.")

    @classmethod
    async def modbus_cache_fill(cls) -> None:
        """Increment the cache-fill read counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_modbus_cache_fill_reads += 1

            cls._update_with_lock(_operation, "modbus cache metrics collection")

        cls._submit(_update)

    @classmethod
    async def modbus_cache_hits(cls, reads: int, hits: int) -> None:
        """
        Record the cache-hit percentage for the current scan cycle.

        Args:
            reads: Total reads attempted in the cycle.
            hits:  Reads satisfied from cache in the cycle.
        """

        def _update() -> None:
            def _operation() -> None:
                percentage = round(hits / reads * 100.0, 2)
                cls.sigenergy2mqtt_modbus_cache_hit_percentage = percentage

            cls._update_with_lock(_operation, "modbus cache metrics collection")

        cls._submit(_update)

    @classmethod
    async def modbus_read(cls, registers: int, seconds: float) -> None:
        """
        Record a completed modbus read operation.

        Args:
            registers: Number of registers read in this operation.
            seconds:   Wall-clock duration of the operation in seconds.
        """

        def _update() -> None:
            def _operation() -> None:
                elapsed = seconds * 1000.0
                cls.sigenergy2mqtt_modbus_reads += 1
                cls.sigenergy2mqtt_modbus_physical_read_percentage = round(cls.sigenergy2mqtt_modbus_cache_fill_reads / cls.sigenergy2mqtt_modbus_reads * 100.0, 2)
                cls.sigenergy2mqtt_modbus_register_reads += registers
                cls.sigenergy2mqtt_modbus_read_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_modbus_read_max = max(cls.sigenergy2mqtt_modbus_read_max, elapsed)
                cls.sigenergy2mqtt_modbus_read_min = min(cls.sigenergy2mqtt_modbus_read_min, elapsed)
                cls.sigenergy2mqtt_modbus_read_mean = cls.sigenergy2mqtt_modbus_read_total / cls.sigenergy2mqtt_modbus_register_reads if cls.sigenergy2mqtt_modbus_register_reads > 0 else 0.0

            cls._update_with_lock(_operation, "modbus read metrics collection")

        cls._submit(_update)

    @classmethod
    async def modbus_read_error(cls) -> None:
        """Increment the modbus read error counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_modbus_read_errors += 1

            cls._update_with_lock(_operation, "modbus read error metrics collection")

        cls._submit(_update)

    @classmethod
    async def modbus_write(cls, registers: int, seconds: float) -> None:
        """
        Record a completed modbus write operation.

        Args:
            registers: Number of registers written in this operation.
            seconds:   Wall-clock duration of the operation in seconds.
        """

        def _update() -> None:
            def _operation() -> None:
                elapsed = seconds * 1000.0
                cls.sigenergy2mqtt_modbus_writes += registers
                cls.sigenergy2mqtt_modbus_write_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_modbus_write_max = max(cls.sigenergy2mqtt_modbus_write_max, elapsed)
                cls.sigenergy2mqtt_modbus_write_min = min(cls.sigenergy2mqtt_modbus_write_min, elapsed)
                cls.sigenergy2mqtt_modbus_write_mean = cls.sigenergy2mqtt_modbus_write_total / cls.sigenergy2mqtt_modbus_writes if cls.sigenergy2mqtt_modbus_writes > 0 else 0.0

            cls._update_with_lock(_operation, "modbus write metrics collection")

        cls._submit(_update)

    @classmethod
    async def mqtt_publish_attempt(cls, physical_publish: bool) -> None:
        """Record an MQTT state publish attempt.

        Args:
            physical_publish: ``True`` when the state message was physically
                published to MQTT; ``False`` when it was suppressed or failed.
        """

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_mqtt_publish_attempts += 1
                if physical_publish:
                    cls.sigenergy2mqtt_mqtt_physical_publishes += 1
                cls.sigenergy2mqtt_mqtt_physical_publish_percentage = (
                    round(cls.sigenergy2mqtt_mqtt_physical_publishes / cls.sigenergy2mqtt_mqtt_publish_attempts * 100.0, 2) if cls.sigenergy2mqtt_mqtt_publish_attempts > 0 else 0.0
                )

            cls._update_with_lock(_operation, "mqtt publish attempt metrics collection")

        cls._submit(_update)

    @classmethod
    async def mqtt_publish_failure(cls) -> None:
        """Increment the MQTT state publish failure counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_mqtt_publish_failures += 1

            cls._update_with_lock(_operation, "mqtt publish failure metrics collection")

        cls._submit(_update)

    @classmethod
    async def modbus_write_error(cls) -> None:
        """Increment the modbus write error counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_modbus_write_errors += 1

            cls._update_with_lock(_operation, "modbus write error metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_write(cls, batch_size: int, seconds: float) -> None:
        """
        Record a completed InfluxDB write operation.

        Args:
            batch_size: Number of data points in the written batch.
            seconds:    Wall-clock duration of the operation in seconds.
        """

        def _update() -> None:
            def _operation() -> None:
                elapsed = seconds * 1000.0
                cls.sigenergy2mqtt_influxdb_writes += 1
                cls.sigenergy2mqtt_influxdb_batch_total += batch_size
                cls.sigenergy2mqtt_influxdb_write_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_influxdb_write_max = max(cls.sigenergy2mqtt_influxdb_write_max, elapsed)
                cls.sigenergy2mqtt_influxdb_write_min = min(cls.sigenergy2mqtt_influxdb_write_min, elapsed)
                cls.sigenergy2mqtt_influxdb_write_mean = cls.sigenergy2mqtt_influxdb_write_total / cls.sigenergy2mqtt_influxdb_writes if cls.sigenergy2mqtt_influxdb_writes > 0 else 0.0

            cls._update_with_lock(_operation, "influxdb write metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_write_error(cls) -> None:
        """Increment the InfluxDB write error counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_influxdb_write_errors += 1

            cls._update_with_lock(_operation, "influxdb write error metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_query(cls) -> None:
        """Record a completed InfluxDB query operation."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_influxdb_queries += 1

            cls._update_with_lock(_operation, "influxdb query metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_query_error(cls) -> None:
        """Increment the InfluxDB query error counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_influxdb_query_errors += 1

            cls._update_with_lock(_operation, "influxdb query error metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_retry(cls) -> None:
        """Increment the InfluxDB retry counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_influxdb_retries += 1

            cls._update_with_lock(_operation, "influxdb retry metrics collection")

        cls._submit(_update)

    @classmethod
    async def influxdb_rate_limit_wait(cls) -> None:
        """Increment the InfluxDB rate-limit wait counter."""

        def _update() -> None:
            def _operation() -> None:
                cls.sigenergy2mqtt_influxdb_rate_limit_waits += 1

            cls._update_with_lock(_operation, "influxdb rate limit metrics collection")

        cls._submit(_update)


# Snapshot the pristine default values at class-definition time, before any
# metrics have been mutated, so that :meth:`Metrics.reset` restores them
# faithfully.
for _name, _value in vars(Metrics).items():
    if not _name.startswith("_") and isinstance(_value, (int, float)):
        Metrics._defaults[_name] = _value
