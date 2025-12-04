from pymodbus import ExceptionResponse
from pymodbus.client import ModbusTcpClient


register: int = 30276
count: int = 1
device_address: int = 247
datatype: ModbusTcpClient.DATATYPE = None


client = ModbusTcpClient("192.168.192.75", port=502)
client.connect()

print(f"Reading registers {register}:{register + count - 1} from device address {device_address}...")
rr = client.read_input_registers(register, count=count, device_id=device_address)
if rr.isError() or isinstance(rr, ExceptionResponse):
    match rr.exception_code:
        case 1:
            print("Result:", "0x01 ILLEGAL FUNCTION")
        case 2:
            print("Result:", "0x02 ILLEGAL DATA ADDRESS")
        case 3:
            print("Result:", "0x03 ILLEGAL DATA VALUE")
        case 4:
            print("Result:", "0x04 SLAVE DEVICE FAILURE")
        case _:
            print(rr)
else:
    if datatype is None:
        match count:
            case 1:
                datatype = ModbusTcpClient.DATATYPE.UINT16
            case 2:
                datatype = ModbusTcpClient.DATATYPE.UINT32
            case 4:
                datatype = ModbusTcpClient.DATATYPE.UINT64
            case _:
                datatype = ModbusTcpClient.DATATYPE.STRING
    print("Result:", client.convert_from_registers(rr.registers, datatype))

client.close()
