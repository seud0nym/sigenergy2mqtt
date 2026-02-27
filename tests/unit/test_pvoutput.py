import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from sigenergy2mqtt.common import ConsumptionSource, StatusField, UnitOfEnergy, UnitOfPower, VoltageSource
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.config.settings import PvOutputConfig
from sigenergy2mqtt.pvoutput import get_gain, get_pvoutput_services
from sigenergy2mqtt.pvoutput.output import PVOutputOutputService
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.status import PVOutputStatusService
from sigenergy2mqtt.sensors.base import Sensor


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


class TestPvOutputConfig:
    """Tests for PvOutputConfig behavior."""

    def test_calc_debug_logging_behavior(self):
        config = PvOutputConfig(calc_debug_logging=True)
        assert config.calc_debug_logging is True

        config = PvOutputConfig()
        assert config.calc_debug_logging is False

    def test_consumption_enabled_logic(self):
        config = PvOutputConfig(consumption=None)
        assert config.consumption_enabled is False
        config = PvOutputConfig(consumption=ConsumptionSource.CONSUMPTION)
        assert config.consumption_enabled is True

    def test_validate_requirements(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="api-key must be provided"):
            PvOutputConfig(enabled=True)

        with pytest.raises(ValidationError, match="system-id must be provided"):
            PvOutputConfig(enabled=True, api_key="abc")

        # Should pass
        PvOutputConfig(enabled=True, api_key="abc", system_id="123")

    # --- _type_to_output_fields ---

    def test_type_to_output_fields_shoulder(self):
        """Lines 138-140: TariffType.SHOULDER branch."""
        from sigenergy2mqtt.common.output_field import OutputField
        from sigenergy2mqtt.common.tariff_type import TariffType

        config = PvOutputConfig()
        export_f, import_f = config._type_to_output_fields(TariffType.SHOULDER)
        assert export_f == OutputField.EXPORT_SHOULDER
        assert import_f == OutputField.IMPORT_SHOULDER

    def test_type_to_output_fields_high_shoulder(self):
        """Lines 141-143: TariffType.HIGH_SHOULDER branch."""
        from sigenergy2mqtt.common.output_field import OutputField
        from sigenergy2mqtt.common.tariff_type import TariffType

        config = PvOutputConfig()
        export_f, import_f = config._type_to_output_fields(TariffType.HIGH_SHOULDER)
        assert export_f == OutputField.EXPORT_HIGH_SHOULDER
        assert import_f == OutputField.IMPORT_HIGH_SHOULDER

    def test_type_to_output_fields_invalid(self):
        """Lines 144-145: invalid type raises ValueError."""
        config = PvOutputConfig()
        with pytest.raises(ValueError, match="Invalid tariff type"):
            # pydantic bypass so logic error can trigger
            config._type_to_output_fields("bogus")

    # --- current_time_period ---

    def test_current_time_period_matches_period(self):
        """Lines 153-165: tariff date+time match with debug logging."""

        from sigenergy2mqtt.common.output_field import OutputField

        config = PvOutputConfig(
            calc_debug_logging=True,
            tariffs=[{"plan": "TestPlan", "from-date": "2000-01-01", "to-date": "2099-12-31", "default": "peak", "periods": [{"type": "off-peak", "start": "00:00", "end": "23:59", "days": ["All"]}]}],
        )
        export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_OFF_PEAK
        assert import_f == OutputField.IMPORT_OFF_PEAK

    def test_current_time_period_default_fallback(self):
        """Lines 166-169: date matches but no time period matches → default."""
        from sigenergy2mqtt.common.output_field import OutputField

        config = PvOutputConfig(
            calc_debug_logging=True,
            tariffs=[
                {
                    "plan": "DefaultTest",
                    "from-date": "2000-01-01",
                    "to-date": "2099-12-31",
                    "default": "high-shoulder",
                    "periods": [
                        {
                            "type": "off-peak",
                            "start": "00:00",
                            "end": "00:01",
                            "days": ["Sun"],  # valid day, but time window 00:00-00:01 makes it miss
                        }
                    ],
                }
            ],
        )

        export_f, import_f = config.current_time_period
        # Should fall through to the tariff default (high-shoulder)
        assert export_f == OutputField.EXPORT_HIGH_SHOULDER
        assert import_f == OutputField.IMPORT_HIGH_SHOULDER

    def test_current_time_period_weekday_match(self):
        """Line 160: 'Weekdays' in period.days branch."""
        from datetime import datetime
        from unittest.mock import patch as _patch

        from sigenergy2mqtt.common.output_field import OutputField

        config = PvOutputConfig(
            tariffs=[{"plan": "WeekdayPlan", "from-date": "2000-01-01", "to-date": "2099-12-31", "default": "peak", "periods": [{"type": "shoulder", "start": "00:00", "end": "23:59", "days": ["Weekdays"]}]}]
        )

        # Patch datetime.now to return a known Wednesday
        fake_now = datetime(2026, 2, 18, 12, 0, 0)  # Wednesday
        with _patch("sigenergy2mqtt.config.settings.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.min = datetime.min
            mock_dt.max = datetime.max
            export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_SHOULDER
        assert import_f == OutputField.IMPORT_SHOULDER

    def test_current_time_period_weekend_match(self):
        """Line 160: 'Weekends' in period.days branch."""
        from datetime import datetime
        from unittest.mock import patch as _patch

        from sigenergy2mqtt.common.output_field import OutputField

        config = PvOutputConfig(
            tariffs=[{"plan": "WeekendPlan", "from-date": "2000-01-01", "to-date": "2099-12-31", "default": "shoulder", "periods": [{"type": "peak", "start": "00:00", "end": "23:59", "days": ["Weekends"]}]}]
        )

        # Patch datetime.now to return a known Saturday
        fake_now = datetime(2026, 2, 21, 12, 0, 0)  # Saturday
        with _patch("sigenergy2mqtt.config.settings.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.min = datetime.min
            mock_dt.max = datetime.max
            export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_PEAK
        assert import_f == OutputField.IMPORT_PEAK

    # --- _parse_time_periods error paths ---

    def test_parse_time_periods_no_days_defaults_to_all(self):
        """Lines 217-218: period without 'days' key defaults to ['All']."""
        config = PvOutputConfig(
            tariffs=[
                {
                    "plan": "Test",
                    "periods": [
                        {"type": "peak", "start": "06:00", "end": "18:00"},
                    ],
                }
            ]
        )
        assert len(config.tariffs) == 1
        assert config.tariffs[0].periods[0].days == ["All"]

    def test_parse_time_periods_days_not_list(self):
        """Line 216: 'days' present but not a list → ValueError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="must be a list of days"):
            PvOutputConfig(
                tariffs=[
                    {
                        "periods": [
                            {"type": "peak", "start": "06:00", "end": "18:00", "days": "Mon"},
                        ]
                    }
                ]
            )

    def test_parse_time_periods_missing_keys(self):
        """Lines 221: period dict missing required keys → ValueError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="must contain 'type', 'start', and 'end'"):
            PvOutputConfig(
                tariffs=[
                    {
                        "periods": [{"type": "peak"}],
                    }
                ]
            )

    def test_parse_time_periods_non_dict_entry(self):
        """Lines 222-223: non-dict entry in periods list → ValueError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="must be a time period definition"):
            PvOutputConfig(tariffs=[{"periods": ["not-a-dict"]}])

    # --- configure ---

    def test_configure_consumption_false(self):
        """Line 245: consumption=False sets None."""
        config = PvOutputConfig(enabled=True, api_key="abc", system_id="1", consumption=False)
        assert config.consumption is None

    def test_configure_consumption_true(self):
        """Line 247: consumption=True sets CONSUMPTION."""
        config = PvOutputConfig(enabled=True, api_key="abc", system_id="1", consumption=True)
        assert config.consumption == ConsumptionSource.CONSUMPTION

    def test_configure_consumption_net_of_battery(self):
        """Lines 250-251: consumption='net-of-battery'."""
        config = PvOutputConfig(enabled=True, api_key="abc", system_id="1", consumption="net-of-battery")
        assert config.consumption == ConsumptionSource.NET_OF_BATTERY

    def test_configure_consumption_invalid(self):
        """Lines 252-253: invalid consumption value raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="pvoutput.consumption must be"):
            PvOutputConfig(enabled=True, api_key="abc", system_id="1", consumption="garbage")

    def test_configure_log_level(self):
        """Line 261: log-level sets log_level."""
        config = PvOutputConfig(enabled=True, api_key="abc", system_id="1", log_level="DEBUG")
        assert config.log_level == logging.DEBUG

    def test_configure_extended_fields(self):
        """Lines 282-284: v7-v12 extended fields."""
        from sigenergy2mqtt.common.status_field import StatusField

        config = PvOutputConfig(enabled=True, api_key="abc", system_id="1", v7="my/topic/v7")
        assert config.extended[StatusField.V7] == "my/topic/v7"

    def test_configure_time_periods_unknown_key(self):
        """Line 302: unknown key in time-period entry raises ValueError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="contains unknown option 'bogus'"):
            PvOutputConfig(
                enabled=True,
                api_key="abc",
                system_id="1",
                tariffs=[
                    {
                        "bogus": "value",
                        "periods": [{"type": "peak", "start": "06:00", "end": "18:00"}],
                    }
                ],
            )

    def test_configure_time_periods_from_date_to_date(self):
        """Lines 307, 309: from-date and to-date parsing in time-periods."""
        config = PvOutputConfig(
            enabled=True,
            api_key="abc",
            system_id="1",
            tariffs=[
                {
                    "plan": "Seasonal",
                    "from-date": "2026-01-01",
                    "to-date": "2026-12-31",
                    "default": "off-peak",
                    "periods": [{"type": "peak", "start": "06:00", "end": "18:00"}],
                }
            ],
        )
        assert len(config.tariffs) == 1
        from datetime import date as dt_date

        assert config.tariffs[0].from_date == dt_date(2026, 1, 1)
        assert config.tariffs[0].to_date == dt_date(2026, 12, 31)

    def test_configure_time_periods_missing_periods_key(self):
        """Line 322: time-period entry without 'periods' raises ValueError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="must contain a 'periods' element"):
            PvOutputConfig(enabled=True, api_key="abc", system_id="1", tariffs=[{"plan": "NoPeriods"}])
