import pytest

from sigenergy2mqtt.sensors.pid_read_only import PIDAlarm2

def test_decode_alarm_bit():
    alarm = PIDAlarm2(plant_index=1, device_address=1)
    
    assert alarm.decode_alarm_bit(0) == "Grid power loss"
    assert alarm.decode_alarm_bit(1) == "Grid over-voltage"
    assert alarm.decode_alarm_bit(2) == "Grid under-voltage"
    assert alarm.decode_alarm_bit(3) == "Grid over-frequency"
    assert alarm.decode_alarm_bit(4) == "Grid under-frequency"

def test_decode_alarm_bit_out_of_range():
    alarm = PIDAlarm2(plant_index=1, device_address=1)
    
    assert alarm.decode_alarm_bit(5) is None
    assert alarm.decode_alarm_bit(6) is None
    assert alarm.decode_alarm_bit(7) is None
    assert alarm.decode_alarm_bit(8) is None
    assert alarm.decode_alarm_bit(9) is None
    assert alarm.decode_alarm_bit(10) is None
    assert alarm.decode_alarm_bit(11) is None
    assert alarm.decode_alarm_bit(12) is None
    assert alarm.decode_alarm_bit(13) is None
    assert alarm.decode_alarm_bit(14) is None
    assert alarm.decode_alarm_bit(15) is None
