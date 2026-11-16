"""Tests for the housekeeping fixes: MID purge, buffered InfluxDB writes, derived-sensor keys."""

import time
from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.mqtt import handler as handler_module
from sigenergy2mqtt.mqtt.handler import MqttHandler


def test_seen_mids_expire():
    h = MqttHandler("cid", None, MagicMock())  # type: ignore[arg-type]
    h.on_response(1, "t", MagicMock())
    assert 1 in h._seen_mids
    h._seen_mid_times[1] = time.time() - handler_module._MID_EXPIRY_SECONDS - 1
    h.on_response(2, "t", MagicMock())
    assert 1 not in h._seen_mids
    assert 2 in h._seen_mids


@pytest.mark.asyncio
async def test_influx_requeue_bounded():
    from sigenergy2mqtt.influxdb.base import InfluxBase

    base = MagicMock(spec=InfluxBase)
    import asyncio

    base._batch_lock = asyncio.Lock()
    base._write_buffer = ["new"]
    base._max_buffer = 3
    base.log_identity = 'x'
    await InfluxBase._requeue_batch(base, ["a", "b", "c"])
    assert base._write_buffer == ["b", "c", "new"]
