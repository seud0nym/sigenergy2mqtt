import asyncio
import logging
from _asyncio import Future
from typing import Any, Generator
from unittest.mock import AsyncMock, patch

import pytest

from sigenergy2mqtt.influxdb import HassHistorySync


@pytest.fixture
def future() -> Generator[Future[Any], Any, None]:
    loop = asyncio.new_event_loop()
    try:
        fut = loop.create_future()
        yield fut
    finally:
        loop.close()


@pytest.fixture
def influx(future: Future[Any]) -> HassHistorySync:
    influx = HassHistorySync(logging.getLogger(__name__))
    influx.online = future
    return influx


async def test_copy_records_v2(influx: HassHistorySync):
    config = {"base": "http://example.com", "token": "abc123", "org": "my-org", "bucket": "my-bucket"}
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    influx.query_v2 = AsyncMock(return_value=(True, "_time,_value\n2023-01-01T00:00:00Z,42\n1"))

    with patch.object(influx, "write_line") as mock_write:
        await influx.copy_records_v2(config, measurement, tags, before_timestamp)

    mock_write.assert_called_once()


async def test_copy_records_v1(influx: HassHistorySync):
    config = {"base": "http://example.com", "auth": None}
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    influx.query_v1 = AsyncMock(return_value=(True, {"results": [{"series": [{"name": measurement, "columns": ["time", "value"], "values": [[1672531200, 42]]}]}]}))

    with patch.object(influx, "write_line") as mock_write:
        await influx.copy_records_v1(config, measurement, tags, before_timestamp)

    mock_write.assert_called_once()


async def test_copy_records_from_homeassistant(influx: HassHistorySync):
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    with patch.object(influx, "copy_records_v2") as mock_copy_v2:
        mock_copy_v2.return_value = 0
        with patch.object(influx, "copy_records_v1") as mock_copy_v1:
            mock_copy_v1.return_value = 5
            result = await influx.copy_records_from_homeassistant(measurement, tags, before_timestamp)

    assert result == 5


async def test_sync_from_homeassistant(influx: HassHistorySync):
    topic_cache = {"sensor.test": {"object_id": "sensor.test", "uom": "/"}}

    with patch.object(influx, "detect_homeassistant_db") as mock_detect:
        mock_detect.return_value = True
        with patch.object(influx, "get_earliest_timestamp") as mock_get_ts:
            mock_get_ts.return_value = 1633072800
            with patch.object(influx, "copy_records_from_homeassistant") as mock_copy:
                mock_copy.return_value = 5
                result = await influx.sync_from_homeassistant(topic_cache)

    assert result == {"_[entity_id=sensor.test]": 5}


async def test_get_earliest_timestamp(influx: HassHistorySync):
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}

    influx.query_v2 = AsyncMock(return_value=(True, "_0,_,1,_2,_3,_value,_time\n,,,,42,2023-01-01T00:00:00Z"))
    with patch.object(influx, "get_config_values") as mock_get_config:
        mock_get_config.return_value = {"base": "http://example.com", "token": "abc123", "org": "my-org", "bucket": "my-bucket", "db": "my-db"}
        result = await influx.get_earliest_timestamp(measurement, tags)
        assert result == 1672531200


async def test_get_earliest_timestamp_no_records(influx: HassHistorySync):
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}

    influx.query_v2 = AsyncMock(return_value=(True, "_0,_,1,_2,_3,_value,_time"))
    with patch.object(influx, "get_config_values") as mock_get_config:
        mock_get_config.return_value = {"base": "http://example.com", "token": "abc123", "org": "my-org", "bucket": "my-bucket", "db": "my-db"}
        with patch("time.time", return_value=123456789):
            result = await influx.get_earliest_timestamp(measurement, tags)
            assert result == 123456789


async def test_copy_records_from_homeassistant_no_token(influx: HassHistorySync):
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    with patch.object(influx, "copy_records_v2") as mock_copy_v2:
        mock_copy_v2.return_value = 0
        with patch.object(influx, "copy_records_v1") as mock_copy_v1:
            mock_copy_v1.side_effect = Exception("error")
            result = await influx.copy_records_from_homeassistant(measurement, tags, before_timestamp)

    assert result == 0


async def test_sync_from_homeassistant_no_sensors(influx: HassHistorySync):
    topic_cache = {}

    with patch.object(influx, "detect_homeassistant_db") as mock_detect:
        mock_detect.return_value = True
        result = await influx.sync_from_homeassistant(topic_cache)

    assert result == {}


async def test_sync_from_homeassistant_error_during_timestamp_query(influx: HassHistorySync):
    topic_cache = {"sensor.test": {"object_id": "sensor.test", "uom": "/"}}

    with patch.object(influx, "detect_homeassistant_db") as mock_detect:
        mock_detect.return_value = True
    with patch.object(influx, "get_earliest_timestamp") as mock_get_ts:
        mock_get_ts.side_effect = Exception("error")
        result = await influx.sync_from_homeassistant(topic_cache)

    assert result == {}


async def test_sync_from_homeassistant_error_during_record_copy(influx: HassHistorySync):
    topic_cache = {"sensor.test": {"object_id": "sensor.test", "uom": "/"}}

    with patch.object(influx, "detect_homeassistant_db") as mock_detect:
        mock_detect.return_value = True
    with patch.object(influx, "get_earliest_timestamp") as mock_get_ts:
        mock_get_ts.return_value = 1633072800
    with patch.object(influx, "copy_records_from_homeassistant") as mock_copy:
        mock_copy.side_effect = Exception("error")
        result = await influx.sync_from_homeassistant(topic_cache)

    assert result == {}
