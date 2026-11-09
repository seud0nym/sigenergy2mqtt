"""Outage tracking in ModbusClient."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ConnectionException, ModbusIOException, ParameterException
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.common.outage import OutageTracker, outage_tracker
from sigenergy2mqtt.modbus.client import ModbusClient

READ = "pymodbus.client.AsyncModbusTcpClient.read_holding_registers"


@pytest.fixture
def metrics():
    with patch("sigenergy2mqtt.metrics.Metrics") as mock_metrics:
        mock_metrics.modbus_read_error = AsyncMock()
        mock_metrics.modbus_read = AsyncMock()
        mock_metrics.modbus_cache_hits = AsyncMock()
        yield mock_metrics


def _ok_pdu():
    pdu = MagicMock(spec=ModbusPDU)
    pdu.isError.return_value = False
    pdu.registers = [1]
    return pdu


async def test_untracked_by_default():
    client = ModbusClient("127.0.0.1", port=15020)
    assert client.outage is None


async def test_tracked_client_shares_tracker_for_host():
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    assert isinstance(client.outage, OutageTracker)
    assert client.outage is outage_tracker("modbus://127.0.0.1:15020")


@pytest.mark.parametrize("error", [ModbusIOException("No response received after 3 retries"), ConnectionException("Not connected"), OSError("unreachable")])
async def test_connectivity_errors_start_outage(metrics, error, caplog):
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    with patch(READ, new_callable=AsyncMock, side_effect=error), caplog.at_level(logging.WARNING):
        with pytest.raises(type(error)):
            await client.read_holding_registers(1)
        with pytest.raises(type(error)):
            await client.read_holding_registers(2)
    assert client.outage.active
    started = [r for r in caplog.records if "outage started" in r.getMessage()]
    assert len(started) == 1
    assert started[0].getMessage().startswith("modbus://127.0.0.1:15020 outage started:")
    assert client.outage.suppressed == 1


async def test_other_modbus_errors_do_not_start_outage(metrics):
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    with patch(READ, new_callable=AsyncMock, side_effect=ParameterException("bad")):
        with pytest.raises(ParameterException):
            await client.read_holding_registers(1)
    assert not client.outage.active


async def test_successful_read_ends_outage(metrics, caplog):
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    client.outage.failure(ModbusIOException("down"))
    with patch(READ, new_callable=AsyncMock, return_value=_ok_pdu()), caplog.at_level(logging.INFO):
        await client.read_holding_registers(1)
    assert not client.outage.active
    assert any("outage ended" in r.getMessage() for r in caplog.records)


async def test_exception_response_ends_outage(metrics):
    """A Modbus exception response still proves the device is reachable."""
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    client.outage.failure(ModbusIOException("down"))
    with patch(READ, new_callable=AsyncMock, return_value=ExceptionResponse(0x03, 0x02)):
        await client.read_holding_registers(1)
    assert not client.outage.active


async def test_untracked_client_ignores_outages(metrics):
    client = ModbusClient("127.0.0.1", port=15020)
    with patch(READ, new_callable=AsyncMock, side_effect=ModbusIOException("down")):
        with pytest.raises(ModbusIOException):
            await client.read_holding_registers(1)
    assert not outage_tracker("modbus://127.0.0.1:15020").active


async def test_trace_connect_counts_disconnects():
    client = ModbusClient("127.0.0.1", port=15020)
    client._trace_connect_handler(True)
    client._trace_connect_handler(False)
    client._trace_connect_handler(False)
    health = client.snapshot()
    assert health.disconnect_count == 2
    assert health.last_disconnected_at is not None
    assert health.close_count == 0


async def test_connection_lost_starts_outage_immediately():
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    client._trace_connect_handler(False)
    assert client.outage.active
    # A subsequent timeout is the same kind of problem, so it is not reported as a new error
    assert client.outage.failure(ModbusIOException("No response received"), kind="connectivity") is False


async def test_application_close_is_not_an_outage():
    client = ModbusClient("127.0.0.1", port=15020, track_outages=True)
    client.close()
    client._trace_connect_handler(False)  # pymodbus may report the disconnection after close() returns
    assert not client.outage.active
