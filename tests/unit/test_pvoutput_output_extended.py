"""Extended tests for sigenergy2mqtt/pvoutput/output.py"""

import asyncio
import logging
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests

from sigenergy2mqtt.config import Config, OutputField
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, Topic

# region Helper


def make_output_service():
    logger = logging.getLogger("test-pvoutput-output")
    return PVOutputOutputService(logger, {})


# endregion


# region _verify tests


@pytest.mark.asyncio
async def test_verify_http_error_handling(caplog):
    """Test HTTP error handling during verification."""
    svc = make_output_service()

    class ErrorResp:
        def __init__(self):
            self.headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(int(time.time() + 3600))}
            self.status_code = 404
            self.reason = "Not Found"
            self.text = ""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch("requests.get", return_value=ErrorResp()):
        # Should catch failure in status_code and log "Verification FAILED"
        result = await svc._verify({"d": "20250101", "t": "12:00"})

        assert result is False
        assert "Verification FAILED" in caplog.text


@pytest.mark.asyncio
async def test_verify_connection_error_handling(caplog):
    """Test connection error during verification."""
    svc = make_output_service()

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("ConnErr")):
        result = await svc._verify({"d": "20250101", "t": "12:00"})

        assert result is False
        assert "Error Connecting:" in caplog.text


@pytest.mark.asyncio
async def test_verify_timeout_handling(caplog):
    """Test timeout during verification."""
    svc = make_output_service()

    with patch("requests.get", side_effect=requests.exceptions.Timeout("TimedOut")):
        result = await svc._verify({"d": "20250101", "t": "12:00"})

        assert result is False
        assert "Timeout Error:" in caplog.text


@pytest.mark.asyncio
async def test_verify_invalid_response_format(caplog):
    """Test verify handles response that doesn't match expected CSV."""
    svc = make_output_service()

    # Enable a topic so verification mismatch can be detected
    st = ServiceTopics(svc, True, svc.logger, value_key=OutputField.PEAK_POWER)
    svc._service_topics[OutputField.PEAK_POWER] = st
    st.register(Topic("test", gain=1.0))

    class BadResp:
        status_code = 200
        text = "20250101,12:00,0,0,0,5000"  # Correct CSV but we want it to NOT match payload or trigger parsing error if we wanted
        # Wait, if it matches payload, result is True.
        # To fail, we make it NOT match.
        headers = {"X-Rate-Limit-Limit": "60", "X-Rate-Limit-Remaining": "59", "X-Rate-Limit-Reset": str(int(time.time() + 3600))}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch("requests.get", return_value=BadResp()):
        # payload has 10000, response has 5000 (at index 5 for pp)
        result = await svc._verify({"d": "20250101", "t": "12:00", OutputField.PEAK_POWER: 10000})

        assert result is False


# endregion


# region schedule tests


@pytest.mark.asyncio
async def test_schedule_day_change_resets_topics():
    """Test daily reset in schedule loop when day changes."""
    svc = make_output_service()
    svc.online = asyncio.Future()

    mock_topic = MagicMock(spec=ServiceTopics)
    mock_topic.reset = MagicMock()
    svc._service_topics[OutputField.GENERATION] = mock_topic

    t1_struct = time.struct_time((2025, 1, 1, 12, 0, 0, 0, 1, 0))
    t2_struct = time.struct_time((2025, 1, 2, 12, 0, 0, 0, 2, 0))

    with patch("time.localtime") as mock_time:
        iteration = 0

        def localtime_side_effect(s=None):
            if s is None:
                if iteration == 1:
                    return t1_struct
                else:
                    return t2_struct
            else:
                if s < 1700000100:
                    return t1_struct
                else:
                    return t2_struct

        mock_time.side_effect = localtime_side_effect

        async def sleep_side_effect(s):
            nonlocal iteration
            iteration += 1
            if iteration >= 2:
                svc.online = False
            return None

        with (
            patch.object(svc, "_next_output_upload", return_value=1700000000.0),
            patch("asyncio.sleep", side_effect=sleep_side_effect),
            patch.object(svc, "_create_payload", return_value={}),
            patch.object(svc, "_upload", return_value=None),
            patch("time.mktime", side_effect=[1700000000.0, 1700000200.0, 1700000000.0, 1700000200.0]),
        ):
            tasks = svc.schedule(MagicMock(), MagicMock())
            await tasks[0]

            mock_topic.reset.assert_called()


@pytest.mark.asyncio
async def test_schedule_peak_power_logging(caplog):
    """Test peak power logging during schedule."""
    caplog.set_level(logging.DEBUG)
    svc = make_output_service()
    svc.online = asyncio.Future()

    mock_gen = MagicMock(spec=ServiceTopics)
    mock_peak = MagicMock(spec=ServiceTopics)
    mock_peak.calculation = Calculation.PEAK

    mock_peak.__getitem__.return_value = MagicMock(state=5000)
    mock_peak.__contains__.return_value = True
    mock_peak.aggregate.return_value = (5000, "12:00", 1)

    svc._service_topics[OutputField.GENERATION] = mock_gen
    svc._service_topics[OutputField.PEAK_POWER] = mock_peak

    Config.pvoutput.testing = True
    mock_time_struct = time.struct_time((2025, 1, 1, 12, 0, 0, 0, 1, 0))

    async def sleep_side_effect(s):
        svc.online = False
        return None

    with (
        patch.object(svc, "_next_output_upload", return_value=1700000000.0),
        patch("asyncio.sleep", side_effect=sleep_side_effect),
        patch.object(svc, "_create_payload", return_value={}),
        patch.object(svc, "_upload", return_value=None),
        patch("time.mktime", return_value=1600000020.0),
        patch("time.localtime", return_value=mock_time_struct),
    ):
        tasks = svc.schedule(MagicMock(), MagicMock())
        await tasks[0]

        assert "Peak Power 5000W recorded" in caplog.text


# endregion


# region subscribe tests


def test_subscribe_registers_topics():
    """Test topic subscription registers topics with mqtt client."""
    svc = make_output_service()
    mock_client = MagicMock()
    mock_handler = MagicMock()

    mock_st = MagicMock(spec=ServiceTopics)
    svc._service_topics[OutputField.GENERATION] = mock_st

    svc.subscribe(mock_client, mock_handler)

    mock_st.subscribe.assert_called_with(mock_client, mock_handler)


# endregion
