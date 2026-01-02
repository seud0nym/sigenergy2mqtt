import pytest
from unittest.mock import MagicMock

import sys
import types

# Ensure a placeholder influxdb_client module exists for environments
try:
    import influxdb_client  # noqa: F401
except Exception:
    mod = types.ModuleType("influxdb_client")
    # provide minimal symbols used by the service
    mod.InfluxDBClient = None
    mod.Point = None
    mod.WriteOptions = None
    sys.modules["influxdb_client"] = mod

import sigenergy2mqtt.influxdb.service as service_module
from sigenergy2mqtt.influxdb.service import InfluxService
from sigenergy2mqtt.config import Config


@pytest.mark.integration
def test_init_prefers_official_client(monkeypatch):
    # Arrange: make a dummy InfluxDBClient that accepts writes
    class DummyWriteAPI:
        def write(self, bucket, org, record):
            return None

    class DummyClient:
        def __init__(self, url=None, token=None, org=None):
            pass

        def write_api(self, write_options=None):
            return DummyWriteAPI()

        def close(self):
            return None

    # Patch module-level client symbol so service will use the dummy client
    monkeypatch.setattr(service_module, "InfluxDBClient", DummyClient, raising=False)
    # Ensure WriteOptions exists for the service's constructor call
    monkeypatch.setattr(service_module, "WriteOptions", lambda *a, **k: None, raising=False)

    # Ensure HTTP is not contacted by making requests.Session.post fail if called
    def _bad_post(*args, **kwargs):
        raise AssertionError("HTTP should not be used when client is available")

    monkeypatch.setattr(service_module.requests.Session, "post", _bad_post, raising=False)

    # Ensure HTTP GET doesn't get called either
    def _bad_get(*args, **kwargs):
        raise AssertionError("HTTP should not be used when client is available")

    monkeypatch.setattr(service_module.requests.Session, "get", _bad_get, raising=False)

    # Arrange Config for the service
    prev_enabled = getattr(Config.influxdb, "enabled", False)
    prev_db = Config.influxdb.database
    prev_pwd = Config.influxdb.password
    try:
        Config.influxdb.enabled = True
        Config.influxdb.database = "test_db"
        Config.influxdb.password = "token"

        svc = InfluxService(MagicMock(), plant_index=0)
        assert svc._writer_type == "client"
        assert svc._writer_obj is not None
    finally:
        Config.influxdb.enabled = prev_enabled
        Config.influxdb.database = prev_db
        Config.influxdb.password = prev_pwd


@pytest.mark.integration
def test_init_falls_back_to_v2_http(monkeypatch):
    # Ensure client path is skipped by not providing a token/password

    # Mock v2 write endpoint to succeed
    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        if "/api/v2/write" in url:
            return FakeResponse(204)
        return FakeResponse(404)

    monkeypatch.setattr(service_module.requests.Session, "post", fake_post, raising=False)

    prev_enabled = getattr(Config.influxdb, "enabled", False)
    prev_db = Config.influxdb.database
    prev_pwd = Config.influxdb.password
    try:
        Config.influxdb.enabled = True
        Config.influxdb.database = "test_db"
        Config.influxdb.password = None

        svc = InfluxService(MagicMock(), plant_index=0)
        assert svc._writer_type == "v2_http"
        assert svc._write_url is not None
    finally:
        Config.influxdb.enabled = prev_enabled
        Config.influxdb.database = prev_db
        Config.influxdb.password = prev_pwd


@pytest.mark.integration
def test_write_line_uses_configured_writer(monkeypatch):
    # No client monkeypatch required; service init is skipped when disabled

    calls = {}

    class FakeResponse:
        def __init__(self, code):
            self.status_code = code

    def fake_post(self, url, headers=None, data=None, timeout=None, params=None, auth=None):
        calls["url"] = url
        calls["data"] = data
        return FakeResponse(204)

    monkeypatch.setattr(service_module.requests.Session, "post", fake_post, raising=False)

    svc = InfluxService(MagicMock(), plant_index=0)
    # Manually configure writer
    svc._writer_type = "v2_http"
    svc._write_url = "http://localhost:8086/api/v2/write?bucket=test_db&precision=s"
    svc._write_headers = {"Authorization": "Token tok"}

    svc._write_line("measurement,tag=1 value=42 1000000000")
    assert "url" in calls and "data" in calls
