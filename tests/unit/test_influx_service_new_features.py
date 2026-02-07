import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.hass_history_sync import HassHistorySync
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
    mock_config = MagicMock()
    # Set defaults required by __init__
    mock_config.enabled = False
    mock_config.max_retries = 3
    mock_config.pool_connections = 100
    mock_config.pool_maxsize = 100
    mock_config.batch_size = 100
    mock_config.flush_interval = 1.0
    mock_config.query_interval = 0.1

    with patch.object(Config, "influxdb", mock_config):
        svc = InfluxService(logger, plant_index=0)
    # Manually configure basic writer for these tests
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"
    svc._write_headers = {}
    svc._online = True  # Mark as online so writes/queries proceed
    return svc


@pytest.fixture
def hass_sync(logger):
    """Create HassHistorySync for testing chunking and sync methods."""
    mock_config = MagicMock()
    mock_config.enabled = False
    mock_config.max_retries = 3
    mock_config.pool_connections = 100
    mock_config.pool_maxsize = 100
    mock_config.batch_size = 100
    mock_config.flush_interval = 1.0
    mock_config.query_interval = 0.1
    mock_config.default_measurement = "state"

    with patch.object(Config, "influxdb", mock_config):
        svc = HassHistorySync(logger, plant_index=0)
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"
    svc._write_headers = {}
    svc._online = True
    return svc


class TestInfluxRetry:
    @pytest.mark.asyncio
    async def testquery_v2_retry_success(self, service):
        """Test that query succeeds after retries."""
        with patch.object(service._session, "post") as mock_post, patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Fail twice then succeed
            mock_post.side_effect = [Exception("Fail 1"), Exception("Fail 2"), MockResponse(200, content=b"success")]

            success, resp = await service.query_v2("http://base", "org", "tok", "flux")

            assert success is True
            assert mock_post.call_count == 3
            assert mock_sleep.call_count == 2  # Slept twice

    @pytest.mark.asyncio
    async def testquery_v2_retry_exhausted(self, service):
        """Test that query fails after max retries."""
        with patch.object(service._session, "post") as mock_post, patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Fail all times
            mock_post.side_effect = Exception("Fail")

            success, resp = await service.query_v2("http://base", "org", "tok", "flux", max_retries=2)

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
            await service.query_v2("http://base", "org", "tok", "q1")

            # Second query immediate, should sleep
            await service.query_v2("http://base", "org", "tok", "q2")

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

        with patch.object(service, "execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service.write_line("line1")
            await service.write_line("line2")
            mock_exec.assert_not_called()

            await service.write_line("line3")
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

        with patch.object(service, "execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service.write_line("line1")

            mock_exec.assert_called()

            args, _ = mock_exec.call_args
            assert b"line1" == args[0]

    @pytest.mark.asyncio
    async def test_manual_flush(self, service):
        """Test public flush_buffer method."""
        with patch.object(service, "execute_write", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = True

            await service.write_line("line1")
            mock_exec.assert_not_called()

            await service.flush_buffer()
            mock_exec.assert_called()


class TestInfluxChunking:
    @pytest.mark.asyncio
    async def testcopy_records_v1_chunking(self, hass_sync):
        """Test that copy_records_v1 fetches multiple chunks."""
        Config.influxdb.sync_chunk_size = 2
        hass_sync.write_line = AsyncMock()

        # Mock query_v1 to return two chunks of 2 records, then an empty result
        chunk1 = {
            "results": [
                {
                    "series": [
                        {
                            "name": "power",
                            "columns": ["time", "value"],
                            "values": [[1000, 10.0], [900, 9.0]],
                        }
                    ]
                }
            ]
        }
        chunk2 = {
            "results": [
                {
                    "series": [
                        {
                            "name": "power",
                            "columns": ["time", "value"],
                            "values": [[800, 8.0], [700, 7.0]],
                        }
                    ]
                }
            ]
        }
        empty = {"results": [{"series": []}]}

        with patch.object(hass_sync, "query_v1", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = [(True, chunk1), (True, chunk2), (True, empty)]

            count = await hass_sync.copy_records_v1({"base": "b", "auth": None}, "power", {}, None)

            assert count == 4
            assert mock_query.call_count == 3
            assert hass_sync.write_line.call_count == 4

            # Verify the queries use DESC and correct current_before
            calls = mock_query.call_args_list
            assert "ORDER BY time DESC LIMIT 2" in calls[0].args[3]
            assert "time < 900s" in calls[1].args[3]
            assert "time < 700s" in calls[2].args[3]
            assert calls[0].kwargs["epoch"] == "s"

    @pytest.mark.asyncio
    async def testcopy_records_v2_chunking(self, hass_sync):
        """Test that copy_records_v2 fetches multiple chunks."""
        Config.influxdb.sync_chunk_size = 2
        hass_sync.write_line = AsyncMock()

        # CSV Responses for Flux
        header = "#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,dateTime:RFC3339,double,string,string\n,result,table,_start,_stop,_time,_value,_field,_measurement\n"
        chunk1_csv = header + ",,0,0,0,2024-01-01T00:00:10Z,10.0,value,power\n,,0,0,0,2024-01-01T00:00:09Z,9.0,value,power"
        chunk2_csv = header + ",,0,0,0,2024-01-01T00:00:08Z,8.0,value,power\n,,0,0,0,2024-01-01T00:00:07Z,7.0,value,power"
        empty_csv = ""

        with patch.object(hass_sync, "query_v2", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = [(True, chunk1_csv), (True, chunk2_csv), (True, empty_csv)]

            count = await hass_sync.copy_records_v2({"base": "b", "org": "o", "token": "t"}, "power", {}, None)

            assert count == 4
            assert mock_query.call_count == 3
            assert hass_sync.write_line.call_count == 4

            # Verify Flux query contains DESC sort and limit
            calls = mock_query.call_args_list
            assert 'sort(columns: ["_time"], desc: true)' in calls[0].args[3]
            assert "limit(n: 2)" in calls[0].args[3]

    @pytest.mark.asyncio
    async def test_chunking_stops_on_offline(self, hass_sync):
        """Test that chunking loop aborts if service goes offline."""
        Config.influxdb.sync_chunk_size = 2
        hass_sync.write_line = AsyncMock()

        chunk1 = {
            "results": [
                {
                    "series": [
                        {
                            "name": "power",
                            "columns": ["time", "value"],
                            "values": [[1000, 10.0], [900, 9.0]],
                        }
                    ]
                }
            ]
        }

        with patch.object(hass_sync, "query_v1", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = (True, chunk1)

            # Set service offline after first chunk
            original_write = hass_sync.write_line

            async def mock_write(*args):
                hass_sync._online = False
                await original_write(*args)

            hass_sync.write_line = mock_write

            count = await hass_sync.copy_records_v1({"base": "b", "auth": None}, "power", {}, None)

            # Should only process first chunk and then stop because self.online is False
            assert count == 2
            assert mock_query.call_count == 1

    @pytest.mark.asyncio
    async def test_sync_from_homeassistant_concurrency(self, hass_sync):
        """Test that sync_from_homeassistant respects max_sync_workers limit."""
        Config.influxdb.max_sync_workers = 2
        hass_sync.detect_homeassistant_db = AsyncMock(return_value=True)
        topic_cache = {
            "topic1": {"uom": "W", "object_id": "sensor1"},
            "topic2": {"uom": "V", "object_id": "sensor2"},
            "topic3": {"uom": "A", "object_id": "sensor3"},
        }

        # Track concurrent calls
        concurrent_calls = 0
        max_seen_concurrency = 0

        async def mock_get_earliest(*args):
            nonlocal concurrent_calls, max_seen_concurrency
            concurrent_calls += 1
            max_seen_concurrency = max(max_seen_concurrency, concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate some work
            concurrent_calls -= 1
            return 0

        hass_sync.get_earliest_timestamp = AsyncMock(side_effect=mock_get_earliest)
        hass_sync.copy_records_from_homeassistant = AsyncMock(return_value=10)

        results = await hass_sync.sync_from_homeassistant(topic_cache)

        assert len(results) == 3
        assert max_seen_concurrency == 2  # Limited by max_sync_workers
        assert hass_sync.copy_records_from_homeassistant.call_count == 3
