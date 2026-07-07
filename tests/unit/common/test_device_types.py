from sigenergy2mqtt.common.types import NonInverter


def test_non_inverter_string_is_empty():
    assert str(NonInverter()) == ""
