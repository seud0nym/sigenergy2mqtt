import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pymodbus import ExceptionResponse
from sigenergy2mqtt.modbus.client import ModbusClient

async def read_single_register(client: ModbusClient, device_address: int, register: int, count: int, type: str):
    logging.debug(f"read: registers = {register}:{register + count - 1} ({count=}) device address = {device_address}")
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

async def main():
    client = ModbusClient("192.168.192.75", port=502)

    logging.info("Connecting to Modbus server...")
    await client.connect()

    await read_single_register(client, 247, 30281, 1, type="input")
    await read_single_register(client, 247, 30286, 2, type="input")
    await read_single_register(client, 247, 30292, 2, type="input")
    await read_single_register(client, 247, 40049, 2, type="holding")

    await read_single_register(client, 1, 30622, 1, type="input")
    await read_single_register(client, 1, 30623, 1, type="input")

    logging.info("Disconnecting from Modbus server...")
    client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
