from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from sigenergy2mqtt.modbus import ModbusClient as _RealModbusClient

    ModbusClientType: TypeAlias = _RealModbusClient
    ModbusDataType: TypeAlias = _RealModbusClient.DATATYPE
else:
    ModbusClientType = Any
    ModbusDataType = Any
