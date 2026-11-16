"""A scan group must keep being polled whatever a sensor raises."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.devices.base import poller as poller_module
from sigenergy2mqtt.devices.base.poller import SensorGroupPoller
from sigenergy2mqtt.sensors.base.sanity_check import SanityCheckException
from sigenergy2mqtt.sensors.plant.read_only import PlantPVPower


def _device() -> MagicMock:
    device = MagicMock()
    device.online = True
    device._shutdown_event = asyncio.Event()
    device.log_identity = "Dev"
    device.rediscover = False
    return device


def _sensor() -> PlantPVPower:
    sensor = PlantPVPower(0)
    sensor.configure_mqtt_topics("dev")
    sensor.scan_interval = 1
    return sensor


async def _run_until(device: MagicMock, sensor: PlantPVPower, transport, publishes: int, timeout: float = 10.0) -> asyncio.Task:
    task = asyncio.create_task(SensorGroupPoller(device).run(transport, MagicMock(), "group", sensor))
    deadline = asyncio.get_running_loop().time() + timeout
    while sensor.publish.call_count < publishes and not task.done() and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.05)
    return task


async def _stop(device: MagicMock, task: asyncio.Task) -> None:
    device.online = False
    await asyncio.wait_for(task, 5)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [KeyError("x"), ZeroDivisionError("z"), SanityCheckException("out of range"), OSError("net down")])
async def test_poller_survives_unexpected_exception(error, caplog):
    device = _device()
    sensor = _sensor()
    sensor.publish = AsyncMock(side_effect=[error, True, True, True, True])

    with caplog.at_level(logging.DEBUG, logger=poller_module.logger.name):
        task = await _run_until(device, sensor, None, publishes=2)
        try:
            assert not task.done(), f"poller ended after {error!r}"
            assert sensor.publish.call_count >= 2, "the sensor was not polled again after the failure"
        finally:
            await _stop(device, task)

    assert task.exception() is None
    assert repr(error) in caplog.text


@pytest.mark.asyncio
async def test_unexpected_exception_is_logged_once_then_demoted(caplog):
    device = _device()
    sensor = _sensor()
    sensor.publish = AsyncMock(side_effect=KeyError("x"))

    with caplog.at_level(logging.DEBUG, logger=poller_module.logger.name):
        task = await _run_until(device, sensor, None, publishes=2)
        await _stop(device, task)

    unexpected = [r for r in caplog.records if "unexpected error" in r.getMessage()]
    assert len(unexpected) >= 2
    assert [r.levelno for r in unexpected].count(logging.ERROR) == 1, "repeats of the same error should be logged at DEBUG"
    assert unexpected[0].levelno == logging.ERROR and unexpected[0].exc_info is not None


@pytest.mark.asyncio
async def test_oserror_reconnects_a_disconnected_modbus_transport():
    device = _device()
    sensor = _sensor()
    sensor.publish = AsyncMock(side_effect=[OSError("reset"), True, True, True])

    transport = MagicMock()
    transport.connected = False
    transport.outage = None
    transport.read_ahead_registers = AsyncMock(return_value=0)

    async def connect():
        transport.connected = True

    transport.connect = AsyncMock(side_effect=connect)

    task = await _run_until(device, sensor, transport, publishes=2)
    try:
        assert transport.connect.await_count == 1
        assert not task.done()
    finally:
        await _stop(device, task)


@pytest.mark.asyncio
async def test_cancellation_is_not_swallowed_by_the_safety_net():
    device = _device()
    sensor = _sensor()

    async def publish(*args, **kwargs):
        await asyncio.sleep(30)

    sensor.publish = AsyncMock(side_effect=publish)
    task = await _run_until(device, sensor, None, publishes=1)
    device.online = False
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 5)
