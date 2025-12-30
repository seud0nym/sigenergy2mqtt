import logging
import pytest
import asyncio
from sigenergy2mqtt.modbus.client import ModbusClient
from test.modbus_test_server import run_async_server, CustomMqttHandler


# Mock MqttClient
class MockMqttClient:
    def __init__(self):
        self._user_data = CustomMqttHandler(asyncio.get_running_loop())

    def user_data_get(self):
        return self._user_data

    def subscribe(self, topic):
        return (0, 1)


@pytest.fixture
async def mock_modbus_server():
    # Start the server in a way that we can connect to it
    mqtt_client = MockMqttClient()

    server_task = asyncio.create_task(run_async_server(mqtt_client, modbus_client=None, use_simplified_topics=False, log_level=logging.DEBUG))

    # Give server time to start
    await asyncio.sleep(2)

    yield

    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_modbus_read(mock_modbus_server):
    """Test reading from the mock Modbus server using the application ModbusClient."""
    client = ModbusClient("127.0.0.1", port=502)
    await client.connect()
    assert client.connected

    # Read OutputType (Address 31004)
    # The mock server populates this with value 2 in CustomDataBlock.add_sensor
    # sensors/base.py defines OutputType with address 31004.

    # Sigenergy ModbusClient signature:
    # read_input_registers(self, address, count: int = 1, device_id: int = 1, ...)

    rr = await client.read_input_registers(31004, 1, device_id=1)

    # Check if we got a valid response
    assert not rr.isError()
    assert rr.registers[0] == 2

    client.close()
