from unittest.mock import MagicMock, patch

import pytest

ENTITY_PREFIX = "sigenergy"


from sigenergy2mqtt.config import Config, _swap_active_config


@pytest.fixture(autouse=True)
def setup_configs():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigenergy"
    cfg.home_assistant.entity_id_prefix = ENTITY_PREFIX
    cfg.sensor_overrides = {}

    mock_device = MagicMock()
    mock_device.scan_interval.realtime = 5
    cfg.modbus = [mock_device]

    with _swap_active_config(cfg):
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
        (Alarm1Sensor, 0, "Software version mismatch"),
        (Alarm1Sensor, 15, "DC component of output current out of limit"),
        (Alarm2Sensor, 0, "Leak current out of limit"),
        (Alarm2Sensor, 9, "Soft start failure"),
        (Alarm3Sensor, 0, "Software version mismatch"),
        (Alarm3Sensor, 6, "Thermal runaway"),
        (Alarm4Sensor, 0, "Software version mismatch"),
        (Alarm5Sensor, 0, "Software version mismatch"),
    ],
)
def test_base_alarms(sensor_class, bit, expected):
    sensor = sensor_class("Alarm", f"{ENTITY_PREFIX}_obj", 0, 1, 30001, Protocol.V2_5)
    assert sensor.decode_alarm_bit(bit) == expected


@pytest.mark.parametrize(
    "sensor_class,bit,expected",
    [
        (ACChargerAlarm1, 0, "Grid over-voltage"),
        (ACChargerAlarm2, 1, "Relay stuck"),
        (ACChargerAlarm3, 0, "Too high internal temperature"),
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
