import logging

from .lock import ModbusLock
from .types import ModbusClientType


class ModbusLockFactory:
    _locks: dict[ModbusClientType, ModbusLock] = {}
    _logger = logging.getLogger("pymodbus")

    @classmethod
    def get(cls, modbus: ModbusClientType | None) -> ModbusLock:
        if modbus is None:
            return ModbusLock(None)
        if modbus not in cls._locks:
            cls._locks[modbus] = ModbusLock(modbus)
        lock = cls._locks[modbus]
        if lock.waiters > 5:
            cls._logger.debug(f"Lock on {lock.host} has {lock.waiters} waiters")
        return lock

    @classmethod
    def get_waiter_count(cls) -> int:
        waiters: int = 0
        for lock in cls._locks.values():
            waiters += lock.waiters
        return waiters
