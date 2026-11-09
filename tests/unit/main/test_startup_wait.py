"""Startup waits for an unreachable Modbus host instead of exiting."""

import logging
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.main import device_setup


class FlakyModbus:
    def __init__(self, succeed_on: int):
        self.attempts = 0
        self.succeed_on = succeed_on
        self.connected = False

    async def connect(self):
        self.attempts += 1
        self.connected = self.attempts >= self.succeed_on
        return self.connected


@pytest.mark.asyncio
async def test_waits_with_backoff_and_reports_one_outage(caplog):
    modbus = FlakyModbus(succeed_on=5)
    delays: list[float] = []

    async def fake_sleep(delay):
        delays.append(delay)

    with patch("sigenergy2mqtt.main.device_setup.asyncio.sleep", fake_sleep), caplog.at_level(logging.DEBUG):
        await device_setup._wait_for_modbus(modbus, "10.10.10.60", 502)

    assert modbus.connected
    # Waits of 5, 10, 20, 40 and 60s, slept in 1s steps so a shutdown signal is noticed promptly
    assert delays == [1] * (5 + 10 + 20 + 40 + 60)
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(errors) == 1
    assert errors[0].startswith("modbus://10.10.10.60:502 outage started: unable to connect")
    assert any(r.levelno == logging.INFO and "outage ended" in r.getMessage() for r in caplog.records)
    assert not outage_tracker("modbus://10.10.10.60:502").active


@pytest.mark.asyncio
async def test_continues_outage_reported_before_restart(caplog):
    """After a restart during an outage, the wait joins the existing outage instead of starting a new one."""
    tracker = outage_tracker("modbus://10.10.10.60:502")
    tracker.failure("ConnectionException('Not connected')")
    caplog.clear()
    modbus = FlakyModbus(succeed_on=2)

    async def fake_sleep(delay):
        pass

    with patch("sigenergy2mqtt.main.device_setup.asyncio.sleep", fake_sleep), caplog.at_level(logging.DEBUG):
        await device_setup._wait_for_modbus(modbus, "10.10.10.60", 502)

    assert [r for r in caplog.records if "outage started" in r.getMessage()] == []
    assert not tracker.active


@pytest.mark.asyncio
async def test_already_connected_returns_immediately():
    modbus = FlakyModbus(succeed_on=0)
    modbus.connected = True
    await device_setup._wait_for_modbus(modbus, "h", 502)
    assert modbus.attempts == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["mqtt", "auto_discovery"])
async def test_shutdown_signal_interrupts_the_wait(flag, monkeypatch):
    """The runtime signal handlers are not installed yet while devices are created, so the wait checks the startup flags."""
    import sigenergy2mqtt.mqtt as mqtt_module
    from sigenergy2mqtt.config import auto_discovery

    modbus = FlakyModbus(succeed_on=1000)
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)
        if len(sleeps) == 3:  # signal arrives part-way through the first backoff
            if flag == "mqtt":
                mqtt_module.interrupt_mqtt_reconnection()
            else:
                monkeypatch.setattr(auto_discovery, "_interrupted", True)

    try:
        with patch("sigenergy2mqtt.main.device_setup.asyncio.sleep", fake_sleep), pytest.raises(KeyboardInterrupt):
            await device_setup._wait_for_modbus(modbus, "h", 502)
    finally:
        mqtt_module.reset_mqtt_reconnection_interrupt()
    assert len(sleeps) == 3
    assert modbus.attempts == 0
