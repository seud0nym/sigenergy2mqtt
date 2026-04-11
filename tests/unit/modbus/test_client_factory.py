"""Unit tests for ModbusClientFactory class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.modbus.client_factory import ModbusClientFactory


class TestModbusClientFactory:
    """Test cases for ModbusClientFactory class."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset factory state before each test."""
        # Save original state
        original_clients = ModbusClientFactory._clients.copy()
        original_hosts = ModbusClientFactory._hosts.copy()
        ModbusClientFactory._clients.clear()
        ModbusClientFactory._hosts.clear()

        yield

        # Restore original state
        ModbusClientFactory._clients = original_clients
        ModbusClientFactory._hosts = original_hosts

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        """Test that get_client creates a new client when not cached."""
        mock_client = MagicMock()
        mock_client.connected = False
        mock_client.connect = AsyncMock()

        # After connect, set connected to True
        async def mock_connect():
            mock_client.connected = True

        mock_client.connect.side_effect = mock_connect

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client) as mock_cls:
            client = await ModbusClientFactory.get_client("192.168.1.100", 502)

            # Verify ModbusClient was instantiated
            mock_cls.assert_called_once_with("192.168.1.100", port=502, timeout=1.0, retries=3)

            # Verify connect was called
            mock_client.connect.assert_awaited_once()

            assert client is mock_client

    @pytest.mark.asyncio
    async def test_get_client_returns_cached_client(self):
        """Test that get_client returns cached client for same host/port."""
        mock_client = MagicMock()
        mock_client.connected = True  # Already connected

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client) as mock_cls:
            client1 = await ModbusClientFactory.get_client("192.168.1.100", 502)
            client2 = await ModbusClientFactory.get_client("192.168.1.100", 502)

            # ModbusClient should only be instantiated once
            mock_cls.assert_called_once()

            # Both calls should return the same client
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_client_different_hosts(self):
        """Test that different hosts get different clients."""
        mock_client1 = MagicMock()
        mock_client1.connected = True
        mock_client2 = MagicMock()
        mock_client2.connected = True

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient") as mock_cls:
            mock_cls.side_effect = [mock_client1, mock_client2]

            client1 = await ModbusClientFactory.get_client("192.168.1.100", 502)
            client2 = await ModbusClientFactory.get_client("192.168.1.101", 502)

            assert client1 is not client2
            assert mock_cls.call_count == 2

    @pytest.mark.asyncio
    async def test_get_client_different_ports(self):
        """Test that different ports on same host get different clients."""
        mock_client1 = MagicMock()
        mock_client1.connected = True
        mock_client2 = MagicMock()
        mock_client2.connected = True

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient") as mock_cls:
            mock_cls.side_effect = [mock_client1, mock_client2]

            client1 = await ModbusClientFactory.get_client("192.168.1.100", 502)
            client2 = await ModbusClientFactory.get_client("192.168.1.100", 503)

            assert client1 is not client2
            assert mock_cls.call_count == 2

    @pytest.mark.asyncio
    async def test_get_client_reconnects_disconnected_client(self):
        """Test that get_client reconnects a disconnected cached client."""
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect = AsyncMock()

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client):
            # First call - client is connected
            await ModbusClientFactory.get_client("192.168.1.100", 502)
            mock_client.connect.assert_not_awaited()

            # Simulate disconnection
            mock_client.connected = False

            async def mock_connect():
                mock_client.connected = True

            mock_client.connect.side_effect = mock_connect

            # Second call should reconnect
            await ModbusClientFactory.get_client("192.168.1.100", 502)
            mock_client.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_client_custom_timeout_and_retries(self):
        """Test that get_client passes custom timeout and retries."""
        mock_client = MagicMock()
        mock_client.connected = True

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client) as mock_cls:
            await ModbusClientFactory.get_client("192.168.1.100", 502, timeout=5.0, retries=10)

            mock_cls.assert_called_once_with("192.168.1.100", port=502, timeout=5.0, retries=10)

    @pytest.mark.asyncio
    async def test_get_client_connection_failure(self):
        """Test that get_client raises AssertionError on connection failure."""
        mock_client = MagicMock()
        mock_client.connected = False
        mock_client.connect = AsyncMock()  # connect() doesn't set connected to True

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client):
            with pytest.raises(AssertionError):
                await ModbusClientFactory.get_client("192.168.1.100", 502)

    def test_get_host_returns_host_for_known_client(self):
        """Test that get_host returns host string for known client."""
        mock_client = MagicMock()
        ModbusClientFactory._hosts[mock_client] = "192.168.1.100:502"

        result = ModbusClientFactory.get_host(mock_client)

        assert result == "192.168.1.100:502"

    def test_get_host_returns_none_for_none(self):
        """Test that get_host returns None for None input."""
        result = ModbusClientFactory.get_host(None)

        assert result is None

    def test_get_host_returns_none_for_unknown_client(self):
        """Test that get_host returns None for unknown client."""
        unknown_client = MagicMock()

        result = ModbusClientFactory.get_host(unknown_client)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_stores_host_mapping(self):
        """Test that get_client stores the host mapping."""
        mock_client = MagicMock()
        mock_client.connected = True

        with patch("sigenergy2mqtt.modbus.client_factory.ModbusClient", return_value=mock_client):
            await ModbusClientFactory.get_client("192.168.1.100", 502)

            # Verify host mapping was stored
            assert ModbusClientFactory.get_host(mock_client) == "192.168.1.100:502"
