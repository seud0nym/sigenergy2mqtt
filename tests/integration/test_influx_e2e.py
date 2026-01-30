"""End-to-end tests for InfluxService sync_from_homeassistant workflow."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.influx_service import InfluxService


@pytest.fixture
def logger():
    return logging.getLogger("test_influx_e2e")


@pytest.fixture
def service(logger):
    """Create InfluxService with disabled init for isolated testing."""
    with patch.object(Config, "influxdb", None):
        svc = InfluxService(logger, plant_index=0)
    return svc


# =============================================================================
# sync_from_homeassistant() E2E tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_no_db_found(service, logger):
    """Test sync_from_homeassistant returns empty when no homeassistant DB found."""
    service.detect_homeassistant_db = AsyncMock(return_value=False)

    results = await service.sync_from_homeassistant()

    assert results == {}
    service.detect_homeassistant_db.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_empty_cache(service, logger):
    """Test sync_from_homeassistant with empty topic cache."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)
    service._topic_cache = {}

    results = await service.sync_from_homeassistant()

    assert results == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_full_workflow(service, logger):
    """Test complete sync_from_homeassistant workflow with mocked components."""
    # Setup mocks
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    # Populate topic cache with sample sensors
    service._topic_cache = {
        "sigenergy2mqtt/sensor/power/state": {"uom": "W", "object_id": "sensor.inverter_power", "unique_id": "uid1"},
        "sigenergy2mqtt/sensor/voltage/state": {"uom": "V", "object_id": "sensor.grid_voltage", "unique_id": "uid2"},
    }

    # Mock get_earliest_timestamp: first sensor has existing data, second doesn't
    async def mock_get_earliest_timestamp(measurement, tags):
        if tags.get("entity_id") == "sensor.inverter_power":
            return 1704067200  # Has existing data
        return None  # No existing data

    service.get_earliest_timestamp = AsyncMock(side_effect=mock_get_earliest_timestamp)

    # Mock copy_records_from_homeassistant
    async def mock_copy_records(measurement, tags, before_timestamp=None):
        if tags.get("entity_id") == "sensor.inverter_power":
            return 50  # Copied 50 older records
        return 100  # Copied 100 records (all)

    service.copy_records_from_homeassistant = AsyncMock(side_effect=mock_copy_records)

    # Run sync
    results = await service.sync_from_homeassistant()

    # Verify results
    assert len(results) == 2
    assert service.detect_homeassistant_db.called
    assert service.get_earliest_timestamp.call_count == 2
    assert service.copy_records_from_homeassistant.call_count == 2

    # Check values returned
    total = sum(results.values())
    assert total == 150  # 50 + 100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_deduplicates_combinations(service, logger):
    """Test sync_from_homeassistant deduplicates measurement/tag combinations."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    # Two topics with same entity_id and uom should only sync once
    service._topic_cache = {
        "topic1": {"uom": "W", "object_id": "sensor.power", "unique_id": "uid1"},
        "topic2": {"uom": "W", "object_id": "sensor.power", "unique_id": "uid2"},  # Same entity/uom
    }

    service.get_earliest_timestamp = AsyncMock(return_value=None)
    service.copy_records_from_homeassistant = AsyncMock(return_value=10)

    results = await service.sync_from_homeassistant()

    # Should only have one entry since measurement/tag combo is the same
    assert len(results) == 1
    assert service.copy_records_from_homeassistant.call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_handles_uom_with_slash(service, logger):
    """Test sync_from_homeassistant handles unit_of_measurement with slash (e.g., kWh/h)."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    # UoM with slash should be converted to underscore
    service._topic_cache = {
        "topic1": {"uom": "kWh/h", "object_id": "sensor.energy_rate", "unique_id": "uid1"},
    }

    captured_measurement = []

    async def mock_copy_records(measurement, tags, before_timestamp=None):
        captured_measurement.append(measurement)
        return 5

    service.get_earliest_timestamp = AsyncMock(return_value=None)
    service.copy_records_from_homeassistant = AsyncMock(side_effect=mock_copy_records)

    await service.sync_from_homeassistant()

    # Measurement should have slash replaced with underscore
    assert captured_measurement[0] == "kWh_h"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_with_existing_data_copies_older(service, logger):
    """Test sync_from_homeassistant only copies records older than earliest existing."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    service._topic_cache = {
        "topic1": {"uom": "W", "object_id": "sensor.power", "unique_id": "uid1"},
    }

    earliest_ts = 1704067200  # Existing data starts at this timestamp
    service.get_earliest_timestamp = AsyncMock(return_value=earliest_ts)

    captured_before = []

    async def mock_copy_records(measurement, tags, before_timestamp=None):
        captured_before.append(before_timestamp)
        return 25

    service.copy_records_from_homeassistant = AsyncMock(side_effect=mock_copy_records)

    await service.sync_from_homeassistant()

    # Should pass earliest timestamp as before_timestamp
    assert captured_before[0] == earliest_ts


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_no_existing_copies_all(service, logger):
    """Test sync_from_homeassistant copies all records when no existing data."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    service._topic_cache = {
        "topic1": {"uom": "W", "object_id": "sensor.power", "unique_id": "uid1"},
    }

    # No existing data
    service.get_earliest_timestamp = AsyncMock(return_value=None)

    captured_before = []

    async def mock_copy_records(measurement, tags, before_timestamp=None):
        captured_before.append(before_timestamp)
        return 100

    service.copy_records_from_homeassistant = AsyncMock(side_effect=mock_copy_records)

    await service.sync_from_homeassistant()

    # Should pass None as before_timestamp (copy all)
    assert captured_before[0] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sync_from_homeassistant_returns_result_key_format(service, logger):
    """Test sync_from_homeassistant returns results with correct key format."""
    service.detect_homeassistant_db = AsyncMock(return_value=True)

    service._topic_cache = {
        "topic1": {"uom": "kW", "object_id": "sensor.power_output", "unique_id": "uid1"},
    }

    service.get_earliest_timestamp = AsyncMock(return_value=None)
    service.copy_records_from_homeassistant = AsyncMock(return_value=42)

    results = await service.sync_from_homeassistant()

    # Key format should be: "{measurement}[{tag=value,...}]"
    expected_key = "kW[entity_id=sensor.power_output]"
    assert expected_key in results
    assert results[expected_key] == 42


# =============================================================================
# detect_homeassistant_db() integration tests
# =============================================================================


class FakeResponse:
    """Helper class for mocking HTTP responses."""

    def __init__(self, code, json_data=None, text=""):
        self.status_code = code
        self._json_data = json_data
        self.text = text

    def json(self):
        return self._json_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_detect_homeassistant_db_v2_found(service, monkeypatch):
    """Test detect_homeassistant_db finds bucket via v2 API."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = "mytoken"
    Config.influxdb.org = "myorg"
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    def fake_get(url, headers=None, timeout=None, params=None, auth=None):
        return FakeResponse(200, {"buckets": [{"name": "homeassistant"}, {"name": "other"}]})

    monkeypatch.setattr(service._session, "get", fake_get)

    result = await service.detect_homeassistant_db()
    assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_detect_homeassistant_db_v1_found(service, monkeypatch):
    """Test detect_homeassistant_db finds database via v1 API."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = None
    Config.influxdb.org = None
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    v1_result = {"results": [{"series": [{"values": [["homeassistant"], ["other"]]}]}]}

    def fake_get(url, params=None, auth=None, timeout=None, headers=None):
        return FakeResponse(200, v1_result)

    monkeypatch.setattr(service._session, "get", fake_get)

    result = await service.detect_homeassistant_db()
    assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_detect_homeassistant_db_not_found(service, monkeypatch):
    """Test detect_homeassistant_db returns False when not found."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = None
    Config.influxdb.org = None
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    v1_result = {"results": [{"series": [{"values": [["mydb"], ["other"]]}]}]}

    def fake_get(*args, **kwargs):
        return FakeResponse(200, v1_result)

    monkeypatch.setattr(service._session, "get", fake_get)

    result = await service.detect_homeassistant_db()
    assert result is False


# =============================================================================
# get_earliest_timestamp() integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_earliest_timestamp_v1_success(service, monkeypatch):
    """Test get_earliest_timestamp returns correct timestamp from v1 API."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = None
    Config.influxdb.org = None
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    v1_result = {"results": [{"series": [{"values": [["2024-01-01T12:00:00Z", 42]]}]}]}

    def fake_get(*args, **kwargs):
        return FakeResponse(200, v1_result)

    monkeypatch.setattr(service._session, "get", fake_get)

    result = await service.get_earliest_timestamp("power", {"entity_id": "sensor.power"})
    # 2024-01-01T12:00:00Z = 1704110400
    assert result == 1704110400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_earliest_timestamp_no_records(service, monkeypatch):
    """Test get_earliest_timestamp returns None when no records exist."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = None
    Config.influxdb.org = None
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    v1_result = {"results": [{}]}

    def fake_get(*args, **kwargs):
        return FakeResponse(200, v1_result)

    monkeypatch.setattr(service._session, "get", fake_get)

    result = await service.get_earliest_timestamp("power", {"entity_id": "sensor.power"})
    assert result is None


# =============================================================================
# copy_records_from_homeassistant() integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_copy_records_from_homeassistant_uses_v2_first(service, monkeypatch):
    """Test copy_records_from_homeassistant tries v2 API first when token present."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = "mytoken"
    Config.influxdb.org = "myorg"
    Config.influxdb.bucket = "mybucket"
    Config.influxdb.username = None
    Config.influxdb.password = None

    service._writer_type = "v2_http"
    service._write_url = "http://localhost:8086/api/v2/write"
    service._write_headers = {"Authorization": "Token mytoken"}

    csv_response = """#group,false
#datatype,string,long
,_result,0
_,_time,_field,_value
,,2024-01-01T12:00:00Z,value,42"""

    post_count = [0]

    def fake_post(url, headers=None, params=None, data=None, timeout=None, auth=None):
        post_count[0] += 1
        if "/api/v2/query" in url:
            return FakeResponse(200, text=csv_response)
        return FakeResponse(204)  # Write success

    monkeypatch.setattr(service._session, "post", fake_post)

    count = await service.copy_records_from_homeassistant("power", {"entity_id": "sensor.power"})
    # Should have at least attempted query
    assert post_count[0] >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_copy_records_from_homeassistant_falls_back_to_v1(service, monkeypatch):
    """Test copy_records_from_homeassistant falls back to v1 API."""
    Config.influxdb.host = "localhost"
    Config.influxdb.port = 8086
    Config.influxdb.database = "testdb"
    Config.influxdb.token = None
    Config.influxdb.org = None
    Config.influxdb.bucket = None
    Config.influxdb.username = None
    Config.influxdb.password = None

    service._writer_type = "v1_http"
    service._write_url = "http://localhost:8086/write"
    service._write_auth = None

    v1_result = {
        "results": [
            {
                "series": [
                    {
                        "name": "power",
                        "columns": ["time", "entity_id", "value"],
                        "values": [[1704110400, "sensor.power", 42]],
                    }
                ]
            }
        ]
    }

    get_count = [0]
    post_count = [0]

    def fake_get(*args, **kwargs):
        get_count[0] += 1
        return FakeResponse(200, v1_result)

    def fake_post(*args, **kwargs):
        post_count[0] += 1
        return FakeResponse(204)

    monkeypatch.setattr(service._session, "get", fake_get)
    monkeypatch.setattr(service._session, "post", fake_post)

    count = await service.copy_records_from_homeassistant("power", {"entity_id": "sensor.power"})
    assert count == 1
    assert get_count[0] == 1
    assert post_count[0] == 1
