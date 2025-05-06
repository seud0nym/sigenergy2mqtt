from pymodbus import FramerType
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from typing import Final
import asyncio
import logging


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
