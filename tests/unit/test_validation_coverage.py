import logging

import pytest

from sigenergy2mqtt.config import validation


def test_is_valid_hostname_extra():
    assert validation.is_valid_hostname("a" * 256) is False
    assert validation.is_valid_hostname("host.") is True  # trailing dot is handled


def test_check_float_extra():
    # allow_none branch
    assert validation.check_float(None, "src", allow_none=True) is None
    # min/max branches for string input
    assert validation.check_float("10.5", "src", min=10.0) == 10.5
    with pytest.raises(ValueError, match="greater than or equal to 10.0"):
        validation.check_float("9.5", "src", min=10.0)
    assert validation.check_float("10.5", "src", max=11.0) == 10.5
    with pytest.raises(ValueError, match="less than or equal to 11.0"):
        validation.check_float("11.5", "src", max=11.0)
    # float input branches
    assert validation.check_float(10.5, "src", min=10.0) == 10.5
    with pytest.raises(ValueError, match="greater than or equal to 10.0"):
        validation.check_float(9.5, "src", min=10.0)
    # Invalid type
    with pytest.raises(ValueError, match="must be a float"):
        validation.check_float([], "src")  # pyrefly: ignore


def test_check_host_extra():
    with pytest.raises(ValueError, match="not appear to be a valid IP address or hostname"):
        validation.check_host("!!!", "src")


def test_check_int_extra():
    # allow_none branch
    assert validation.check_int(None, "src", allow_none=True) is None
    with pytest.raises(ValueError, match="not null"):
        validation.check_int(None, "src", allow_none=False)
    # allowed branch
    assert validation.check_int(123, "src", allowed=123) == 123
    # min/max branch for int
    with pytest.raises(ValueError, match="greater than or equal to 10"):
        validation.check_int(9, "src", min=10)
    with pytest.raises(ValueError, match="less than or equal to 11"):
        validation.check_int(12, "src", max=11)
    # error if not int (though it uses int(value) mostly)
    # If int() conversion succeeds but it's not and... wait line 103 seems unreachable if int() succeeds
    # result = value if isinstance(value, int) else int(value)
    # if isinstance(result, int): ... else: raise ValueError (line 103)


def test_check_int_list_extra():
    assert validation.check_int_list(None, "src") == []
    with pytest.raises(ValueError, match="list of integers"):
        validation.check_int_list(["a"], "src")  # pyrefly: ignore


def test_check_log_level_extra():
    assert validation.check_log_level("WARNING", "src") == logging.WARNING
    assert validation.check_log_level("ERROR", "src") == logging.ERROR
    assert validation.check_log_level("CRITICAL", "src") == logging.CRITICAL
    with pytest.raises(ValueError, match="must be one of"):
        validation.check_log_level("UNKNOWN", "src")


def test_check_module_extra():
    from unittest.mock import MagicMock, patch

    with patch("importlib.import_module") as mock_import:
        # Valid module
        mock_mod = MagicMock()
        mock_mod.SmartPort = True
        mock_import.return_value = mock_mod
        assert validation.check_module("enphase", "src") == "enphase"

        # Module without SmartPort
        del mock_mod.SmartPort
        with pytest.raises(ValueError, match="must be a valid module that contains a SmartPort class"):
            validation.check_module("nomod", "src")

        mock_import.side_effect = ImportError("import error")
        with pytest.raises(ValueError, match="must be a valid module"):
            validation.check_module("error", "src")


def test_check_port_extra():
    # coverage for line 159 (which is probably unreachable if check_int works correctly)
    from unittest.mock import patch

    with patch("sigenergy2mqtt.config.validation.check_int", return_value="not-an-int"):
        with pytest.raises(ValueError, match="must be a port number"):
            validation.check_port(80, "src")


def test_check_string_extra():
    # allow_none=False
    with pytest.raises(ValueError, match="not null"):
        validation.check_string(None, "src", allow_none=False)
    # allow_empty=False
    with pytest.raises(ValueError, match="not empty"):
        validation.check_string("", "src", allow_empty=False)
    # hex_chars_only
    assert validation.check_string("abc", "src", hex_chars_only=True) == "abc"
    with pytest.raises(ValueError, match="hexadecimal characters"):
        validation.check_string("xyz", "src", hex_chars_only=True)
    # starts_with
    assert validation.check_string("prefix_val", "src", starts_with="prefix") == "prefix_val"
    with pytest.raises(ValueError, match="must start with 'prefix"):
        validation.check_string("val", "src", starts_with="prefix")
    # Invalid type
    with pytest.raises(ValueError, match="must be a valid string"):
        validation.check_string([], "src")


def test_check_string_list_extra():
    # Test None
    assert validation.check_string_list(None, "src") == []

    # Test string input with comma separation and whitespace
    assert validation.check_string_list("item1, item2,  item3 ", "src") == ["item1", "item2", "item3"]

    # Test list input
    assert validation.check_string_list(["val1", "val2"], "src") == ["val1", "val2"]

    # Test empty list
    assert validation.check_string_list([], "src") == []

    # Test invalid list content
    with pytest.raises(ValueError, match="list of strings separated by commas"):
        validation.check_string_list(["valid", 123], "src")  # pyrefly: ignore
