from .custom_lock import CustomLock
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import asyncio
import logging



class LockFactory:
    _locks: dict[ModbusClient, CustomLock] = {}
    _logger = logging.getLogger("pymodbus")

    @classmethod
    def get_lock(self, modbus: ModbusClient) -> asyncio.Lock:
        if modbus not in self._locks:
            self._locks[modbus] = CustomLock(modbus)
        lock = self._locks[modbus]
        if lock.waiters > 5:
            self._logger.debug(f"Lock on {lock.host} has {lock.waiters} waiters")
        return lock
