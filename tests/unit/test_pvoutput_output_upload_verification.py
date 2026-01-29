import asyncio
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.pvoutput.output import PVOutputOutputService


def make_output_service():
    logger = logging.getLogger("test-pvoutput-output-upload")
    return PVOutputOutputService(logger, {})


@pytest.mark.asyncio
async def test_upload_verifies_when_last_upload_of_day_is_true():
    """Test that _verify is called when last_upload_of_day is True."""
    svc = make_output_service()
    payload: dict[str, float | int | str] = {"d": "20250101", "pp": 100}

    # Mock is_payload_changed to return True so upload happens
    svc._is_payload_changed = MagicMock(return_value=True)

    with patch.object(svc, "upload_payload", return_value=True) as mock_upload, patch.object(svc, "_verify", return_value=True) as mock_verify:
        await svc._upload(payload, last_upload_of_day=True)

        mock_upload.assert_called()
        mock_verify.assert_called_with(payload, force=True)


@pytest.mark.asyncio
async def test_upload_does_not_verify_when_last_upload_of_day_is_false():
    """Test that _verify is NOT called when last_upload_of_day is False."""
    svc = make_output_service()
    payload: dict[str, float | int | str] = {"d": "20250101", "pp": 100}

    # Mock is_payload_changed to return True so upload happens
    svc._is_payload_changed = MagicMock(return_value=True)

    with patch.object(svc, "upload_payload", return_value=True) as mock_upload, patch.object(svc, "_verify", return_value=True) as mock_verify:
        await svc._upload(payload, last_upload_of_day=False)

        mock_upload.assert_called()
        mock_verify.assert_not_called()


@pytest.mark.asyncio
async def test_upload_force_verification_on_failure():
    """Test that if last_upload_of_day is True and verification fails, it retries and forces changed=True."""
    svc = make_output_service()
    payload: dict[str, float | int | str] = {"d": "20250101", "pp": 100}

    # Mock is_payload_changed to return True initially
    svc._is_payload_changed = MagicMock(return_value=True)

    # We want to simulate:
    # 1. Upload #1 (changed=True) -> Success
    # 2. Verify #1 -> Fail
    # 3. Upload #2 (changed=True forced) -> Success
    # 4. Verify #2 -> Success

    with patch.object(svc, "upload_payload", return_value=True) as mock_upload, patch.object(svc, "_verify", side_effect=[False, True]) as mock_verify:
        await svc._upload(payload, last_upload_of_day=True)

        assert mock_upload.call_count == 2
        assert mock_verify.call_count == 2


@pytest.mark.asyncio
async def test_schedule_calculates_last_upload_of_day():
    """Test that schedule logic correctly identifies the last upload of the day."""
    svc = make_output_service()
    svc.online = asyncio.Future()  # Create a future that we can cancel or set to break loop

    # Setup mocks to control the flow and break the loop
    # We want to run one iteration where `now >= next` is True

    # Helper to control the loop: run once then stop
    async def sleep_side_effect(s):
        svc.online = False  # Stop the loop
        return None

    # We need to mock time functions to simulate day crossing
    # Current time: Day 1, 23:55 (example)
    # Next upload time: Day 2, 00:05 (example) -> different day -> last_upload_of_day = True

    t1_struct = time.struct_time((2025, 1, 1, 23, 55, 0, 0, 1, 0))  # Current time
    t2_struct = time.struct_time((2025, 1, 2, 0, 5, 0, 0, 2, 0))  # Next day time

    t1_ts = 1735775700.0  # Day 1, 23:55
    t2_ts = 1735776300.0  # Day 2, 00:05

    def localtime_side_effect(ts=None):
        if ts is None or ts == t1_ts:
            return t1_struct
        elif ts == t2_ts:
            return t2_struct
        return t1_struct

    with (
        patch("time.localtime", side_effect=localtime_side_effect),
        patch("time.mktime", return_value=t1_ts),
        patch.object(svc, "_next_output_upload", side_effect=[1735772100.0, t2_ts]),  # First call for init (< now), second for tomorrow var
        patch.object(svc, "_create_payload", return_value={"d": "20250101"}),
        patch.object(svc, "_upload") as mock_upload,
        patch("asyncio.sleep", side_effect=sleep_side_effect),
        patch.object(svc, "lock") as mock_lock,  # Mock lock context manager
    ):
        # We need mock_lock to be an async context manager
        mock_lock.return_value.__aenter__.return_value = None
        mock_lock.return_value.__aexit__.return_value = None

        await svc.schedule(None, None)[0]

        # Check if _upload was called with last_upload_of_day=True
        mock_upload.assert_called_with({"d": "20250101"}, True)
