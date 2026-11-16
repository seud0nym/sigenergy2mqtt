"""Tests for the housekeeping fixes: MID purge, buffered InfluxDB writes, derived-sensor keys."""

import time
from unittest.mock import AsyncMock, MagicMock

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


@pytest.mark.asyncio
async def test_influx_write_line_does_not_start_second_write_while_sending():
    import asyncio

    from sigenergy2mqtt.influxdb.base import InfluxBase

    base = MagicMock(spec=InfluxBase)
    base._batch_lock = asyncio.Lock()
    base._send_lock = asyncio.Lock()
    base._write_buffer = []
    base._max_buffer = 2
    base._batch_size = 1
    base._flush_interval = 1000.0
    base._last_flush = time.time()
    base.log_identity = "x"
    base._take_batch = lambda: InfluxBase._take_batch(base)
    base._send_batch = AsyncMock()
    async with base._send_lock:
        for i in range(4):
            await InfluxBase.write_line(base, f"l{i}")
    base._send_batch.assert_awaited()
    assert all(call.args[0] == [] for call in base._send_batch.await_args_list)
    assert base._write_buffer == ["l2", "l3"]
