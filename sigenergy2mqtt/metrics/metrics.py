"""
Centralised runtime metrics store for sigenergy2mqtt.

All mutable state is protected by an :class:`asyncio.Lock`. Callers should
use the async helper methods rather than mutating class attributes directly.
Timing values are stored in milliseconds unless noted otherwise.

Call :meth:`Metrics.commence` from the service ``on_commencement`` handler to
initialise the time-sensitive ``_started`` and ``sigenergy2mqtt_started``
fields at actual service start rather than at module-import time.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime


class Metrics:
    """
    Class-level store for all sigenergy2mqtt operational metrics.

    Attributes are class variables so they can be read cheaply from anywhere
    without an instance. All writes go through the provided async helper
    methods, which acquire the internal :class:`asyncio.Lock` before mutating
    state, preventing TOCTOU races.
    """

    # asyncio.Lock must be created inside a running event loop, so it is
    # initialised lazily by _get_lock() rather than here at class body time.
    _lock: asyncio.Lock | None = None

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
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """
        Return the asyncio.Lock, creating it on first call.

        The lock must be created inside a running event loop, so it cannot be
        a class-level initialiser.
        """
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    @asynccontextmanager
    async def lock(cls, timeout: float | None = 1.0):
        """
        Async context manager that acquires the internal asyncio.Lock.

        Using :class:`asyncio.Lock` rather than :class:`threading.Lock` ensures
        that contention never blocks the event loop thread.

        Args:
            timeout: Maximum seconds to wait for the lock. Raises
                :class:`TimeoutError` if the lock cannot be acquired in time.
                Pass ``None`` to wait indefinitely.

        Raises:
            TimeoutError: When ``timeout`` is set and the lock is not acquired
                within that period.
        """
        try:
            await asyncio.wait_for(cls._get_lock().acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Failed to acquire Metrics lock within the timeout period.")
        try:
            yield
        finally:
            cls._get_lock().release()

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
    async def modbus_cache_fill(cls) -> None:
        """Increment the cache-fill read counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_cache_fill_reads += 1
        except Exception as exc:
            logging.warning(f"Error during modbus cache metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_cache_hits(cls, reads: int, hits: int) -> None:
        """
        Record the cache-hit percentage for the current scan cycle.

        Args:
            reads: Total reads attempted in the cycle.
            hits:  Reads satisfied from cache in the cycle.
        """
        try:
            percentage = round(hits / reads * 100.0, 2)
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_cache_hit_percentage = percentage
        except Exception as exc:
            logging.warning(f"Error during modbus cache metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_read(cls, registers: int, seconds: float) -> None:
        """
        Record a completed modbus read operation.

        Args:
            registers: Number of registers read in this operation.
            seconds:   Wall-clock duration of the operation in seconds.
        """
        try:
            elapsed = seconds * 1000.0
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_reads += 1
                cls.sigenergy2mqtt_modbus_physical_read_percentage = round(cls.sigenergy2mqtt_modbus_cache_fill_reads / cls.sigenergy2mqtt_modbus_reads * 100.0, 2)
                cls.sigenergy2mqtt_modbus_register_reads += registers
                cls.sigenergy2mqtt_modbus_read_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_modbus_read_max = max(cls.sigenergy2mqtt_modbus_read_max, elapsed)
                cls.sigenergy2mqtt_modbus_read_min = min(cls.sigenergy2mqtt_modbus_read_min, elapsed)
                cls.sigenergy2mqtt_modbus_read_mean = cls.sigenergy2mqtt_modbus_read_total / cls.sigenergy2mqtt_modbus_register_reads if cls.sigenergy2mqtt_modbus_register_reads > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during modbus read metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_read_error(cls) -> None:
        """Increment the modbus read error counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_read_errors += 1
        except Exception as exc:
            logging.warning(f"Error during modbus read error metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_write(cls, registers: int, seconds: float) -> None:
        """
        Record a completed modbus write operation.

        Args:
            registers: Number of registers written in this operation.
            seconds:   Wall-clock duration of the operation in seconds.
        """
        try:
            elapsed = seconds * 1000.0
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_writes += registers
                cls.sigenergy2mqtt_modbus_write_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_modbus_write_max = max(cls.sigenergy2mqtt_modbus_write_max, elapsed)
                cls.sigenergy2mqtt_modbus_write_min = min(cls.sigenergy2mqtt_modbus_write_min, elapsed)
                cls.sigenergy2mqtt_modbus_write_mean = cls.sigenergy2mqtt_modbus_write_total / cls.sigenergy2mqtt_modbus_writes if cls.sigenergy2mqtt_modbus_writes > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during modbus write metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_write_error(cls) -> None:
        """Increment the modbus write error counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_write_errors += 1
        except Exception as exc:
            logging.warning(f"Error during modbus write error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_write(cls, batch_size: int, seconds: float) -> None:
        """
        Record a completed InfluxDB write operation.

        Args:
            batch_size: Number of data points in the written batch.
            seconds:    Wall-clock duration of the operation in seconds.
        """
        try:
            elapsed = seconds * 1000.0
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_writes += 1
                cls.sigenergy2mqtt_influxdb_batch_total += batch_size
                cls.sigenergy2mqtt_influxdb_write_total += elapsed
                # min/max computed inside the lock to prevent TOCTOU races
                cls.sigenergy2mqtt_influxdb_write_max = max(cls.sigenergy2mqtt_influxdb_write_max, elapsed)
                cls.sigenergy2mqtt_influxdb_write_min = min(cls.sigenergy2mqtt_influxdb_write_min, elapsed)
                cls.sigenergy2mqtt_influxdb_write_mean = cls.sigenergy2mqtt_influxdb_write_total / cls.sigenergy2mqtt_influxdb_writes if cls.sigenergy2mqtt_influxdb_writes > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during influxdb write metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_write_error(cls) -> None:
        """Increment the InfluxDB write error counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_write_errors += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb write error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_query(cls) -> None:
        """Record a completed InfluxDB query operation."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_queries += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb query metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_query_error(cls) -> None:
        """Increment the InfluxDB query error counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_query_errors += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb query error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_retry(cls) -> None:
        """Increment the InfluxDB retry counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_retries += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb retry metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_rate_limit_wait(cls) -> None:
        """Increment the InfluxDB rate-limit wait counter."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_rate_limit_waits += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb rate limit metrics collection: {repr(exc)}")
