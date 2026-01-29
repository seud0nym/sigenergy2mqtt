import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus import ExceptionResponse, ModbusException

from sigenergy2mqtt.config import auto_discovery


@pytest.mark.asyncio
async def test_probe_register_success():
    modbus = AsyncMock()
    response = MagicMock(isError=lambda: False)
    response.registers = [0] * 1
    modbus.read_input_registers.return_value = response

    result = await auto_discovery.probe_register(modbus, 30051)
    assert result is True
    modbus.read_input_registers.assert_called_once_with(address=30051, count=1, device_id=247)


@pytest.mark.asyncio
async def test_probe_register_error_response():
    modbus = AsyncMock()
    modbus.read_input_registers.return_value = MagicMock(isError=lambda: True)

    result = await auto_discovery.probe_register(modbus, 30051)
    assert result is False


@pytest.mark.asyncio
async def test_probe_register_modbus_exception():
    modbus = AsyncMock()
    modbus.connected = False
    modbus.close = MagicMock()
    modbus.connect = AsyncMock()

    def side_effect_connect():
        modbus.connected = True

    modbus.connect.side_effect = side_effect_connect

    modbus.read_input_registers.side_effect = ModbusException("error")

    with patch("logging.debug"):
        result = await auto_discovery.probe_register(modbus, 30051)

    assert result is False
    assert modbus.connect.called


@pytest.mark.asyncio
async def test_probe_register_generic_exception():
    modbus = AsyncMock()
    modbus.read_input_registers.side_effect = Exception("boom")
    modbus.comm_params.host = "127.0.0.1"
    modbus.comm_params.port = 502

    with patch("logging.debug") as mock_log:
        result = await auto_discovery.probe_register(modbus, 30051)
        assert result is False
        mock_log.assert_called()


@pytest.mark.asyncio
async def test_get_serial_number_success():
    modbus = AsyncMock()
    rr = MagicMock()
    rr.isError.return_value = False
    rr.registers = [0] * 10
    modbus.read_input_registers = AsyncMock(return_value=rr)
    modbus.convert_from_registers = MagicMock(return_value="SERIAL123")

    result = await auto_discovery.get_serial_number(modbus, device_id=1)
    assert result == "SERIAL123"


@pytest.mark.asyncio
async def test_get_serial_number_exception_response():
    modbus = AsyncMock()
    modbus.read_input_registers.return_value = ExceptionResponse(0x04)

    result = await auto_discovery.get_serial_number(modbus, device_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_get_serial_number_modbus_exception():
    modbus = AsyncMock()
    modbus.read_input_registers.side_effect = ModbusException("error")
    modbus.comm_params.host = "127.0.0.1"
    modbus.comm_params.port = 502

    result = await auto_discovery.get_serial_number(modbus, device_id=1)
    assert result is None


def test_ping_worker():
    from queue import Queue

    ip_queue = Queue()
    ip_queue.put("1.2.3.4")
    found_hosts = {}

    class MockPacket:
        def __init__(self, t):
            self.time = t
            self.sent_time = t - 5.0

    rx = MockPacket(10.0)
    tx = MockPacket(10.0)

    mock_ans = MagicMock()
    layer1 = MagicMock()
    layer1.__getitem__.side_effect = lambda i: [tx, rx][i]
    mock_ans.__getitem__.return_value = layer1

    with patch("sigenergy2mqtt.config.auto_discovery.sr1", return_value=mock_ans):
        auto_discovery.ping_worker(ip_queue, found_hosts, 0.5)

    assert "1.2.3.4" in found_hosts
    assert found_hosts["1.2.3.4"] == 5.0


def test_ping_scan():
    with patch("sigenergy2mqtt.config.auto_discovery.threading.Thread") as mock_thread:
        with patch("sigenergy2mqtt.config.auto_discovery.Queue") as mock_queue_cls:
            mock_queue = mock_queue_cls.return_value
            mock_t = MagicMock()
            mock_thread.return_value = mock_t

            results = auto_discovery.ping_scan(["1.2.3.4"], threads=1)

            assert mock_thread.called
            assert mock_t.start.called
            assert mock_queue.join.called


@pytest.mark.asyncio
async def test_scan_host_modbus_exception():
    results = []
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock(side_effect=ModbusException("fail"))

        await auto_discovery.scan_host("1.2.3.4", 502, results)
        assert len(results) == 0


@pytest.mark.asyncio
async def test_scan_host_no_plant():
    results = []
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        mock_client.close = MagicMock()

        with patch("sigenergy2mqtt.config.auto_discovery.probe_register", return_value=False):
            await auto_discovery.scan_host("1.2.3.4", 502, results)
            assert len(results) == 0


@pytest.mark.asyncio
async def test_scan_host_full_discovery():
    results = []
    auto_discovery.serial_numbers = []
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        mock_client.close = MagicMock()

        async def mock_probe(m, address, count=1, device_id=247):
            if address == 30051:
                return True
            if address == 31501 and device_id == 1:
                return True
            if address == 30578 and device_id == 2:
                return True
            if address == 32000 and device_id == 3:
                return True
            return False

        with patch("sigenergy2mqtt.config.auto_discovery.probe_register", side_effect=mock_probe):
            with patch("sigenergy2mqtt.config.auto_discovery.get_serial_number", side_effect=["SN1", "SN2"]):
                await auto_discovery.scan_host("1.2.3.4", 502, results)

    assert len(results) == 1
    device = results[0]
    assert 1 in device["dc-chargers"]
    assert 1 in device["inverters"]
    assert 2 in device["inverters"]
    assert 3 in device["ac-chargers"]


@pytest.mark.asyncio
async def test_scan_host_ignored_serials():
    results = []
    auto_discovery.serial_numbers = ["SN1"]
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        mock_client.close = MagicMock()

        async def mock_probe(m, address, count=1, device_id=247):
            if address == 30051:
                return True
            if address == 31501 and device_id == 1:
                return True
            return False

        with patch("sigenergy2mqtt.config.auto_discovery.probe_register", side_effect=mock_probe):
            with patch("sigenergy2mqtt.config.auto_discovery.get_serial_number", return_value="SN1"):
                with patch("logging.info") as mock_log:
                    await auto_discovery.scan_host("1.2.3.4", 502, results)
                    mock_log.assert_any_call(" -> IGNORED Inverter 1 at 1.2.3.4:502 - serial number SN1 already discovered")

    assert len(results) == 0
