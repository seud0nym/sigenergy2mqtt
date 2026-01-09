import pytest

from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.const import StateClass
from sigenergy2mqtt.sensors.sanity_check import SanityCheck


class TestSanityCheck:

    def test_init_default(self):
        sc = SanityCheck()
        sc.init(unit="W", state_class=None, data_type=ModbusClient.DATATYPE.UINT16)
        assert sc.min_raw == 0
        assert sc.max_raw is not None  # Should be set based on UINT16
        assert sc.delta is False

    def test_init_delta(self):
        sc = SanityCheck()
        sc.init(unit="kWh", state_class=StateClass.TOTAL_INCREASING, data_type=ModbusClient.DATATYPE.UINT32)
        assert sc.delta is True
        assert sc.min_raw == 0

    def test_check_value_in_range(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=False)
        assert sc.check(50, []) is True

    def test_check_value_out_of_range(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=False)
        with pytest.raises(ValueError):
            sc.check(150, [])
        with pytest.raises(ValueError):
            sc.check(-1, [])

    def test_check_delta_valid(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=True)
        # Previous state: 100, Current state: 110. Delta = 10. Valid.
        # Note: previous_states is list[tuple[timestamp, value]]
        assert sc.check(110, [(0, 100)]) is True

    def test_check_delta_invalid(self):
        sc = SanityCheck(min_raw=0, max_raw=10, delta=True)
        # Previous state: 100, Current state: 120. Delta = 20. Invalid.
        with pytest.raises(ValueError):
            sc.check(120, [(0, 100)])

    def test_check_no_previous_state_delta(self):
        sc = SanityCheck(min_raw=0, max_raw=100, delta=True)
        assert sc.check(100, []) is True
