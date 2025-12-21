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
        kwargs["trace_packet"] = self._trace_packet_handler
        super().__init__(*args, **kwargs)
        self._read_ahead_pdu: dict[int, dict[int, ReadAhead]] = {}
        self._trace: bool = False
        self._read_count: int = 0
        self._cache_hits: int = 0

    def _trace_packet_handler(self, is_send: bool, data: bytes) -> bytes:
        if self._trace:
            if is_send:
                log_text = Log.build_msg("send: {}", data, ":hex")
            else:
                log_text = Log.build_msg("recv: {}", data, ":hex")
            logging.debug(log_text)
        return data

    async def _read_registers(
        self, address: int, count: int = 1, device_id: int = 1, input_type: InputType = InputType.HOLDING, no_response_expected: bool = False, use_pre_read: bool = False, trace: bool = False
    ) -> ModbusPDU:
        if use_pre_read:
            self._read_count += 1
            if device_id in self._read_ahead_pdu and address in self._read_ahead_pdu[device_id]:
                pre_read = self._read_ahead_pdu[device_id][address]
                if pre_read is not None:
                    self._cache_hits += 1
                    await Metrics.modbus_cache_hits(self._read_count, self._cache_hits)
                    return pre_read.get_registers(address, count=count)
            await Metrics.modbus_cache_hits(self._read_count, self._cache_hits)
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

    def bypass_read_ahead(self, address: int, count: int = 1, device_id: int = 1) -> None:
        if device_id in self._read_ahead_pdu:
            self._read_ahead_pdu[device_id].update({key: None for key in range(address, address + count)})

    async def read_ahead_registers(self, address, count: int = 1, device_id: int = 1, input_type: InputType = InputType.INPUT, no_response_expected: bool = False, trace: bool = False) -> int:
        rr = await self._read_registers(address, count=count, device_id=device_id, input_type=input_type, no_response_expected=no_response_expected, use_pre_read=False, trace=trace)
        if rr:
            if (rr.isError() or isinstance(rr, ExceptionResponse)):
                self._read_ahead_pdu[device_id].update({key: None for key in range(address, address + count)}) # Set registers to None to prevent unexpected values 
            else:
                if device_id not in self._read_ahead_pdu:
                    self._read_ahead_pdu[device_id] = {}
                self._read_ahead_pdu[device_id].update({key: ReadAhead(address, count, device_id, input_type, rr) for key in range(address, address + count)})
            return rr.exception_code
        return -1

    async def read_holding_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False, trace: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.HOLDING, no_response_expected=no_response_expected, use_pre_read=True, trace=trace)

    async def read_input_registers(self, address, count: int = 1, device_id: int = 1, no_response_expected: bool = False, trace: bool = False) -> ModbusPDU:
        return await self._read_registers(address, count=count, device_id=device_id, input_type=InputType.INPUT, no_response_expected=no_response_expected, use_pre_read=True, trace=trace)
