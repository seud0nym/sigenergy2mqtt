import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from test import get_sensor_instances, cancel_sensor_futures
from pymodbus import __version__ as pymodbus_version
from pymodbus import FramerType, ModbusDeviceIdentification
from pymodbus.client.base import ModbusClientMixin
from pymodbus.datastore import ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartAsyncTcpServer
from random import randint

_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


class CustomDataBlock(ModbusSparseDataBlock):
    """Custom data block to work around problem running in pymodbus 3.11.1"""

    def __init__(self, values=None, mutable=True):
        super().__init__(values=values, mutable=mutable)

    @classmethod
    def create(cls, values=None):
        return cls(values)

    async def async_getValues(self, fc_as_hex: int, address: int, count=1):
        return super().getValues(address, count)


async def run_async_server() -> None:
    context = {}
    sensors = await get_sensor_instances(hass=False)
    for sensor in sensors.values():
        if hasattr(sensor, "_device_address"):
            if sensor._device_address not in context:
                context[sensor._device_address] = CustomDataBlock.create()
            if sensor._data_type == ModbusClientMixin.DATATYPE.STRING:
                match sensor._address:
                    case 30500:
                        value = "SigenStor EC 12.0 TP"
                    case 30515:
                        value = "CMU123A45BP678"
                    case 30525:
                        value = "V100R001C00SPC108B088F"
                    case _:
                        value = "string value"
                registers = ModbusClientMixin.convert_to_registers(value, sensor._data_type)
                if len(registers) < sensor._count:
                    registers.extend([0] * (sensor._count - len(registers)))  # Pad with zeros
                elif len(registers) > sensor._count:
                    registers = registers[: sensor._count]  # Truncate to the required length
            else:
                match sensor._address:
                    case 31025:
                        value = 16
                    case 31026:
                        value = 4
                    case _:
                        value = randint(0,255)
                registers = ModbusClientMixin.convert_to_registers(value, sensor._data_type)
            context[sensor._device_address].setValues(sensor._address, registers)
    cancel_sensor_futures()
    _logger.info("Starting ASYNC Modbus TCP Testing Server...")
    await StartAsyncTcpServer(
        context=ModbusServerContext(devices=context, single=False if len(context) > 1 else True),
        identity=ModbusDeviceIdentification(
            info_name={
                "VendorName": "seud0nym",
                "ProductCode": "sigenergy2mqtt",
                "VendorUrl": "https://github.com/seud0nym/sigenergy2mqtt/",
                "ProductName": "sigenergy2mqtt Testing Modbus Server",
                "ModelName": "sigenergy2mqtt Testing Modbus Server",
                "MajorMinorRevision": pymodbus_version,
            }
        ),
        address=("0.0.0.0", 502),
        framer=FramerType.SOCKET,
    )


async def async_helper() -> None:
    await run_async_server()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
