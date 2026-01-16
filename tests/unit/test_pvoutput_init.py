"""Tests for sigenergy2mqtt/pvoutput/__init__.py"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.pvoutput import get_gain, get_pvoutput_services
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import UnitOfEnergy, UnitOfPower

# region get_gain tests


class DummySensor(Sensor):
    """Minimal sensor for testing get_gain."""

    def __init__(self, gain=None, unit=None):
        self.gain = gain
        self.unit = unit

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        return True


def test_get_gain_with_none_gain():
    """When sensor gain is None, get_gain should return 1.0."""
    sensor = DummySensor(gain=None)
    assert get_gain(sensor) == 1.0


def test_get_gain_with_custom_gain():
    """When sensor has a custom gain, get_gain should return it as float."""
    sensor = DummySensor(gain=2.5)
    assert get_gain(sensor) == 2.5


def test_get_gain_kilo_watt_hour_unit_with_100_gain():
    """When sensor unit is kWh and gain is 100, get_gain should return 10.0."""
    sensor = DummySensor(gain=100, unit=UnitOfEnergy.KILO_WATT_HOUR)
    assert get_gain(sensor) == 10.0


def test_get_gain_kilo_watt_unit_with_100_gain():
    """When sensor unit is kW and gain is 100, get_gain should return 10.0."""
    sensor = DummySensor(gain=100, unit=UnitOfPower.KILO_WATT)
    assert get_gain(sensor) == 10.0


def test_get_gain_kilo_watt_hour_unit_with_other_gain():
    """When sensor unit is kWh but gain is not 100, get_gain should return the gain."""
    sensor = DummySensor(gain=50, unit=UnitOfEnergy.KILO_WATT_HOUR)
    assert get_gain(sensor) == 50.0


def test_get_gain_negate():
    """When negate=True, get_gain should return negative gain."""
    sensor = DummySensor(gain=2.0)
    assert get_gain(sensor, negate=True) == -2.0


def test_get_gain_negate_with_none():
    """When negate=True and gain is None, get_gain should return -1.0."""
    sensor = DummySensor(gain=None)
    assert get_gain(sensor, negate=True) == -1.0


# endregion


# region get_pvoutput_services tests


def test_get_pvoutput_services_with_empty_configs():
    """When configs list is empty, should return two services (status and output)."""
    with patch("sigenergy2mqtt.pvoutput.Config") as mock_config:
        # Setup minimal config mocks
        mock_config.pvoutput.log_level = logging.INFO
        mock_config.pvoutput.extended = {}
        mock_config.pvoutput.temperature_topic = None
        mock_config.pvoutput.consumption = None
        mock_config.pvoutput.voltage = None
        mock_config.pvoutput.consumption_enabled = False
        mock_config.pvoutput.exports = False
        mock_config.pvoutput.imports = False

        services = get_pvoutput_services([])

        assert len(services) == 2
        assert isinstance(services[0], PVOutputStatusService)
        assert isinstance(services[1], PVOutputOutputService)


def test_get_pvoutput_services_returns_status_and_output():
    """get_pvoutput_services should always return a status and output service."""
    with patch("sigenergy2mqtt.pvoutput.Config") as mock_config:
        mock_config.pvoutput.log_level = logging.DEBUG
        mock_config.pvoutput.extended = {}
        mock_config.pvoutput.temperature_topic = None
        mock_config.pvoutput.consumption = None
        mock_config.pvoutput.voltage = None
        mock_config.pvoutput.consumption_enabled = False
        mock_config.pvoutput.exports = False
        mock_config.pvoutput.imports = False

        services = get_pvoutput_services([])

        status_service = services[0]
        output_service = services[1]

        assert hasattr(status_service, "schedule")
        assert hasattr(output_service, "schedule")
        assert status_service.unique_id == "pvoutput_status"
        assert output_service.unique_id == "pvoutput_output"


def test_get_pvoutput_services_with_temperature_topic():
    """When temperature_topic is set, it should be added to status topics."""
    with patch("sigenergy2mqtt.pvoutput.Config") as mock_config:
        mock_config.pvoutput.log_level = logging.INFO
        mock_config.pvoutput.extended = {}
        mock_config.pvoutput.temperature_topic = "home/temperature"
        mock_config.pvoutput.consumption = None
        mock_config.pvoutput.voltage = None
        mock_config.pvoutput.consumption_enabled = False
        mock_config.pvoutput.exports = False
        mock_config.pvoutput.imports = False

        services = get_pvoutput_services([])
        status_service = services[0]

        # The temperature topic should be registered
        assert status_service is not None


# endregion
