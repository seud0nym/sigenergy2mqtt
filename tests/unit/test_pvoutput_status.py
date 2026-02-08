import logging
import time

from sigenergy2mqtt.config import Config, StatusField
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.pvoutput.topic import Topic


def make_status_service(topics=None, extended=None):
    logger = logging.getLogger("test")
    topics = {} if topics is None else topics
    extended = {} if extended is None else extended
    return PVOutputStatusService(logger, topics, extended)


import pytest


def test_create_payload_includes_generation_power():
    # ensure deterministic started time
    Config.pvoutput.started = time.time() - 3600
    # create a generation power topic
    now = time.time()
    t = Topic("g/topic", gain=1.0, state=10.5, timestamp=time.localtime(now))
    # simulate a previous energy value an hour earlier so DIFFERENCE calculation can produce a value
    t.previous_state = 8.5
    t.previous_timestamp = time.localtime(now - 3600)
    svc = make_status_service(topics={StatusField.GENERATION_POWER: [t]}, extended={})
    payload, snapshot = svc._create_payload(time.localtime())
    # 'v2' is the value for GENERATION_POWER; difference (10.5-8.5)=2.0 converted to watts over 1h -> 2.0
    assert StatusField.GENERATION_POWER.value in payload
    assert pytest.approx(payload[StatusField.GENERATION_POWER.value], rel=1e-3) == 2.0
    # snapshot should contain previous state entries for enabled topics
    assert isinstance(snapshot, dict)


def test_create_payload_includes_donation_when_donator_true():
    # mark extended V7 present so it's enabled and donation-flagged
    Config.pvoutput.extended[StatusField.V7] = "energy"
    # force service donator state
    from sigenergy2mqtt.pvoutput.service import Service

    Service._donator = True
    # ensure started flag so updating checks pass
    Config.pvoutput.started = time.time() - 3600
    t = Topic("v7/topic", gain=1.0, state=2.0, timestamp=time.localtime())
    # pass empty extended to avoid forcing SUM/DIFFERENCE calculation in constructor
    svc = make_status_service(topics={StatusField.V7: [t]}, extended={})
    payload, snapshot = svc._create_payload(time.localtime())
    assert StatusField.V7.value in payload


@pytest.mark.asyncio
async def test_seconds_until_status_upload_testing_mode():
    # ensure testing mode returns seconds == 60
    Config.pvoutput.testing = True
    svc = make_status_service()
    seconds, next_time = await svc.seconds_until_status_upload(1, 2)
    # in testing mode seconds should be 60 (per Service.seconds_until_status_upload)
    assert seconds == 60 or seconds == 60.0
