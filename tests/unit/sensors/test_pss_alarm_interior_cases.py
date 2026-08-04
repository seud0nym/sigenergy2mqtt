"""Tests for PSS alarm sensor decode_alarm_bit odd-numbered cases.

Covers missing lines in pss_read_only.py:
  125, 127, 129, 131, 133, 135, 137, 139, 141, 143, 145, 147, 149, 151,
  177, 179, 181, 183, 185, 187

The existing test_pss_sensor_instantiation.py already covers cases 0, 15, and None
for PSSTeleindication1 and PSSTeleindication2. These tests cover the interior cases.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor


@pytest.fixture(autouse=True)
def pss_config():
    """Configure active_config for PSS sensor construction."""
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.enabled = False
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.enabled_by_default = True
    cfg.home_assistant.sigenergy_local_modbus_naming = False
    cfg.persistent_state_path = Path(".")
    cfg.modbus = []

    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            yield cfg

    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


PLANT_INDEX = 0
DEVICE_ADDRESS = 200


class TestPSSTeleindication1AlarmBitDecoding:
    """Test PSSTeleindication1 decode_alarm_bit for all interior cases.

    Covers lines 125, 127, 129, 131, 133, 135, 137, 139, 141, 143, 145, 147, 149, 151.
    """

    def test_decode_alarm_bit_case_1(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(1) == "Measurement & control unit general alarm"

    def test_decode_alarm_bit_case_3(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(3) == "Transformer light gas alarm"

    def test_decode_alarm_bit_case_5(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(5) == "Transformer low oil level alarm"

    def test_decode_alarm_bit_case_7(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(7) == "Transformer oil high temperature alarm"

    def test_decode_alarm_bit_case_9(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(9) == "Transformer winding high temperature alarm"

    def test_decode_alarm_bit_case_11(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(11) == "Low voltage room dual smoke sensor trip"

    def test_decode_alarm_bit_case_13(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(13) == "Low voltage room maintenance door open trip"

    def test_decode_alarm_bit_even_cases(self):
        """Test even-numbered cases to ensure complete mapping."""
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication1
        s = PSSTeleindication1(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(2) == "Transformer heavy gas trip"
        assert s.decode_alarm_bit(4) == "Transformer pressure relief trip"
        assert s.decode_alarm_bit(6) == "Transformer high oil level alarm"
        assert s.decode_alarm_bit(8) == "Transformer oil over-temperature trip"
        assert s.decode_alarm_bit(10) == "Transformer winding over-temperature trip"
        assert s.decode_alarm_bit(12) == "Medium voltage room dual smoke sensor trip"
        assert s.decode_alarm_bit(14) == "Transformer room door open trip"


class TestPSSTeleindication2AlarmBitDecoding:
    """Test PSSTeleindication2 decode_alarm_bit for all interior cases.

    Covers lines 177, 179, 181, 183, 185, 187.
    """

    def test_decode_alarm_bit_case_1(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(1) == "Medium voltage room over-temperature trip"

    def test_decode_alarm_bit_case_3(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(3) == "Emergency stop"

    def test_decode_alarm_bit_case_5(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(5) == "LA Low voltage room heat exchanger fault"

    def test_decode_alarm_bit_case_7(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(7) == "Low voltage room smoke sensor alarm"

    def test_decode_alarm_bit_case_9(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(9) == "Medium voltage cabinet G3 circuit breaker switch-off failure"

    def test_decode_alarm_bit_case_11(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(11) == "LB low voltage cabinet SPD fault"

    def test_decode_alarm_bit_case_13(self):
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(13) == "LA low voltage cabinet over-temperature alarm"

    def test_decode_alarm_bit_even_cases(self):
        """Test even-numbered cases to ensure complete mapping."""
        from sigenergy2mqtt.sensors.pss_read_only import PSSTeleindication2
        s = PSSTeleindication2(PLANT_INDEX, DEVICE_ADDRESS)
        assert s.decode_alarm_bit(2) == "Medium voltage cabinet insulation gas low pressure alarm"
        assert s.decode_alarm_bit(4) == "Medium voltage room air conditioner/heat exchanger fault"
        assert s.decode_alarm_bit(6) == "LB Low voltage room heat exchanger fault"
        assert s.decode_alarm_bit(8) == "Medium voltage room smoke sensor alarm"
        assert s.decode_alarm_bit(10) == "LA low voltage cabinet SPD fault"
        assert s.decode_alarm_bit(12) == "Distribution cabinet SPD fault"
        assert s.decode_alarm_bit(14) == "LB low voltage cabinet over-temperature alarm"
