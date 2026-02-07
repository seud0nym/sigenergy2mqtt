from unittest.mock import MagicMock

import pytest
import requests

import sigenergy2mqtt.influxdb.influx_base as base_module
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.influxdb.hass_history_sync import HassHistorySync
from sigenergy2mqtt.influxdb.influx_service import InfluxService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_init_prefers_v2_http_with_token(monkeypatch):
    # Tests that when a token is provided, we try v2 HTTP first

    # Mock requests.Session.post to capture calls
    calls = []

    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        calls.append(url)
        if "/api/v2/write" in url:
            return FakeResponse(204)
        return FakeResponse(404)

    monkeypatch.setattr(requests.Session, "post", fake_post)

    prev_enabled = getattr(Config.influxdb, "enabled", False)
    prev_db = Config.influxdb.database
    prev_pwd = Config.influxdb.password
    prev_tok = Config.influxdb.token

    try:
        Config.influxdb.enabled = True
        Config.influxdb.database = "test_db"
        Config.influxdb.token = "mytoken"

        svc = InfluxService(MagicMock(), plant_index=0)
        await svc.async_init()

        # It should have chosen v2_http
        assert svc._writer_type == "v2_http"
        # And the URL should look like v2
        assert "/api/v2/write" in svc._write_url

        # Verify call history - first call should have been to v2
        assert len(calls) > 0
        assert "/api/v2/write" in calls[0]

    finally:
        Config.influxdb.enabled = prev_enabled
        Config.influxdb.database = prev_db
        Config.influxdb.password = prev_pwd
        Config.influxdb.token = prev_tok


@pytest.mark.integration
@pytest.mark.asyncio
async def test_init_falls_back_to_v2_http_implicit(monkeypatch):
    # If no token but password is used (legacy), or no token at all but v2 endpoint works

    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        if "/api/v2/write" in url:
            return FakeResponse(204)
        return FakeResponse(404)

    monkeypatch.setattr(requests.Session, "post", fake_post)

    prev_enabled = getattr(Config.influxdb, "enabled", False)
    prev_db = Config.influxdb.database
    prev_pwd = Config.influxdb.password
    try:
        Config.influxdb.enabled = True
        Config.influxdb.database = "test_db"
        Config.influxdb.password = None

        svc = InfluxService(MagicMock(), plant_index=0)
        await svc.async_init()
        assert svc._writer_type == "v2_http"
        assert svc._write_url is not None
    finally:
        Config.influxdb.enabled = prev_enabled
        Config.influxdb.database = prev_db
        Config.influxdb.password = prev_pwd


@pytest.mark.integration
@pytest.mark.asyncio
async def testwrite_line_uses_configured_writer(monkeypatch):
    calls = {}

    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        calls["url"] = url
        calls["data"] = data
        return FakeResponse(204)

    monkeypatch.setattr(requests.Session, "post", fake_post)

    svc = InfluxService(MagicMock(), plant_index=0)
    # Manually configure writer
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write?bucket=test_db&precision=s"
    svc._write_headers = {"Authorization": "Token tok"}
    svc._online = True

    await svc.write_line("measurement,tag=1 value=42 1000000000")
    await svc.flush_buffer()
    assert "url" in calls and "data" in calls


# =============================================================================
# _try_v1_write() integration tests
# =============================================================================


class FakeResponse:
    """Helper class for mocking HTTP responses."""

    def __init__(self, code, json_data=None, text="", content=b""):
        self.status_code = code
        self._json_data = json_data
        self.text = text
        self.content = content

    def json(self):
        return self._json_data


@pytest.mark.integration
def test_try_v1_write_success_first_attempt(monkeypatch):
    """Test _try_v1_write succeeds on first attempt."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    call_count = [0]

    def fake_post(self, url, params=None, data=None, auth=None, timeout=None, headers=None):
        call_count[0] += 1
        return FakeResponse(204)

    monkeypatch.setattr(svc._session, "post", lambda *args, **kwargs: fake_post(None, *args, **kwargs))

    result = svc._try_v1_write("http://localhost:8086", "testdb", ("user", "pass"), b"test value=1")
    assert result is True
    assert svc._writer_type == "v1_http"
    assert svc._write_url == "http://localhost:8086/write"
    assert call_count[0] == 1


@pytest.mark.integration
def test_try_v1_write_creates_database_on_404(monkeypatch):
    """Test _try_v1_write creates database after 404 error."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    call_count = [0]

    def fake_post(self, url, params=None, data=None, auth=None, timeout=None, headers=None):
        call_count[0] += 1
        if call_count[0] == 1:
            return FakeResponse(404, content=b"database not found")
        elif call_count[0] == 2:
            # CREATE DATABASE query
            return FakeResponse(200)
        else:
            # Retry write
            return FakeResponse(204)

    monkeypatch.setattr(svc._session, "post", lambda *args, **kwargs: fake_post(None, *args, **kwargs))

    result = svc._try_v1_write("http://localhost:8086", "testdb", None, b"test value=1")
    assert result is True
    assert svc._writer_type == "v1_http"
    assert call_count[0] == 3


@pytest.mark.integration
def test_try_v1_write_complete_failure(monkeypatch):
    """Test _try_v1_write returns False on complete failure."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    def fake_post(*args, **kwargs):
        raise Exception("Network error")

    monkeypatch.setattr(svc._session, "post", fake_post)

    result = svc._try_v1_write("http://localhost:8086", "testdb", None, b"test value=1")
    assert result is False
    assert svc._writer_type is None


# =============================================================================
# _try_v2_write() integration tests
# =============================================================================


@pytest.mark.integration
def test_try_v2_write_success_first_attempt(monkeypatch):
    """Test _try_v2_write succeeds on first attempt."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    call_count = [0]
    captured_url = [None]

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        call_count[0] += 1
        captured_url[0] = url
        return FakeResponse(204)

    monkeypatch.setattr(svc._session, "post", lambda *args, **kwargs: fake_post(None, *args, **kwargs))

    result = svc._try_v2_write("http://localhost:8086", "mybucket", "myorg", "mytoken", b"test value=1")
    assert result is True
    assert svc._writer_type == "v2_http"
    assert "mybucket" in svc._write_url
    assert "myorg" in svc._write_url
    assert call_count[0] == 1


@pytest.mark.integration
def test_try_v2_write_creates_bucket_on_404(monkeypatch):
    """Test _try_v2_write creates bucket after 404 error."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    call_count = [0]

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        call_count[0] += 1
        if call_count[0] == 1:
            return FakeResponse(404)
        elif call_count[0] == 2:
            # Create bucket
            return FakeResponse(201)
        else:
            # Retry write
            return FakeResponse(204)

    def fake_get(url, headers=None, timeout=None, params=None, auth=None):
        return FakeResponse(200, {"orgs": [{"id": "org123"}]})

    monkeypatch.setattr(svc._session, "post", lambda *args, **kwargs: fake_post(None, *args, **kwargs))
    monkeypatch.setattr(svc._session, "get", fake_get)

    result = svc._try_v2_write("http://localhost:8086", "mybucket", "myorg", "mytoken", b"test value=1")
    assert result is True
    assert svc._writer_type == "v2_http"


@pytest.mark.integration
def test_try_v2_write_complete_failure(monkeypatch):
    """Test _try_v2_write returns False on complete failure."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)

    def fake_post(*args, **kwargs):
        raise Exception("Network error")

    monkeypatch.setattr(svc._session, "post", fake_post)

    result = svc._try_v2_write("http://localhost:8086", "mybucket", None, None, b"test value=1")
    assert result is False
    assert svc._writer_type is None


# =============================================================================
# query_v1() integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v1_success(monkeypatch):
    """Test query_v1 returns successful query result."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    expected_result = {"results": [{"series": [{"name": "meas", "columns": ["time", "value"], "values": [["2024-01-01T00:00:00Z", 42]]}]}]}

    def fake_get(url, params=None, auth=None, timeout=None, headers=None):
        return FakeResponse(200, expected_result)

    monkeypatch.setattr(svc._session, "get", fake_get)

    success, result = await svc.query_v1("http://localhost:8086", "testdb", None, "SELECT * FROM meas")
    assert success is True
    assert result == expected_result


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v1_with_epoch(monkeypatch):
    """Test query_v1 passes epoch parameter correctly."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    captured_params = [None]

    def fake_get(url, params=None, auth=None, timeout=None, headers=None):
        captured_params[0] = params
        return FakeResponse(200, {"results": []})

    monkeypatch.setattr(svc._session, "get", fake_get)

    await svc.query_v1("http://localhost:8086", "testdb", None, "SELECT * FROM meas", epoch="s")
    assert captured_params[0]["epoch"] == "s"


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v1_failure(monkeypatch):
    """Test query_v1 handles HTTP errors gracefully."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    def fake_get(*args, **kwargs):
        return FakeResponse(500)

    monkeypatch.setattr(svc._session, "get", fake_get)

    success, result = await svc.query_v1("http://localhost:8086", "testdb", None, "SELECT * FROM meas")
    assert success is False
    assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v1_exception(monkeypatch):
    """Test query_v1 handles exceptions gracefully."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    def fake_get(*args, **kwargs):
        raise Exception("Network error")

    monkeypatch.setattr(svc._session, "get", fake_get)

    success, result = await svc.query_v1("http://localhost:8086", "testdb", None, "SELECT * FROM meas")
    assert success is False
    assert result is None


# =============================================================================
# query_v2() integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v2_success(monkeypatch):
    """Test query_v2 returns successful Flux query result."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    csv_response = """#group,false,false,true,true,false,false,true,true
#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,dateTime:RFC3339,double,string,string
#default,_result,,,,,,,
,result,table,_start,_stop,_time,_value,_field,_measurement
,,0,2024-01-01T00:00:00Z,2024-01-02T00:00:00Z,2024-01-01T12:00:00Z,42.5,value,temperature"""

    def fake_post(url, headers=None, params=None, data=None, timeout=None, auth=None):
        return FakeResponse(200, text=csv_response)

    monkeypatch.setattr(svc._session, "post", fake_post)

    success, result = await svc.query_v2("http://localhost:8086", "myorg", "mytoken", 'from(bucket: "test")')
    assert success is True
    assert "42.5" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v2_with_org(monkeypatch):
    """Test query_v2 passes org parameter correctly."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    captured_params = [None]

    def fake_post(url, headers=None, params=None, data=None, timeout=None, auth=None):
        captured_params[0] = params
        return FakeResponse(200, text="ok")

    monkeypatch.setattr(svc._session, "post", fake_post)

    await svc.query_v2("http://localhost:8086", "myorg", "mytoken", 'from(bucket: "test")')
    assert captured_params[0]["org"] == "myorg"


@pytest.mark.integration
@pytest.mark.asyncio
async def testquery_v2_failure(monkeypatch):
    """Test query_v2 handles HTTP errors gracefully."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    def fake_post(*args, **kwargs):
        return FakeResponse(500)

    monkeypatch.setattr(svc._session, "post", fake_post)

    success, result = await svc.query_v2("http://localhost:8086", "myorg", "mytoken", "query")
    assert success is False
    assert result is None


# =============================================================================
# copy_records_v1() integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def testcopy_records_v1_success(monkeypatch):
    """Test copy_records_v1 copies records correctly."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    # Configure writer
    svc._writer_type = "v1_http"
    svc._write_url = "http://localhost:8086/write"
    Config.influxdb.database = "target_db"

    query_result = {
        "results": [
            {
                "series": [
                    {
                        "name": "power",
                        "columns": ["time", "entity_id", "value"],
                        "values": [
                            [1704067200, "sensor.power", 100],
                            [1704067260, "sensor.power", 200],
                        ],
                    }
                ]
            }
        ]
    }

    get_call_count = [0]
    post_call_count = [0]

    def fake_get(url, params=None, auth=None, timeout=None, headers=None):
        get_call_count[0] += 1
        return FakeResponse(200, query_result)

    def fake_post(url, headers=None, params=None, data=None, timeout=None, auth=None):
        post_call_count[0] += 1
        return FakeResponse(204)

    monkeypatch.setattr(svc._session, "get", fake_get)
    monkeypatch.setattr(svc._session, "post", fake_post)

    config = {"base": "http://localhost:8086", "db": "homeassistant", "auth": None}
    count = await svc.copy_records_v1(config, "power", {"entity_id": "sensor.power"}, before_timestamp=None)
    await svc.flush_buffer()

    assert count == 2
    assert get_call_count[0] == 1
    assert post_call_count[0] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def testcopy_records_v1_empty_result(monkeypatch):
    """Test copy_records_v1 handles empty result set."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    query_result = {"results": [{}]}

    def fake_get(*args, **kwargs):
        return FakeResponse(200, query_result)

    monkeypatch.setattr(svc._session, "get", fake_get)

    config = {"base": "http://localhost:8086", "db": "homeassistant", "auth": None}
    count = await svc.copy_records_v1(config, "power", {"entity_id": "sensor.power"}, before_timestamp=None)

    assert count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def testcopy_records_v1_with_before_timestamp(monkeypatch):
    """Test copy_records_v1 passes before_timestamp in query."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    captured_params = [None]

    def fake_get(url, params=None, auth=None, timeout=None, headers=None):
        captured_params[0] = params
        return FakeResponse(200, {"results": [{}]})

    monkeypatch.setattr(svc._session, "get", fake_get)

    config = {"base": "http://localhost:8086", "db": "homeassistant", "auth": None}
    await svc.copy_records_v1(config, "power", {"entity_id": "sensor.power"}, before_timestamp=1704067200)

    # Check that the query includes time filter
    assert "time < 1704067200s" in captured_params[0]["q"]


@pytest.mark.integration
@pytest.mark.asyncio
async def testcopy_records_v1_multiple_series(monkeypatch):
    """Test copy_records_v1 handles multiple series."""
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True

    svc._writer_type = "v1_http"
    svc._write_url = "http://localhost:8086/write"
    Config.influxdb.database = "target_db"

    query_result = {
        "results": [
            {
                "series": [
                    {
                        "name": "power",
                        "columns": ["time", "entity_id", "value"],
                        "values": [[1704067200, "sensor.power", 100]],
                    },
                    {
                        "name": "power",
                        "columns": ["time", "entity_id", "value"],
                        "values": [[1704067260, "sensor.power", 200]],
                    },
                ]
            }
        ]
    }

    post_count = [0]

    def fake_get(*args, **kwargs):
        return FakeResponse(200, query_result)

    def fake_post(*args, **kwargs):
        post_count[0] += 1
        return FakeResponse(204)

    monkeypatch.setattr(svc._session, "get", fake_get)
    monkeypatch.setattr(svc._session, "post", fake_post)

    config = {"base": "http://localhost:8086", "db": "homeassistant", "auth": None}
    count = await svc.copy_records_v1(config, "power", {"entity_id": "sensor.power"}, before_timestamp=None)

    assert count == 2


@pytest.mark.asyncio
async def testcopy_records_v1_field_standardization():
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True
    svc._writer_type = "v1_http"
    svc._write_url = "http://localhost:8086/write"
    svc._session = MagicMock()

    # Mock query result with mixed types and non-standard field names
    # columns: time, old_field_int, old_field_str
    query_result = {
        "results": [
            {
                "series": [
                    {
                        "name": "test_measurement",
                        "columns": ["time", "old_field_int", "old_field_str"],
                        "values": [
                            [1704067200, 42, "string_val"],  # int and string. 1704067200 is timestamp
                            [1704067260, 42.5, None],  # float and None
                        ],
                    }
                ]
            }
        ]
    }

    svc._session.get.return_value = FakeResponse(200, json_data=query_result)
    svc._session.post.return_value = FakeResponse(204)

    # Capture written lines
    written_lines = []

    async def fake_write(line):
        written_lines.append(line)

    svc.write_line = fake_write

    config = {"base": "http://localhost:8086", "db": "homeassistant", "auth": None}
    await svc.copy_records_v1(config, "test_measurement", {}, None)

    assert len(written_lines) == 2

    line1 = written_lines[0]
    # Expected: 42 -> 42.0 (float), field name "value"
    # "string_val" -> "value_str"
    print(f"Line 1: {line1}")
    assert "value=42.0" in line1
    assert 'value_str="string_val"' in line1

    line2 = written_lines[1]
    # Expected: 42.5 -> 42.5 (float), field name "value"
    print(f"Line 2: {line2}")
    assert "value=42.5" in line2
    assert "value_str" not in line2


@pytest.mark.asyncio
async def testcopy_records_v2_field_standardization():
    logger = MagicMock()
    svc = HassHistorySync(logger, plant_index=0)
    svc._online = True
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write"
    svc._session = MagicMock()

    # Mock CSV response for v2
    # Headers default indices: _time=5, _value=7, _field=6 (based on influx_service.py defaults if not in header)
    # But usually headers are parsed.
    # The Service parses headers from lines starting with underscore.

    csv_response = """
#group,false,false,true,true,false,false,true,true
#datatype,string,long,dateTime:RFC3339,dateTime:RFC3339,dateTime:RFC3339,double,string,string
#default,_result,,,,,,,
,result,table,_start,_stop,_time,_value,_field,_measurement
,,0,2024-01-01,2024-01-02,2024-01-01T00:00:00Z,42,state,test_meas
,,0,2024-01-01,2024-01-02,2024-01-01T00:01:00Z,stringval,state,test_meas
""".strip()

    svc._session.post.return_value = FakeResponse(200, text=csv_response)

    written_lines = []

    async def fake_write(line):
        written_lines.append(line)

    svc.write_line = fake_write

    config = {"base": "http://localhost:8086", "org": "org", "token": "tok", "bucket": "bkt"}
    await svc.copy_records_v2(config, "test_meas", {}, None)

    assert len(written_lines) == 2

    # Line 1: 42 -> float -> value=42.0
    print(f"V2 Line 1: {written_lines[0]}")
    assert "value=42.0" in written_lines[0]

    # Line 2: "stringval" -> str -> value_str="stringval"
    print(f"V2 Line 2: {written_lines[1]}")
    assert 'value_str="stringval"' in written_lines[1]
