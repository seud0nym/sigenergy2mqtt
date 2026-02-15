import asyncio
from unittest.mock import AsyncMock, patch

from sigenergy2mqtt.config import auto_discovery


def test_ping_scan_chunking_calls_async_multiping_multiple_times():
    """Ensure ping_scan chunks the IP list and calls async_multiping per chunk."""
    ip_list = [f"192.168.0.{i}" for i in range(1, 8)]  # 7 IPs
    concurrent = 3
    # Patch module's asyncio.gather to inspect chunking behavior
    async def fake_gather(*coros, return_exceptions=True):
        # return successful (ip, latency) tuples for each coroutine
        results = []
        for c in coros:
            # c is a coroutine returned by check_single_host(ip)
            # we can't run it directly here, so fabricate a tuple placeholder
            # use the IP index from repr(c) as a fallback; instead, return a dummy
            results.append(("0.0.0.0", None))
        return results

    with patch("sigenergy2mqtt.config.auto_discovery.asyncio.gather", new=AsyncMock(side_effect=fake_gather)) as mock_gather:
        results = asyncio.run(auto_discovery.ping_scan(ip_list, concurrent=concurrent, timeout=1))

        # Expect ceil(7/3) == 3 gather invocations (one per chunk)
        assert mock_gather.call_count == 3

        # Verify the sizes of the gathered coroutines per call match expected chunk sizes
        expected_chunk_sizes = [3, 3, 1]
        for call, expected_size in zip(mock_gather.call_args_list, expected_chunk_sizes):
            assert len(call.args) == expected_size

        # No hosts returned (fake_gather returns None latencies)
        assert isinstance(results, dict)
        assert len(results) == 0
