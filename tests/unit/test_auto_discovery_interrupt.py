import asyncio
import os
import signal
import time
from queue import Queue
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import auto_discovery

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_interrupted():
    """Ensure the _interrupted flag is reset before and after each test."""
    auto_discovery._interrupted = False
    yield
    auto_discovery._interrupted = False


@pytest.fixture(autouse=True)
def reset_serial_numbers():
    """Ensure the serial_numbers list is reset before each test."""
    auto_discovery.serial_numbers = []


# ---------------------------------------------------------------------------
# _check_interrupted
# ---------------------------------------------------------------------------


class TestCheckInterrupted:
    def test_does_not_raise_when_not_interrupted(self):
        auto_discovery._interrupted = False
        auto_discovery._check_interrupted()  # should not raise

    def test_raises_keyboard_interrupt_when_interrupted(self):
        auto_discovery._interrupted = True
        with pytest.raises(KeyboardInterrupt, match="interrupted by signal"):
            auto_discovery._check_interrupted()


# ---------------------------------------------------------------------------
# ping_worker interruption
# ---------------------------------------------------------------------------


class TestPingWorkerInterruption:
    def test_ping_worker_drains_queue_when_interrupted(self):
        """When _interrupted is set, ping_worker should drain the queue and return
        without actually pinging any hosts."""
        ip_queue: Queue[str] = Queue()
        for ip in ["10.0.0.1", "10.0.0.2", "10.0.0.3"]:
            ip_queue.put(ip)

        found_hosts: dict[str, float] = {}
        auto_discovery._interrupted = True

        # async ping_scan should return immediately and not call network connect
        with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection") as mock_open:
            results = asyncio.run(auto_discovery.ping_scan(["10.0.0.1", "10.0.0.2", "10.0.0.3"], concurrent=3, timeout=1))
            mock_open.assert_not_called()

        assert isinstance(results, dict)
        assert len(results) == 0

    def test_ping_worker_processes_normally_when_not_interrupted(self):
        """When _interrupted is False, ping_worker should process normally."""
        ip_queue: Queue[str] = Queue()
        ip_queue.put("1.2.3.4")
        found_hosts: dict[str, float] = {}

        mock_ans = MagicMock()
        mock_ans.is_alive = True
        mock_ans.destination = "1.2.3.4"
        mock_ans.avg_rtt = 100.0

        async def fake_open(host, port):
            writer = MagicMock()
            writer.close = MagicMock()
            writer.wait_closed = AsyncMock()
            return (MagicMock(), writer)

        with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", new=AsyncMock(side_effect=fake_open)):
            results = asyncio.run(auto_discovery.ping_scan(["1.2.3.4"], timeout=1))

        assert "1.2.3.4" in results


# ---------------------------------------------------------------------------
# ping_scan interruption
# ---------------------------------------------------------------------------


class TestPingScanInterruption:
    def test_ping_scan_returns_promptly_when_interrupted(self):
        """When _interrupted is set, ping_scan should return partial results
        within ~100ms rather than waiting for all pings to complete."""

        # Use a slow async_multiping that would block, but interrupted should avoid calling it
        async def slow_open(*args, **kwargs):
            time.sleep(10)
            writer = MagicMock()
            writer.close = MagicMock()
            writer.wait_closed = AsyncMock()
            return (MagicMock(), writer)

        auto_discovery._interrupted = True

        with patch("sigenergy2mqtt.config.auto_discovery.asyncio.open_connection", side_effect=slow_open) as mock_open:
            start = time.monotonic()
            result = asyncio.run(auto_discovery.ping_scan(["10.0.0.1", "10.0.0.2", "10.0.0.3"], concurrent=3, timeout=1))
            elapsed = time.monotonic() - start

        # Should return almost immediately (< 1s), not wait for multiping calls
        assert elapsed < 1.0
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# scan_host interruption
# ---------------------------------------------------------------------------


class TestScanHostInterruption:
    @pytest.mark.asyncio
    async def test_scan_host_stops_probing_when_interrupted(self):
        """When _interrupted is set during device probing, scan_host should raise
        KeyboardInterrupt rather than probing all 246 device IDs."""
        results = []

        probe_count = {"n": 0}

        async def mock_probe(m, address, count=1, device_id=247):
            probe_count["n"] += 1
            if address == 30051 and device_id == 247:
                return True  # Plant found
            # After the first device probe, set interrupted
            if probe_count["n"] >= 3:
                auto_discovery._interrupted = True
            return False

        with patch("sigenergy2mqtt.config.auto_discovery.AsyncModbusTcpClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.connect = AsyncMock()
            mock_client.connected = True
            mock_client.close = MagicMock()

            with patch("sigenergy2mqtt.config.auto_discovery.probe_register", side_effect=mock_probe):
                with pytest.raises(KeyboardInterrupt):
                    await auto_discovery.scan_host("1.2.3.4", 502, results)

        # Should have been interrupted well before probing all 246 device IDs
        assert probe_count["n"] < 20


# ---------------------------------------------------------------------------
# scan() interruption
# ---------------------------------------------------------------------------


class TestScanInterruption:
    def test_scan_stops_iterating_hosts_when_interrupted(self):
        """When _interrupted is set, scan() should raise KeyboardInterrupt
        instead of scanning all hosts."""
        auto_discovery._interrupted = True

        with patch("sigenergy2mqtt.config.auto_discovery.ping_scan", return_value={"1.2.3.4": 0.1, "5.6.7.8": 0.2}):
            snicaddr = MagicMock()
            snicaddr.family.name = "AF_INET"
            snicaddr.address = "192.168.1.100"
            snicaddr.netmask = "255.255.255.0"

            with patch("psutil.net_if_addrs", return_value={"eth0": [snicaddr]}):
                with pytest.raises(KeyboardInterrupt):
                    asyncio.run(auto_discovery.scan(port=502, modbus_timeout=0.1))


# ---------------------------------------------------------------------------
# __main__ early signal handler
# ---------------------------------------------------------------------------


class TestMainEarlySignalHandlers:
    def test_early_exit_sets_interrupted_flag(self):
        """First signal should set auto_discovery._interrupted = True."""
        import sigenergy2mqtt.config.auto_discovery as ad

        ad._interrupted = False

        from sigenergy2mqtt.__main__ import main

        # We need to capture the handler that main() would register
        # but we don't want to actually run main(). Instead, test the logic directly.
        # Simulate what _early_exit does:
        handlers = {}
        original_signal = signal.signal

        def capture_signal(sig, handler):
            handlers[sig] = handler
            return original_signal(sig, signal.SIG_DFL)

        with patch("signal.signal", side_effect=capture_signal):
            with patch("sigenergy2mqtt.__main__.initialize", side_effect=KeyboardInterrupt):
                import warnings

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=r"coroutine .* was never awaited", category=RuntimeWarning)
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    # Force garbage collection while our warning filter is active so
                    # any AsyncMock-created coroutine objects are collected under
                    # the filter instead of emitting unraisable warnings later.
                    import gc

                    gc.collect()
                assert exc_info.value.code == 130

        # Check that handlers were registered
        assert signal.SIGINT in handlers
        assert signal.SIGTERM in handlers

    def test_early_exit_first_signal_sets_flag(self):
        """Calling the early exit handler once should set _interrupted."""
        import sigenergy2mqtt.config.auto_discovery as ad

        ad._interrupted = False

        handlers = {}
        original_signal = signal.signal

        def capture_signal(sig, handler):
            handlers[sig] = handler
            return original_signal(sig, signal.SIG_DFL)

        with patch("signal.signal", side_effect=capture_signal):
            with patch("sigenergy2mqtt.__main__.initialize"):
                with patch("sigenergy2mqtt.__main__.asyncio.run"), patch("sigenergy2mqtt.__main__.async_main"):
                    import warnings

                    from sigenergy2mqtt.__main__ import main

                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message=r"coroutine .* was never awaited", category=RuntimeWarning)
                        main()
                        import gc

                        gc.collect()

        # Simulate first signal
        handler = handlers[signal.SIGINT]
        handler(signal.SIGINT, None)
        assert ad._interrupted is True

    def test_early_exit_second_signal_force_exits(self):
        """Calling the early exit handler twice should os._exit()."""
        import sigenergy2mqtt.config.auto_discovery as ad

        ad._interrupted = False

        handlers = {}
        original_signal = signal.signal

        def capture_signal(sig, handler):
            handlers[sig] = handler
            return original_signal(sig, signal.SIG_DFL)

        with patch("signal.signal", side_effect=capture_signal):
            with patch("sigenergy2mqtt.__main__.initialize"):
                with patch("sigenergy2mqtt.__main__.asyncio.run"), patch("sigenergy2mqtt.__main__.async_main"):
                    from sigenergy2mqtt.__main__ import main

                    main()

        handler = handlers[signal.SIGINT]
        # First call — sets flag
        handler(signal.SIGINT, None)
        assert ad._interrupted is True

        # Second call — should force exit via os._exit
        with patch("os._exit") as mock_exit:
            handler(signal.SIGINT, None)
            mock_exit.assert_called_once_with(130)

    def test_early_exit_sigterm_exit_code(self):
        """SIGTERM second signal should os._exit with code 143."""
        import sigenergy2mqtt.config.auto_discovery as ad

        ad._interrupted = False

        handlers = {}
        original_signal = signal.signal

        def capture_signal(sig, handler):
            handlers[sig] = handler
            return original_signal(sig, signal.SIG_DFL)

        with patch("signal.signal", side_effect=capture_signal):
            with patch("sigenergy2mqtt.__main__.initialize"):
                with patch("sigenergy2mqtt.__main__.asyncio.run"), patch("sigenergy2mqtt.__main__.async_main"):
                    from sigenergy2mqtt.__main__ import main

                    main()

        handler = handlers[signal.SIGTERM]
        # First call
        handler(signal.SIGTERM, None)
        # Second call — force exit with 143
        with patch("os._exit") as mock_exit:
            handler(signal.SIGTERM, None)
            mock_exit.assert_called_once_with(143)
