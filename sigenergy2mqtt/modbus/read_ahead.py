from dataclasses import dataclass
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from sigenergy2mqtt.sensors.const import InputType
import copy


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

    def get_registers(self, address: int, count: int) -> ModbusPDU | None:
        if address < self.address or address + count - 1 > self.last_address or isinstance(self.pdu, ExceptionResponse) or self.pdu.isError():
            return None
        start = address - self.address
        end = start + count
        registers = self.pdu.registers[start:end]
        if len(registers) != count:
            return None
        pdu = copy.deepcopy(self.pdu)
        pdu.address = address
        pdu.count = count
        pdu.registers = registers
        return pdu
