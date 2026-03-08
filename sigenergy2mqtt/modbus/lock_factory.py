import logging

from .client import ModbusClient
from .lock import ModbusLock


class ModbusLockFactory:
    """Singleton-style cache for per-client :class:`ModbusLock` instances."""
    _locks: dict[ModbusClient, ModbusLock] = {}
    _logger = logging.getLogger("pymodbus")

    @classmethod
    def clear(cls):
        """Remove all cached lock instances from the factory."""
        cls._locks.clear()

    @classmethod
    def get(cls, modbus: ModbusClient | None) -> ModbusLock:
        """Return a stable lock for a client, creating it on first use.

        Args:
            modbus: Client key used to retrieve/create the lock.

        Returns:
            A cached lock for the client, or a new standalone lock when
            ``modbus`` is ``None``.
        """
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
        """Return the total number of current waiters across all locks."""
        waiters: int = 0
        for lock in cls._locks.values():
            waiters += lock.waiters
        return waiters
