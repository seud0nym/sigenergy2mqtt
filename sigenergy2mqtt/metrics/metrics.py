import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime


class Metrics:
    _lock = threading.Lock()

    _started: float = time.monotonic()

    sigenergy2mqtt_modbus_cache_fill_reads: int = 0
    sigenergy2mqtt_modbus_cache_hit_percentage: float = 0.0

    sigenergy2mqtt_modbus_reads: int = 0
    sigenergy2mqtt_modbus_register_reads: int = 0
    sigenergy2mqtt_modbus_read_total: float = 0.0
    sigenergy2mqtt_modbus_read_max: float = 0.0
    sigenergy2mqtt_modbus_read_mean: float = 0.0
    sigenergy2mqtt_modbus_read_min: float = float("inf")
    sigenergy2mqtt_modbus_read_errors: int = 0

    sigenergy2mqtt_modbus_physical_read_percentage: float = 0.0

    sigenergy2mqtt_modbus_writes: int = 0
    sigenergy2mqtt_modbus_write_total: float = 0.0
    sigenergy2mqtt_modbus_write_max: float = 0.0
    sigenergy2mqtt_modbus_write_mean: float = 0.0
    sigenergy2mqtt_modbus_write_min: float = float("inf")
    sigenergy2mqtt_modbus_write_errors: int = 0

    # InfluxDB metrics
    sigenergy2mqtt_influxdb_writes: int = 0
    sigenergy2mqtt_influxdb_write_errors: int = 0
    sigenergy2mqtt_influxdb_write_total: float = 0.0
    sigenergy2mqtt_influxdb_write_max: float = 0.0
    sigenergy2mqtt_influxdb_write_mean: float = 0.0
    sigenergy2mqtt_influxdb_queries: int = 0
    sigenergy2mqtt_influxdb_query_errors: int = 0
    sigenergy2mqtt_influxdb_retries: int = 0
    sigenergy2mqtt_influxdb_rate_limit_waits: int = 0
    sigenergy2mqtt_influxdb_batch_total: int = 0

    sigenergy2mqtt_started: str = datetime.now().astimezone().isoformat()

    @classmethod
    @asynccontextmanager
    async def lock(cls, timeout=1.0):
        acquired: bool = False
        try:
            if timeout is None:
                acquired = Metrics._lock.acquire()
            else:
                acquired = Metrics._lock.acquire(timeout=timeout)
                if not acquired:
                    raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired:
                Metrics._lock.release()

    @classmethod
    async def modbus_cache_fill(cls) -> None:
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_cache_fill_reads += 1
        except Exception as exc:
            logging.warning(f"Error during modbus cache metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_cache_hits(cls, reads: int, hits: int) -> None:
        try:
            percentage = round(hits / reads * 100.0, 2)
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_cache_hit_percentage = percentage
        except Exception as exc:
            logging.warning(f"Error during modbus cache metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_read(cls, registers: int, seconds: float) -> None:
        try:
            elapsed = seconds * 1000.0
            read_max = max(cls.sigenergy2mqtt_modbus_read_max, elapsed)
            read_min = min(cls.sigenergy2mqtt_modbus_read_min, elapsed)
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_reads += 1
                cls.sigenergy2mqtt_modbus_physical_read_percentage = round(cls.sigenergy2mqtt_modbus_cache_fill_reads / cls.sigenergy2mqtt_modbus_reads * 100.0, 2)
                cls.sigenergy2mqtt_modbus_register_reads += registers
                cls.sigenergy2mqtt_modbus_read_total += elapsed
                cls.sigenergy2mqtt_modbus_read_max = read_max
                cls.sigenergy2mqtt_modbus_read_min = read_min
                cls.sigenergy2mqtt_modbus_read_mean = cls.sigenergy2mqtt_modbus_read_total / cls.sigenergy2mqtt_modbus_register_reads if cls.sigenergy2mqtt_modbus_register_reads > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during modbus read metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_read_error(cls) -> None:
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_read_errors += 1
        except Exception as exc:
            logging.warning(f"Error during modbus read error metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_write(cls, registers: int, seconds: float) -> None:
        try:
            elapsed = seconds * 1000.0
            write_max = max(cls.sigenergy2mqtt_modbus_write_max, elapsed)
            write_min = min(cls.sigenergy2mqtt_modbus_write_min, elapsed)
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_writes += registers
                cls.sigenergy2mqtt_modbus_write_total += elapsed
                cls.sigenergy2mqtt_modbus_write_max = write_max
                cls.sigenergy2mqtt_modbus_write_min = write_min
                cls.sigenergy2mqtt_modbus_write_mean = cls.sigenergy2mqtt_modbus_write_total / cls.sigenergy2mqtt_modbus_writes if cls.sigenergy2mqtt_modbus_writes > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during modbus write metrics collection: {repr(exc)}")

    @classmethod
    async def modbus_write_error(cls) -> None:
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_write_errors += 1
        except Exception as exc:
            logging.warning(f"Error during modbus write error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_write(cls, batch_size: int, seconds: float) -> None:
        """Record InfluxDB write operation metrics."""
        try:
            elapsed = seconds * 1000.0
            write_max = max(cls.sigenergy2mqtt_influxdb_write_max, elapsed)
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_writes += 1
                cls.sigenergy2mqtt_influxdb_batch_total += batch_size
                cls.sigenergy2mqtt_influxdb_write_total += elapsed
                cls.sigenergy2mqtt_influxdb_write_max = write_max
                cls.sigenergy2mqtt_influxdb_write_mean = cls.sigenergy2mqtt_influxdb_write_total / cls.sigenergy2mqtt_influxdb_writes if cls.sigenergy2mqtt_influxdb_writes > 0 else 0.0
        except Exception as exc:
            logging.warning(f"Error during influxdb write metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_write_error(cls) -> None:
        """Record InfluxDB write error."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_write_errors += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb write error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_query(cls, seconds: float) -> None:
        """Record InfluxDB query operation metrics."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_queries += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb query metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_query_error(cls) -> None:
        """Record InfluxDB query error."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_query_errors += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb query error metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_retry(cls) -> None:
        """Record InfluxDB retry attempt."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_retries += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb retry metrics collection: {repr(exc)}")

    @classmethod
    async def influxdb_rate_limit_wait(cls) -> None:
        """Record InfluxDB rate limit wait."""
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_influxdb_rate_limit_waits += 1
        except Exception as exc:
            logging.warning(f"Error during influxdb rate limit metrics collection: {repr(exc)}")
