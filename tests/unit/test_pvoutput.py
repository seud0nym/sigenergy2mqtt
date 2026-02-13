import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.config import Config, ConsumptionSource, StatusField, VoltageSource
from sigenergy2mqtt.config.config import active_config
from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration
from sigenergy2mqtt.pvoutput import get_gain, get_pvoutput_services
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.pvoutput.topic import Topic
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import UnitOfEnergy, UnitOfPower


def make_service():
    logger = logging.getLogger("test-pvoutput")
    return Service("pvtest", "pvtest", "pvmodel", logger)


class TestPVOutputBase:
    """Tests for base PVOutput Service logic and utility functions."""

    def test_get_response_headers_and_reset(self, monkeypatch):
        svc = make_service()
        monkeypatch.setattr(time, "time", lambda: 1000.0)
        resp = requests.Response()
        resp.status_code = 200
        resp.headers = {
            "X-Rate-Limit-Limit": "60",
            "X-Rate-Limit-Remaining": "58",
            "X-Rate-Limit-Reset": "1060.0",
        }
        limit, remaining, at, reset = svc.get_response_headers(resp)
        assert limit == 60
        assert remaining == 58
        assert at == 1060.0
        assert isinstance(reset, int)

    @pytest.mark.asyncio
    async def test_seconds_until_status_upload_testing(self):
        svc = make_service()
        with patch.object(active_config.pvoutput, "testing", True):
            seconds, next_time = await svc.seconds_until_status_upload(rand_min=1, rand_max=1)
            assert seconds == 60
            assert isinstance(next_time, int)
            assert Service._interval == 5

    @pytest.mark.asyncio
    async def test_upload_payload_testing_mode(self):
        svc = make_service()
        with patch.object(active_config.pvoutput, "testing", True):
            uploaded = await svc.upload_payload("https://pvoutput.org/addstatus.jsp", {"d": "20250101"})
            assert uploaded is True

    @pytest.mark.asyncio
    async def test_upload_payload_http_error_bad_request(self, monkeypatch):
        svc = make_service()
        with patch.object(active_config.pvoutput, "testing", False):
            resp = requests.Response()
            resp.status_code = 400
            resp.reason = "Bad Request"
            resp.headers = {"X-Rate-Limit-Remaining": "5", "X-Rate-Limit-Limit": "60", "X-Rate-Limit-Reset": "1100.0"}
            resp._content = b"Bad Request"

            monkeypatch.setattr("requests.post", MagicMock(side_effect=requests.exceptions.HTTPError(response=resp)))
            monkeypatch.setattr(asyncio, "sleep", AsyncMock())

            uploaded = await svc.upload_payload("url", {"d": "20250101"})
            assert uploaded is False


class TestPVOutputGain:
    """Tests for get_gain utility function."""

    class DummySensor(Sensor):
        def __init__(self, gain=None, unit=None):
            self.gain = gain
            self.unit = unit

        async def _update_internal_state(self, **kwargs):
            return True

    def test_get_gain_cases(self):
        assert get_gain(self.DummySensor(gain=None)) == 1.0
        assert get_gain(self.DummySensor(gain=2.5)) == 2.5
        assert get_gain(self.DummySensor(gain=100, unit=UnitOfEnergy.KILO_WATT_HOUR)) == 10.0
        assert get_gain(self.DummySensor(gain=100, unit=UnitOfPower.KILO_WATT)) == 10.0
        assert get_gain(self.DummySensor(gain=2.0), negate=True) == -2.0
        assert get_gain(self.DummySensor(gain=None), negate=True) == -1.0


class TestPVOutputInit:
    """Tests for PVOutput service initialization."""

    def test_get_pvoutput_services_comprehensive(self):
        with (
            patch.object(active_config.pvoutput, "enabled", True),
            patch.object(active_config.pvoutput, "consumption", ConsumptionSource.NET_OF_BATTERY),
            patch.object(active_config.pvoutput, "voltage", VoltageSource.PV),
            patch.object(active_config.pvoutput, "temperature_topic", "temp/topic"),
            patch.object(active_config.pvoutput, "extended", {StatusField.V7: "ExtendedMock", StatusField.V8: "", StatusField.V9: "", StatusField.V10: "", StatusField.V11: "", StatusField.V12: ""}),
        ):
            # mock for get_pvoutput_services
            services = get_pvoutput_services([])
            assert len(services) == 2
            assert isinstance(services[0], PVOutputStatusService)
            assert isinstance(services[1], PVOutputOutputService)


class TestPVOutputConfiguration:
    """Tests for PVOutputConfiguration behavior."""

    def test_calc_debug_logging_behavior(self):
        config = PVOutputConfiguration()
        assert config.calc_debug_logging is False
        config.calc_debug_logging = True
        assert config.calc_debug_logging is True

    def test_consumption_enabled_logic(self):
        config = PVOutputConfiguration()
        config.consumption = None
        assert config.consumption_enabled is False
        config.consumption = ConsumptionSource.CONSUMPTION
        assert config.consumption_enabled is True

    def test_validate_requirements(self):
        config = PVOutputConfiguration()
        config.enabled = True
        with pytest.raises(ValueError, match="api-key must be provided"):
            config.validate()
        config.api_key = "abc"
        with pytest.raises(ValueError, match="system-id must be provided"):
            config.validate()
        config.system_id = "123"
        config.validate()
