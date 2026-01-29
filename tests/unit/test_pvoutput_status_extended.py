"""Extended tests for sigenergy2mqtt/pvoutput/status.py"""

import asyncio
import logging
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from sigenergy2mqtt.config import Config, StatusField
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, Topic
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService

# region Helper


def make_status_service():
    logger = logging.getLogger("test-pvoutput-status")
    return PVOutputStatusService(logger, {}, {})


# endregion


# region _create_payload tests


@pytest.mark.asyncio
async def test_create_payload_basic():
    """Test payload creation with some sample topics."""
    svc = make_status_service()
    now = time.localtime()

    # Enable some topics
    st_gen = ServiceTopics(svc, True, svc.logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM)
    svc._service_topics[StatusField.GENERATION_POWER] = st_gen
    t = Topic("gen", gain=1.0)
    st_gen.register(t)

    # Properly update state via handle_update to ensure it's included in aggregation
    await st_gen.handle_update(None, MagicMock(), 500.0, "gen", MagicMock())

    payload, snapshot = svc._create_payload(now)

    assert payload["d"] == time.strftime("%Y%m%d", now)
    assert payload["t"] == time.strftime("%H:%M", now)
    assert StatusField.GENERATION_POWER.value in payload
    assert payload[StatusField.GENERATION_POWER.value] == 500.0


def test_create_payload_requires_donation_skips_when_not_donator():
    """Test that donation-required topics are skipped for non-donators."""
    svc = make_status_service()
    now = time.localtime()

    # v7 requires donation
    st_v7 = ServiceTopics(svc, True, svc.logger, value_key=StatusField.V7, donation=True)
    svc._service_topics[StatusField.V7] = st_v7
    st_v7.register(Topic("v7", gain=1.0, state=100.0))
    # It seems ServiceTopics.requires_donation depends on 'donation' arg in __init__

    with patch("sigenergy2mqtt.pvoutput.service.Service._donator", False):
        payload, _ = svc._create_payload(now)
        assert StatusField.V7.value not in payload


# endregion


# region schedule tests


@pytest.mark.asyncio
async def test_schedule_loop_upload():
    """Test that schedule loop calls upload_payload."""
    svc = make_status_service()
    svc.online = asyncio.Future()

    # Mock payload with mandatory fields (v2)
    payload = {StatusField.GENERATION_POWER.value: 500}

    with (
        patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time()), (10, time.time() + 10)]),
        patch.object(svc, "_create_payload", return_value=(payload, {})),
        patch.object(svc, "upload_payload", return_value=True) as mock_upload,
    ):

        async def sleep_se(s):
            svc.online = False
            return None

        with patch("asyncio.sleep", side_effect=sleep_se):
            tasks = svc.schedule(None, None)
            await tasks[0]

        mock_upload.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_skips_upload_if_no_main_fields(caplog):
    """Test that upload is skipped if no v1-v4 fields are present."""
    svc = make_status_service()
    svc.online = asyncio.Future()

    # Mock payload with NO v1, v2, v3, v4
    payload = {StatusField.TEMPERATURE.value: 25}

    with patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]), patch.object(svc, "_create_payload", return_value=(payload, {})), patch.object(svc, "upload_payload") as mock_upload:

        async def sleep_se(s):
            svc.online = False
            return None

        with patch("asyncio.sleep", side_effect=sleep_se):
            tasks = svc.schedule(None, None)
            await tasks[0]

        mock_upload.assert_not_called()
        assert "skipping..." in caplog.text


@pytest.mark.asyncio
async def test_schedule_c1_logic():
    """Test c1 flag logic in schedule loop."""
    svc = make_status_service()

    async def run_c1_test(p_input):
        svc.online = asyncio.Future()
        mock_upload = MagicMock(return_value=True)
        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
            patch.object(svc, "_create_payload", return_value=(p_input.copy(), {})),
            patch.object(svc, "upload_payload", mock_upload),
            patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
        ):
            tasks = svc.schedule(None, None)
            await tasks[0]
            return mock_upload.call_args[0][1].get("c1")

    # Case 1: Gen + Con -> c1=1
    p1 = {StatusField.GENERATION_ENERGY.value: 100, StatusField.CONSUMPTION_ENERGY.value: 50}
    assert await run_c1_test(p1) == 1

    # Case 2: Gen only -> c1=2
    p2 = {StatusField.GENERATION_ENERGY.value: 100}
    assert await run_c1_test(p2) == 2

    # Case 3: Con only -> c1=3
    p3 = {StatusField.CONSUMPTION_ENERGY.value: 100}
    assert await run_c1_test(p3) == 3


@pytest.mark.asyncio
async def test_schedule_adjusts_negative_consumption(caplog):
    """Test that negative consumption power is adjusted to 0."""
    svc = make_status_service()
    svc.online = asyncio.Future()

    payload = {StatusField.GENERATION_POWER.value: 500, StatusField.CONSUMPTION_POWER.value: -100}

    # Mock consumption_enabled to True using PropertyMock on the configuration object
    with patch.object(type(Config.pvoutput), "consumption_enabled", new_callable=PropertyMock) as mock_ce:
        mock_ce.return_value = True

        with (
            patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
            patch.object(svc, "_create_payload", return_value=(payload, {})),
            patch.object(svc, "upload_payload", return_value=True) as mock_upload,
            patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
        ):
            tasks = svc.schedule(None, None)
            await tasks[0]

            sent_payload = mock_upload.call_args[0][1]
            assert sent_payload[StatusField.CONSUMPTION_POWER.value] == 0
            assert "Adjusted" in caplog.text


@pytest.mark.asyncio
async def test_schedule_failed_upload_restores_state():
    """Test that topic state is restored if upload fails."""
    svc = make_status_service()
    svc.online = asyncio.Future()

    topic = Topic("test", gain=1.0)
    topic.previous_state = 100.0
    topic.previous_timestamp = None

    st_dict = ServiceTopics(svc, True, svc.logger, value_key=StatusField.GENERATION_POWER)
    svc._service_topics[StatusField.GENERATION_POWER] = st_dict
    st_dict["test"] = topic

    snapshot = {StatusField.GENERATION_POWER: {"test": (100.0, None)}}
    payload = {StatusField.GENERATION_POWER.value: 500}

    with (
        patch.object(svc, "seconds_until_status_upload", side_effect=[(0, time.time())]),
        patch.object(svc, "_create_payload", return_value=(payload, snapshot)),
        patch.object(svc, "upload_payload", return_value=False),
        patch("asyncio.sleep", side_effect=lambda s: setattr(svc, "online", False)),
    ):
        # Simulate state update before "failed" upload restores it
        topic.previous_state = 200.0

        tasks = svc.schedule(None, None)
        await tasks[0]

        assert topic.previous_state == 100.0


# endregion


# region subscribe tests


def test_subscribe_registers_topics():
    """Test topic subscription registers topics with mqtt client."""
    svc = make_status_service()
    mock_client = MagicMock()
    mock_handler = MagicMock()

    mock_st = MagicMock(spec=ServiceTopics)
    svc._service_topics[StatusField.GENERATION_POWER] = mock_st

    svc.subscribe(mock_client, mock_handler)

    mock_st.subscribe.assert_called_with(mock_client, mock_handler)


# endregion
