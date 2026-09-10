import copy
from dataclasses import dataclass

from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.common import InputType


@dataclass
class ReadAhead:
    """Snapshot of a contiguous Modbus register response for cache reuse.

    The object stores the original address range and response PDU from a
    successful read. Future narrower reads can be fulfilled by slicing the
    original register payload through :meth:`get_registers`.
    """
    address: int
    count: int
    device_id: int
    input_type: InputType
    pdu: ModbusPDU

    @property
    def last_address(self) -> int:
        """Return the inclusive final register address in this cached range."""
        return self.address + self.count - 1

    def get_registers(self, address: int, count: int) -> ModbusPDU:
        """Extract a sub-range from the cached PDU as a new response object.

        Args:
            address: Start address for the requested sub-range.
            count: Number of registers requested from the cached span.

        Returns:
            A deep-copied PDU with ``address``, ``count``, and ``registers`` set
            to the requested sub-range.

        Raises:
            IndexError: If the request falls outside the cached span, the source
                PDU is an error response, or the sliced payload length mismatches
                ``count``.
        """
        if address < self.address:
            raise IndexError(f"{address=} < {self.address=})")
        elif address + count - 1 > self.last_address:
            raise IndexError(f"{address=} + {count=} - 1 > {self.last_address=})")
        elif isinstance(self.pdu, ExceptionResponse) or self.pdu.isError():
            raise IndexError(f"Underlying PDU is in error ({self.pdu.exception_code=})")
        start = address - self.address
        end = start + count
        registers = self.pdu.registers[start:end]
        if len(registers) != count:
            raise IndexError(f"Requested {count=} but {len(registers)=}")
        pdu = copy.deepcopy(self.pdu)
        pdu.address = address
        pdu.count = count
        pdu.registers = registers
        return pdu
