import logging

from .client import ModbusClient


class ModbusClientFactory:
    _clients: dict[tuple[str, int], ModbusClient] = {}
    _hosts: dict[ModbusClient, str] = {}

    @classmethod
    async def get_client(cls, host: str, port: int, timeout: float = 1.0, retries: int = 3) -> ModbusClient:
        key = (host, port)
        if key not in cls._clients:
            logging.debug(f"Creating Modbus client for {host}:{port} ({timeout=}s {retries=})")
            modbus = ModbusClient(host, port=port, timeout=timeout, retries=retries)
            cls._clients[key] = modbus
            cls._hosts[modbus] = f"{host}:{port}"
        client = cls._clients[key]
        if not client.connected:
            await client.connect()
            assert client.connected
            logging.info(f"Connected to modbus://{host}:{port} ({timeout=}s {retries=})")
        return client

    @classmethod
    def get_host(cls, modbus: ModbusClient):
        return None if modbus not in cls._hosts else cls._hosts[modbus]
