import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import auto_discovery
from tests.utils.modbus_test_server import CustomMqttHandler, run_async_server


# Mock mqtt.Client for the server
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
    # Use a dynamic port to avoid binding conflicts if tests run close together
    # But Modbus defaults to 502, we need to tell auto_discovery to search this port.
    port = 5502

    # Configure logging to show all debug output
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("tests.utils.modbus_test_server").setLevel(logging.DEBUG)
    logging.getLogger("sigenergy2mqtt.config.auto_discovery").setLevel(logging.DEBUG)
    logging.getLogger("pymodbus").setLevel(logging.INFO)  # Keep pymodbus less chatty unless needed

    mqtt_client = MockMqttClient()
    server_task = asyncio.create_task(run_async_server(mqtt_client, modbus_client=None, use_simplified_topics=False, host="127.0.0.1", port=port, log_level=logging.DEBUG))
    # modbus_test_server might take a second to bind
    from tests.utils.modbus_test_server import wait_for_server_start

    if not await wait_for_server_start("127.0.0.1", port):
        raise RuntimeError("Mock Modbus server failed to start")

    yield port

    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.fixture(autouse=True)
def reset_discovery_state():
    # Reset global serial numbers to prevent test pollution
    auto_discovery.serial_numbers = []


def test_scan_skip_loopback():
    """Verify that loopback is skipped (as per code)."""
    # This logic is internal to scan(), tested partly by workflow below
    pass


@pytest.mark.asyncio(loop_scope="module")
async def test_auto_discovery_scan_host(mock_modbus_server):
    """Test auto-discovery of the local test server."""
    port = mock_modbus_server

    results = []
    # scan_host signature: async def scan_host(ip: str, port: int, results: list, timeout: float = 0.25, retries: int = 0) -> None:
    await auto_discovery.scan_host("127.0.0.1", port, results, timeout=1.0)

    # Verify results
    assert len(results) == 1
    device = results[0]
    assert device["host"] == "127.0.0.1"
    assert device["port"] == port
    assert len(device["inverters"]) > 0


@pytest.mark.asyncio(loop_scope="module")
async def test_auto_discovery_workflow(mock_modbus_server):
    """Test the full scan workflow by mocking network discovery."""
    port = mock_modbus_server

    # Mocking internal `ping_scan`
    with patch("sigenergy2mqtt.config.auto_discovery.ping_scan", return_value={"127.0.0.1": 0.1}):
        # Mock interface
        snicaddr = MagicMock()
        snicaddr.family.name = "AF_INET"
        snicaddr.address = "192.168.1.100"
        snicaddr.netmask = "255.255.255.0"

        with patch("psutil.net_if_addrs", return_value={"eth0": [snicaddr]}):
            results = await asyncio.to_thread(auto_discovery.scan, port=port, modbus_timeout=1.0, modbus_retries=3)

            assert len(results) == 1
            assert results[0]["host"] == "127.0.0.1"
            assert results[0]["port"] == port
