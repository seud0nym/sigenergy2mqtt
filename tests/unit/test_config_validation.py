import logging
from datetime import date, time

import pytest

from sigenergy2mqtt.config import validation


class TestConfigValidation:
    def test_is_valid_ipv4(self):
        assert validation.is_valid_ipv4("192.168.1.1") is True
        assert validation.is_valid_ipv4("10.0.0.1") is True
        assert validation.is_valid_ipv4("256.0.0.1") is False
        assert validation.is_valid_ipv4("invalid") is False

    def test_is_valid_ipv6(self):
        assert validation.is_valid_ipv6("::1") is True
        assert validation.is_valid_ipv6("2001:db8::1") is True
        assert validation.is_valid_ipv6("invalid") is False

    def test_is_valid_hostname(self):
        assert validation.is_valid_hostname("localhost") is True
        assert validation.is_valid_hostname("example.com") is True
        assert validation.is_valid_hostname("-invalid") is False
        assert validation.is_valid_hostname("invalid-") is False

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

    def test_check_log_level(self):
        assert validation.check_log_level("DEBUG", "test") == logging.DEBUG
        assert validation.check_log_level("INFO", "test") == logging.INFO
        assert validation.check_log_level(logging.WARNING, "test") == logging.WARNING
        with pytest.raises(ValueError):
            validation.check_log_level("INVALID", "test")

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
