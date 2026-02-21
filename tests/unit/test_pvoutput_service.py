import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from sigenergy2mqtt.config import ConsumptionSource, OutputField, StatusField, active_config
from sigenergy2mqtt.config.config import active_config
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.pvoutput.topic import Topic


def make_service() -> Service:
    logger = logging.getLogger("test-pvoutput-service")
    return Service("pvtest", "pvtest", "pvmodel", logger)


class TestPVOutputService:
    """Tests for the base Service class and general PVOutput service logic."""

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_fetches_system_info(self, monkeypatch):
        svc = make_service()
        # Reset class-level cache
        Service._interval = None
        Service._interval_updated = None
        Service._donator = False

        with patch.object(active_config.pvoutput, "testing", False):
            # Mock the response: interval=10 at index 15, donations=1 (donator=True)
            section0 = ",".join(["0"] * 15 + ["10"])
            response_text = f"{section0};unused;1"

            class DummyResp:
                text = response_text
                status_code = 200
                headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 60)}

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())

            seconds, next_time = await svc.seconds_until_status_upload()

            assert isinstance(seconds, float)
            assert Service._interval == 10
            assert Service._donator is True
            assert Service._interval_updated is not None

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_exception_uses_defaults(self, monkeypatch):
        svc = make_service()
        Service._interval = None
        Service._interval_updated = None
        Service._donator = None

        with patch.object(active_config.pvoutput, "testing", False):
            monkeypatch.setattr("requests.get", MagicMock(side_effect=requests.exceptions.ConnectionError("Network error")))
            seconds, next_time = await svc.seconds_until_status_upload()
            assert isinstance(seconds, float)
            assert Service._interval == 5
            assert Service._donator is False

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_uses_cache(self, monkeypatch):
        svc = make_service()
        Service._interval = 7
        Service._interval_updated = time.time()
        Service._donator = True

        with patch.object(active_config.pvoutput, "testing", False):
            mock_get = MagicMock(side_effect=Exception("Should not be called"))
            monkeypatch.setattr("requests.get", mock_get)
            seconds, next_time = await svc.seconds_until_status_upload()
            assert isinstance(seconds, float)
            assert not mock_get.called
            assert Service._interval == 7

    @pytest.mark.asyncio
    async def test_upload_payload_success_on_second_attempt(self, monkeypatch):
        svc = make_service()
        calls = {"count": 0}

        class Resp:
            def __init__(self, sc):
                self.status_code = sc
                self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 60)}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                if self.status_code >= 400:
                    err = requests.exceptions.HTTPError("Error")
                    err.response = self
                    raise err

        def fake_post(*a, **k):
            calls["count"] += 1
            return Resp(500 if calls["count"] == 1 else 200)

        with patch.object(active_config.pvoutput, "testing", False):
            monkeypatch.setattr(asyncio, "sleep", AsyncMock())
            monkeypatch.setattr("requests.post", fake_post)
            assert await svc.upload_payload("url", {"d": "20250101"}) is True
            assert calls["count"] == 2

    @pytest.mark.asyncio
    async def test_upload_payload_rate_limit_sleep(self, monkeypatch):
        svc = make_service()
        sleep_called = {"times": 0}

        async def track_sleep(duration):
            sleep_called["times"] += 1
            if sleep_called["times"] > 5:
                raise asyncio.CancelledError()

        class RespLowRate:
            status_code = 500
            headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "5", "X-Rate-Limit-Reset": str(time.time() + 30)}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                err = requests.exceptions.HTTPError("Error")
                err.response = self
                raise err

        with patch.object(active_config.pvoutput, "testing", False):
            monkeypatch.setattr(asyncio, "sleep", track_sleep)
            monkeypatch.setattr("requests.post", lambda *a, **k: RespLowRate())
            assert await svc.upload_payload("url", {"d": "20250101"}) is False
            assert sleep_called["times"] >= 1

    def test_publish_availability_is_noop(self):
        svc = make_service()
        svc.publish_availability(MagicMock(), "online")

    def test_publish_discovery_is_noop(self):
        svc = make_service()
        assert svc.publish_discovery(MagicMock()) is None

    def test_request_headers_contains_api_key(self):
        svc = make_service()
        with patch.object(active_config.pvoutput, "api_key", "test_api_key"), patch.object(active_config.pvoutput, "system_id", "12345"):
            headers = svc.request_headers
            assert headers["X-Pvoutput-Apikey"] == "test_api_key"
            assert headers["X-Pvoutput-SystemId"] == "12345"

    @pytest.mark.asyncio
    async def test_service_remaining_misses(self, caplog):
        """Targets missing lines in service.py."""
        caplog.set_level(logging.DEBUG)
        svc = Service("Test", "id", "model", logging.getLogger("test-service"))

        with patch.object(active_config.pvoutput, "api_key", "k"), patch.object(active_config.pvoutput, "system_id", "s"), patch("requests.get") as mock_get:
            resp = MagicMock()
            resp.status_code = 200
            resp.text = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,5;Don;1"
            resp.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 3600)}
            mock_get.return_value = resp

            Service._interval = 0
            Service._interval_updated = None
            await svc.seconds_until_status_upload()
            assert "Status Interval changed" in caplog.text

        Service._interval_updated = None
        with patch("requests.get") as mock_get2:
            resp2 = MagicMock()
            resp2.status_code = 200
            resp2.text = "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,5;Not;0"
            resp2.headers = resp.headers
            mock_get2.return_value = resp2

            Service._donator = True
            await svc.seconds_until_status_upload()
            assert Service._donator is False
            assert "Donation Status changed" in caplog.text


class TestPVOutputComponentIntegration:
    """Integration style tests for individual PVOutput services."""

    def test_pvoutput_output_service_payload(self):
        with patch.object(active_config.pvoutput, "exports", False), patch.object(active_config.pvoutput, "imports", False):
            svc = PVOutputOutputService(logging.getLogger("test"), {})
            st = svc._service_topics[OutputField.GENERATION]
            st.enabled = True
            t = Topic("gen", gain=1.0, state=5000.0, timestamp=time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S"))
            st.register(t)

            now = time.strptime("2023-10-27 12:05:00", "%Y-%m-%d %H:%M:%S")
            payload = svc._create_payload(now, interval=5)
            assert payload["d"] == "20231027"
            assert payload["g"] == 5000

    def test_pvoutput_status_service_payload(self):
        # Patch 'consumption' instead of read-only 'consumption_enabled'
        with patch.object(active_config.pvoutput, "consumption", ConsumptionSource.CONSUMPTION), patch.object(active_config.pvoutput, "temperature_topic", None):
            svc = PVOutputStatusService(logging.getLogger("test"), {}, {})
            st = svc._service_topics[StatusField.GENERATION_ENERGY]
            st.enabled = True
            t = Topic("gen_e", gain=1.0, state=12345.0, timestamp=time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S"))
            st.register(t)

            now = time.strptime("2023-10-27 12:00:00", "%Y-%m-%d %H:%M:%S")
            payload, _ = svc._create_payload(now)
            assert payload["d"] == "20231027"
            assert payload["t"] == "12:00"
            assert payload["v1"] == 12345
