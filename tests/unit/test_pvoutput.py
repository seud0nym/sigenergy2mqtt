import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.config import ConsumptionSource, StatusField, VoltageSource, active_config
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

    # --- _type_to_output_fields: lines 138-145 ---

    def test_type_to_output_fields_shoulder(self):
        """Lines 138-140: TariffType.SHOULDER branch."""
        from sigenergy2mqtt.config.pvoutput_config import OutputField, TariffType

        config = PVOutputConfiguration()
        export_f, import_f = config._type_to_output_fields(TariffType.SHOULDER)
        assert export_f == OutputField.EXPORT_SHOULDER
        assert import_f == OutputField.IMPORT_SHOULDER

    def test_type_to_output_fields_high_shoulder(self):
        """Lines 141-143: TariffType.HIGH_SHOULDER branch."""
        from sigenergy2mqtt.config.pvoutput_config import OutputField, TariffType

        config = PVOutputConfiguration()
        export_f, import_f = config._type_to_output_fields(TariffType.HIGH_SHOULDER)
        assert export_f == OutputField.EXPORT_HIGH_SHOULDER
        assert import_f == OutputField.IMPORT_HIGH_SHOULDER

    def test_type_to_output_fields_invalid(self):
        """Lines 144-145: invalid type raises ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="Invalid tariff type"):
            config._type_to_output_fields("bogus")

    # --- current_time_period: lines 153-169 ---

    def test_current_time_period_matches_period(self):
        """Lines 153-165: tariff date+time match with debug logging."""
        from datetime import date as dt_date
        from datetime import datetime
        from datetime import time as dt_time

        from sigenergy2mqtt.config.pvoutput_config import (
            OutputField,
            Tariff,
            TariffType,
            TimePeriod,
        )

        config = PVOutputConfiguration()
        config.calc_debug_logging = True
        # Create a period that covers the entire day with "All" days
        period = TimePeriod(
            type=TariffType.OFF_PEAK,
            start=dt_time(0, 0),
            end=dt_time(23, 59, 59),
            days=["All"],
        )
        tariff = Tariff(
            plan="TestPlan",
            from_date=dt_date(2000, 1, 1),
            to_date=dt_date(2099, 12, 31),
            default=TariffType.PEAK,
            periods=[period],
        )
        config.tariffs = [tariff]
        export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_OFF_PEAK
        assert import_f == OutputField.IMPORT_OFF_PEAK

    def test_current_time_period_default_fallback(self):
        """Lines 166-169: date matches but no time period matches → default."""
        from datetime import date as dt_date
        from datetime import time as dt_time

        from sigenergy2mqtt.config.pvoutput_config import (
            OutputField,
            Tariff,
            TariffType,
            TimePeriod,
        )

        config = PVOutputConfiguration()
        config.calc_debug_logging = True
        # Period with impossible time window (just midnight for 1 second-ish)
        period = TimePeriod(
            type=TariffType.OFF_PEAK,
            start=dt_time(0, 0, 0),
            end=dt_time(0, 0, 1),
            days=["InvalidDayName"],  # will never match any real day-of-week
        )
        tariff = Tariff(
            plan="DefaultTest",
            from_date=dt_date(2000, 1, 1),
            to_date=dt_date(2099, 12, 31),
            default=TariffType.HIGH_SHOULDER,
            periods=[period],
        )
        config.tariffs = [tariff]
        export_f, import_f = config.current_time_period
        # Should fall through to the tariff default (high-shoulder)
        assert export_f == OutputField.EXPORT_HIGH_SHOULDER
        assert import_f == OutputField.IMPORT_HIGH_SHOULDER

    def test_current_time_period_weekday_match(self):
        """Line 160: 'Weekdays' in period.days branch."""
        from datetime import date as dt_date
        from datetime import datetime
        from datetime import time as dt_time
        from unittest.mock import patch as _patch

        from sigenergy2mqtt.config.pvoutput_config import (
            OutputField,
            Tariff,
            TariffType,
            TimePeriod,
        )

        config = PVOutputConfiguration()
        period = TimePeriod(
            type=TariffType.SHOULDER,
            start=dt_time(0, 0),
            end=dt_time(23, 59, 59),
            days=["Weekdays"],
        )
        tariff = Tariff(
            plan="WeekdayPlan",
            from_date=dt_date(2000, 1, 1),
            to_date=dt_date(2099, 12, 31),
            default=TariffType.PEAK,
            periods=[period],
        )
        config.tariffs = [tariff]
        # Patch datetime.now to return a known Wednesday
        fake_now = datetime(2026, 2, 18, 12, 0, 0)  # Wednesday
        with _patch("sigenergy2mqtt.config.pvoutput_config.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.min = datetime.min
            mock_dt.max = datetime.max
            export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_SHOULDER
        assert import_f == OutputField.IMPORT_SHOULDER

    def test_current_time_period_weekend_match(self):
        """Line 160: 'Weekends' in period.days branch."""
        from datetime import date as dt_date
        from datetime import datetime
        from datetime import time as dt_time
        from unittest.mock import patch as _patch

        from sigenergy2mqtt.config.pvoutput_config import (
            OutputField,
            Tariff,
            TariffType,
            TimePeriod,
        )

        config = PVOutputConfiguration()
        period = TimePeriod(
            type=TariffType.PEAK,
            start=dt_time(0, 0),
            end=dt_time(23, 59, 59),
            days=["Weekends"],
        )
        tariff = Tariff(
            plan="WeekendPlan",
            from_date=dt_date(2000, 1, 1),
            to_date=dt_date(2099, 12, 31),
            default=TariffType.SHOULDER,
            periods=[period],
        )
        config.tariffs = [tariff]
        # Patch datetime.now to return a known Saturday
        fake_now = datetime(2026, 2, 21, 12, 0, 0)  # Saturday
        with _patch("sigenergy2mqtt.config.pvoutput_config.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.min = datetime.min
            mock_dt.max = datetime.max
            export_f, import_f = config.current_time_period
        assert export_f == OutputField.EXPORT_PEAK
        assert import_f == OutputField.IMPORT_PEAK

    # --- _parse_time_periods error paths: lines 216-218, 221-223, 227 ---

    def test_parse_time_periods_no_days_defaults_to_all(self):
        """Lines 217-218: period without 'days' key defaults to ['All']."""
        config = PVOutputConfiguration()
        periods = config._parse_time_periods(
            [
                {"type": "peak", "start": "06:00", "end": "18:00"},
            ]
        )
        assert len(periods) == 1
        assert periods[0].days == ["All"]

    def test_parse_time_periods_days_not_list(self):
        """Line 216: 'days' present but not a list → ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="must be a list of days"):
            config._parse_time_periods(
                [
                    {"type": "peak", "start": "06:00", "end": "18:00", "days": "Mon"},
                ]
            )

    def test_parse_time_periods_missing_keys(self):
        """Lines 221: period dict missing required keys → ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="must contain 'type', 'start', and 'end'"):
            config._parse_time_periods([{"type": "peak"}])

    def test_parse_time_periods_non_dict_entry(self):
        """Lines 222-223: non-dict entry in periods list → ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="must be a time period definition"):
            config._parse_time_periods(["not-a-dict"])

    def test_parse_time_periods_non_list_input(self):
        """Line 227: non-list input → ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="must contain a list of time period definitions"):
            config._parse_time_periods("not-a-list")

    # --- configure: lines 245, 247, 250-253, 261, 282-284, 302, 307, 309, 322, 329-331 ---

    def test_configure_consumption_false(self):
        """Line 245: consumption=False sets None."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure({"enabled": True, "consumption": False})
        assert config.consumption is None

    def test_configure_consumption_true(self):
        """Line 247: consumption=True sets CONSUMPTION."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure({"enabled": True, "consumption": True})
        assert config.consumption == ConsumptionSource.CONSUMPTION

    def test_configure_consumption_net_of_battery(self):
        """Lines 250-251: consumption='net-of-battery'."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure({"enabled": True, "consumption": "net-of-battery"})
        assert config.consumption == ConsumptionSource.NET_OF_BATTERY

    def test_configure_consumption_invalid(self):
        """Lines 252-253: invalid consumption value raises ValueError."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        with pytest.raises(ValueError, match="pvoutput.consumption must be"):
            config.configure({"enabled": True, "consumption": "garbage"})

    def test_configure_log_level(self):
        """Line 261: log-level sets log_level."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure({"enabled": True, "log-level": "DEBUG"})
        assert config.log_level == logging.DEBUG

    def test_configure_extended_fields(self):
        """Lines 282-284: v7-v12 extended fields."""
        from sigenergy2mqtt.config.pvoutput_config import StatusField

        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure({"enabled": True, "v7": "my/topic/v7"})
        assert config.extended[StatusField.V7] == "my/topic/v7"

    def test_configure_time_periods_unknown_key(self):
        """Line 302: unknown key in time-period entry raises ValueError."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        with pytest.raises(ValueError, match="contains unknown option 'bogus'"):
            config.configure(
                {
                    "enabled": True,
                    "time-periods": [
                        {
                            "bogus": "value",
                            "periods": [{"type": "peak", "start": "06:00", "end": "18:00"}],
                        }
                    ],
                }
            )

    def test_configure_time_periods_from_date_to_date(self):
        """Lines 307, 309: from-date and to-date parsing in time-periods."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        config.configure(
            {
                "enabled": True,
                "time-periods": [
                    {
                        "plan": "Seasonal",
                        "from-date": "2026-01-01",
                        "to-date": "2026-12-31",
                        "default": "off-peak",
                        "periods": [{"type": "peak", "start": "06:00", "end": "18:00"}],
                    }
                ],
            }
        )
        assert len(config.tariffs) == 1
        from datetime import date as dt_date

        assert config.tariffs[0].from_date == dt_date(2026, 1, 1)
        assert config.tariffs[0].to_date == dt_date(2026, 12, 31)

    def test_configure_time_periods_missing_periods_key(self):
        """Line 322: time-period entry without 'periods' raises ValueError."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        with pytest.raises(ValueError, match="must contain a 'periods' element"):
            config.configure(
                {
                    "enabled": True,
                    "time-periods": [{"plan": "NoPeriods"}],
                }
            )

    def test_configure_unknown_option(self):
        """Lines 329: unknown config field raises ValueError."""
        config = PVOutputConfiguration(enabled=True, api_key="abc", system_id="1")
        with pytest.raises(ValueError, match="unknown option 'not-a-field'"):
            config.configure({"enabled": True, "not-a-field": "value"})

    def test_configure_non_dict(self):
        """Lines 330-331: non-dict config raises ValueError."""
        config = PVOutputConfiguration()
        with pytest.raises(ValueError, match="must contain options and their values"):
            config.configure("not-a-dict")
