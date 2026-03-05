import pytest

from sigenergy2mqtt.config import validation


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
