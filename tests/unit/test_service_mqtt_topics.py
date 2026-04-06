import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config, OutputField, _swap_active_config, active_config
from sigenergy2mqtt.config.settings import PvOutputConfig
from sigenergy2mqtt.pvoutput.service_topics import Calculation as Calc
from sigenergy2mqtt.pvoutput.service_topics import ServiceTopics, TimePeriodServiceTopics
from sigenergy2mqtt.pvoutput.topic import Topic


def make_st(enabled=True, calc=Calc.SUM, value_key=OutputField.GENERATION, **kwargs):
    service = MagicMock()
    service.unique_id = MagicMock()
    service.unique_id.__str__.return_value = "<MagicMock"
    service.scan_interval.return_value = 300
    service.lock.return_value.__aenter__ = AsyncMock()
    service.lock.return_value.__aexit__ = AsyncMock()
    logger = logging.getLogger("sigenergy2mqtt.test")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    return ServiceTopics(service, enabled, logger, value_key=value_key, calc=calc, **kwargs)


def test_setters_and_assertions():
    st = make_st()
    st.calculation = Calc.AVERAGE
    assert st.calculation == Calc.AVERAGE
    with pytest.raises(AssertionError):
        st.calculation = "not"
    st.decimals = 2
    assert st.decimals == 2
    with pytest.raises(AssertionError):
        st.decimals = "not"
    st.enabled = False
    assert st.enabled is False
    with pytest.raises(AssertionError):
        st.enabled = "not"


def test_registration(caplog):
    caplog.set_level(logging.DEBUG)
    st = make_st()
    st.register(Topic(" "))
    assert "empty topic" in caplog.text
    caplog.clear()
    st.enabled = False
    st.register(Topic("t1"))
    assert "uploading is disabled" in caplog.text
    st.enabled = True
    st.register(Topic("t1"))
    assert "Registered" in caplog.text


def test_aggregate_adjustment_logging(caplog):
    caplog.set_level(logging.DEBUG)
    cfg_obj = Config()
    cfg_obj.pvoutput.calc_debug_logging = True
    with _swap_active_config(cfg_obj):
        st = make_st(negative=False)
        st.register(Topic("t1", state=-10.0, timestamp=time.localtime()))
        st.aggregate(exclude_zero=False)
        assert "Using state=0.0" in caplog.text


def test_aggregate_difference_logic(caplog):
    caplog.set_level(logging.DEBUG)
    now = time.time()
    cfg_obj = Config()
    cfg_obj.pvoutput.calc_debug_logging = True
    with _swap_active_config(cfg_obj):
        st = make_st(calc=Calc.DIFFERENCE | Calc.CONVERT_TO_WATTS)
        t = Topic("t1", state=100.0, timestamp=time.localtime(now))
        t.previous_state = 10.0
        t.previous_timestamp = time.localtime(now - 3600)
        st.register(t)
        st.aggregate(False)
        assert "Calculated difference" in caplog.text
        assert "Converted" in caplog.text

        # mismatch branch
        st.clear()
        t2 = Topic("t2", state=100.0, timestamp=time.localtime(now))
        t2.previous_state = 10.0
        t2.previous_timestamp = time.localtime(now - 100000)
        st.register(t2)
        assert st.aggregate(False)[2] == 0

        # skip conversion
        st.clear()
        t3 = Topic("t3", state=100.0, timestamp=time.localtime(now))
        t3.previous_state = 50.0
        t3.previous_timestamp = time.localtime(now)
        st.register(t3)
        caplog.clear()
        st.aggregate(False)
        assert "Skipped converting" in caplog.text


def test_check_is_updating_branches(caplog):
    caplog.set_level(logging.DEBUG)
    now = time.time()
    st = make_st()
    cfg_obj = Config()
    cfg_obj.pvoutput.update_debug_logging = True

    # started recently
    cfg_obj.pvoutput.started = now
    with _swap_active_config(cfg_obj):
        assert st.check_is_updating(5, time.localtime(now)) is True
        assert "just started" in caplog.text

        # started long ago
        active_config.pvoutput.started = 0
        caplog.clear()
        st.register(Topic("t1", timestamp=time.localtime(now)))
        st.check_is_updating(5, time.localtime(now))
        assert "last updated" in caplog.text

        # stale
        st.clear()
        st.register(Topic("t2", timestamp=time.localtime(now - 7200)))
        st._last_update_warning = None
        st.check_is_updating(5, time.localtime(now))
        assert "has not been updated" in caplog.text

        # never
        st.clear()
        st.register(Topic("t3", timestamp=None))
        st._last_update_warning = None
        st.check_is_updating(5, time.localtime(now))
        assert "has never been updated" in caplog.text

        # failed
        st.clear()
        st._last_update_warning = 0
        assert st.check_is_updating(5, time.localtime(now)) is False

    # disabled (Line 236)
    st.enabled = False
    assert st.check_is_updating(5, time.localtime(now)) is False


def test_restore_state_branches(caplog):
    caplog.set_level(logging.DEBUG)
    st = make_st(calc=Calc.PEAK, value_key=OutputField.PEAK_POWER)
    st._name = MagicMock()
    st._name.__str__.return_value = "<MagicMock"

    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path:
        mock_file = MagicMock()
        mock_path.return_value = mock_file
        mock_obsolete = MagicMock()
        mock_obsolete.is_file.return_value = True
        mock_file.is_file.return_value = False

        mocks = {}

        def side_effect(*args):
            arg_str = str(args[0]) if args else ""
            if arg_str not in mocks:
                m = MagicMock()
                # If this is the peak power request, return mock_obsolete when divided
                m.__truediv__.side_effect = lambda x: mock_obsolete if "peak_power" in (arg_str + str(x)).lower() else mock_file
                m.is_file.return_value = False
                mock_file.is_file.return_value = False
                mock_file.__truediv__.return_value.is_file.return_value = False
                m.is_file.return_value = False
                mocks[arg_str] = m
            return mocks[arg_str]

        mock_path.side_effect = side_effect
        st.restore_state(Topic("t1"))
        assert mock_obsolete.rename.called

    # JSON error
    with patch("sigenergy2mqtt.pvoutput.service_topics.state_store") as mock_ss:
        mock_ss.load_sync.return_value = "INVALID"
        st.restore_state(Topic("t1"))
        assert "Failed to decode" in caplog.text

    # Stale/Not found
    with patch("sigenergy2mqtt.pvoutput.service_topics.state_store") as mock_ss:
        mock_ss.load_sync.return_value = None
        st.restore_state(Topic("t1"))
        assert "No persisted state found" in caplog.text


def test_reset_with_child():
    st = make_st()
    child = make_st()
    child.reset = MagicMock()
    st._time_periods = [child]
    st.reset()
    child.reset.assert_called()


def test_aggregate_logging_no_dt(caplog):
    caplog.set_level(logging.DEBUG)
    cfg_obj = Config()
    cfg_obj.pvoutput.calc_debug_logging = True
    with _swap_active_config(cfg_obj):
        # Average
        st = make_st(calc=Calc.AVERAGE | Calc.PEAK)
        st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
        st.add_to_payload({}, 5, time.localtime())
        assert "Averaged" in caplog.text
        # L-L Avg
        caplog.clear()
        st = make_st(calc=Calc.L_L_AVG | Calc.PEAK)
        st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
        payload = {}
        st.add_to_payload(payload, 5, time.localtime())
        assert "L-L Averaged" in caplog.text
        # Sum
        caplog.clear()
        st = make_st(calc=Calc.SUM | Calc.PEAK)
        st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
        st.add_to_payload({}, 5, time.localtime())
        assert "Summed" in caplog.text


def test_aggregate_logging_with_dt(caplog):
    caplog.set_level(logging.DEBUG)
    cfg_obj = Config()
    cfg_obj.pvoutput.calc_debug_logging = True
    with _swap_active_config(cfg_obj):
        st = make_st(calc=Calc.SUM | Calc.PEAK, value_key=OutputField.GENERATION)
        st._datetime_key = "dt"
        st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
        st.add_to_payload({}, 5, time.localtime())
        assert "Summed" in caplog.text
        # Switch to L-L
        st.calculation = Calc.L_L_AVG | Calc.PEAK
        st.add_to_payload({}, 5, time.localtime())
        assert "L-L Averaged" in caplog.text


def test_payload_deletion_and_remaining_gaps(caplog):
    caplog.set_level(logging.DEBUG)

    # 158: check_is_updating fails
    cfg_obj = Config()
    cfg_obj.pvoutput.started = 0
    with _swap_active_config(cfg_obj):
        st = make_st(calc=Calc.SUM)
        # No topics -> check_is_updating returns False
        assert st.add_to_payload({}, 5, time.localtime()) is False

    # 102-105: payload deletion in AVERAGE
    st = make_st(calc=Calc.AVERAGE | Calc.PEAK, value_key=OutputField.GENERATION)
    # No topics registered -> count = 0
    payload = {"g": 123}
    assert st.add_to_payload(payload, 5, time.localtime()) is False
    assert "g" not in payload
    assert "Removed 'g' from payload" in caplog.text

    # 123-126: _squared_root_into fails with key in payload
    st = make_st(calc=Calc.L_L_AVG | Calc.PEAK, value_key=OutputField.GENERATION)
    payload = {"g": 123}
    assert st.add_to_payload(payload, 5, time.localtime()) is False
    assert "g" not in payload

    # 112-114: L-L Averaged with datetime
    caplog.clear()
    cfg_obj = Config()
    cfg_obj.pvoutput.calc_debug_logging = True
    with _swap_active_config(cfg_obj):
        st = make_st(calc=Calc.L_L_AVG | Calc.PEAK, value_key=OutputField.GENERATION)
        st._datetime_key = "dt"
        st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
        st.add_to_payload({}, 5, time.localtime())
        assert "L-L Averaged" in caplog.text
        assert "dt=" in caplog.text


@pytest.mark.asyncio
async def test_handle_update_complex_branches(caplog):
    caplog.set_level(logging.DEBUG)
    st = make_st(calc=Calc.PEAK)
    child = make_st()
    st._time_periods = [child]
    st.register(Topic("t1", state=100.0, timestamp=time.localtime()))

    cfg_obj = Config()
    cfg_obj.pvoutput.update_debug_logging = True
    with _swap_active_config(cfg_obj):
        await st.handle_update(None, MagicMock(), 110.0, "t1", MagicMock())
        assert "Updating" in caplog.text
        # child branch non-current
        with patch.object(PvOutputConfig, "current_time_period", return_value=[]):
            await st.handle_update(None, MagicMock(), 120.0, "t1", MagicMock())
            assert "Updating GENERATION children" in caplog.text
        # Peak ignoring
        t = st["t1"]
        t.state = 200.0
        # Use a fixed time in the future and mock time.time() to ensure int(seconds) % 60 == 0
        fixed_now = 1000000.0
        t.restore_timestamp = time.localtime(fixed_now + 60)
        with patch("time.time", return_value=fixed_now):
            await st.handle_update(None, MagicMock(), 150.0, "t1", MagicMock())
        assert "Ignoring" in caplog.text
    # disabled
    st.enabled = False
    assert await st.handle_update(None, MagicMock(), 1.0, "t1", MagicMock()) is False


def test_subscribe_branches(caplog):
    caplog.set_level(logging.DEBUG)
    st = make_st()
    st["t1"] = Topic("t1")
    st.subscribe(MagicMock(), MagicMock())
    assert "Subscribed to topic t1" in caplog.text
    st.enabled = False
    st.subscribe(MagicMock(), MagicMock())
    assert "Not subscribing" in caplog.text


def test_time_period_misc():
    tp = TimePeriodServiceTopics(MagicMock(), True, logging.getLogger(), value_key=OutputField.GENERATION)
    tp.subscribe(None, None)
    tp.register(Topic("t1"))
