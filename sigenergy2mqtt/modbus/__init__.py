"""Modbus client, locking, and factory primitives used by the application."""

from typing import TypeAlias

from .client import ModbusClient
from .client_factory import ModbusClientFactory
from .lock import ModbusLock
from .lock_factory import ModbusLockFactory

ModbusDataType: TypeAlias = ModbusClient.DATATYPE


__all__ = ["ModbusClientFactory", "ModbusClient", "ModbusLockFactory", "ModbusLock", "ModbusDataType"]
