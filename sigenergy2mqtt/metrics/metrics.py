from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import logging
import time


class Metrics:
    _lock = asyncio.Lock()

    _started: float = time.monotonic()

    sigenergy2mqtt_modbus_reads: int = 0
    sigenergy2mqtt_modbus_read_total: float = 0.0
    sigenergy2mqtt_modbus_read_max: float = 0.0
    sigenergy2mqtt_modbus_read_mean: float = 0.0
    sigenergy2mqtt_modbus_read_min: float = float("inf")
    sigenergy2mqtt_modbus_read_errors: int = 0

    sigenergy2mqtt_modbus_writes: int = 0
    sigenergy2mqtt_modbus_write_total: float = 0.0
    sigenergy2mqtt_modbus_write_max: float = 0.0
    sigenergy2mqtt_modbus_write_mean: float = 0.0
    sigenergy2mqtt_modbus_write_min: float = float("inf")
    sigenergy2mqtt_modbus_write_errors: int = 0

    sigenergy2mqtt_started: float = datetime.now().astimezone().isoformat()

    @classmethod
    @asynccontextmanager
    async def lock(cls, timeout=None):
        acquired: bool = False
        try:
            if timeout is None:
                acquired = await Metrics._lock.acquire()
            else:
                acquired = await asyncio.wait_for(Metrics._lock.acquire(), timeout)
                if not acquired:
                    raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired and Metrics._lock.locked():
                Metrics._lock.release()

    @classmethod
    async def modbus_read(cls, registers: int, seconds: float) -> None:
        try:
            elapsed = seconds * 1000.0
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_reads += registers
                cls.sigenergy2mqtt_modbus_read_total += elapsed
                cls.sigenergy2mqtt_modbus_read_max = max(cls.sigenergy2mqtt_modbus_read_max, elapsed)
                cls.sigenergy2mqtt_modbus_read_min = min(cls.sigenergy2mqtt_modbus_read_min, elapsed)
                cls.sigenergy2mqtt_modbus_read_mean = cls.sigenergy2mqtt_modbus_read_total / cls.sigenergy2mqtt_modbus_reads if cls.sigenergy2mqtt_modbus_reads > 0 else 0.0
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
        elapsed = seconds * 1000.0
        try:
            async with cls.lock(timeout=1):
                cls.sigenergy2mqtt_modbus_writes += registers
                cls.sigenergy2mqtt_modbus_write_total += elapsed
                cls.sigenergy2mqtt_modbus_write_max = max(cls.sigenergy2mqtt_modbus_write_max, elapsed)
                cls.sigenergy2mqtt_modbus_write_min = min(cls.sigenergy2mqtt_modbus_write_min, elapsed)
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
