import json
import logging
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch


import pytest

from sigenergy2mqtt.config import OutputField, StatusField, active_config
from sigenergy2mqtt.config.settings import PvOutputConfig
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics
from sigenergy2mqtt.pvoutput.topic import Topic




def make_service(unique_id: str = "test_service") -> Service:
    logger = logging.getLogger("test")
    return Service("pv", unique_id, "model", logger)


def make_service_topics(name="test", enabled=True, value_key=OutputField.GENERATION, **kwargs):
    logger = logging.getLogger("test-pvoutput-topics")
    service = MagicMock(spec=Service)
    service.unique_id = "test_service"
    service.lock = MagicMock()
    return ServiceTopics(service, enabled, logger, value_key=value_key, **kwargs)


class TestPVOutputTopic:
    """Tests for Topic class."""

    def test_topic_json_encoding_decoding(self):
        ts = list(time.localtime())
        t_dict = {"topic": "test", "gain": 1.0, "state": 10.0, "timestamp": ts, "previous_state": 5.0, "previous_timestamp": ts}
        decoded = Topic.json_decoder(t_dict)
        assert isinstance(decoded.previous_timestamp, time.struct_time)
        assert decoded.state == 10.0

        with pytest.raises(TypeError):
            Topic.json_encoder(object())

    def test_topic_json_roundtrip(self):
        now = time.localtime()
        t = Topic(topic="a/b", scan_interval=60, gain=2.0, precision=1, state=3.5, timestamp=now)
        encoded = json.dumps(t, default=Topic.json_encoder)
        loaded = json.loads(encoded, object_hook=Topic.json_decoder)
        assert isinstance(loaded, Topic)
        assert loaded.topic == t.topic
        assert loaded.state == t.state

    def test_json_decoder_handles_list_timestamps(self):
        ts_list = list(time.localtime())
        obj = {"topic": "x", "scan_interval": 10, "gain": 1.0, "state": 2.0, "timestamp": ts_list}
        topic = Topic.json_decoder(obj)
        assert isinstance(topic, Topic)
        assert isinstance(topic.timestamp, time.struct_time)


class TestPVOutputServiceTopics:
    """Tests for ServiceTopics and TimePeriodServiceTopics."""

    def test_aggregate_disabled_returns_none(self):
        st = make_service_topics(enabled=False)
        total, at, count = st.aggregate(exclude_zero=True)
        assert total is None and at is None and count == 0

    def test_register_and_sum_and_check_updating(self):
        active_config.pvoutput.started = time.time() - 3600
        st = make_service_topics()

        t1 = Topic("t/1", scan_interval=60, gain=1.0, state=2.0, timestamp=time.localtime())
        t2 = Topic("t/2", scan_interval=60, gain=1.0, state=3.0, timestamp=time.localtime())
        st.register(t1)
        st.register(t2)

        now_struct = time.localtime()
        assert st.check_is_updating(5, now_struct) is True

        payload = {}
        assert st.add_to_payload(payload, 5, now_struct) is True
        assert payload[OutputField.GENERATION.value] == round(2.0 + 3.0)

    def test_average_and_decimals(self):
        st = make_service_topics(calc=Calculation.AVERAGE, decimals=1)
        t1 = Topic("t/a", gain=1.0, state=1.25, timestamp=time.localtime())
        t2 = Topic("t/b", gain=1.0, state=2.25, timestamp=time.localtime())
        st.register(t1)
        st.register(t2)
        payload = {}
        st.add_to_payload(payload, 5, time.localtime())
        assert pytest.approx(payload[OutputField.GENERATION.value], rel=1e-3) == 1.8

    def test_ll_avg_squared_root(self):
        st = make_service_topics(calc=Calculation.L_L_AVG, decimals=2)
        t1 = Topic("t/1", gain=1.0, state=3.0, timestamp=time.localtime())
        t2 = Topic("t/2", gain=1.0, state=4.0, timestamp=time.localtime())
        st.register(t1)
        st.register(t2)
        payload = {}
        st.add_to_payload(payload, 5, time.localtime())
        total_sq = 3.0**2 + 4.0**2
        expected = round((total_sq**0.5) / (3**0.5), 2)
        assert payload[OutputField.GENERATION.value] == expected

    def test_difference_and_convert_to_watts(self):
        now_ts = 1704110400.0
        now = time.localtime(now_ts)
        active_config.pvoutput.started = now_ts - 3600

        st = make_service_topics(calc=Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
        prev_ts = now_ts - 3600
        topic = Topic("t/d", gain=1.0, state=5.0, timestamp=now, previous_state=2.0, previous_timestamp=time.localtime(prev_ts))
        st.register(topic)
        payload = {}
        st.add_to_payload(payload, 5, now)
        assert pytest.approx(payload[OutputField.GENERATION.value], rel=1e-3) == 3.0

    @pytest.mark.asyncio
    async def test_handle_update_peak_calculation(self):
        st = make_service_topics(calc=Calculation.PEAK)
        with patch("sigenergy2mqtt.pvoutput.service_topics.state_store") as mock_ss:
            mock_ss.is_initialised = True
            mock_ss.load_sync.return_value = None

            t = Topic("t/1", gain=1.0, state=50.0)
            st.register(t)

            st._service.lock.return_value.__aenter__ = AsyncMock()
            st._service.lock.return_value.__aexit__ = AsyncMock()

            await st.handle_update(None, MagicMock(), 100.0, "t/1", MagicMock())
            assert t.state == 100.0
            mock_ss.save_sync.assert_called()


    def test_restore_state_from_file(self):
        st = make_service_topics(value_key=OutputField.PEAK_POWER)
        topic = Topic("test/topic", gain=1.0)

        with patch("sigenergy2mqtt.pvoutput.service_topics.state_store") as mock_ss:
            mock_ss.is_initialised = True
            saved_topic = Topic("test/topic", state=100.0, timestamp=time.localtime())
            # StateStore returns the raw JSON string of the object as stored
            mock_ss.load_sync.return_value = json.dumps({"test/topic": saved_topic}, default=Topic.json_encoder)

            st.restore_state(topic)
            assert st["test/topic"].state == 100.0


    def test_reset_clears_state(self):
        st = make_service_topics()
        t1 = Topic("t1", state=10.0, previous_state=5.0)
        st.register(t1)
        st._persistent_state_file = MagicMock()
        st.reset()
        assert st["t1"].state == 0.0
        assert st["t1"].previous_state is None

    @pytest.mark.asyncio
    async def test_time_period_service_topics_integration(self):
        st = make_service_topics()
        tp = TimePeriodServiceTopics(st._service, True, logging.getLogger(), value_key=OutputField.EXPORT_PEAK)
        st._time_periods = [tp]

        with patch("pathlib.Path.is_file", return_value=False):
            st.register(Topic("t_tp_st"))

        with patch.object(PvOutputConfig, "current_time_period", new_callable=PropertyMock) as mock_cp:
            mock_cp.return_value = [OutputField.EXPORT_PEAK]
            st._service.lock.return_value.__aenter__ = AsyncMock()
            st._service.lock.return_value.__aexit__ = AsyncMock()

            await st.handle_update(None, MagicMock(), 10.0, "t_tp_st", MagicMock())
            assert tp.aggregate(True, never_return_none=True)[0] == 10.0

    def test_check_is_updating_stale_warning(self, caplog):
        st = make_service_topics()
        t = Topic("t/1", gain=1.0, timestamp=time.localtime(time.time() - 3600))
        st.register(t)
        with patch("sigenergy2mqtt.config.active_config.pvoutput.started", time.time() - 4000):
            result = st.check_is_updating(interval_minutes=5, now_struct=time.localtime())
            assert result is False
            assert "has not been updated for" in caplog.text

    @pytest.mark.asyncio
    async def test_service_topics_remaining_misses(self, caplog):
        """Targets specific missing lines in service_topics.py."""
        caplog.set_level(logging.DEBUG)
        st = make_service_topics(value_key=StatusField.GENERATION_POWER, decimals=2, calc=Calculation.AVERAGE, datetime_key="dt")
        with patch.object(active_config.pvoutput, "calc_debug_logging", True):
            st.register(Topic("t1", state=10.0, timestamp=time.localtime()))
            payload = {"dt": "something"}
            st.add_to_payload(payload, 5, time.localtime())
            assert "Averaged" in caplog.text

        # del payload if sum fails
        st_sum = make_service_topics(value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM | Calculation.PEAK)
        payload_sum = {"v2": 100.0}
        st_sum.add_to_payload(payload_sum, 5, time.localtime())
        assert "v2" not in payload_sum

    def test_subscribe_skips_supervisor_topics(self):
        st = make_service_topics(value_key=StatusField.V7)
        st.register(Topic("__ha_sensor__:sensor.grid_power", gain=1.0))
        mqtt_handler = MagicMock()
        st.subscribe(MagicMock(), mqtt_handler)
        mqtt_handler.register.assert_not_called()
