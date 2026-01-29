import asyncio
from contextlib import asynccontextmanager

from .client_factory import ModbusClientFactory
from .types import ModbusClientType


class ModbusLock:
    def __init__(self, modbus: ModbusClientType | None):
        self._lock: asyncio.Lock = asyncio.Lock()
        self.waiters: int = 0
        self.host: str | None = ModbusClientFactory.get_host(modbus)

    async def acquire(self, timeout=None):
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
        acquired = await self.acquire(timeout)
        try:
            if not acquired:
                raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired:
                self.release()

    def release(self):
        if self._lock.locked():
            self._lock.release()

    def locked(self):
        return self._lock.locked()
