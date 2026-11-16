"""Sensor.publish error handling for failures that are not Modbus exceptions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.sensors.base.sanity_check import SanityCheckException
from sigenergy2mqtt.sensors.plant.read_only import PlantPVPower


def _sensor() -> PlantPVPower:
    sensor = PlantPVPower(0)
    sensor.configure_mqtt_topics("dev")
    return sensor


@pytest.mark.asyncio
async def test_sanity_check_failure_without_transport_is_counted_not_raised():
    sensor = _sensor()
    sensor._attempt_publish = AsyncMock(side_effect=SanityCheckException("out of range"))

    with patch("sigenergy2mqtt.sensors.base.sensor.active_config.sanity_check_failures_increment", True, create=True):
        assert await sensor.publish(MagicMock(), None) is False

    assert sensor._failures == 1


@pytest.mark.asyncio
async def test_oserror_with_connected_transport_is_counted_as_a_failure():
    sensor = _sensor()
    sensor._attempt_publish = AsyncMock(side_effect=ConnectionResetError("reset"))
    transport = MagicMock()
    transport.connected = True
    transport.outage = None

    assert await sensor.publish(MagicMock(), transport) is False
    assert sensor._failures == 1


@pytest.mark.asyncio
async def test_oserror_with_disconnected_transport_is_raised_for_the_poller_to_reconnect():
    sensor = _sensor()
    sensor._attempt_publish = AsyncMock(side_effect=ConnectionResetError("reset"))
    transport = MagicMock()
    transport.connected = False
    transport.outage = None

    with pytest.raises(ConnectionResetError):
        await sensor.publish(MagicMock(), transport)
    assert sensor._failures == 0


@pytest.mark.asyncio
async def test_timeout_is_left_to_the_caller():
    sensor = _sensor()
    sensor._attempt_publish = AsyncMock(side_effect=TimeoutError("slow"))
    transport = MagicMock()
    transport.connected = True

    with pytest.raises(TimeoutError):
        await sensor.publish(MagicMock(), transport)
    assert sensor._failures == 0
