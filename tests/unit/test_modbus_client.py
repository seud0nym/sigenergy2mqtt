"""Unit tests for ModbusClient class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.modbus.read_ahead import ReadAhead
from sigenergy2mqtt.sensors.const import InputType


class TestModbusClient:
    """Test cases for ModbusClient class."""

    @pytest.fixture
    def client(self):
        """Create a ModbusClient instance for testing."""
        with patch.object(ModbusClient, "__init__", lambda self, *args, **kwargs: None):
            client = ModbusClient.__new__(ModbusClient)
            client._read_ahead_pdu = {}
            client._trace = False
            client._read_count = 0
            client._cache_hits = 0
            return client

    @pytest.fixture
    def mock_pdu(self):
        """Create a mock ModbusPDU."""
        pdu = MagicMock(spec=ModbusPDU)
        pdu.isError.return_value = False
        pdu.registers = [100, 200, 300, 400, 500]
        pdu.exception_code = 0
        return pdu

    @pytest.fixture
    def mock_error_pdu(self):
        """Create a mock error ModbusPDU."""
        pdu = MagicMock(spec=ModbusPDU)
        pdu.isError.return_value = True
        pdu.exception_code = 2
        return pdu

    def test_trace_packet_handler_send(self, client):
        """Test trace packet handler for send."""
        client._trace = True

        with patch("sigenergy2mqtt.modbus.client.logging") as mock_logging:
            result = client._trace_packet_handler(is_send=True, data=b"\x01\x02\x03")

            mock_logging.debug.assert_called_once()
            assert "send" in mock_logging.debug.call_args[0][0].lower()

        assert result == b"\x01\x02\x03"

    def test_trace_packet_handler_recv(self, client):
        """Test trace packet handler for receive."""
        client._trace = True

        with patch("sigenergy2mqtt.modbus.client.logging") as mock_logging:
            result = client._trace_packet_handler(is_send=False, data=b"\x04\x05\x06")

            mock_logging.debug.assert_called_once()
            assert "recv" in mock_logging.debug.call_args[0][0].lower()

        assert result == b"\x04\x05\x06"

    def test_trace_packet_handler_disabled(self, client):
        """Test trace packet handler when tracing is disabled."""
        client._trace = False

        with patch("sigenergy2mqtt.modbus.client.logging") as mock_logging:
            result = client._trace_packet_handler(is_send=True, data=b"\x01\x02\x03")

            mock_logging.debug.assert_not_called()

        assert result == b"\x01\x02\x03"

    @pytest.mark.asyncio
    async def test_read_registers_cache_hit(self, client, mock_pdu):
        """Test _read_registers with cache hit."""
        # Set up cache
        read_ahead = MagicMock(spec=ReadAhead)
        read_ahead.get_registers.return_value = mock_pdu
        client._read_ahead_pdu = {1: {100: read_ahead}}

        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_cache_hits = AsyncMock()

            result = await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=True)

            assert result is mock_pdu
            assert client._cache_hits == 1
            assert client._read_count == 1
            read_ahead.get_registers.assert_called_once_with(100, count=1)

    @pytest.mark.asyncio
    async def test_read_registers_cache_miss_index_error(self, client, mock_pdu):
        """Test _read_registers when pre-read raises IndexError."""
        # Set up cache that will raise IndexError
        read_ahead = MagicMock(spec=ReadAhead)
        read_ahead.get_registers.side_effect = IndexError("Out of range")
        client._read_ahead_pdu = {1: {100: read_ahead}}

        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_cache_hits = AsyncMock()
            mock_metrics.modbus_read = AsyncMock()

            # Mock the parent class read method
            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_pdu

                await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=True)

                # Should fall through to actual read
                mock_read.assert_awaited_once()
                mock_metrics.modbus_read.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_registers_no_cache(self, client, mock_pdu):
        """Test _read_registers without using pre-read cache."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_pdu

                result = await client._read_registers(address=100, count=10, device_id=1, input_type=InputType.HOLDING, use_pre_read=False)

                # Verify metrics called with count=10
                mock_metrics.modbus_read.assert_awaited_once()
                assert mock_metrics.modbus_read.call_args[0][0] == 10
                mock_read.assert_awaited_once()
                assert result is mock_pdu

    @pytest.mark.asyncio
    async def test_read_registers_input_type(self, client, mock_pdu):
        """Test _read_registers with INPUT input type."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_input_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_pdu

                await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.INPUT, use_pre_read=False)

                mock_read.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_registers_none_response(self, client):
        """Test _read_registers when response is None."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read_error = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = None

                result = await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=False)

                # Should create ExceptionResponse
                assert isinstance(result, ExceptionResponse)
                mock_metrics.modbus_read_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_registers_error_response(self, client, mock_error_pdu):
        """Test _read_registers with error response."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read_error = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_error_pdu

                result = await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=False)

                assert result is mock_error_pdu
                mock_metrics.modbus_read_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_registers_modbus_exception(self, client):
        """Test _read_registers when ModbusException is raised."""
        from pymodbus.exceptions import ModbusException

        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read_error = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.side_effect = ModbusException("Connection error")

                with pytest.raises(ModbusException):
                    await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=False)

                mock_metrics.modbus_read_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_registers_unknown_input_type(self, client):
        """Test _read_registers with unknown input type."""
        with patch("sigenergy2mqtt.modbus.client.Metrics"):
            with pytest.raises(Exception, match="Unknown input type"):
                await client._read_registers(address=100, count=1, device_id=1, input_type="INVALID", use_pre_read=False)

    def test_bypass_read_ahead(self, client, mock_pdu):
        """Test bypass_read_ahead clears cache for specified registers."""
        read_ahead = MagicMock(spec=ReadAhead)
        client._read_ahead_pdu = {1: {100: read_ahead, 101: read_ahead, 102: read_ahead, 103: read_ahead}}

        client.bypass_read_ahead(address=101, count=2, device_id=1)

        # Registers 101 and 102 should be set to None
        assert client._read_ahead_pdu[1][100] is read_ahead
        assert client._read_ahead_pdu[1][101] is None
        assert client._read_ahead_pdu[1][102] is None
        assert client._read_ahead_pdu[1][103] is read_ahead

    def test_bypass_read_ahead_no_existing_cache(self, client):
        """Test bypass_read_ahead when device_id not in cache."""
        client._read_ahead_pdu = {}

        # Should not raise
        client.bypass_read_ahead(address=100, count=5, device_id=1)

    @pytest.mark.asyncio
    async def test_read_ahead_registers_stores_cache(self, client, mock_pdu):
        """Test read_ahead_registers stores response in cache."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read = AsyncMock()
            mock_metrics.modbus_cache_fill = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_input_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_pdu

                await client.read_ahead_registers(address=100, count=5, device_id=1, input_type=InputType.INPUT)

                # Verify cache fill metric called
                mock_metrics.modbus_cache_fill.assert_awaited_once()

                # Cache should be populated
                assert 1 in client._read_ahead_pdu
                for addr in range(100, 105):
                    assert addr in client._read_ahead_pdu[1]
                    assert isinstance(client._read_ahead_pdu[1][addr], ReadAhead)

    @pytest.mark.asyncio
    async def test_read_ahead_registers_error_clears_cache(self, client, mock_error_pdu):
        """Test read_ahead_registers sets cache to None on error."""
        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_read_error = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_input_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_error_pdu

                await client.read_ahead_registers(address=100, count=5, device_id=1, input_type=InputType.INPUT)

                # Cache should be set to None for all addresses
                assert 1 in client._read_ahead_pdu
                for addr in range(100, 105):
                    assert client._read_ahead_pdu[1][addr] is None

    @pytest.mark.asyncio
    async def test_read_holding_registers_delegates(self, client, mock_pdu):
        """Test read_holding_registers delegates to _read_registers."""
        with patch.object(client, "_read_registers", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = mock_pdu

            await client.read_holding_registers(100, count=2, device_id=3)

            mock_read.assert_awaited_once_with(100, count=2, device_id=3, input_type=InputType.HOLDING, no_response_expected=False, use_pre_read=True, trace=False)

    @pytest.mark.asyncio
    async def test_read_input_registers_delegates(self, client, mock_pdu):
        """Test read_input_registers delegates to _read_registers."""
        with patch.object(client, "_read_registers", new_callable=AsyncMock) as mock_read:
            mock_read.return_value = mock_pdu

            await client.read_input_registers(200, count=4, device_id=2)

            mock_read.assert_awaited_once_with(200, count=4, device_id=2, input_type=InputType.INPUT, no_response_expected=False, use_pre_read=True, trace=False)

    @pytest.mark.asyncio
    async def test_read_registers_cache_preread_none(self, client, mock_pdu):
        """Test _read_registers when pre-read entry is None (bypassed)."""
        # Set up cache with None entry (bypassed)
        client._read_ahead_pdu = {1: {100: None}}

        with patch("sigenergy2mqtt.modbus.client.Metrics") as mock_metrics:
            mock_metrics.modbus_cache_hits = AsyncMock()
            mock_metrics.modbus_read = AsyncMock()

            with patch("pymodbus.client.AsyncModbusTcpClient.read_holding_registers", new_callable=AsyncMock) as mock_read:
                mock_read.return_value = mock_pdu

                await client._read_registers(address=100, count=1, device_id=1, input_type=InputType.HOLDING, use_pre_read=True)

                # Should fall through to actual read since pre-read is None
                mock_read.assert_awaited_once()
