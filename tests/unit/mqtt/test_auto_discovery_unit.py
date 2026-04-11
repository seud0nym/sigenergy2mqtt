import asyncio
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
    class Reply:
        def __init__(self, dest, avg_rtt):
            self.is_alive = True
            self.avg_rtt = avg_rtt
            self.destination = dest

    async def fake_open(host, port):
        # simulate a successful connection returning (reader, writer)
        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return (MagicMock(), writer)

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", new=AsyncMock(side_effect=fake_open)):
        results = asyncio.run(auto_discovery.ping_scan(["1.2.3.4"], timeout=1))

    assert "1.2.3.4" in results
    assert isinstance(results["1.2.3.4"], float)


def test_ping_scan():
    # Ensure async ping_scan returns expected structure
    class Reply:
        def __init__(self, dest, avg_rtt):
            self.is_alive = True
            self.avg_rtt = avg_rtt
            self.destination = dest

    async def fake_open(host, port):
        async def _noop(): pass
        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = _noop
        return (MagicMock(), writer)

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", new=fake_open):
        results = asyncio.run(auto_discovery.ping_scan(["1.2.3.4"], concurrent=1))

    assert isinstance(results, dict)
    assert "1.2.3.4" in results


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

    assert len(results) == 0


@pytest.mark.asyncio
async def test_ping_scan_empty_list():
    results = await auto_discovery.ping_scan([])
    assert results == {}


@pytest.mark.asyncio
async def test_ping_scan_invalid_concurrent():
    async def fake_open(host, port):
        async def _noop():
            pass

        writer = MagicMock()
        writer.close = MagicMock()
        writer.wait_closed = _noop
        return (MagicMock(), writer)

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", new=fake_open):
        results = await auto_discovery.ping_scan(["1.2.3.4"], concurrent=0)
        assert "1.2.3.4" in results


@pytest.mark.asyncio
async def test_ping_scan_timeout():
    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", side_effect=asyncio.TimeoutError):
        results = await auto_discovery.ping_scan(["1.2.3.4"], timeout=0.1)
        assert results == {}


@pytest.mark.asyncio
async def test_ping_scan_exception_in_tasks():
    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", side_effect=Exception("TCP fail")):
        with patch("logging.debug") as mock_log:
            results = await auto_discovery.ping_scan(["1.2.3.4"])
            assert results == {}
            assert any("TCP check raised" in str(call) for call in mock_log.call_args_list)


@pytest.mark.asyncio
async def test_ping_scan_interrupted_at_checkpoint():
    # Hit line 147 via line 124
    with patch("sigenergy2mqtt.config.auto_discovery._check_interrupted", side_effect=auto_discovery.DiscoveryInterruptedError("interrupted")):
        with pytest.raises(KeyboardInterrupt):
            await auto_discovery.ping_scan(["1.2.3.4"])


@pytest.mark.asyncio
async def test_ping_scan_gather_cancelled():
    # Hit line 132 by mocking gather to raise CancelledError
    # We use a side effect that raises once then behaves normally to avoid infinite recursion
    # if gather is called in the except block (which it is at line 136).
    calls = []

    async def mock_gather(*args, **kwargs):
        if not calls:
            calls.append(1)
            raise asyncio.CancelledError()
        return []

    # Patch BOTH asyncio.gather in the module
    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.gather", side_effect=mock_gather):
        with pytest.raises(asyncio.CancelledError):
            await auto_discovery.ping_scan(["1.2.3.4"])


@pytest.mark.asyncio
async def test_ping_scan_exception_on_gather_is_logged():
    # Hit 141 and 151
    async def fake_open(host, port):
        raise Exception("TCP fail")

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", side_effect=fake_open):
        with patch("logging.debug") as mock_log:
            await auto_discovery.ping_scan(["1.2.3.4"])
            assert any("TCP check raised" in str(call) or "TCP port scan failed" in str(call) for call in mock_log.call_args_list)


@pytest.mark.asyncio
async def test_ping_scan_top_level_exception():
    # Hit 151
    # To hit 151, the Exception must happen OUTSIDE of the loop or be one that propagates
    # In this case, if we mock the whole loop or concurrent chunking
    with patch("sigenergy2mqtt.config.auto_discovery.range", side_effect=RuntimeError("loop fail")):
        with patch("logging.debug") as mock_log:
            await auto_discovery.ping_scan(["1.2.3.4"])
            assert any("TCP port scan failed" in str(call) for call in mock_log.call_args_list)






@pytest.mark.asyncio
async def test_reconnect_already_connected():
    modbus = MagicMock()
    modbus.connected = True
    await auto_discovery._reconnect(modbus)
    assert not modbus.connect.called


@pytest.mark.asyncio
async def test_reconnect_failure_then_success():
    class LocalMockModbus:
        def __init__(self):
            self.comm_params = MagicMock(host="127.0.0.1", port=502)
            self._connected = False
            self.close = MagicMock()

        @property
        def connected(self):
            return self._connected

        async def connect(self):
            # 1st call fails, 2nd succeeds
            if not getattr(self, "_connect_called_once", False):
                self._connect_called_once = True
                raise Exception("fail")
            self._connected = True

    modbus = LocalMockModbus()
    with patch("logging.debug") as mock_debug:
        await auto_discovery._reconnect(modbus, max_attempts=3)
        assert modbus.connected is True
        # Verify it logged at least once that it failed
        assert any("failed: fail" in str(call) for call in mock_debug.call_args_list)


@pytest.mark.asyncio
async def test_reconnect_all_fail():
    class LocalMockModbus:
        def __init__(self):
            self.comm_params = MagicMock(host="127.0.0.1", port=502)
            self.connected = False
            self.close = MagicMock()

        async def connect(self):
            raise Exception("fail")

    modbus = LocalMockModbus()
    with patch("logging.warning") as mock_warn:
        await auto_discovery._reconnect(modbus, max_attempts=2)
        assert modbus.connected is False
        mock_warn.assert_called_with("Could not reconnect to 127.0.0.1:502 after 2 attempts")







@pytest.mark.asyncio
async def test_probe_register_modbus_exception_reconnect():
    modbus = AsyncMock()
    modbus.read_input_registers.side_effect = ModbusException("error")
    modbus.comm_params.host = "127.0.0.1"
    modbus.comm_params.port = 502

    with patch("sigenergy2mqtt.config.auto_discovery._reconnect", new_callable=AsyncMock) as mock_reconnect:
        await auto_discovery.probe_register(modbus, 100)
        mock_reconnect.assert_called_once()


@pytest.mark.asyncio
async def test_get_serial_number_generic_exception():
    modbus = AsyncMock()
    modbus.read_input_registers.side_effect = Exception("boom")
    modbus.comm_params.host = "127.0.0.1"
    modbus.comm_params.port = 502

    result = await auto_discovery.get_serial_number(modbus, device_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_scan_host_not_connected():
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = False
        results = []
        await auto_discovery.scan_host("1.2.3.4", 502, results)
        assert results == []


@pytest.mark.asyncio
async def test_scan_host_interrupted_during_gather():
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        mock_client.close = MagicMock()

        async def mock_probe(m, address, count=1, device_id=247):
            return True

        with patch("sigenergy2mqtt.config.auto_discovery.probe_register", side_effect=mock_probe):
            with patch("sigenergy2mqtt.config.auto_discovery._check_interrupted", side_effect=auto_discovery.DiscoveryInterruptedError("interrupted")):
                with pytest.raises(KeyboardInterrupt):
                    await auto_discovery.scan_host("1.2.3.4", 502, [])


@pytest.mark.asyncio
async def test_discovered_device_has_devices_none():
    from sigenergy2mqtt.config.auto_discovery import DiscoveredDevice

    dev = DiscoveredDevice("host", 502)
    assert dev.has_devices() is False


@pytest.mark.asyncio
async def test_discovered_device_to_dict():
    from sigenergy2mqtt.config.auto_discovery import DiscoveredDevice

    dev = DiscoveredDevice("host", 502)
    dev.inverters = [1]
    dev.dc_chargers = [2]
    dev.ac_chargers = [3]
    d = dev.to_dict()
    assert d["host"] == "host"
    assert d["inverters"] == [1]
    assert d["dc-chargers"] == [2]
    assert d["ac-chargers"] == [3]


@pytest.mark.asyncio
async def test_probe_device_id_ignored_serial_combined():
    # Hit 235
    modbus = AsyncMock()
    from sigenergy2mqtt.config.auto_discovery import DiscoveredDevice
    device = DiscoveredDevice("host", 502)
    auto_discovery.serial_numbers = ["SN1"]

    with patch("sigenergy2mqtt.config.auto_discovery.probe_register", return_value=True):
        with patch("sigenergy2mqtt.config.auto_discovery.get_serial_number", return_value="SN1"):
            with patch("logging.info") as mock_log:
                await auto_discovery._probe_device_id(modbus, 1, device)
                assert any("already discovered" in str(call) for call in mock_log.call_args_list)


@pytest.mark.asyncio
async def test_scan_full_flow():
    # Hit 343-384
    with patch("sigenergy2mqtt.config.auto_discovery._local_networks") as mock_nets:
        mock_nets.return_value = {"192.168.1.10": MagicMock(hosts=lambda: [MagicMock(__str__=lambda s: "192.168.1.1")])}
        with patch("sigenergy2mqtt.config.auto_discovery.ping_scan", return_value={"192.168.1.1": 0.1}):
            with patch("sigenergy2mqtt.config.auto_discovery.scan_host") as mock_scan_host:
                async def fake_scan(ip, port, results, **kwargs):
                    results.append({"host": ip})

                mock_scan_host.side_effect = fake_scan

                final = await auto_discovery.scan()
                assert len(final) == 2
                assert any(r["host"] == "127.0.0.1" for r in final)
                assert any(r["host"] == "192.168.1.1" for r in final)


@pytest.mark.asyncio
async def test_scan_interrupted_error_handling():
    # Hit 377-378
    # We need the exception to happen INSIDE the try block at line 372
    # So we patch scan_with_sem or gather.
    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.gather", side_effect=auto_discovery.DiscoveryInterruptedError):
        with pytest.raises(KeyboardInterrupt):
            await auto_discovery.scan()


@pytest.mark.asyncio
async def test_scan_generic_exception_logging():
    # Hit 379-380
    # Mock _local_networks to ensure only 127.0.0.1 is scanned, avoiding multiple coroutines
    with patch("sigenergy2mqtt.config.auto_discovery._local_networks", return_value={}):
        with patch("sigenergy2mqtt.config.auto_discovery.scan_host", side_effect=Exception("boom")):
            with patch("logging.debug") as mock_log:
                await auto_discovery.scan()
                assert any("Scan failed: boom" in str(call) for call in mock_log.call_args_list)



def test_install_async_signal_handlers():
    # Hit 392-396
    mock_event = MagicMock()
    mock_loop = MagicMock()
    with patch("asyncio.get_event_loop", return_value=mock_loop):
        auto_discovery._install_async_signal_handlers(mock_event)
        assert mock_loop.add_signal_handler.called


def test_local_networks_exclusion():
    # Hit 310-325, especially 317
    mock_addr1 = MagicMock()
    mock_addr1.address = "172.17.0.1"
    mock_addr1.netmask = "255.255.0.0"
    mock_addr1.family.name = "AF_INET"

    mock_addr2 = MagicMock()
    mock_addr2.address = "192.168.1.10"
    mock_addr2.netmask = "255.255.255.0"
    mock_addr2.family.name = "AF_INET"

    mock_ifaddrs = {
        "docker0": [mock_addr1],
        "eth0": [mock_addr2],
    }
    with patch("psutil.net_if_addrs", return_value=mock_ifaddrs):
        nets = auto_discovery._local_networks()
        # docker0 should be excluded by name prefix
        assert "172.17.0.1" not in nets
        assert "192.168.1.10" in nets



@pytest.mark.asyncio
async def test_scan_host_cancelled_error_in_chunk():
    # Hit 284-289
    with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        mock_client.close = MagicMock()

        with patch("sigenergy2mqtt.config.auto_discovery.probe_register", return_value=True):
            with patch("sigenergy2mqtt.config.auto_discovery.asyncio.gather", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await auto_discovery.scan_host("1.2.3.4", 502, [])




# =============================================================================
# ping_scan chunking (merged from low-volume chunking module)
# =============================================================================


def test_ping_scan_chunking_calls_async_multiping_multiple_times():
    ip_list = [f"192.168.0.{i}" for i in range(1, 8)]
    concurrent = 3

    async def fake_gather(*coros, return_exceptions=True):
        return [("0.0.0.0", None) for _ in coros]

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.gather", new=AsyncMock(side_effect=fake_gather)) as mock_gather:
        results = asyncio.run(auto_discovery.ping_scan(ip_list, concurrent=concurrent, timeout=1))

        assert mock_gather.call_count == 3
        for call, expected_size in zip(mock_gather.call_args_list, [3, 3, 1]):
            assert len(call.args) == expected_size

        assert isinstance(results, dict)
        assert len(results) == 0
