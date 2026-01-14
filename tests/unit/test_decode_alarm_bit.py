import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock circular dependencies before importing sensors
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

ENTITY_PREFIX = "sigenergy"


@pytest.fixture(autouse=True)
def setup_configs():
    with patch("sigenergy2mqtt.sensors.base.Config") as m1, patch("sigenergy2mqtt.sensors.ac_charger_read_only.Config") as m2, patch("sigenergy2mqtt.sensors.plant_read_only.Config") as m3:
        for m in [m1, m2, m3]:
            m.home_assistant.unique_id_prefix = "sigenergy"
            m.home_assistant.entity_id_prefix = ENTITY_PREFIX
            m.sensor_overrides = {}

            mock_device = MagicMock()
            mock_device.scan_interval.realtime = 5
            m.devices = [mock_device]

        yield


from sigenergy2mqtt.common import Protocol  # noqa: E402
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerAlarm1, ACChargerAlarm2, ACChargerAlarm3  # noqa: E402
from sigenergy2mqtt.sensors.base import Alarm1Sensor, Alarm2Sensor, Alarm3Sensor, Alarm4Sensor, Alarm5Sensor, Sensor  # noqa: E402
from sigenergy2mqtt.sensors.plant_read_only import Alarm6, Alarm7  # noqa: E402


@pytest.fixture(autouse=True)
def clear_sensor_registries():
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()
    yield
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


@pytest.mark.parametrize(
    "sensor_class,bit,expected",
    [
        (Alarm1Sensor, 0, "1001: Software version mismatch"),
        (Alarm1Sensor, 15, "1016: DC component of output current out of limit"),
        (Alarm2Sensor, 0, "1017: Leak current out of limit"),
        (Alarm2Sensor, 9, "1026: Soft start failure"),
        (Alarm3Sensor, 0, "2001: Software version mismatch"),
        (Alarm3Sensor, 6, "2009: Thermal runaway"),
        (Alarm4Sensor, 0, "3001: Software version mismatch"),
        (Alarm5Sensor, 0, "5101: Software version mismatch"),
    ],
)
def test_base_alarms(sensor_class, bit, expected):
    sensor = sensor_class("Alarm", f"{ENTITY_PREFIX}_obj", 0, 1, 30001, Protocol.V2_5)
    assert sensor.decode_alarm_bit(bit) == expected


@pytest.mark.parametrize(
    "sensor_class,bit,expected",
    [
        (ACChargerAlarm1, 0, "5001_1: Grid over-voltage"),
        (ACChargerAlarm2, 1, "5002_2: Relay stuck"),
        (ACChargerAlarm3, 0, "5003: Too high internal temperature"),
    ],
)
def test_ac_charger_alarms(sensor_class, bit, expected):
    sensor = sensor_class(0, 1)
    assert sensor.decode_alarm_bit(bit) == expected


@pytest.mark.parametrize(
    "sensor_class,bit,expected",
    [
        (Alarm6, 0, "Gateway communication abnormal"),
        (Alarm7, 1, "RPR Fault"),
    ],
)
def test_plant_alarms(sensor_class, bit, expected):
    sensor = sensor_class(0)
    assert sensor.decode_alarm_bit(bit) == expected
