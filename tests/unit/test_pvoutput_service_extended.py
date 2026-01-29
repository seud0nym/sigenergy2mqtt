"""Extended tests for sigenergy2mqtt/pvoutput/service.py"""

import asyncio
import logging
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.pvoutput.service import Service


def make_service() -> Service:
    logger = logging.getLogger("test-pvoutput-service")
    return Service("pvtest", "pvtest", "pvmodel", logger)


# region lock tests


@pytest.mark.asyncio
async def test_lock_with_timeout_success():
    """Test lock acquisition with timeout completes successfully."""
    svc = make_service()
    async with svc.lock(timeout=5):
        # Lock acquired
        assert svc._lock.locked()
    # Lock released
    assert not svc._lock.locked()


@pytest.mark.asyncio
async def test_lock_without_timeout():
    """Test lock acquisition without timeout."""
    svc = make_service()
    async with svc.lock():
        assert svc._lock.locked()
    assert not svc._lock.locked()


@pytest.mark.asyncio
async def test_lock_timeout_error():
    """Test that lock timeout raises TimeoutError."""
    svc = make_service()

    # Acquire lock in background
    await svc._lock.acquire()

    # Try to acquire again with very short timeout
    with pytest.raises(asyncio.TimeoutError):
        async with svc.lock(timeout=0.01):
            pass

    # Release the first lock
    svc._lock.release()


# endregion


# region seconds_until_status_upload tests


@pytest.mark.asyncio
async def test_seconds_until_status_upload_fetches_system_info(monkeypatch):
    """Test that seconds_until_status_upload fetches interval from PVOutput API when cache is stale."""
    svc = make_service()

    # Clear cache
    Service._interval = None
    Service._interval_updated = None
    Service._donator = False

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        # Mock the response
        section0 = ",".join(["0"] * 15 + ["10"])  # interval=10 at index 15
        response_text = f"{section0};unused;1"  # donations=1

        class DummyResp:
            def __init__(self):
                self.text = response_text
                self.status_code = 200
                self.headers = {
                    "X-Rate-Limit-Limit": "60",
                    "X-Rate-Limit-Remaining": "59",
                    "X-Rate-Limit-Reset": str(time.time() + 60),
                }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_get(url, headers=None, timeout=None):
            return DummyResp()

        monkeypatch.setattr("requests.get", fake_get)

        seconds, next_time = await svc.seconds_until_status_upload()

        assert isinstance(seconds, float)
        assert Service._interval == 10
        assert Service._donator is True
        assert Service._interval_updated is not None

    finally:
        Config.pvoutput.testing = orig_testing
        # Reset to defaults
        Service._interval = 5
        Service._interval_updated = None
        Service._donator = False


@pytest.mark.asyncio
async def test_seconds_until_status_upload_exception_uses_defaults(monkeypatch):
    """Test that seconds_until_status_upload uses defaults when request fails."""
    svc = make_service()

    # Clear cache
    Service._interval = None
    Service._interval_updated = None
    Service._donator = None

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        def fake_get_error(url, headers=None, timeout=None):
            raise requests.exceptions.ConnectionError("Network error")

        monkeypatch.setattr("requests.get", fake_get_error)

        seconds, next_time = await svc.seconds_until_status_upload()

        assert isinstance(seconds, float)
        assert Service._interval == 5  # Default interval
        assert Service._donator is False  # Default donator

    finally:
        Config.pvoutput.testing = orig_testing
        Service._interval = 5
        Service._interval_updated = None
        Service._donator = False


@pytest.mark.asyncio
async def test_seconds_until_status_upload_uses_cache(monkeypatch):
    """Test that seconds_until_status_upload uses cached values when not stale."""
    svc = make_service()

    # Set cache as recent
    Service._interval = 7
    Service._interval_updated = time.time()
    Service._donator = True

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        # This should NOT be called since cache is fresh
        called = {"get": False}

        def fake_get(url, headers=None, timeout=None):
            called["get"] = True
            raise Exception("Should not be called")

        monkeypatch.setattr("requests.get", fake_get)

        seconds, next_time = await svc.seconds_until_status_upload()

        assert isinstance(seconds, float)
        assert called["get"] is False
        assert Service._interval == 7

    finally:
        Config.pvoutput.testing = orig_testing
        Service._interval = 5
        Service._interval_updated = None
        Service._donator = False


@pytest.mark.asyncio
async def test_seconds_until_status_upload_response_non_200(monkeypatch):
    """Test handling of non-200 response from PVOutput API."""
    svc = make_service()

    # Clear cache to force request
    Service._interval = 5
    Service._interval_updated = None
    Service._donator = False

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        class DummyResp:
            def __init__(self):
                self.status_code = 403
                self.reason = "Forbidden"
                self.headers = {
                    "X-Rate-Limit-Limit": "60",
                    "X-Rate-Limit-Remaining": "59",
                    "X-Rate-Limit-Reset": str(time.time() + 60),
                }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_get(url, headers=None, timeout=None):
            return DummyResp()

        monkeypatch.setattr("requests.get", fake_get)

        seconds, next_time = await svc.seconds_until_status_upload()

        # Should still return valid seconds
        assert isinstance(seconds, float)

    finally:
        Config.pvoutput.testing = orig_testing
        Service._interval = 5
        Service._interval_updated = None
        Service._donator = False


# endregion


# region upload_payload tests


@pytest.mark.asyncio
async def test_upload_payload_connection_error(monkeypatch):
    """Test that upload_payload handles ConnectionError."""
    svc = make_service()

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        sleep_count = {"count": 0}

        async def limited_sleep(*a, **k):
            sleep_count["count"] += 1
            if sleep_count["count"] > 5:
                # Prevent infinite loop
                raise asyncio.CancelledError("Test stopping retry loop")
            return None

        monkeypatch.setattr(asyncio, "sleep", limited_sleep)

        def fake_post_error(url, headers=None, data=None, timeout=None):
            raise requests.exceptions.ConnectionError("Connection refused")

        monkeypatch.setattr("requests.post", fake_post_error)

        uploaded = await svc.upload_payload("https://pvoutput.org/test", {"d": "20250101"})
        assert uploaded is False

    finally:
        Config.pvoutput.testing = orig_testing


@pytest.mark.asyncio
async def test_upload_payload_timeout_error(monkeypatch):
    """Test that upload_payload handles Timeout."""
    svc = make_service()

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        sleep_count = {"count": 0}

        async def limited_sleep(*a, **k):
            sleep_count["count"] += 1
            if sleep_count["count"] > 5:
                raise asyncio.CancelledError("Test stopping retry loop")
            return None

        monkeypatch.setattr(asyncio, "sleep", limited_sleep)

        def fake_post_timeout(url, headers=None, data=None, timeout=None):
            raise requests.exceptions.Timeout("Request timed out")

        monkeypatch.setattr("requests.post", fake_post_timeout)

        uploaded = await svc.upload_payload("https://pvoutput.org/test", {"d": "20250101"})
        assert uploaded is False

    finally:
        Config.pvoutput.testing = orig_testing


@pytest.mark.asyncio
async def test_upload_payload_rate_limit_sleep(monkeypatch):
    """Test that upload_payload sleeps when rate limit is low."""
    svc = make_service()

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        sleep_called = {"times": 0, "durations": []}

        async def track_sleep(duration):
            sleep_called["times"] += 1
            sleep_called["durations"].append(duration)
            if sleep_called["times"] > 5:
                raise asyncio.CancelledError("Test stopping retry loop")
            return None

        monkeypatch.setattr(asyncio, "sleep", track_sleep)

        call_count = {"count": 0}

        class RespLowRate:
            def __init__(self):
                self.status_code = 500
                self.reason = "Server Error"
                self.text = "Error"
                self.headers = {
                    "X-Rate-Limit-Limit": "60",
                    "X-Rate-Limit-Remaining": "5",  # Low remaining
                    "X-Rate-Limit-Reset": str(time.time() + 30),
                }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                call_count["count"] += 1
                err = requests.exceptions.HTTPError("Error")
                err.response = self
                raise err

        def fake_post(url, headers=None, data=None, timeout=None):
            return RespLowRate()

        monkeypatch.setattr("requests.post", fake_post)

        uploaded = await svc.upload_payload("https://pvoutput.org/test", {"d": "20250101"})
        assert uploaded is False
        # Should have slept due to rate limiting at least once
        assert sleep_called["times"] >= 1

    finally:
        Config.pvoutput.testing = orig_testing


@pytest.mark.asyncio
async def test_upload_payload_generic_exception(monkeypatch):
    """Test that upload_payload handles generic Exception."""
    svc = make_service()

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        sleep_count = {"count": 0}

        async def limited_sleep(*a, **k):
            sleep_count["count"] += 1
            if sleep_count["count"] > 5:
                raise asyncio.CancelledError("Test stopping retry loop")
            return None

        monkeypatch.setattr(asyncio, "sleep", limited_sleep)

        def fake_post_error(url, headers=None, data=None, timeout=None):
            raise RuntimeError("Unknown error")

        monkeypatch.setattr("requests.post", fake_post_error)

        uploaded = await svc.upload_payload("https://pvoutput.org/test", {"d": "20250101"})
        assert uploaded is False

    finally:
        Config.pvoutput.testing = orig_testing


@pytest.mark.asyncio
async def test_upload_payload_success_on_second_attempt(monkeypatch):
    """Test that upload_payload retries and succeeds."""
    svc = make_service()

    orig_testing = Config.pvoutput.testing
    try:
        Config.pvoutput.testing = False

        async def no_sleep(*a, **k):
            return None

        monkeypatch.setattr(asyncio, "sleep", no_sleep)

        calls = {"count": 0}

        class SuccessResp:
            def __init__(self):
                self.status_code = 200
                self.headers = {
                    "X-Rate-Limit-Limit": "60",
                    "X-Rate-Limit-Remaining": "59",
                    "X-Rate-Limit-Reset": str(time.time() + 60),
                }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class ErrorResp:
            """Response for 500 error with proper headers for retry."""

            def __init__(self):
                self.status_code = 500
                self.reason = "Server Error"
                self.text = "Error"
                self.headers = {
                    "X-Rate-Limit-Limit": "60",
                    "X-Rate-Limit-Remaining": "59",
                    "X-Rate-Limit-Reset": str(time.time() + 60),
                }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                err = requests.exceptions.HTTPError("Error")
                err.response = self
                raise err

        def fake_post(url, headers=None, data=None, timeout=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return ErrorResp()  # First attempt fails
            return SuccessResp()  # Second attempt succeeds

        monkeypatch.setattr("requests.post", fake_post)

        uploaded = await svc.upload_payload("https://pvoutput.org/test", {"d": "20250101"})
        assert uploaded is True
        assert calls["count"] == 2

    finally:
        Config.pvoutput.testing = orig_testing


# endregion


# region publish_availability and publish_discovery (no-op) tests


def test_publish_availability_is_noop():
    """Test that publish_availability does nothing."""
    svc = make_service()
    mock_client = MagicMock()
    # Should not raise
    svc.publish_availability(mock_client, "online")


def test_publish_discovery_is_noop():
    """Test that publish_discovery does nothing."""
    svc = make_service()
    mock_client = MagicMock()
    result = svc.publish_discovery(mock_client)
    assert result is None


# endregion


# region request_headers tests


def test_request_headers_contains_api_key(monkeypatch):
    """Test that request_headers includes API key and system ID."""
    svc = make_service()

    with patch.object(Config.pvoutput, "api_key", "test_api_key"):
        with patch.object(Config.pvoutput, "system_id", "12345"):
            headers = svc.request_headers

            assert headers["X-Pvoutput-Apikey"] == "test_api_key"
            assert headers["X-Pvoutput-SystemId"] == "12345"
            assert headers["X-Rate-Limit"] == "1"


# endregion
