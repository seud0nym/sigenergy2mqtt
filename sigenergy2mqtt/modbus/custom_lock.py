from .client_factory import ClientFactory
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import asyncio


class CustomLock:
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

    async def acquire(self):
        self._waiters += 1
        await self._lock.acquire()
        self._waiters -= 1

    def release(self):
        self._lock.release()
        pass

    def locked(self):
        return self._lock.locked()
