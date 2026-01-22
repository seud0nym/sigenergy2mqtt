import pytest

from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.const import StateClass
from sigenergy2mqtt.sensors.sanity_check import SanityCheck, SanityCheckException


class TestSanityCheck:
    def test_init_default(self):
        sc = SanityCheck(unit="W", state_class=None, data_type=ModbusClient.DATATYPE.UINT16)
        assert sc.min_raw == 0
        assert sc.max_raw is not None  # Should be set based on UINT16
        assert sc.delta is False

    def test_init_delta(self):
        sc = SanityCheck(unit="kWh", state_class=StateClass.TOTAL_INCREASING, data_type=ModbusClient.DATATYPE.UINT32)
        assert sc.delta is True
        assert sc.min_raw == 0

    def test_init_energy_device_class(self):
        from sigenergy2mqtt.sensors.const import DeviceClass

        sc = SanityCheck(unit="kWh", state_class=None, data_type=ModbusClient.DATATYPE.UINT32, device_class=DeviceClass.ENERGY)
        assert sc.delta is True
        assert sc.min_raw == 0

    def test_check_value_in_range(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=False)
        assert sc.is_sane(50, []) is True

    def test_check_value_out_of_range(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=False)
        with pytest.raises(SanityCheckException):
            sc.is_sane(150, [])
        with pytest.raises(SanityCheckException):
            sc.is_sane(-1, [])

    def test_check_delta_valid(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=True)
        # Previous state: 100, Current state: 110. Delta = 10. Valid.
        # Note: previous_states is list[tuple[timestamp, value]]
        assert sc.is_sane(110, [(0, 100)]) is True

    def test_check_delta_invalid(self):
        sc = SanityCheck(min_raw=0, max_raw=10, delta=True)
        # Previous state: 100, Current state: 120. Delta = 20. Invalid.
        with pytest.raises(SanityCheckException):
            sc.is_sane(120, [(0, 100)])

    def test_init_all_datatypes(self):
        from sigenergy2mqtt.modbus.types import ModbusDataType

        # Note: SanityCheck.min_raw is capped at max_raw * -1 for signed types
        assert SanityCheck(data_type=ModbusDataType.INT16).min_raw == -32767
        assert SanityCheck(data_type=ModbusDataType.INT16).max_raw == 32767

        sc = SanityCheck(data_type=ModbusDataType.INT32)
        assert sc.min_raw == -2147483647
        assert sc.max_raw == 2147483647

        sc = SanityCheck(data_type=ModbusDataType.UINT32)
        assert sc.min_raw == 0
        assert sc.max_raw == 4294967295

        sc = SanityCheck(data_type=ModbusDataType.INT64)
        assert sc.min_raw == -9223372036854775807
        assert sc.max_raw == 9223372036854775807

        sc = SanityCheck(data_type=ModbusDataType.UINT64)
        assert sc.min_raw == 0
        assert sc.max_raw == 18446744073709551615

    def test_init_percentage(self):
        from sigenergy2mqtt.sensors.const import PERCENTAGE

        sc = SanityCheck(unit=PERCENTAGE, gain=10)
        assert sc.max_raw == 1000

    def test_repr(self):
        from sigenergy2mqtt.sensors.const import PERCENTAGE

        sc = SanityCheck(min_raw=0, max_raw=100, unit=PERCENTAGE)
        r = repr(sc)
        assert "between 0 % and 100 %" in r

        sc = SanityCheck()
        assert repr(sc) == "Disabled"

        # Delta repr
        sc = SanityCheck(min_raw=0, max_raw=10, delta=True, unit="V")
        r = repr(sc)
        assert "delta of the value" in r
        assert "between 0 V and 10 V" in r

        # Only max
        sc = SanityCheck(max_raw=100)
        r = repr(sc)
        assert "maximum of 100" in r

        # Only min
        sc = SanityCheck(min_raw=10)
        r = repr(sc)
        assert "minimum of 10" in r

    def test_raw2value(self):
        sc = SanityCheck(gain=10, precision=2, unit="A")
        assert sc._raw2value(123) == "12.3 A"

        sc = SanityCheck(gain=1, precision=0, unit="X")
        assert sc._raw2value(123.6) == "124 X"

        assert sc._raw2value(None) is None

    def test_is_enabled(self):
        assert SanityCheck(min_raw=0).is_enabled is True
        assert SanityCheck(max_raw=100).is_enabled is True
        assert SanityCheck().is_enabled is False

    def test_is_sane_only_min_max(self):
        # Only max
        sc = SanityCheck(max_raw=100)
        assert sc.is_sane(50, []) is True
        with pytest.raises(SanityCheckException):
            sc.is_sane(150, [])

        # Only min
        sc = SanityCheck(min_raw=0)
        assert sc.is_sane(50, []) is True
        with pytest.raises(SanityCheckException):
            sc.is_sane(-50, [])

    def test_is_sane_delta_no_numeric_previous(self):
        sc = SanityCheck(delta=True, max_raw=10)
        # Previous state is a string
        assert sc.is_sane(100, [(0, "unknown")]) is True
