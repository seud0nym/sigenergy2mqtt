import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pymodbus import ExceptionResponse
from sigenergy2mqtt.modbus.client import ModbusClient


register: int = 30613
count: int = 11
device_address: int = 1


async def read_single_register():
    client = ModbusClient("192.168.192.75", port=502)

    logging.info("Connecting to Modbus server...")
    await client.connect()

    logging.debug(f"Reading registers {register}:{register + count - 1} from device address {device_address}...")
    rr = await client.read_input_registers(register, count=count, device_id=device_address)
    if rr.isError() or isinstance(rr, ExceptionResponse):
        match rr.exception_code:
            case 1:
                logging.error("Result:", "0x01 ILLEGAL FUNCTION")
            case 2:
                logging.error("Result:", "0x02 ILLEGAL DATA ADDRESS")
            case 3:
                logging.error("Result:", "0x03 ILLEGAL DATA VALUE")
            case 4:
                logging.error("Result:", "0x04 SLAVE DEVICE FAILURE")
            case _:
                logging.error(rr)

    logging.info("Disconnecting from Modbus server...")
    client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(read_single_register())
    loop.close()
