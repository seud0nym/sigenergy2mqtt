import asyncio
import logging
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from sigenergy2mqtt.config import OutputField, active_config
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, Topic


def make_output_service():
    logger = logging.getLogger("test-pvoutput-output")
    return PVOutputOutputService(logger, {})


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(time.time() + 60)}
        self.reason = "OK"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestPVOutputOutput:
    """Tests for PVOutputOutputService."""

    def test_create_payload_and_change_detection(self):
        svc = make_output_service()
        # fixed struct for date
        now_struct = time.localtime(1700000000)
        payload = svc._create_payload(now_struct, 1440)
        assert "d" in payload
        # when previous payload equals current, _is_payload_changed should return False
        svc._previous_payload = dict(payload)
        assert svc._is_payload_changed(payload) is False
        # modified payload triggers change
        payload2 = dict(payload)
        payload2["g"] = 100
        assert svc._is_payload_changed(payload2) is True

    def test_create_payload_with_peak_power(self):
        svc = make_output_service()
        # ensure peak power topic is enabled by default
        topic = Topic(topic="peak", state=123.0, timestamp=time.localtime())
        svc._service_topics[OutputField.PEAK_POWER].register(topic)

        now_struct = time.localtime()
        payload = svc._create_payload(now_struct, 1440)
        assert payload.get("d") is not None
        # 'pp' is peak power value key
        assert payload.get("pp") == round(123.0)

    @pytest.mark.asyncio
    async def test_next_output_upload_uses_seconds_until_status(self, monkeypatch):
        svc = make_output_service()

        async def fake_seconds(rand_min=1, rand_max=1):
            return 5, 12345

        monkeypatch.setattr(svc, "seconds_until_status_upload", fake_seconds)
        with patch.object(active_config.pvoutput, "output_hour", -1):
            nxt = await svc._next_output_upload()
            assert isinstance(nxt, float)

    @pytest.mark.asyncio
    async def test_next_output_upload_testing_mode(self):
        with patch.object(active_config.pvoutput, "testing", True), patch.object(active_config.pvoutput, "output_hour", 3):
            svc = make_output_service()
            n = await svc._next_output_upload()
            # testing mode should schedule ~now + 60 seconds
            assert n - time.time() <= 65

    @pytest.mark.asyncio
    async def test_next_output_upload_rolls_over_to_tomorrow(self):
        svc = make_output_service()
        with patch.object(active_config.pvoutput, "testing", False):
            # set output_hour to an earlier hour to force next <= now
            now = time.localtime()
            past_hour = now.tm_hour - 1 if now.tm_hour > 0 else 0
            with patch.object(active_config.pvoutput, "output_hour", past_hour):
                nxt = await svc._next_output_upload(minute=0)
                assert nxt > time.time()
                # should be roughly at least 1 hour ahead (tomorrow)
                assert nxt - time.time() > 3500

    @pytest.mark.asyncio
    async def test_upload_sets_previous_payload_when_output_hour_minus1(self, monkeypatch):
        svc = make_output_service()
        payload = {"d": "20250101", "pp": 50}
        svc._previous_payload = None

        async def fake_upload(url, pl):
            return True

        async def fake_verify(pl, force=False):
            return True

        monkeypatch.setattr(svc, "upload_payload", fake_upload)
        monkeypatch.setattr(svc, "_verify", fake_verify)

        with patch.object(active_config.pvoutput, "output_hour", -1):
            await svc._upload(payload, last_upload_of_day=False)
            assert svc._previous_payload == payload

    @pytest.mark.asyncio
    async def test_upload_skips_unchanged_and_verifies(self, monkeypatch):
        svc = make_output_service()
        payload = {"d": datetime.now(timezone.utc).strftime("%Y%m%d"), "g": 1}
        svc._previous_payload = dict(payload)

        called = {"upload": False, "verify": False}

        async def fake_upload(url, pl):
            called["upload"] = True
            return True

        async def fake_verify(pl, force=False):
            called["verify"] = True
            return True

        monkeypatch.setattr(svc, "upload_payload", fake_upload)
        monkeypatch.setattr(svc, "_verify", fake_verify)

        await svc._upload(payload, last_upload_of_day=True)
        assert called["upload"] is False
        assert called["verify"] is True

    @pytest.mark.asyncio
    async def test_upload_verifies_when_last_upload_of_day_is_true(self):
        svc = make_output_service()
        payload = {"d": "20250101", "pp": 100}
        svc._is_payload_changed = MagicMock(return_value=True)

        with patch.object(svc, "upload_payload", return_value=True) as mock_upload, patch.object(svc, "_verify", return_value=True) as mock_verify:
            await svc._upload(payload, last_upload_of_day=True)
            mock_upload.assert_called()
            mock_verify.assert_called_with(payload, force=True)

    @pytest.mark.asyncio
    async def test_upload_force_verification_on_failure(self):
        svc = make_output_service()
        payload = {"d": "20250101", "pp": 100}
        svc._is_payload_changed = MagicMock(return_value=True)

        with patch.object(svc, "upload_payload", return_value=True) as mock_upload, patch.object(svc, "_verify", side_effect=[False, True]) as mock_verify:
            await svc._upload(payload, last_upload_of_day=True)
            assert mock_upload.call_count == 2
            assert mock_verify.call_count == 2

    @pytest.mark.asyncio
    async def test_verify_in_testing_mode(self, monkeypatch):
        svc = make_output_service()
        payload = {"d": "20250101", "g": 10}

        with patch.object(active_config.pvoutput, "testing", True):
            monkeypatch.setattr(asyncio, "sleep", AsyncMock())
            # not forced -> verify_retries == 1 -> should return False
            assert await svc._verify(payload, force=False) is False
            # forced -> should return True
            assert await svc._verify(payload, force=True) is True

    @pytest.mark.asyncio
    async def test_verify_parses_remote_response(self, monkeypatch):
        svc = make_output_service()
        with patch.object(active_config.pvoutput, "testing", False), patch.object(active_config.pvoutput, "exports", True), patch.object(active_config.pvoutput, "imports", True):
            payload = {"d": "20250101", "pp": 10, "ep": 0}
            parts = ["NaN"] * 18
            parts[0], parts[5], parts[14] = "20250101", "10", "0"
            text = ",".join(parts)

            monkeypatch.setattr("requests.get", lambda *a, **k: DummyResponse(text))
            monkeypatch.setattr(asyncio, "sleep", AsyncMock())

            assert await svc._verify(payload, force=False) is True

    @pytest.mark.asyncio
    async def test_verify_http_error_handling(self, caplog):
        svc = make_output_service()

        class ErrorResp:
            headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(int(time.time() + 3600))}
            status_code, reason, text = 404, "Not Found", ""

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("requests.get", return_value=ErrorResp()):
            assert await svc._verify({"d": "20250101"}) is False
            assert "Verification FAILED" in caplog.text

    @pytest.mark.asyncio
    async def test_verify_connection_error_handling(self, caplog):
        svc = make_output_service()
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("ConnErr")):
            assert await svc._verify({"d": "20250101"}) is False
            assert "Error Connecting:" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_day_change_resets_topics(self):
        svc = make_output_service()
        svc.online = asyncio.Future()
        mock_topic = MagicMock(spec=ServiceTopics)
        svc._service_topics[OutputField.GENERATION] = mock_topic

        t1 = time.struct_time((2025, 1, 1, 12, 0, 0, 0, 1, 0))
        t2 = time.struct_time((2025, 1, 2, 12, 0, 0, 0, 2, 0))

        with patch("time.localtime") as mock_time:
            iteration = 0

            def localtime_se(s=None):
                if s == 1700000000.0:
                    return t1
                if s == 1700000100.0:
                    return t2
                return t1 if iteration < 2 else t2

            mock_time.side_effect = localtime_se

            async def sleep_se(s):
                nonlocal iteration
                iteration += 1
                if iteration >= 5:
                    svc.online = False

            with (
                # Return next that is > now so we don't tight loop
                patch.object(svc, "_next_output_upload", side_effect=[1700000100.0, 1700000200.0, 1700001000.0, 1700002000.0, 1700003000.0]),
                patch("asyncio.sleep", side_effect=sleep_se),
                patch.object(svc, "_create_payload", return_value={"d": "20250101"}),
                patch.object(svc, "_upload"),
                patch("time.mktime", side_effect=lambda st: 1700000000.0 if st.tm_yday == 1 else 1700000100.0),
            ):
                await svc.schedule(None, None)[0]
                mock_topic.reset.assert_called()

    @pytest.mark.asyncio
    async def test_schedule_peak_power_logging(self, caplog):
        caplog.set_level(logging.DEBUG)
        svc = make_output_service()
        svc.online = asyncio.Future()
        mock_peak = MagicMock(spec=ServiceTopics)
        mock_peak.calculation = Calculation.PEAK
        mock_peak.__getitem__.return_value = MagicMock(state=5000)
        mock_peak.__contains__.return_value = True
        mock_peak.aggregate.return_value = (5000, "12:00", 1)
        svc._service_topics[OutputField.PEAK_POWER] = mock_peak

        with patch.object(active_config.pvoutput, "testing", True):
            iteration = 0

            async def sleep_se(s):
                nonlocal iteration
                iteration += 1
                if iteration >= 2:
                    svc.online = False

            with (
                # next > now to enter the elif branch for logging
                patch.object(svc, "_next_output_upload", return_value=1700000100.0),
                patch("asyncio.sleep", side_effect=sleep_se),
                patch.object(svc, "_create_payload", return_value={}),
                patch.object(svc, "_upload"),
                patch("time.mktime", return_value=1600000020.0),
                patch("time.localtime", return_value=time.localtime(1600000020)),
            ):
                await svc.schedule(None, None)[0]
                assert "Peak Power 5000W recorded" in caplog.text

    def test_subscribe_registers_topics(self):
        svc = make_output_service()
        mock_client, mock_handler = MagicMock(), MagicMock()
        mock_st = MagicMock(spec=ServiceTopics)
        svc._service_topics[OutputField.GENERATION] = mock_st
        svc.subscribe(mock_client, mock_handler)
        mock_st.subscribe.assert_called_with(mock_client, mock_handler)

    @pytest.mark.asyncio
    async def test_output_remaining_misses(self, caplog):
        """Targets missing lines in output.py."""
        caplog.set_level(logging.DEBUG)
        svc = make_output_service()

        payload = {"d": "20250101", "g": 100}
        with patch.object(svc, "upload_payload", AsyncMock(side_effect=[True, True])), patch.object(svc, "_verify", AsyncMock(side_effect=[False, True])):
            await svc._upload(payload, last_upload_of_day=False)
            assert "Upload completed" in caplog.text

        with patch.object(active_config.pvoutput, "output_hour", -1):
            svc._previous_payload = None
            with patch.object(svc, "upload_payload", AsyncMock(return_value=True)), patch.object(svc, "_verify", AsyncMock(return_value=True)):
                await svc._upload(payload, last_upload_of_day=False)
                assert svc._previous_payload == payload
