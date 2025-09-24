from dataclasses import dataclass
from pymodbus import FramerType
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.sensors.const import InputType
from typing import Final
import asyncio
import copy
import logging
import time


@dataclass
class ReadAhead:
    address: int
    count: int
    device_id: int
    input_type: InputType
    pdu: ModbusPDU

    @property
    def last_address(self) -> int:
        return self.address + self.count - 1

    def get_registers(self, address: int, count: int) -> ModbusPDU | None:
        if address < self.address or address + count - 1 > self.last_address or isinstance(self.pdu, ExceptionResponse) or self.pdu.isError():
            return None
        start = address - self.address
        end = start + count
        registers = self.pdu.registers[start:end]
        if len(registers) != count:
            return None
        pdu = copy.deepcopy(self.pdu)
        pdu.address = address
        pdu.count = count
        pdu.registers = registers
        return pdu


class ModbusClient(AsyncModbusTcpClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_ahead_pdu: dict[int, ReadAhead] = {}

    async def _read_registers(
        self, address, count: int = 1, device_id: int = 1, input_type: InputType = InputType.HOLDING, no_response_expected: bool = False, use_pre_read: bool = False
    ) -> ModbusPDU:
        if use_pre_read and address in self._read_ahead_pdu and self._read_ahead_pdu[address] is not None:
            pre_read = self._read_ahead_pdu[address]
            if pre_read is not None:
                return pre_read.get_registers(address, count=count)
        try:
            start = time.monotonic()
            if input_type == InputType.HOLDING:
                rr = await super().read_holding_registers(address, count=count, device_id=device_id, no_response_expected=no_response_expected)
            elif input_type == InputType.INPUT:
                rr = await super().read_input_registers(address, count=count, device_id=device_id, no_response_expected=no_response_expected)
            else:
                raise Exception(f"Unknown input type '{input_type}'")
            elapsed = time.monotonic() - start
            if rr is None:
                return None
            elif rr.isError() or isinstance(rr, ExceptionResponse):
                await Metrics.modbus_read_error()
                return rr
            else:
                await Metrics.modbus_read(count, elapsed)
                return rr
        except ModbusException:
            await Metrics.modbus_read_error()
            raise
        except Exception:
            raise

    def bypass_read_ahead(self, address: int, count: int = 1) -> None:
        self._read_ahead_pdu.update({key: None for key in range(address, address + count)})

    async def read_ahead_registers(self, address, count: int = 1, device_id: int = 1, input_type: InputType = InputType.HOLDING, no_response_expected: bool = False) -> None:
        rr = await self._read_registers(address, count=count, device_id=device_id, input_type=input_type, no_response_expected=no_response_expected)
        if rr is not None and not rr.isError() and not isinstance(rr, ExceptionResponse):
            self._read_ahead_pdu.update({key: ReadAhead(address, count, device_id, input_type, rr) for key in range(address, address + count)})

    async def read_holding_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.HOLDING, no_response_expected=no_response_expected, use_pre_read=True)

    async def read_input_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.INPUT, no_response_expected=no_response_expected, use_pre_read=True)


class ClientFactory:
    _clients: dict[tuple[str, int], ModbusClient] = {}
    _hosts: dict[ModbusClient, asyncio.Lock] = {}
    _logger: Final = logging.getLogger("pymodbus")

    @classmethod
    async def get_client(self, host: str, port: int) -> ModbusClient:
        key = (host, port)
        if key not in self._clients:
            self._logger.info(f"Creating Modbus client for {host}:{port}")
            modbus = ModbusClient(host, port=port, framer=FramerType.SOCKET, timeout=1)
            self._clients[key] = modbus
            self._hosts[modbus] = f"{host}:{port}"
        client = self._clients[key]
        if not client.connected:
            await client.connect()
            assert client.connected
            self._logger.info(f"Connected to Modbus interface at {host}:{port}")
        return client

    @classmethod
    def get_host(self, modbus: ModbusClient):
        return None if modbus not in self._hosts else self._hosts[modbus]
