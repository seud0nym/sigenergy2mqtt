from .read_ahead import ReadAhead
from pymodbus import FramerType
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.logging import Log
from pymodbus.pdu import ExceptionResponse, ModbusPDU
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.sensors.const import InputType
import logging
import time


class ModbusClient(AsyncModbusTcpClient):
    def __init__(self, *args, **kwargs):
        kwargs["framer"] = FramerType.SOCKET
        kwargs["timeout"] = 1
        kwargs["trace_packet"] = self._trace_packet_handler
        super().__init__(*args, **kwargs)
        self._read_ahead_pdu: dict[int, ReadAhead] = {}
        self._trace: bool = False

    def _trace_packet_handler(self, is_send: bool, data: bytes) -> bytes:
        if self._trace:
            if is_send:
                log_text = Log.build_msg("send: {}", data, ":hex")
            else:
                log_text = Log.build_msg("recv: {}", data, ":hex")
            logging.debug(log_text)
        return data

    async def _read_registers(
        self, address, count: int = 1, device_id: int = 1, input_type: InputType = InputType.HOLDING, no_response_expected: bool = False, use_pre_read: bool = False, trace: bool = False
    ) -> ModbusPDU:
        if use_pre_read and address in self._read_ahead_pdu and self._read_ahead_pdu[address] is not None:
            pre_read = self._read_ahead_pdu[address]
            if pre_read is not None:
                return pre_read.get_registers(address, count=count)
        self._trace = trace
        try:
            start = time.monotonic()
            if input_type == InputType.HOLDING:
                rr = await super().read_holding_registers(address, count=count, device_id=device_id, no_response_expected=no_response_expected)
            elif input_type == InputType.INPUT:
                rr = await super().read_input_registers(address, count=count, device_id=device_id, no_response_expected=no_response_expected)
            else:
                raise Exception(f"Unknown input type '{input_type}'")
            elapsed = time.monotonic() - start
            if rr is None:
                return None
            elif rr.isError() or isinstance(rr, ExceptionResponse):
                await Metrics.modbus_read_error()
                return rr
            else:
                await Metrics.modbus_read(count, elapsed)
                return rr
        except ModbusException:
            await Metrics.modbus_read_error()
            raise
        except Exception:
            raise
        finally:
            self._trace = False

    def bypass_read_ahead(self, address: int, count: int = 1) -> None:
        self._read_ahead_pdu.update({key: None for key in range(address, address + count)})

    async def read_ahead_registers(self, address, count: int = 1, device_id: int = 1, input_type: InputType = InputType.HOLDING, no_response_expected: bool = False, trace: bool = False) -> None:
        rr = await self._read_registers(address, count=count, device_id=device_id, input_type=input_type, no_response_expected=no_response_expected, trace=trace)
        if rr is not None and not rr.isError() and not isinstance(rr, ExceptionResponse):
            self._read_ahead_pdu.update({key: ReadAhead(address, count, device_id, input_type, rr) for key in range(address, address + count)})

    async def read_holding_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False, trace: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.HOLDING, no_response_expected=no_response_expected, use_pre_read=True, trace=trace)

    async def read_input_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False, trace: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.INPUT, no_response_expected=no_response_expected, use_pre_read=True, trace=trace)
