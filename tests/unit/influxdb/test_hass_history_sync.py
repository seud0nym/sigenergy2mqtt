import asyncio
import logging
from _asyncio import Future
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# copy_records_v2
# ---------------------------------------------------------------------------


async def test_copy_records_v2(influx: HassHistorySync):
    config = {"base": "http://example.com", "token": "abc123", "org": "my-org", "bucket": "my-bucket"}
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    influx.query_v2 = AsyncMock(return_value=(True, "_time,_value\n2023-01-01T00:00:00Z,42\n1"))

    with patch.object(influx, "write_line") as mock_write:
        await influx.copy_records_v2(config, measurement, tags, before_timestamp)

    mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# copy_records_v1
# ---------------------------------------------------------------------------


async def test_copy_records_v1(influx: HassHistorySync):
    config = {"base": "http://example.com", "auth": None}
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}
    before_timestamp = None

    influx.query_v1 = AsyncMock(return_value=(True, {"results": [{"series": [{"name": measurement, "columns": ["time", "value"], "values": [[1672531200, 42]]}]}]}))

    with patch.object(influx, "write_line") as mock_write:
        await influx.copy_records_v1(config, measurement, tags, before_timestamp)

    mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# copy_records_from_homeassistant
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# sync_from_homeassistant
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# get_earliest_timestamp
# ---------------------------------------------------------------------------


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


async def test_get_earliest_timestamp_exception(influx: HassHistorySync):
    """Lines 241-242: get_earliest_timestamp exception handler returns current time."""
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}

    with patch.object(influx, "get_config_values", side_effect=RuntimeError("boom")):
        with patch("time.time", return_value=999999):
            result = await influx.get_earliest_timestamp(measurement, tags)

    assert result == 999999


async def test_get_earliest_timestamp_v1_fallback(influx: HassHistorySync):
    """get_earliest_timestamp falls back to v1 when no token is configured."""
    measurement = "sensor"
    tags = {"entity_id": "sensor.test"}

    influx.query_v1 = AsyncMock(
        return_value=(True, {"results": [{"series": [{"columns": ["time", "value"], "values": [["2023-01-01T00:00:00Z", 42]]}]}]})
    )
    with patch.object(influx, "get_config_values") as mock_get_config:
        mock_get_config.return_value = {"base": "http://example.com", "token": None, "org": None, "bucket": "my-bucket", "db": "my-db", "auth": None}
        result = await influx.get_earliest_timestamp(measurement, tags)

    assert result == 1672531200


# ---------------------------------------------------------------------------
# detect_homeassistant_db — v2 path
# ---------------------------------------------------------------------------


async def test_detect_homeassistant_db_v2_exception(influx: HassHistorySync):
    """Lines 74-75: Exception in v2 bucket probe is caught and falls through to v1."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("bad json")

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    # All v1 probes should return 'not found'
    influx.query_v1 = AsyncMock(return_value=(False, None))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": "tok",
            "auth": None,
            "db": "",
            "org": "org",
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_detect_homeassistant_db_v2_found(influx: HassHistorySync):
    """v2 bucket list returns homeassistant bucket -> True."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"buckets": [{"name": "homeassistant"}]}

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": "tok",
            "auth": None,
            "db": "",
            "org": "org",
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is True


# ---------------------------------------------------------------------------
# detect_homeassistant_db — check_v1_databases paths
# ---------------------------------------------------------------------------


async def test_detect_homeassistant_db_v1_generic_non200(influx: HassHistorySync):
    """Lines 91-92, 94-96: generic SHOW DATABASES returns non-200 -> False."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "service unavailable"

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    # probe_homeassistant_v1 also fails
    influx.query_v1 = AsyncMock(return_value=(False, None))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_detect_homeassistant_db_v1_generic_missing_results_key(influx: HassHistorySync):
    """Lines 98-100: SHOW DATABASES payload has no 'results' key -> False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # no 'results' key

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    influx.query_v1 = AsyncMock(return_value=(False, None))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_detect_homeassistant_db_v1_generic_empty_results(influx: HassHistorySync):
    """Lines 98-100: SHOW DATABASES payload has empty 'results' list -> False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    influx.query_v1 = AsyncMock(return_value=(False, None))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_detect_homeassistant_db_v1_via_db_name(influx: HassHistorySync):
    """Lines 167-168: check_v1_databases(config["db"]) path hit when generic probe fails."""
    # Generic probe returns 200 but homeassistant not in the list
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"series": [{"values": [["_internal"]]}]}]}

    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    # First call (check_v1_databases(config["db"])) finds homeassistant
    influx.query_v1 = AsyncMock(
        return_value=(True, {"results": [{"series": [{"values": [["homeassistant", "_internal"]]}]}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is True


# ---------------------------------------------------------------------------
# detect_homeassistant_db — probe_homeassistant_v1 paths
# ---------------------------------------------------------------------------


async def _make_influx_with_v1_session_and_probe(influx, query_v1_return):
    """Configure influx so generic session probe returns no homeassistant,
    then first query_v1 call (check_v1_databases) also finds nothing,
    and second call (probe_homeassistant_v1) returns query_v1_return."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"series": [{"values": [["_internal"]]}]}]}
    influx._session = MagicMock()
    influx._session.get.return_value = mock_response

    influx.query_v1 = AsyncMock(
        side_effect=[
            (True, {"results": [{"series": [{"values": [["_internal"]]}]}]}),
            query_v1_return,
        ]
    )


async def test_probe_homeassistant_v1_query_failed(influx: HassHistorySync):
    """Lines 124-126: probe_homeassistant_v1 query returns success=False -> False."""
    await _make_influx_with_v1_session_and_probe(influx, (False, None))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_result_not_dict(influx: HassHistorySync):
    """Lines 124-126: probe_homeassistant_v1 result is not a dict -> False."""
    await _make_influx_with_v1_session_and_probe(influx, (True, "unexpected string"))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_missing_results_list(influx: HassHistorySync):
    """Lines 128-130: probe_homeassistant_v1 results is not a list -> False."""
    await _make_influx_with_v1_session_and_probe(influx, (True, {"results": None}))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_empty_results_list(influx: HassHistorySync):
    """Lines 128-130: probe_homeassistant_v1 results is empty list -> False."""
    await _make_influx_with_v1_session_and_probe(influx, (True, {"results": []}))

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_database_not_found_error(influx: HassHistorySync):
    """Lines 137-139: error contains 'database not found' -> False."""
    await _make_influx_with_v1_session_and_probe(
        influx, (True, {"results": [{"error": "database not found: homeassistant"}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_other_error_db_reachable(influx: HassHistorySync):
    """Lines 137-140: error does NOT contain 'database not found' -> DB reachable -> True."""
    await _make_influx_with_v1_session_and_probe(
        influx, (True, {"results": [{"error": "permission denied", "statement_id": 0}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is True


async def test_probe_homeassistant_v1_series_empty(influx: HassHistorySync):
    """Lines 147-149: first_result has 'series' key but series list is empty -> False."""
    await _make_influx_with_v1_session_and_probe(
        influx, (True, {"results": [{"series": []}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_series_name_mismatch(influx: HassHistorySync):
    """Lines 152-154: series name is not 'measurements' -> False."""
    await _make_influx_with_v1_session_and_probe(
        influx,
        (True, {"results": [{"series": [{"name": "other_series", "values": [["m1"]]}]}]}),
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_unrecognised_payload(influx: HassHistorySync):
    """Lines 157-159: first_result has no 'series', 'statement_id', or 'error' -> False."""
    await _make_influx_with_v1_session_and_probe(
        influx, (True, {"results": [{"unexpected_key": "value"}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is False


async def test_probe_homeassistant_v1_statement_id_present(influx: HassHistorySync):
    """Lines 155-156: first_result has 'statement_id' but no 'series' or 'error' -> True."""
    await _make_influx_with_v1_session_and_probe(
        influx, (True, {"results": [{"statement_id": 0}]})
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is True


async def test_probe_homeassistant_v1_measurements_series_found(influx: HassHistorySync):
    """probe_homeassistant_v1 with valid 'measurements' series name -> True."""
    await _make_influx_with_v1_session_and_probe(
        influx,
        (True, {"results": [{"series": [{"name": "measurements", "values": [["state"]]}]}]}),
    )

    with patch.object(influx, "get_config_values") as mock_cfg:
        mock_cfg.return_value = {
            "base": "http://example.com",
            "token": None,
            "auth": None,
            "db": "sigenergy",
            "org": None,
            "bucket": "bucket",
        }
        result = await influx.detect_homeassistant_db()

    assert result is True


async def test_detect_homeassistant_db_outer_exception(influx: HassHistorySync):
    """Lines 177-179: outer exception handler returns False."""
    with patch.object(influx, "get_config_values", side_effect=RuntimeError("fatal")):
        result = await influx.detect_homeassistant_db()

    assert result is False
