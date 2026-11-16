"""ModbusClientFactory.get_client waits for an unreachable host instead of asserting."""

from unittest.mock import AsyncMock, patch

import pytest
from pymodbus.exceptions import ConnectionException

from sigenergy2mqtt.common.outage import clear_outage_trackers, outage_tracker
from sigenergy2mqtt.modbus import ModbusClientFactory, ModbusConnectAborted
from sigenergy2mqtt.modbus import client_factory as factory_module


@pytest.fixture(autouse=True)
def clean_factory():
    ModbusClientFactory._clients.clear()
    ModbusClientFactory._hosts.clear()
    clear_outage_trackers()
    yield
    ModbusClientFactory._clients.clear()
    ModbusClientFactory._hosts.clear()
    clear_outage_trackers()


class FakeClient:
    """Connects on the Nth attempt."""

    def __init__(self, connect_on: int | None):
        self.connected = False
        self.attempts = 0
        self._connect_on = connect_on
        self.outage = outage_tracker("modbus://h:502")
        self.closed = False

    async def connect(self):
        self.attempts += 1
        if self._connect_on is not None and self.attempts >= self._connect_on:
            self.connected = True
        return self.connected

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_single_attempt_failure_raises_connection_exception_and_leaves_the_pool():
    fake = FakeClient(connect_on=None)
    with patch.object(factory_module, "ModbusClient", return_value=fake), pytest.raises(ConnectionException):
        await ModbusClientFactory.get_client("h", 502)
    assert ModbusClientFactory._clients == {}
    assert fake.closed is True


@pytest.mark.asyncio
async def test_retries_until_connected_and_reports_one_outage():
    fake = FakeClient(connect_on=3)
    with patch.object(factory_module, "ModbusClient", return_value=fake), patch.object(factory_module.asyncio, "sleep", AsyncMock()):
        client = await ModbusClientFactory.get_client("h", 502, stopping=lambda: False)
    assert client is fake and fake.connected is True
    assert fake.attempts == 3
    assert fake.outage.active is True, "the outage ends with the first successful read, as for any other loss of the host"


@pytest.mark.asyncio
async def test_stopping_abandons_the_wait():
    fake = FakeClient(connect_on=None)
    with patch.object(factory_module, "ModbusClient", return_value=fake), patch.object(factory_module.asyncio, "sleep", AsyncMock()), pytest.raises(ModbusConnectAborted):
        await ModbusClientFactory.get_client("h", 502, stopping=lambda: True)
    assert fake.attempts == 1
    assert ModbusClientFactory._clients == {}


@pytest.mark.asyncio
async def test_connect_raising_is_treated_as_a_failed_attempt():
    fake = FakeClient(connect_on=None)
    fake.connect = AsyncMock(side_effect=OSError("unreachable"))
    with patch.object(factory_module, "ModbusClient", return_value=fake), pytest.raises(ConnectionException):
        await ModbusClientFactory.get_client("h", 502)
