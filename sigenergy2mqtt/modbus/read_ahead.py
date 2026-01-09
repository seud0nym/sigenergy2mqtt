import copy
from dataclasses import dataclass

from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.sensors.const import InputType


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

    def get_registers(self, address: int, count: int) -> ModbusPDU:
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
