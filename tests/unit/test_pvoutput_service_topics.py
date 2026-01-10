import logging
import time

import pytest

from sigenergy2mqtt.config import Config, OutputField
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics
from sigenergy2mqtt.pvoutput.topic import Topic


def make_service() -> Service:
    logger = logging.getLogger("test")
    return Service("pv", "uid", "model", logger)


def test_aggregate_disabled_returns_none():
    svc = make_service()
    st = ServiceTopics(svc, enabled=False, logger=svc.logger, value_key=OutputField.GENERATION)
    total, at, count = st.aggregate(exclude_zero=True)
    assert total is None and at is None and count == 0


def test_register_and_sum_and_check_updating(tmp_path, monkeypatch):
    svc = make_service()
    # ensure pvoutput thinks service has been started long ago
    Config.pvoutput.started = time.time() - 3600
    st = ServiceTopics(svc, enabled=True, logger=svc.logger, value_key=OutputField.GENERATION)

    # create topics and register
    t1 = Topic("t/1", scan_interval=60, gain=1.0, state=2.0, timestamp=time.localtime())
    t2 = Topic("t/2", scan_interval=60, gain=1.0, state=3.0, timestamp=time.localtime())
    st.register(t1)
    st.register(t2)

    # check_is_updating should be True because topics were just timestamped
    now_struct = time.localtime()
    assert st.check_is_updating(5, now_struct) is True

    payload = {}
    # SUM is default calculation
    assert st.add_to_payload(payload, 5, now_struct) is True
    assert OutputField.GENERATION.value in payload
    assert payload[OutputField.GENERATION.value] == round(2.0 + 3.0)


def test_average_and_decimals():
    svc = make_service()
    Config.pvoutput.started = time.time() - 3600
    st = ServiceTopics(svc, enabled=True, logger=svc.logger, value_key=OutputField.GENERATION, calc=Calculation.AVERAGE, decimals=1)
    t1 = Topic("t/a", gain=1.0, state=1.25, timestamp=time.localtime())
    t2 = Topic("t/b", gain=1.0, state=2.25, timestamp=time.localtime())
    st.register(t1)
    st.register(t2)
    payload = {}
    assert st.add_to_payload(payload, 5, time.localtime()) is True
    # average (1.25+2.25)/2 = 1.75 -> rounded to 1 decimal = 1.8
    assert pytest.approx(payload[OutputField.GENERATION.value], rel=1e-3) == 1.8


def test_ll_avg_squared_root():
    svc = make_service()
    Config.pvoutput.started = time.time() - 3600
    st = ServiceTopics(svc, enabled=True, logger=svc.logger, value_key=OutputField.GENERATION, calc=Calculation.L_L_AVG, decimals=2)
    # values contribute squared
    t1 = Topic("t/1", gain=1.0, state=3.0, timestamp=time.localtime())
    t2 = Topic("t/2", gain=1.0, state=4.0, timestamp=time.localtime())
    st.register(t1)
    st.register(t2)
    payload = {}
    assert st.add_to_payload(payload, 5, time.localtime()) is True
    total_sq = 3.0**2 + 4.0**2
    expected = round((total_sq**0.5) / (3**0.5), 2)
    assert payload[OutputField.GENERATION.value] == expected


def test_difference_and_convert_to_watts():
    svc = make_service()
    Config.pvoutput.started = time.time() - 3600
    # configure calculation to include DIFFERENCE and CONVERT_TO_WATTS
    st = ServiceTopics(svc, enabled=True, logger=svc.logger, value_key=OutputField.GENERATION, calc=Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
    # create a topic with previous_state set to simulate energy reading earlier
    now = time.time()
    topic = Topic("t/d", gain=1.0, state=5.0, timestamp=time.localtime(now), previous_state=2.0, previous_timestamp=time.localtime(now - 3600))
    st.register(topic)
    payload = {}
    # check aggregate (difference should be 3.0, converted over 1 hour -> power=3.0)
    assert st.add_to_payload(payload, 5, time.localtime()) is True
    assert OutputField.GENERATION.value in payload
    # float nearly equal to 3.0 (power)
    assert pytest.approx(payload[OutputField.GENERATION.value], rel=1e-3) == 3.0
import logging
import time

import pytest

from sigenergy2mqtt.config import OutputField
from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics
from sigenergy2mqtt.pvoutput.topic import Topic


def make_service_topics(calc=Calculation.SUM, enabled=True, decimals=0):
    logger = logging.getLogger("pvtest")
    from types import SimpleNamespace

    svc = SimpleNamespace(unique_id="pvtest")
    return ServiceTopics(svc, enabled, logger, value_key=OutputField.GENERATION, calc=calc, decimals=decimals)


def test_sum_into_and_aggregate():
    st = make_service_topics(Calculation.SUM)
    t1 = Topic(topic="t1", state=1.0, timestamp=time.localtime(), gain=1.0)
    t2 = Topic(topic="t2", state=2.0, timestamp=time.localtime(), gain=2.0)
    st.register(t1)
    st.register(t2)
    payload = {}
    added = st.add_to_payload(payload, 1440, time.localtime())
    assert added is True
    # sum: 1*1 + 2*2 = 5
    assert payload[OutputField.GENERATION.value] == 5


def test_average_into():
    st = make_service_topics(Calculation.AVERAGE, decimals=1)
    t1 = Topic(topic="t1", state=1.5, timestamp=time.localtime(), gain=1.0)
    t2 = Topic(topic="t2", state=2.5, timestamp=time.localtime(), gain=1.0)
    st.register(t1)
    st.register(t2)
    payload = {}
    added = st.add_to_payload(payload, 1440, time.localtime())
    assert added is True
    assert payload[OutputField.GENERATION.value] == round((1.5 + 2.5) / 2, 1)


def test_squared_root_into():
    st = make_service_topics(Calculation.L_L_AVG)
    # squared total should be sum(state**2 * gain). L-L avg divides sqrt(total)/sqrt(3)
    t1 = Topic(topic="t1", state=3.0, timestamp=time.localtime(), gain=1.0)
    st.register(t1)
    payload = {}
    added = st.add_to_payload(payload, 1440, time.localtime())
    assert added is True
    import math

    expected = round(math.sqrt(3.0**2) / math.sqrt(3))
    assert payload[OutputField.GENERATION.value] == expected


def test_difference_and_convert_to_watts():
    st = make_service_topics(Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
    # create topic with previous state one hour earlier
    now = time.localtime()
    prev = time.localtime(time.time() - 3600)
    t = Topic(topic="t1", state=200.0, timestamp=now, gain=1.0)
    t.previous_state = 100.0
    t.previous_timestamp = prev
    st.register(t)
    payload = {}
    added = st.add_to_payload(payload, 1440, now)
    # difference = 100 energy units over 1 hour -> converted to power = 100
    assert added is True
    assert payload[OutputField.GENERATION.value] == 100


def test_check_is_updating_and_restore_warning(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    st = make_service_topics(Calculation.SUM)
    # service just started -> should skip updating check
    orig_started = Config.pvoutput.started
    try:
        Config.pvoutput.started = time.time()
        t = Topic(topic="t1", state=1.0, timestamp=None, gain=1.0)
        st.register(t)
        # now_struct within 120s -> check_is_updating returns True
        assert st.check_is_updating(5, time.localtime()) is True
    finally:
        Config.pvoutput.started = orig_started
