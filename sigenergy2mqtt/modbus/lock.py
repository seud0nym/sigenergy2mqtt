import asyncio
from contextlib import asynccontextmanager

from .client import ModbusClient
from .client_factory import ModbusClientFactory


class ModbusLock:
    """Async lock wrapper that tracks queued waiters per Modbus client.

    This lock is used to serialize network operations against the same Modbus
    endpoint and expose queue depth for diagnostics/metrics.
    """
    def __init__(self, modbus: ModbusClient | None):
        """Create a lock instance associated with an optional Modbus client.

        Args:
            modbus: Modbus client this lock belongs to, or ``None`` for a
                standalone lock without host metadata.
        """
        self._lock: asyncio.Lock = asyncio.Lock()
        self.waiters: int = 0
        self.host: str | None = ModbusClientFactory.get_host(modbus)

    async def acquire(self, timeout=None):
        """Acquire the lock and account for waiting coroutines.

        Args:
            timeout: Optional timeout in seconds. If provided, acquisition is
                wrapped in :func:`asyncio.wait_for`.

        Returns:
            ``True`` when the lock is acquired.
        """
        self.waiters += 1
        try:
            if timeout is None:
                return await self._lock.acquire()
            else:
                return await asyncio.wait_for(self._lock.acquire(), timeout)
        finally:
            self.waiters -= 1

    @asynccontextmanager
    async def lock(self, timeout=None):
        """Async context manager that acquires and reliably releases the lock.

        Args:
            timeout: Optional timeout in seconds for acquisition.

        Yields:
            None while the lock is held.

        Raises:
            TimeoutError: If acquisition fails before the timeout.
        """
        acquired = await self.acquire(timeout)
        try:
            if not acquired:
                raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired:
                self.release()

    def release(self):
        """Release the lock if it is currently held."""
        if self._lock.locked():
            self._lock.release()

    def locked(self):
        """Return whether the underlying lock is currently held."""
        return self._lock.locked()
