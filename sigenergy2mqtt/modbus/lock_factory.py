from .custom_lock import ModbusLock
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
import logging



class ModbusLockFactory:
    _locks: dict[ModbusClient, ModbusLock] = {}
    _logger = logging.getLogger("pymodbus")

    @classmethod
    def get_lock(self, modbus: ModbusClient) -> ModbusLock:
        if modbus not in self._locks:
            self._locks[modbus] = ModbusLock(modbus)
        lock = self._locks[modbus]
        if lock.waiters > 5:
            self._logger.debug(f"Lock on {lock.host} has {lock.waiters} waiters")
        return lock
