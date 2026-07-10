from datetime import date, time
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import RegisterAccess
from sigenergy2mqtt.config import Settings, active_config, validation
from sigenergy2mqtt.config.models import ModbusConfig


class TestConfigValidation:
    def setup_method(self):
        # Reset active_config state before each test
        active_config.reset()

    def test_ems_mode_check_enabled_validates(self):
        """Test validation passes when ems_mode_check is enabled (default)."""
        device = ModbusConfig(host="1", registers=RegisterAccess())
        # Should not raise
        settings = Settings(ems_mode_check=True, modbus=[device])
        settings.finalize_modbus([])

    def test_ems_mode_check_disabled_valid_config(self):
        """Test validation passes when ems_mode_check is disabled and config is correct."""
        # valid configuration: no_remote_ems=False, read_write=True
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=True))
        # Should not raise
        settings = Settings(ems_mode_check=False, modbus=[device])
        settings.finalize_modbus([])

    def test_ems_mode_check_disabled_invalid_no_remote_ems(self):
        """Test validation fails when ems_mode_check is disabled and no_remote_ems is True."""
        # invalid: no_remote_ems=True
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=True, read_write=True))

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, no_remote_ems must be False"):
            settings = Settings(ems_mode_check=False, modbus=[device])
            settings.finalize_modbus([])

    def test_ems_mode_check_disabled_invalid_read_write(self):
        """Test validation fails when ems_mode_check is disabled and read_write is False."""
        # invalid: read_write=False
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=False))

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, read_write must be True"):
            settings = Settings(ems_mode_check=False, modbus=[device])
            settings.finalize_modbus([])

    def test_ems_mode_check_disabled_multiple_devices_one_invalid(self):
        """Test validation fails if any device is invalid."""
        device1 = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=True))
        device2 = ModbusConfig(host="2", registers=RegisterAccess(no_remote_ems=True, read_write=True))  # Invalid

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, no_remote_ems must be False"):
            settings = Settings(ems_mode_check=False, modbus=[device1, device2])
            settings.finalize_modbus([])

    def test_check_bool(self):
        assert validation.check_bool(True, "test") is True
        assert validation.check_bool(False, "test") is False
        assert validation.check_bool("true", "test") is True
        assert validation.check_bool("False", "test") is False
        assert validation.check_bool("1", "test") is True
        assert validation.check_bool("0", "test") is False
        with pytest.raises(ValueError):
            validation.check_bool("invalid", "test")

    def test_check_int(self):
        assert validation.check_int(10, "test") == 10
        assert validation.check_int("10", "test") == 10
        assert validation.check_int(5, "test", min=0, max=10) == 5
        with pytest.raises(ValueError):
            validation.check_int("invalid", "test")
        with pytest.raises(ValueError):
            validation.check_int(11, "test", max=10)
        with pytest.raises(ValueError):
            validation.check_int(-1, "test", min=0)

    def test_check_float(self):
        assert validation.check_float(10.5, "test") == 10.5
        assert validation.check_float("10.5", "test") == 10.5
        assert validation.check_float(None, "test", allow_none=True) is None
        with pytest.raises(ValueError, match="must be a float and not null"):
            validation.check_float(None, "test")
        with pytest.raises(ValueError):
            validation.check_float("invalid", "test")
        with pytest.raises(ValueError):
            validation.check_float(10.5, "test", max=10.0)

    def test_check_string(self):
        assert validation.check_string("test", "test") == "test"
        assert validation.check_string(None, "test", allow_none=True) is None
        with pytest.raises(ValueError):
            validation.check_string(None, "test", allow_none=False)
        with pytest.raises(ValueError):
            validation.check_string("", "test", allow_empty=False)
        with pytest.raises(ValueError):
            validation.check_string("abc", "test", "def", "ghi")  # "abc" not in valid values

    def test_check_date(self):
        d = date(2023, 1, 1)
        assert validation.check_date(d, "test") == d
        assert validation.check_date("2023-01-01", "test") == d
        with pytest.raises(ValueError):
            validation.check_date("invalid", "test")

    def test_check_time(self):
        t = time(12, 0)
        assert validation.check_time(t, "test") == t
        assert validation.check_time("12:00", "test") == t
        assert validation.check_time("24:00", "test") == time(23, 59, 59, 999999)
        with pytest.raises(ValueError):
            validation.check_time("invalid", "test")

    def test_settings_handle_negated_flags_not_dict(self):
        assert Settings.handle_negated_flags(["not a dict"]) == ["not a dict"]

    def test_settings_validate_consumption_invalid(self):
        with pytest.raises(ValueError, match="consumption must be one of"):
            Settings.validate_consumption("invalid_consumption")

    def test_settings_invert_no_ems_mode_check_bool(self):
        assert Settings.invert_no_ems_mode_check(True) is True
        assert Settings.invert_no_ems_mode_check(False) is False

    def test_settings_invert_no_metrics_bool(self):
        assert Settings.invert_no_metrics(True) is True
        assert Settings.invert_no_metrics(False) is False

    def test_settings_validate_networks_str_and_invalid(self):
        assert Settings.validate_networks("192.168.1.0/24, 10.0.0.0/8") == ["192.168.1.0/24", "10.0.0.0/8"]
        with pytest.raises(ValueError, match="Invalid IPv4 CIDR network"):
            Settings.validate_networks(["invalid_network"])

    def test_settings_validate_excludes_str_and_invalid(self):
        assert Settings.validate_excludes("PID, PSS") == ["PID", "PSS"]
        with pytest.raises(ValueError, match="Invalid Device class name"):
            Settings.validate_excludes(["InvalidClass"])

    def test_settings_validate_max_device_id_str_invalid(self):
        with pytest.raises(ValueError, match="modbus-auto-discovery-max-device-id must be a positive integer"):
            Settings.validate_max_device_id("invalid_int")

    @patch("sigenergy2mqtt.config.settings.datetime")
    def test_pvoutput_current_time_period_debug_logging(self, mock_datetime):
        import logging
        from datetime import datetime as dt

        from sigenergy2mqtt.config.models import PvOutputConfig

        mock_dt = dt(2023, 1, 2, 12, 0)  # Monday
        mock_datetime.now.return_value = mock_dt

        # Test branch where time matches
        pv_config1 = PvOutputConfig(
            log_level=logging.DEBUG, calc_debug_logging=True, tariffs=[{"plan": "test_plan", "periods": [{"days": ["All"], "start": "10:00", "end": "14:00", "type": "peak"}], "default": "shoulder"}]
        )
        export1, import1 = pv_config1.current_time_period

        # Test branch where time doesn't match
        pv_config2 = PvOutputConfig(
            log_level=logging.DEBUG, calc_debug_logging=True, tariffs=[{"plan": "test_plan", "periods": [{"days": ["All"], "start": "14:00", "end": "16:00", "type": "peak"}], "default": "shoulder"}]
        )
        export2, import2 = pv_config2.current_time_period
