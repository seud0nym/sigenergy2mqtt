"""Focused coverage for the writer boundary used by InfluxBase."""

from unittest.mock import MagicMock

import pytest
import requests

from sigenergy2mqtt.common import service_health_registry
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.base import InfluxBase
from sigenergy2mqtt.influxdb.writers import V1HttpWriter, V2HttpWriter
from tests.unit.influxdb.conftest import _bring_online

_online = _bring_online


@pytest.mark.parametrize("status", [200, 204])
def test_v1_writer_accepts_success_statuses_and_uses_runtime_timeout(monkeypatch, status):
    writer = V1HttpWriter("http://influx", "configured-db", ("user", "pass"), "test")
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=status)
    monkeypatch.setattr(active_config.influxdb, "write_timeout", 47.0)

    assert writer.write(session, b"measurement value=1") is True
    session.post.assert_called_once_with(
        "http://influx/write",
        params={"db": "configured-db", "precision": "s"},
        data=b"measurement value=1",
        auth=("user", "pass"),
        timeout=47.0,
    )


@pytest.mark.parametrize("status", [200, 204])
def test_v2_writer_accepts_success_statuses_and_uses_runtime_timeout(monkeypatch, status):
    writer = V2HttpWriter("http://influx", "bucket", "org", "token", "test")
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=status)
    monkeypatch.setattr(active_config.influxdb, "write_timeout", 48.0)

    assert writer.write(session, b"measurement value=1") is True
    session.post.assert_called_once_with(
        "http://influx/api/v2/write?bucket=bucket&precision=s&org=org",
        headers={"Authorization": "Token token"},
        data=b"measurement value=1",
        timeout=48.0,
    )


@pytest.mark.asyncio
async def test_execute_write_dispatches_selected_writer_and_handles_request_error():
    service = InfluxBase("influx", 0, "unique", "manufacturer", "model")
    _online(service)
    writer = MagicMock(writer_type="future_http")
    writer.write.side_effect = requests.RequestException("unreachable")
    service._writers["future_http"] = writer
    service._writer_type = "future_http"

    assert await service.execute_write(b"measurement value=1") is False
    writer.write.assert_called_once_with(service._session, b"measurement value=1")
    assert service_health_registry.get_health(service.service_health_key) is False


@pytest.mark.asyncio
async def test_copy_connection_shares_session_and_writer_without_probing():
    source = InfluxBase("source", 0, "source", "manufacturer", "model")
    target = InfluxBase("target", 0, "target", "manufacturer", "model")
    writer = MagicMock(writer_type="v3_http")
    writer.write.return_value = True
    source._writer_type = "v3_http"
    source._writers["v3_http"] = writer

    target.copy_connection_from(source)
    _online(target)

    assert target._session is source._session
    assert target._writers is not source._writers
    assert target._writers["v3_http"] is writer
    assert await target.execute_write(b"measurement value=1") is True
    writer.write.assert_called_once_with(source._session, b"measurement value=1")


@pytest.mark.parametrize("writer", [V1HttpWriter("http://influx", "db", None, "test"), V2HttpWriter("http://influx", "bucket", "org", "token", "test")])
def test_writer_raises_on_rejected_write(writer):
    from sigenergy2mqtt.influxdb.writers import InfluxWriteError

    session = MagicMock()
    session.post.return_value = MagicMock(status_code=503, text="service unavailable")
    with pytest.raises(InfluxWriteError) as excinfo:
        writer.write(session, b"measurement value=1")
    assert excinfo.value.status_code == 503
    assert "HTTP 503: service unavailable" in str(excinfo.value)


@pytest.mark.asyncio
async def test_execute_write_reports_outage_once_and_recovery(caplog):
    import logging

    from sigenergy2mqtt.influxdb.writers import InfluxWriteError

    first = InfluxBase("influx", 0, "unique0", "manufacturer", "model")
    second = InfluxBase("influx", 1, "unique1", "manufacturer", "model")
    writer = MagicMock(writer_type="future_http")
    for service in (first, second):
        _online(service)
        service._writers["future_http"] = writer
        service._writer_type = "future_http"
    assert first.outage is second.outage

    writer.write.side_effect = [
        requests.ConnectionError("read timed out"),
        requests.ConnectionError("read timed out"),
        InfluxWriteError(503, "unavailable", "http://influx/write"),
        True,
    ]
    with caplog.at_level(logging.DEBUG, logger="sigenergy2mqtt.influxdb.base"):
        assert await first.execute_write(b"m v=1") is False
        assert await second.execute_write(b"m v=1") is False
        assert await first.execute_write(b"m v=1") is False
        assert await second.execute_write(b"m v=1") is True

    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(errors) == 2
    assert "outage started: ConnectionError('read timed out')" in errors[0]
    assert "new error" in errors[1] and "HTTP 503" in errors[1]
    ended = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO and "outage ended" in r.getMessage()]
    assert len(ended) == 1 and "(1 similar messages suppressed)" in ended[0]
    assert service_health_registry.get_health(second.service_health_key) is True
