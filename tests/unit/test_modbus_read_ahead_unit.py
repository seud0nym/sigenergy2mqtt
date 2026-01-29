"""Unit tests for ReadAhead class edge cases."""

import copy
from unittest.mock import MagicMock, patch

import pytest
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.modbus.read_ahead import ReadAhead
from sigenergy2mqtt.sensors.const import InputType


class TestReadAhead:
    """Test cases for ReadAhead class."""

    @pytest.fixture
    def mock_pdu(self):
        """Create a mock ModbusPDU with registers."""
        pdu = MagicMock(spec=ModbusPDU)
        pdu.isError.return_value = False
        pdu.registers = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        pdu.exception_code = 0
        pdu.address = 1000
        pdu.count = 10
        return pdu

    @pytest.fixture
    def read_ahead(self, mock_pdu):
        """Create a ReadAhead instance for testing."""
        return ReadAhead(address=1000, count=10, device_id=1, input_type=InputType.INPUT, pdu=mock_pdu)

    def test_last_address_property(self, read_ahead):
        """Test last_address property calculation."""
        # address=1000, count=10, so last_address = 1000 + 10 - 1 = 1009
        assert read_ahead.last_address == 1009

    def test_last_address_single_register(self):
        """Test last_address with single register."""
        pdu = MagicMock(spec=ModbusPDU)
        pdu.registers = [100]
        ra = ReadAhead(address=500, count=1, device_id=1, input_type=InputType.HOLDING, pdu=pdu)

        assert ra.last_address == 500

    def test_get_registers_success(self, read_ahead, mock_pdu):
        """Test successful get_registers within range."""
        with patch("sigenergy2mqtt.modbus.read_ahead.copy") as mock_copy:
            # Create a real deepcopy for the test
            copied_pdu = MagicMock(spec=ModbusPDU)
            mock_copy.deepcopy.return_value = copied_pdu

            result = read_ahead.get_registers(address=1002, count=3)

            # Verify the copied PDU was modified
            assert copied_pdu.address == 1002
            assert copied_pdu.count == 3
            assert copied_pdu.registers == [300, 400, 500]

    def test_get_registers_first_register(self, read_ahead, mock_pdu):
        """Test get_registers for first register in range."""
        with patch("sigenergy2mqtt.modbus.read_ahead.copy") as mock_copy:
            copied_pdu = MagicMock(spec=ModbusPDU)
            mock_copy.deepcopy.return_value = copied_pdu

            result = read_ahead.get_registers(address=1000, count=1)

            assert copied_pdu.registers == [100]

    def test_get_registers_last_register(self, read_ahead, mock_pdu):
        """Test get_registers for last register in range."""
        with patch("sigenergy2mqtt.modbus.read_ahead.copy") as mock_copy:
            copied_pdu = MagicMock(spec=ModbusPDU)
            mock_copy.deepcopy.return_value = copied_pdu

            result = read_ahead.get_registers(address=1009, count=1)

            assert copied_pdu.registers == [1000]

    def test_get_registers_full_range(self, read_ahead, mock_pdu):
        """Test get_registers for entire range."""
        with patch("sigenergy2mqtt.modbus.read_ahead.copy") as mock_copy:
            copied_pdu = MagicMock(spec=ModbusPDU)
            mock_copy.deepcopy.return_value = copied_pdu

            result = read_ahead.get_registers(address=1000, count=10)

            assert copied_pdu.registers == [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

    def test_get_registers_address_below_range(self, read_ahead):
        """Test get_registers raises IndexError when address is below range."""
        with pytest.raises(IndexError) as exc_info:
            read_ahead.get_registers(address=999, count=1)

        assert "address=999" in str(exc_info.value)
        assert "self.address=1000" in str(exc_info.value)

    def test_get_registers_address_plus_count_exceeds_range(self, read_ahead):
        """Test get_registers raises IndexError when address+count exceeds range."""
        with pytest.raises(IndexError) as exc_info:
            read_ahead.get_registers(address=1008, count=5)

        # 1008 + 5 - 1 = 1012 > 1009
        assert "count=5" in str(exc_info.value)
        assert "last_address" in str(exc_info.value)

    def test_get_registers_exactly_at_boundary(self, read_ahead, mock_pdu):
        """Test get_registers exactly at the boundary (should succeed)."""
        with patch("sigenergy2mqtt.modbus.read_ahead.copy") as mock_copy:
            copied_pdu = MagicMock(spec=ModbusPDU)
            mock_copy.deepcopy.return_value = copied_pdu

            # Address 1007, count 3: last address = 1007 + 3 - 1 = 1009 (exactly at boundary)
            result = read_ahead.get_registers(address=1007, count=3)

            assert copied_pdu.registers == [800, 900, 1000]

    def test_get_registers_pdu_is_exception_response(self):
        """Test get_registers raises IndexError when PDU is ExceptionResponse."""
        exception_pdu = ExceptionResponse(function_code=0x03, exception_code=0x02, device_id=1)

        ra = ReadAhead(address=1000, count=10, device_id=1, input_type=InputType.HOLDING, pdu=exception_pdu)

        with pytest.raises(IndexError) as exc_info:
            ra.get_registers(address=1000, count=1)

        assert "exception_code" in str(exc_info.value)

    def test_get_registers_pdu_is_error(self):
        """Test get_registers raises IndexError when PDU.isError() returns True."""
        error_pdu = MagicMock(spec=ModbusPDU)
        error_pdu.isError.return_value = True
        error_pdu.exception_code = 5
        error_pdu.registers = [100, 200]

        ra = ReadAhead(address=1000, count=2, device_id=1, input_type=InputType.INPUT, pdu=error_pdu)

        with pytest.raises(IndexError) as exc_info:
            ra.get_registers(address=1000, count=1)

        assert "exception_code" in str(exc_info.value)

    def test_get_registers_count_mismatch(self):
        """Test get_registers raises IndexError when register count doesn't match."""
        pdu = MagicMock(spec=ModbusPDU)
        pdu.isError.return_value = False
        # Only 3 registers but claiming count of 5
        pdu.registers = [100, 200, 300]

        ra = ReadAhead(address=1000, count=5, device_id=1, input_type=InputType.INPUT, pdu=pdu)

        # Try to get 5 registers but only 3 exist
        with pytest.raises(IndexError) as exc_info:
            ra.get_registers(address=1000, count=5)

        assert "Requested" in str(exc_info.value)
        assert "count=5" in str(exc_info.value)

    def test_read_ahead_dataclass_fields(self):
        """Test that ReadAhead has correct dataclass fields."""
        pdu = MagicMock(spec=ModbusPDU)

        ra = ReadAhead(address=2000, count=20, device_id=5, input_type=InputType.HOLDING, pdu=pdu)

        assert ra.address == 2000
        assert ra.count == 20
        assert ra.device_id == 5
        assert ra.input_type == InputType.HOLDING
        assert ra.pdu is pdu

    def test_get_registers_preserves_original_pdu(self, read_ahead, mock_pdu):
        """Test that get_registers doesn't modify the original PDU."""
        original_address = mock_pdu.address
        original_count = mock_pdu.count
        original_registers = mock_pdu.registers.copy()

        # Use real copy.deepcopy
        with patch("sigenergy2mqtt.modbus.read_ahead.copy.deepcopy") as mock_deepcopy:
            copied_pdu = MagicMock()
            mock_deepcopy.return_value = copied_pdu

            read_ahead.get_registers(address=1005, count=2)

        # Original values should be unchanged
        assert mock_pdu.address == original_address
        assert mock_pdu.count == original_count
        assert mock_pdu.registers == original_registers
