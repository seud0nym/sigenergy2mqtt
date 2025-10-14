from .client import ModbusClient
import asyncio
import logging


class ModbusClientFactory:
    _clients: dict[tuple[str, int], ModbusClient] = {}
    _hosts: dict[ModbusClient, asyncio.Lock] = {}

    @classmethod
    async def get_client(self, host: str, port: int, timeout: float = 1.0, retries: int = 3) -> ModbusClient:
        key = (host, port)
        if key not in self._clients:
            logging.debug(f"Creating Modbus client for {host}:{port} ({timeout=}s {retries=})")
            modbus = ModbusClient(host, port=port, timeout=timeout, retries=retries)
            self._clients[key] = modbus
            self._hosts[modbus] = f"{host}:{port}"
        client = self._clients[key]
        if not client.connected:
            await client.connect()
            assert client.connected
            logging.info(f"Connected to modbus://{host}:{port} ({timeout=}s {retries=})")
        return client

    @classmethod
    def get_host(self, modbus: ModbusClient):
        return None if modbus not in self._hosts else self._hosts[modbus]
