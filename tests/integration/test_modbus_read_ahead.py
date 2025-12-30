import logging
import pytest
import asyncio
from sigenergy2mqtt.modbus.client import ModbusClient
from test.modbus_test_server import run_async_server, CustomMqttHandler
from sigenergy2mqtt.sensors.const import InputType


# Mock MqttClient for the server
class MockMqttClient:
    def __init__(self):
        self._user_data = CustomMqttHandler(asyncio.get_running_loop())

    def user_data_get(self):
        return self._user_data

    def subscribe(self, topic):
        return (0, 1)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def mock_modbus_server():
    port = 5503  # Use a different port to avoid conflicts

    # Configure logging
    # logging.basicConfig(level=logging.DEBUG)

    mqtt_client = MockMqttClient()
    server_task = asyncio.create_task(run_async_server(mqtt_client, modbus_client=None, use_simplified_topics=False, host="127.0.0.1", port=port, log_level=logging.INFO))

    # Allow server to bind
    await asyncio.sleep(2)

    yield port

    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio(loop_scope="module")
async def test_read_ahead_caching(mock_modbus_server):
    port = mock_modbus_server
    client = ModbusClient("127.0.0.1", port=port)
    await client.connect()
    assert client.connected

    # Ensure cache is empty initially
    assert client._read_ahead_pdu == {}
    assert client._cache_hits == 0

    # Perform Read Ahead
    # Range 31000-31010. 31004 is known to be populated (value 2).
    # We use InputType.INPUT for 31004.

    start_addr = 31000
    count = 10

    # Pre-read registers
    await client.read_ahead_registers(start_addr, count, device_id=1, input_type=InputType.INPUT)

    # Verify cache is populated
    assert 1 in client._read_ahead_pdu
    assert start_addr in client._read_ahead_pdu[1]

    # Verify NO cache hits yet (the pre-read itself doesn't count as a hit, or does it?)
    # The _read_registers logic only increments cache hits if use_pre_read=True is passed.
    # read_ahead_registers calls _read_registers with use_pre_read=False.
    assert client._cache_hits == 0

    # Test Cache HIT
    # Read register 31004. read_input_registers calls _read_registers with use_pre_read=True.
    rr = await client.read_input_registers(31004, 1, device_id=1)
    assert not rr.isError()
    assert rr.registers[0] == 2  # Known value
    assert client._cache_hits == 1  # Should increment

    # Test Cache HIT 2
    # Read register 31000
    rr2 = await client.read_input_registers(31000, 1, device_id=1)
    assert not rr2.isError()
    assert client._cache_hits == 2

    # Test Cache MISS (Out of range)
    # Read register 31020
    rr3 = await client.read_input_registers(31020, 1, device_id=1)
    assert not rr3.isError()
    assert client._cache_hits == 2  # Should NOT increment

    client.close()
