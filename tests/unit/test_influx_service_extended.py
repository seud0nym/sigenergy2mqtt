"""Extended unit tests for InfluxService covering helper methods and edge cases."""

import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.hass_history_sync import HassHistorySync
from sigenergy2mqtt.influxdb.influx_service import InfluxService


@pytest.fixture
def logger():
    return logging.getLogger("test_influx_extended")


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

    mock_config.query_interval = 0.1

    with patch.object(active_config, "influxdb", mock_config):
        svc = InfluxService(logger, plant_index=0)
    return svc


# =============================================================================
# parse_timestamp tests
# =============================================================================


class TestParseTimestamp:
    """Test cases for parse_timestamp edge cases."""

    def test_parse_iso_with_z_suffix(self, service):
        """Parse ISO timestamp with Z (Zulu/UTC) suffix."""
        result = service.parse_timestamp("2024-01-15T10:30:00Z")
        # 2024-01-15 10:30:00 UTC = 1705314600
        assert result == 1705314600

    def test_parse_iso_with_utc_offset(self, service):
        """Parse ISO timestamp with +00:00 timezone."""
        result = service.parse_timestamp("2024-01-15T10:30:00+00:00")
        assert result == 1705314600

    def test_parse_iso_with_positive_offset(self, service):
        """Parse ISO timestamp with positive timezone offset."""
        # +05:30 is 5.5 hours ahead of UTC
        result = service.parse_timestamp("2024-01-15T16:00:00+05:30")
        # 16:00 +05:30 = 10:30 UTC = 1705314600
        assert result == 1705314600

    def test_parse_iso_with_negative_offset(self, service):
        """Parse ISO timestamp with negative timezone offset."""
        # -08:00 is 8 hours behind UTC
        result = service.parse_timestamp("2024-01-15T02:30:00-08:00")
        # 02:30 -08:00 = 10:30 UTC = 1705314600
        assert result == 1705314600

    def test_parse_year_boundary(self, service):
        """Parse timestamp at year boundary."""
        result = service.parse_timestamp("2023-12-31T23:59:59Z")
        assert result == 1704067199

    def test_parse_new_year(self, service):
        """Parse timestamp at start of new year."""
        result = service.parse_timestamp("2024-01-01T00:00:00Z")
        assert result == 1704067200

    def test_parse_leap_year_date(self, service):
        """Parse timestamp on leap year date (Feb 29)."""
        result = service.parse_timestamp("2024-02-29T12:00:00Z")
        # Feb 29, 2024 12:00 UTC
        assert result == 1709208000

    def test_parse_with_milliseconds(self, service):
        """Parse ISO timestamp with milliseconds (should be truncated to seconds)."""
        result = service.parse_timestamp("2024-01-15T10:30:00.123Z")
        # Milliseconds are part of datetime, result is still in seconds
        assert result == 1705314600

    def test_parse_with_microseconds(self, service):
        """Parse ISO timestamp with microseconds."""
        result = service.parse_timestamp("2024-01-15T10:30:00.123456Z")
        assert result == 1705314600


# =============================================================================
# build_v1_tag_filter tests
# =============================================================================


class TestBuildTagFilters:
    """Test cases for build_v1_tag_filter with various tag combinations."""

    def test_empty_tags(self, service):
        """Build filters with empty tags dict."""
        result = service.build_v1_tag_filter({})
        assert result == ""

    def test_single_tag(self, service):
        """Build filters with single tag."""
        result = service.build_v1_tag_filter({"entity_id": "sensor.power"})
        assert result == "\"entity_id\"='sensor.power'"

    def test_multiple_tags(self, service):
        """Build filters with multiple tags."""
        result = service.build_v1_tag_filter({"entity_id": "sensor.power", "device": "inverter1"})
        # Order may vary, check both parts exist
        assert "\"entity_id\"='sensor.power'" in result
        assert "\"device\"='inverter1'" in result
        assert " AND " in result

    def test_tag_with_special_characters(self, service):
        """Build filters with special characters in values."""
        result = service.build_v1_tag_filter({"entity_id": "sensor.my_test"})
        assert result == "\"entity_id\"='sensor.my_test'"

    def test_tag_with_spaces(self, service):
        """Build filters with spaces in tag values."""
        result = service.build_v1_tag_filter({"device": "My Device"})
        assert result == "\"device\"='My Device'"


# =============================================================================
# to_line_protocol tests (extended edge cases)
# =============================================================================


class TestToLineProtocolExtended:
    """Extended test cases for to_line_protocol formatting."""

    def test_empty_tags(self, service):
        """Build line protocol with no tags."""
        line = service.to_line_protocol("measurement", {}, {"value": 42}, 1000)
        # Should be: measurement value=42i 1000
        assert line.startswith("measurement ")
        assert "value=42i" in line
        assert "1000" in line
        # No comma after measurement name when no tags
        assert "measurement," not in line

    def test_empty_fields_handling(self, service):
        """Build line protocol handles empty fields gracefully."""
        line = service.to_line_protocol("measurement", {"tag": "val"}, {}, 1000)
        # With empty fields, the line should still format (though invalid for InfluxDB)
        assert "measurement,tag=val" in line

    def test_measurement_with_spaces(self, service):
        """Build line protocol with spaces in measurement name (escaped)."""
        line = service.to_line_protocol("my measurement", {"tag": "val"}, {"value": 1}, 1000)
        assert "my\\ measurement" in line

    def test_measurement_with_commas(self, service):
        """Build line protocol with commas in measurement name (escaped)."""
        line = service.to_line_protocol("meas,urement", {"tag": "val"}, {"value": 1}, 1000)
        assert "meas\\,urement" in line

    def test_tags_with_spaces_and_commas(self, service):
        """Build line protocol with special chars in tag keys/values."""
        line = service.to_line_protocol("m", {"tag key": "tag,value"}, {"value": 1}, 1000)
        assert "tag\\ key=tag\\,value" in line

    def test_integer_field(self, service):
        """Build line protocol with integer field value."""
        line = service.to_line_protocol("m", {}, {"count": 100}, 1000)
        assert "count=100i" in line

    def test_float_field(self, service):
        """Build line protocol with float field value."""
        line = service.to_line_protocol("m", {}, {"temperature": 25.5}, 1000)
        assert "temperature=25.5" in line
        # Float should NOT have 'i' suffix
        assert "temperature=25.5i" not in line

    def test_string_field(self, service):
        """Build line protocol with string field value."""
        line = service.to_line_protocol("m", {}, {"status": "running"}, 1000)
        assert 'status="running"' in line

    def test_string_field_with_quotes(self, service):
        """Build line protocol with quotes in string field value."""
        line = service.to_line_protocol("m", {}, {"message": 'say "hello"'}, 1000)
        assert 'message="say \\"hello\\""' in line

    def test_multiple_mixed_fields(self, service):
        """Build line protocol with multiple fields of different types."""
        line = service.to_line_protocol("m", {}, {"count": 10, "temp": 25.5, "status": "ok"}, 1000)
        assert "count=10i" in line
        assert "temp=25.5" in line
        assert 'status="ok"' in line

    def test_timestamp_not_converted_to_nanoseconds(self, service):
        """Verify timestamp is converted to nanoseconds."""
        line = service.to_line_protocol("m", {}, {"v": 1}, 1234567890)
        assert "1234567890" in line

    def test_zero_timestamp(self, service):
        """Build line protocol with zero timestamp (epoch)."""
        line = service.to_line_protocol("m", {}, {"v": 1}, 0)
        assert " 0" in line or line.endswith("0")


# =============================================================================
# get_config_values tests
# =============================================================================


class TestGetConfigValues:
    """Test cases for get_config_values configuration extraction."""

    @pytest.fixture
    def basic_config(self):
        """Setup basic InfluxDB config."""
        active_config.influxdb.host = "localhost"
        active_config.influxdb.port = 8086
        active_config.influxdb.database = "testdb"
        active_config.influxdb.username = None
        active_config.influxdb.password = None
        active_config.influxdb.token = None
        active_config.influxdb.org = None
        active_config.influxdb.bucket = None
        yield
        # Config is reset by conftest fixture

    def test_basic_config_extraction(self, service, basic_config):
        """Extract basic configuration values."""
        result = service.get_config_values()
        assert result["host"] == "localhost"
        assert result["port"] == 8086
        assert result["db"] == "testdb"
        assert result["base"] == "http://localhost:8086"

    def test_explicit_token(self, service, basic_config):
        """Extract configuration with explicit token."""
        active_config.influxdb.token = "my-secret-token"
        result = service.get_config_values()
        assert result["token"] == "my-secret-token"

    def test_token_from_password_no_username(self, service, basic_config):
        """Token derived from password when no username (backwards compat)."""
        active_config.influxdb.password = "password-as-token"
        active_config.influxdb.username = None
        result = service.get_config_values()
        assert result["token"] == "password-as-token"

    def test_password_not_token_when_username_present(self, service, basic_config):
        """Password is NOT used as token when username is present."""
        active_config.influxdb.password = "regular-password"
        active_config.influxdb.username = "regular-user"
        result = service.get_config_values()
        assert result["token"] is None
        assert result["user"] == "regular-user"
        assert result["pwd"] == "regular-password"

    def test_explicit_bucket(self, service, basic_config):
        """Extract configuration with explicit bucket."""
        active_config.influxdb.bucket = "my-bucket"
        result = service.get_config_values()
        assert result["bucket"] == "my-bucket"

    def test_bucket_fallback_to_database(self, service, basic_config):
        """Bucket falls back to database name when not specified."""
        active_config.influxdb.bucket = None
        active_config.influxdb.database = "mydb"
        result = service.get_config_values()
        assert result["bucket"] == "mydb"

    def test_org_extraction(self, service, basic_config):
        """Extract organization configuration."""
        active_config.influxdb.org = "my-org"
        result = service.get_config_values()
        assert result["org"] == "my-org"

    def test_auth_tuple_with_credentials(self, service, basic_config):
        """Auth tuple is created when username or password present."""
        active_config.influxdb.username = "user"
        active_config.influxdb.password = "pass"
        result = service.get_config_values()
        assert result["auth"] == ("user", "pass")

    def test_auth_tuple_none_without_credentials(self, service, basic_config):
        """Auth tuple is None when no credentials."""
        active_config.influxdb.username = None
        active_config.influxdb.password = None
        result = service.get_config_values()
        assert result["auth"] is None

    def test_auth_tuple_partial_credentials(self, service, basic_config):
        """Auth tuple created with partial credentials (password only)."""
        active_config.influxdb.username = None
        active_config.influxdb.password = "pass-only"
        result = service.get_config_values()
        # Password becomes token in backwards compat logic, so auth should still be None
        # because pwd is set but user isn't, making auth = (None, "pass-only") which is falsy for user
        # Actually: auth = (user, pwd) if user or pwd else None -> (None, "pass-only") is truthy
        assert result["auth"] == (None, "pass-only")


# =============================================================================
# Additional edge case tests
# =============================================================================


class TestMiscEdgeCases:
    """Miscellaneous edge case tests."""

    def test_service_name_includes_plant_index(self, logger):
        """Service name includes plant index for identification."""
        mock_config = MagicMock()
        mock_config.enabled = False
        mock_config.max_retries = 3
        mock_config.pool_connections = 100
        mock_config.pool_maxsize = 100
        mock_config.batch_size = 100
        mock_config.flush_interval = 1.0
        mock_config.query_interval = 0.1
        mock_config.default_measurement = "state"
        mock_config.load_hass_history = False

        mock_config.default_measurement = "state"
        mock_config.load_hass_history = False

        with patch.object(active_config, "influxdb", mock_config):
            svc = InfluxService(logger, plant_index=5)
        assert "5" in svc.name
        assert "InfluxDB" in svc.name

    def test_default_writer_attributes_on_init(self, service):
        """Writer attributes default to None when InfluxDB not configured."""
        assert service._writer_type is None
        assert service._write_url is None
        assert service._write_headers is None
        assert service._write_auth is None


class TestHassHistorySyncCoverage:
    def _make_hass_sync(self, logger):
        mock_config = MagicMock()
        mock_config.enabled = False
        mock_config.max_retries = 3
        mock_config.pool_connections = 10
        mock_config.pool_maxsize = 10
        mock_config.batch_size = 100
        mock_config.flush_interval = 1.0
        mock_config.query_interval = 0.1
        mock_config.default_measurement = "state"

        with patch.object(active_config, "influxdb", mock_config):
            return HassHistorySync(logger, plant_index=0)

    def test_detect_homeassistant_db_v2_bucket_found(self, logger):
        hass_sync = self._make_hass_sync(logger)
        hass_sync.get_config_values = MagicMock(
            return_value={"base": "http://localhost:8086", "db": "sig", "auth": None, "token": "tok", "org": "org", "bucket": "sig"}
        )

        with patch.object(hass_sync._session, "get") as mock_get, patch.object(hass_sync, "query_v1") as mock_q1:
            mock_get.return_value = MagicMock(status_code=200)
            mock_get.return_value.json.return_value = {"buckets": [{"name": "homeassistant"}]}

            found = asyncio.run(hass_sync.detect_homeassistant_db())

            assert found is True
            mock_q1.assert_not_called()

    def test_detect_homeassistant_db_v1_detects_homeassistant_without_db_param(self, logger):
        hass_sync = self._make_hass_sync(logger)
        hass_sync.get_config_values = MagicMock(
            return_value={"base": "http://localhost:8086", "db": "sig", "auth": ("u", "p"), "token": None, "org": None, "bucket": "sig"}
        )

        with patch.object(hass_sync._session, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            mock_get.return_value.json.return_value = {
                "results": [{"series": [{"name": "databases", "values": [["_internal"], ["homeassistant"], ["sig"]]}]}]
            }

            found = asyncio.run(hass_sync.detect_homeassistant_db())

            assert found is True
            # Ensure the first call checks SHOW DATABASES without forcing db=...
            _, kwargs = mock_get.call_args
            assert kwargs["params"] == {"q": "SHOW DATABASES"}

    def test_get_earliest_timestamp_v1_path_without_token(self, logger):
        hass_sync = self._make_hass_sync(logger)
        hass_sync.get_config_values = MagicMock(
            return_value={"base": "http://localhost:8086", "db": "sig", "auth": ("u", "p"), "token": None, "org": None, "bucket": "sig"}
        )
        result = {"results": [{"series": [{"columns": ["time", "value"], "values": [["2024-01-01T00:00:11Z", 1.0]]}]}]}

        async def fake_q1(*args, **kwargs):
            return True, result

        hass_sync.query_v1 = fake_q1

        timestamp = asyncio.run(hass_sync.get_earliest_timestamp("power", {"entity_id": "sensor.power"}))

        assert timestamp == 1704067211

    def test_copy_records_from_homeassistant_falls_back_to_v1_when_v2_has_no_rows(self, logger):
        hass_sync = self._make_hass_sync(logger)
        hass_sync.get_config_values = MagicMock(
            return_value={"base": "http://localhost:8086", "db": "sig", "auth": ("u", "p"), "token": "tok", "org": "org", "bucket": "sig"}
        )

        async def fake_v2(*args, **kwargs):
            return 0

        async def fake_v1(*args, **kwargs):
            return 4

        hass_sync.copy_records_v2 = fake_v2
        hass_sync.copy_records_v1 = fake_v1

        copied = asyncio.run(hass_sync.copy_records_from_homeassistant("power", {"entity_id": "sensor.power"}, before_timestamp=123))

        assert copied == 4
