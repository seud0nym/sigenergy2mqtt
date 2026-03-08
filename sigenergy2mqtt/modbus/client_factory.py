import logging

from .client import ModbusClient


class ModbusClientFactory:
    """Connection pool and lifecycle manager for Modbus TCP clients."""
    _clients: dict[tuple[str, int], ModbusClient] = {}
    _hosts: dict[ModbusClient, str] = {}

    @classmethod
    async def get_client(cls, host: str, port: int, timeout: float = 1.0, retries: int = 3) -> ModbusClient:
        """Get or create a connected Modbus client for ``host:port``.

        Args:
            host: Target host name or IP.
            port: Target TCP port.
            timeout: Per-request timeout passed to pymodbus.
            retries: Retry count passed to pymodbus.

        Returns:
            A connected :class:`ModbusClient` instance from the pool.

        Raises:
            AssertionError: If connection attempt does not result in a connected
                client instance.
        """
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
    def get_host(cls, modbus: ModbusClient | None) -> str | None:
        """Return the tracked ``host:port`` for a pooled client."""
        return None if modbus is None or modbus not in cls._hosts else cls._hosts[modbus]

    @classmethod
    def clear(cls):
        """Close and remove all pooled clients and host mappings."""
        for client in cls._clients.values():
            try:
                client.close()
            except Exception:
                pass
        cls._clients.clear()
        cls._hosts.clear()

    @classmethod
    def remove(cls, client: ModbusClient):
        """Remove one client from the pool and close it if possible.

        Args:
            client: Client instance to remove and close.
        """
        # Find the key by searching for the client instance. This is safer than
        # relying on client.comm_params which may be absent in mock objects.
        key = next((k for k, v in cls._clients.items() if v is client), None)

        if key:
            del cls._clients[key]
            if client in cls._hosts:
                del cls._hosts[client]

        # Always attempt to close the client.
        try:
            client.close()
        except Exception:
            pass
