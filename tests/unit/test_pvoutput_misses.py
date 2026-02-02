"""Tests designed specifically to hit remaining coverage gaps in sigenergy2mqtt/pvoutput."""

import asyncio
import logging
import math
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from sigenergy2mqtt.config import Config, OutputField, StatusField, VoltageSource
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics, Topic
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService


@pytest.mark.asyncio
async def test_service_topics_remaining_misses(caplog):
    """Targets specific missing lines in service_topics.py."""
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("test-misses")
    svc = MagicMock()
    svc.lock.return_value.__aenter__.return_value = MagicMock()

    # Averaged debug log with datetime_key (91-93)
    st = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, decimals=2, calc=Calculation.AVERAGE, datetime_key="dt")
    Config.pvoutput.calc_debug_logging = True
    st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
    payload = {"dt": "something"}
    st.add_to_payload(payload, 5, time.localtime())
    assert "Averaged" in caplog.text

    # del payload if average fails (103)
    st2 = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.AVERAGE | Calculation.PEAK)
    payload2 = {"v2": 100.0}
    st2.add_to_payload(payload2, 5, time.localtime())
    assert "v2" not in payload2

    # L-L Averaged debug log with datetime_key (112-114)
    caplog.clear()
    st_ll = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.L_L_AVG, datetime_key="dt", decimals=1)
    st_ll.register(Topic("t_ll", state=200.0, timestamp=time.localtime()))
    payload_ll = {"dt": "prev"}
    st_ll.add_to_payload(payload_ll, 5, time.localtime())
    assert "L-L Averaged" in caplog.text

    # del payload if L-L fails (123-126)
    st_ll2 = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.L_L_AVG | Calculation.PEAK)
    payload_ll2 = {"v2": 100.0}
    st_ll2.add_to_payload(payload_ll2, 5, time.localtime())
    assert "v2" not in payload_ll2

    # del payload if sum fails (145)
    st_sum = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM | Calculation.PEAK)
    payload_sum = {"v2": 100.0}
    st_sum.add_to_payload(payload_sum, 5, time.localtime())
    assert "v2" not in payload_sum

    # Using state=... debug log (173)
    st_neg = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, negative=False)
    st_neg.register(Topic("t_neg", state=-10.0, timestamp=time.localtime()))
    st_neg.aggregate(False)
    assert "Using state=0.0" in caplog.text

    # Skipped converting ... warning if hours == 0 (191-192)
    st_diff = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
    t_diff = Topic("t_diff", state=10.0, timestamp=time.localtime())
    t_diff.previous_state = 5.0
    t_diff.previous_timestamp = t_diff.timestamp
    st_diff.register(t_diff)
    st_diff.aggregate(False)
    assert "Skipped converting" in caplog.text

    # obsolete.rename(...) migration (259)
    # Skipped due to complexity of mocking Path correctly across multiple calls

    # Subscribed to topic ... debug log (296-297)
    with patch.object(Config.pvoutput, "enabled", True):
        handler = MagicMock()
        st_sub = ServiceTopics(svc, True, logger, value_key=StatusField.GENERATION_POWER)
        st_sub.register(Topic("t_sub"))
        st_sub.subscribe(MagicMock(), handler)
        assert "Subscribed to topic t_sub" in caplog.text

    # await child.handle_update(...) in the else branch (334)
    tp = TimePeriodServiceTopics(svc, True, logger, value_key=OutputField.GENERATION)
    st_child = ServiceTopics(svc, True, logger, value_key=OutputField.GENERATION, periods=[tp])
    st_child.register(Topic("t_c"))
    with patch("sigenergy2mqtt.config.pvoutput_config.PVOutputConfiguration.current_time_period", new_callable=PropertyMock) as mock_cp:
        mock_cp.return_value = [OutputField.PEAK_POWER]
        await st_child.handle_update(None, MagicMock(), 10.0, "t_c", MagicMock())

    # handle_update return False if enabled=False (337)
    st_off = ServiceTopics(svc, False, logger, value_key=StatusField.GENERATION_POWER)
    res = await st_off.handle_update(None, MagicMock(), 10.0, "t_off", MagicMock())
    assert res is False


@pytest.mark.asyncio
async def test_output_remaining_misses(caplog):
    """Targets missing lines in output.py."""
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("test-output")
    svc = PVOutputOutputService(logger, {})

    payload = {"d": "20250101", "g": 100}
    with patch.object(svc, "upload_payload", AsyncMock(side_effect=[True, True])), patch.object(svc, "_verify", AsyncMock(side_effect=[False, True])):
        await svc._upload(payload, last_upload_of_day=False)
        assert "Upload completed" in caplog.text

    with patch.object(Config.pvoutput, "output_hour", -1):
        svc._previous_payload = None
        with patch.object(svc, "upload_payload", AsyncMock(return_value=True)), patch.object(svc, "_verify", AsyncMock(return_value=True)):
            await svc._upload(payload, last_upload_of_day=False)
            assert svc._previous_payload == payload


@pytest.mark.asyncio
async def test_service_remaining_misses(caplog):
    """Targets missing lines in service.py."""
    caplog.set_level(logging.DEBUG)
    svc = Service("Test", "id", "model", logging.getLogger("test-service"))

    with patch("sigenergy2mqtt.pvoutput.service.Config.pvoutput.api_key", "k"), patch("sigenergy2mqtt.pvoutput.service.Config.pvoutput.system_id", "s"), patch("requests.get") as mock_get:
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
        assert "Donation Status changed from True to False" in caplog.text
