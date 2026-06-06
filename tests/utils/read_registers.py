import asyncio
import logging
import os
import sys
from typing import TypeAlias

from pymodbus import ExceptionResponse
from pymodbus.client.mixin import ModbusClientMixin

ModbusDataType: TypeAlias = ModbusClientMixin.DATATYPE

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
os.environ["SIGENERGY2MQTT_LOG_LEVEL"] = "DEBUG"
os.environ["SIGENERGY2MQTT_LOG_FMT"] = "{asctime} {levelname:<8} {message}"

from sigenergy2mqtt.modbus.client import ModbusClient  # noqa: E402


async def read_single_register(client: ModbusClient, device_address: int, register: int, count: int, type: str, data_type: ModbusDataType):
    logging.info(f"read: registers = {register}:{register + count - 1} ({count=}) device address = {device_address}")
    if type == "input":
        rr = await client.read_input_registers(register, count=count, device_id=device_address, trace=True)
    elif type == "holding":
        rr = await client.read_holding_registers(register, count=count, device_id=device_address, trace=True)
    else:
        raise Exception(f"invalid {type=}")
    if rr.isError() or isinstance(rr, ExceptionResponse):
        match rr.exception_code:
            case 1:
                logging.error("then: 0x01 ILLEGAL FUNCTION")
            case 2:
                logging.error("then: 0x02 ILLEGAL DATA ADDRESS")
            case 3:
                logging.error("then: 0x03 ILLEGAL DATA VALUE")
            case 4:
                logging.error("then: 0x04 SLAVE DEVICE FAILURE")
            case _:
                logging.error(rr)
    else:
        logging.info(f"then: value returned = {client.convert_from_registers(rr.registers, data_type)} ({data_type.name})")


async def main():
    client = ModbusClient("10.10.20.75", port=502)

    logging.info("Connecting to Modbus server...")
    await client.connect()

    await read_single_register(client, 1, 30500, 15, type="input", data_type=ModbusDataType.STRING)
    await read_single_register(client, 1, 30515, 10, type="input", data_type=ModbusDataType.STRING)
    await read_single_register(client, 1, 30525, 15, type="input", data_type=ModbusDataType.STRING)

    await read_single_register(client, 247, 30272, 2, type="input", data_type=ModbusDataType.UINT32)
    await read_single_register(client, 247, 30274, 2, type="input", data_type=ModbusDataType.UINT32)
    await read_single_register(client, 247, 30286, 1, type="input", data_type=ModbusDataType.UINT16)
    await read_single_register(client, 247, 40157, 1, type="holding", data_type=ModbusDataType.UINT16)
    await read_single_register(client, 247, 40158, 1, type="holding", data_type=ModbusDataType.UINT16)
    await read_single_register(client, 247, 40159, 1, type="holding", data_type=ModbusDataType.UINT16)

    await read_single_register(client, 247, 50000, 1, type="holding", data_type=ModbusDataType.UINT16)

    await read_single_register(client, 247, 32500, 15, type="input", data_type=ModbusDataType.STRING)

    await read_single_register(client, 247, 42500, 1, type="holding", data_type=ModbusDataType.UINT16)

    await read_single_register(client, 247, 30002, 1, type="input", data_type=ModbusDataType.INT16)

    await read_single_register(client, 1, 30622, 1, type="input", data_type=ModbusDataType.UINT16)
    await read_single_register(client, 1, 30623, 1, type="input", data_type=ModbusDataType.UINT16)

    await read_single_register(client, 247, 30281, 2, type="input", data_type=ModbusDataType.UINT16)
    await read_single_register(client, 247, 40049, 2, type="holding", data_type=ModbusDataType.UINT32)

    logging.info("Disconnecting from Modbus server...")
    client.close()


if __name__ == "__main__":
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
