from .client_factory import ClientFactory
from contextlib import asynccontextmanager
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import asyncio


class ModbusLock:
    def __init__(self, modbus: ModbusClient):
        self._lock = asyncio.Lock()
        self._waiters = 0
        self._host = ClientFactory.get_host(modbus)

    @property
    def host(self) -> str:
        return self._host

    @property
    def waiters(self):
        return self._waiters

    async def acquire(self, timeout=None):
        self._waiters += 1
        try:
            if timeout is None:
                return await self._lock.acquire()
            else:
                return await asyncio.wait_for(self._lock.acquire(), timeout)
        finally:
            self._waiters -= 1
            
    @asynccontextmanager
    async def acquire_with_timeout(self, timeout=None):
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
