import asyncio
import logging
from collections.abc import Callable
from typing import ClassVar

from pymodbus.exceptions import ConnectionException, ModbusException

from .client import CONNECTIVITY, ModbusClient

logger = logging.getLogger(__name__)

# Backoff between attempts to reach a Modbus host that a worker thread needs
CONNECT_INITIAL_DELAY = 5.0
CONNECT_MAX_DELAY = 60.0
CONNECT_POLL_INTERVAL = 0.5


class ModbusConnectAborted(RuntimeError):
    """Raised when waiting for a Modbus host is abandoned because the caller is stopping."""


class ModbusClientFactory:
    """Connection pool and lifecycle manager for Modbus TCP clients."""

    _clients: ClassVar[dict[tuple[str, int], ModbusClient]] = {}
    _hosts: ClassVar[dict[ModbusClient, str]] = {}

    @classmethod
    async def get_client(cls, host: str, port: int, timeout: float = 1.0, retries: int = 3, stopping: Callable[[], bool] | None = None) -> ModbusClient:
        """Get or create a connected Modbus client for ``host:port``.

        Args:
            host: Target host name or IP.
            port: Target TCP port.
            timeout: Per-request timeout passed to pymodbus.
            retries: Retry count passed to pymodbus.
            stopping: Optional callable. When supplied, a failed connection is
                retried with backoff until the host is reachable (reported as a
                single outage of the host) or ``stopping()`` returns ``True``.
                Without it, a single attempt is made.

        Returns:
            A connected :class:`ModbusClient` instance from the pool.

        Raises:
            ModbusConnectAborted: If ``stopping()`` returned ``True`` while
                waiting for the host. The client is removed from the pool.
            ConnectionException: If no ``stopping`` callable was supplied and
                the connection attempt failed. The client is removed from the pool.
        """
        key = (host, port)
        if key not in cls._clients:
            logger.debug(f"Creating Modbus client for {host}:{port} ({timeout=}s {retries=})")
            modbus = ModbusClient(host, port=port, timeout=timeout, retries=retries, track_outages=True)
            cls._clients[key] = modbus
            cls._hosts[modbus] = f"{host}:{port}"
        client = cls._clients[key]
        if not client.connected:
            delay = CONNECT_INITIAL_DELAY
            while True:
                try:
                    await client.connect()
                except (ModbusException, OSError) as e:
                    logger.debug(f"Connecting to modbus://{host}:{port} raised {e!r}")
                if client.connected:
                    break
                if stopping is None:
                    cls.remove(client)
                    raise ConnectionException(f"Failed to connect to modbus://{host}:{port}")
                outage = client.outage
                if outage is not None:
                    outage.failure(
                        "unable to connect; retrying until it is available",
                        kind=CONNECTIVITY,
                        detail=f"Failed to connect to modbus://{host}:{port}; retrying in {delay:.0f}s",
                    )
                waited = 0.0
                while waited < delay:
                    if stopping():
                        cls.remove(client)
                        raise ModbusConnectAborted(f"Stopped waiting for modbus://{host}:{port}")
                    await asyncio.sleep(CONNECT_POLL_INTERVAL)
                    waited += CONNECT_POLL_INTERVAL
                delay = min(delay * 2, CONNECT_MAX_DELAY)
            logger.info(f"Connected to modbus://{host}:{port} ({timeout=}s {retries=})")
        return client

    @classmethod
    def get_host(cls, modbus: ModbusClient | None) -> str | None:
        """Return the tracked ``host:port`` for a pooled client."""
        return None if modbus is None or modbus not in cls._hosts else cls._hosts[modbus]

    @classmethod
    def clear(cls):
        """Close and remove all pooled clients and host mappings."""
        for key, client in cls._clients.items():
            host = key[0]
            port = key[1]
            try:
                client.close()
                logger.info(f"Disconnected from modbus://{host}:{port}")
            except (ValueError, TypeError, ModbusException, OSError, RuntimeError) as e:
                logger.info(f"Disconnecting from modbus://{host}:{port} raised non-critical exception: {e}")
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
            host = key[0]
            port = key[1]
        else:
            try:
                host = client.comm_params.host
                port = client.comm_params.port
            except (AttributeError, ValueError, TypeError, RuntimeError):
                host = "[undetermined]"
                port = 502

        # Always attempt to close the client.
        try:
            client.close()
            logger.info(f"Disconnected from modbus://{host}:{port}")
        except (ModbusException, OSError, RuntimeError) as e:
            logger.info(f"Disconnecting from modbus://{host}:{port} raised non-critical exception: {e}")
