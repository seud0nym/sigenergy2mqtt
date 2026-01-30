import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.influx_service import InfluxService


class MockResponse:
    def __init__(self, status_code, json_data=None, content=b""):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content
        self.text = "mock text"

    def json(self):
        return self._json_data


@pytest.fixture
def logger():
    return logging.getLogger("test_influx_new")


@pytest.fixture
def service(logger):
    """Create InfluxService with disabled init for isolated testing."""
    with patch.object(Config, "influxdb", None):
        svc = InfluxService(logger, plant_index=0)
    # Manually configure basic writer for these tests
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"
    svc._write_headers = {}
    return svc


class TestInfluxRetry:
    @pytest.mark.asyncio
    async def test_query_v2_retry_success(self, service):
        """Test that query succeeds after retries."""
        with patch.object(service._session, "post") as mock_post, patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Fail twice then succeed
            mock_post.side_effect = [Exception("Fail 1"), Exception("Fail 2"), MockResponse(200, content=b"success")]

            success, resp = await service._query_v2("http://base", "org", "tok", "flux")

            assert success is True
            assert mock_post.call_count == 3
            assert mock_sleep.call_count == 2  # Slept twice

    @pytest.mark.asyncio
    async def test_query_v2_retry_exhausted(self, service):
        """Test that query fails after max retries."""
        with patch.object(service._session, "post") as mock_post, patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Fail all times
            mock_post.side_effect = Exception("Fail")

            success, resp = await service._query_v2("http://base", "org", "tok", "flux", max_retries=2)

            assert success is False
            assert mock_post.call_count == 3  # Initial + 2 retries
            assert mock_sleep.call_count == 2


class TestInfluxRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiting_enforces_delay(self, service):
        """Test that rapid queries trigger rate limiting sleep."""
        # Use a real lock/semaphore but mock sleep to verify it's called
        service._query_interval = 1.0

        with patch.object(service._session, "post", return_value=MockResponse(200)) as mock_post, patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # First query sets the time
            await service._query_v2("http://base", "org", "tok", "q1")

            # Second query immediate, should sleep
            await service._query_v2("http://base", "org", "tok", "q2")

            # Verify sleep was called
            assert mock_sleep.called
            # Verify call args are roughly the interval
            args, _ = mock_sleep.call_args
            assert args[0] > 0.0


class TestInfluxBatching:
    @pytest.mark.asyncio
    async def test_batch_flush_on_threshold(self, service):
        """Test validation that batch flushes when size threshold is reached."""
        service._batch_size = 3
        service._flush_interval = 1000  # Large interval

        with patch.object(service, "_execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service._write_line("line1")
            await service._write_line("line2")
            mock_exec.assert_not_called()

            await service._write_line("line3")
            mock_exec.assert_called()

            # Verify batch content
            args, _ = mock_exec.call_args
            data = args[0]
            assert b"line1\nline2\nline3" == data

    @pytest.mark.asyncio
    async def test_batch_flush_on_interval(self, service):
        """Test validation that batch flushes when time interval is exceeded."""
        service._batch_size = 100
        service._flush_interval = 0.5
        service._last_flush = time.time() - 1.0  # Force interval expiry

        with patch.object(service, "_execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service._write_line("line1")

            mock_exec.assert_called()

            args, _ = mock_exec.call_args
            assert b"line1" == args[0]

    @pytest.mark.asyncio
    async def test_manual_flush(self, service):
        """Test public flush_buffer method."""
        with patch.object(service, "_execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service._write_line("line1")
            mock_exec.assert_not_called()

            await service.flush_buffer()
            mock_exec.assert_called()
