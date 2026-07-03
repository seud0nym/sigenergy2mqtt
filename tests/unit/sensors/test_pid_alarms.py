from sigenergy2mqtt.sensors.pid_read_only import PIDAlarm1, PIDAlarm2


def test_decode_alarm_bit():
    alarm = PIDAlarm1(plant_index=1, device_address=1)

    assert alarm.decode_alarm_bit(0) == "Software version mismatch"
    assert alarm.decode_alarm_bit(1) == "Software and hardware version mismatch"
    assert alarm.decode_alarm_bit(2) == "Startup failure"
    assert alarm.decode_alarm_bit(3) == "Insulation resistance alarm"
    assert alarm.decode_alarm_bit(4) == "Insulation resistance pre-alarm"
    assert alarm.decode_alarm_bit(5) == "Over-temperature"
    assert alarm.decode_alarm_bit(6) == "Power module abnormal"
    assert alarm.decode_alarm_bit(7) == "Fan fault"
    assert alarm.decode_alarm_bit(8) == "Reserved"
    assert alarm.decode_alarm_bit(9) == "Inverter bus over-voltage protection"
    assert alarm.decode_alarm_bit(10) == "Output over-voltage protection"
    assert alarm.decode_alarm_bit(11) == "Inverter output over-voltage protection"
    assert alarm.decode_alarm_bit(12) == "Inverter output over-current protection"
    assert alarm.decode_alarm_bit(13) == "Output over-current protection"
    assert alarm.decode_alarm_bit(14) == "Output failure"
    assert alarm.decode_alarm_bit(15) == "Rs485 communication abnormal"

    alarm = PIDAlarm2(plant_index=1, device_address=1)

    assert alarm.decode_alarm_bit(0) == "Grid power loss"
    assert alarm.decode_alarm_bit(1) == "Grid over-voltage"
    assert alarm.decode_alarm_bit(2) == "Grid under-voltage"
    assert alarm.decode_alarm_bit(3) == "Grid over-frequency"
    assert alarm.decode_alarm_bit(4) == "Grid under-frequency"


def test_decode_alarm_bit_negative():
    alarm = PIDAlarm1(plant_index=1, device_address=1)

    assert alarm.decode_alarm_bit(-1) is None
    assert alarm.decode_alarm_bit(-2) is None
    assert alarm.decode_alarm_bit(-3) is None
    assert alarm.decode_alarm_bit(-4) is None
    assert alarm.decode_alarm_bit(-5) is None
    assert alarm.decode_alarm_bit(-6) is None
    assert alarm.decode_alarm_bit(-7) is None
    assert alarm.decode_alarm_bit(-8) is None
    assert alarm.decode_alarm_bit(-9) is None
    assert alarm.decode_alarm_bit(-10) is None
    assert alarm.decode_alarm_bit(-11) is None
    assert alarm.decode_alarm_bit(-12) is None
    assert alarm.decode_alarm_bit(-13) is None
    assert alarm.decode_alarm_bit(-14) is None
    assert alarm.decode_alarm_bit(-15) is None


def test_decode_alarm_bit_large():
    alarm = PIDAlarm1(plant_index=1, device_address=1)

    assert alarm.decode_alarm_bit(16) is None
    assert alarm.decode_alarm_bit(17) is None
    assert alarm.decode_alarm_bit(18) is None
    assert alarm.decode_alarm_bit(19) is None
    assert alarm.decode_alarm_bit(20) is None
    assert alarm.decode_alarm_bit(21) is None
    assert alarm.decode_alarm_bit(22) is None
    assert alarm.decode_alarm_bit(23) is None
    assert alarm.decode_alarm_bit(24) is None
    assert alarm.decode_alarm_bit(25) is None
    assert alarm.decode_alarm_bit(26) is None
    assert alarm.decode_alarm_bit(27) is None
    assert alarm.decode_alarm_bit(28) is None
    assert alarm.decode_alarm_bit(29) is None
    assert alarm.decode_alarm_bit(30) is None


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
