from datetime import date, time

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
        Settings(ems_mode_check=True, modbus=[device])

    def test_ems_mode_check_disabled_valid_config(self):
        """Test validation passes when ems_mode_check is disabled and config is correct."""
        # valid configuration: no_remote_ems=False, read_write=True
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=True))
        # Should not raise
        Settings(ems_mode_check=False, modbus=[device])

    def test_ems_mode_check_disabled_invalid_no_remote_ems(self):
        """Test validation fails when ems_mode_check is disabled and no_remote_ems is True."""
        # invalid: no_remote_ems=True
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=True, read_write=True))

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, no_remote_ems must be False"):
            Settings(ems_mode_check=False, modbus=[device])

    def test_ems_mode_check_disabled_invalid_read_write(self):
        """Test validation fails when ems_mode_check is disabled and read_write is False."""
        # invalid: read_write=False
        device = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=False))

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, read_write must be True"):
            Settings(ems_mode_check=False, modbus=[device])

    def test_ems_mode_check_disabled_multiple_devices_one_invalid(self):
        """Test validation fails if any device is invalid."""
        device1 = ModbusConfig(host="1", registers=RegisterAccess(no_remote_ems=False, read_write=True))
        device2 = ModbusConfig(host="2", registers=RegisterAccess(no_remote_ems=True, read_write=True))  # Invalid

        with pytest.raises(ValueError, match="When ems_mode_check is disabled, no_remote_ems must be False"):
            Settings(ems_mode_check=False, modbus=[device1, device2])

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
