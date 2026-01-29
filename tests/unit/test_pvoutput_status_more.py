import asyncio
import time

import pytest

from sigenergy2mqtt.config import StatusField
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.pvoutput.topic import Topic


@pytest.mark.asyncio
async def test_schedule_clips_negative_consumption_and_sets_c1(monkeypatch):
    logger = __import__("logging").getLogger("test")
    svc = PVOutputStatusService(logger, {}, {})

    # prepare payload: has generation energy and negative consumption power
    payload = {"d": "20250101", StatusField.GENERATION_ENERGY.value: 10, StatusField.CONSUMPTION_POWER.value: -5}
    snapshot = {}

    async def fake_seconds(rand_min=1, rand_max=1):
        return 0.0, time.time() + 10

    async def fake_upload(url, pl):
        # upload called after schedule prepares payload; ensure negative consumption clipped
        assert pl[StatusField.CONSUMPTION_POWER.value] == 0
        svc.online = False

    monkeypatch.setattr(svc, "seconds_until_status_upload", fake_seconds)
    monkeypatch.setattr(svc, "_create_payload", lambda now: (payload, snapshot))
    monkeypatch.setattr(svc, "upload_payload", fake_upload)

    svc.online = asyncio.get_running_loop().create_future()
    tasks = svc.schedule(None, None)
    # run the single publish_updates coroutine
    await tasks[0]


def test_create_payload_excludes_donation_when_not_donator():
    logger = __import__("logging").getLogger("test")
    # ensure donator False
    from sigenergy2mqtt.pvoutput.service import Service

    orig_donator = Service._donator
    try:
        Service._donator = False
        t = Topic("v7/topic", gain=1.0, state=2.0, timestamp=time.localtime())
        svc = PVOutputStatusService(logger, topics={StatusField.V7: [t]}, extended_data={StatusField.V7: "energy"})
        payload, snapshot = svc._create_payload(time.localtime())
        assert StatusField.V7.value not in payload
    finally:
        Service._donator = orig_donator
