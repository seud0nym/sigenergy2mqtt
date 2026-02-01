from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.ac_charger_read_only import (
    ACChargerAlarm1,
    ACChargerAlarm2,
    ACChargerAlarm3,
    ACChargerAlarms,
    ACChargerChargingPower,
    ACChargerInputBreaker,
    ACChargerRatedCurrent,
    ACChargerRatedPower,
    ACChargerRatedVoltage,
    ACChargerRunningState,
    ACChargerTotalEnergyConsumed,
)
from sigenergy2mqtt.sensors.ac_charger_read_write import ACChargerOutputCurrent, ACChargerStatus
from sigenergy2mqtt.sensors.base import InputType, Sensor


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.sensors.ac_charger_read_only.Config") as mock_ro_config, patch("sigenergy2mqtt.sensors.ac_charger_read_write.Config") as mock_rw_config:
        for cfg in [mock_ro_config, mock_rw_config]:
            cfg.home_assistant.entity_id_prefix = "sigenergy"
            cfg.home_assistant.unique_id_prefix = "sigenergy"
            cfg.home_assistant.discovery_prefix = "homeassistant"
            cfg.home_assistant.enabled = True
            cfg.home_assistant.use_simplified_topics = False
            cfg.home_assistant.edit_percentage_with_box = False
            cfg.modbus = [MagicMock()]
            cfg.modbus[0].scan_interval.high = 10
            cfg.modbus[0].scan_interval.realtime = 5
            cfg.modbus[0].scan_interval.low = 600
            cfg.modbus[0].scan_interval.medium = 60

        yield mock_ro_config


class TestACChargerReadOnly:
    @pytest.mark.asyncio
    async def test_ac_charger_running_state(self, mock_config):
        sensor = ACChargerRunningState(plant_index=0, device_address=10)
        assert sensor["name"] == "Running State"
        assert sensor.address == 32000

        # Test get_state with various values
        with patch("sigenergy2mqtt.sensors.base.ReadOnlySensor.get_state", new_callable=AsyncMock) as mock_get_state:
            # Raw value
            mock_get_state.return_value = 5
            assert await sensor.get_state(raw=True) == 5

            # Decoded value
            mock_get_state.return_value = 5
            assert await sensor.get_state() == "Charging"

            # Unknown value
            mock_get_state.return_value = 99
            assert await sensor.get_state() == "Unknown State code: 99"

            # None value
            mock_get_state.return_value = None
            assert await sensor.get_state() is None

    def test_ac_charger_total_energy(self, mock_config):
        sensor = ACChargerTotalEnergyConsumed(plant_index=0, device_address=10)
        assert sensor["name"] == "Total Energy Consumed"
        assert sensor.address == 32001
        assert sensor.data_type == ModbusDataType.UINT32

    def test_ac_charger_alarms_decoding(self, mock_config):
        alarm1 = ACChargerAlarm1(plant_index=0, device_address=10)
        assert alarm1.decode_alarm_bit(0) == "Grid over-voltage"
        assert alarm1.decode_alarm_bit(8) == "PEN Fault"
        assert alarm1.decode_alarm_bit(9) is None

        alarm2 = ACChargerAlarm2(plant_index=0, device_address=10)
        assert alarm2.decode_alarm_bit(0) == "Leak current detection circuit fault"
        assert alarm2.decode_alarm_bit(5) == "Lamp panel communication fault"
        assert alarm2.decode_alarm_bit(6) is None

        alarm3 = ACChargerAlarm3(plant_index=0, device_address=10)
        assert alarm3.decode_alarm_bit(0) == "Too high internal temperature"
        assert alarm3.decode_alarm_bit(2) == "Meter communication fault"
        assert alarm3.decode_alarm_bit(3) is None

    def test_ac_charger_alarms_combined(self, mock_config):
        a1 = ACChargerAlarm1(0, 10)
        a2 = ACChargerAlarm2(0, 10)
        a3 = ACChargerAlarm3(0, 10)
        combined = ACChargerAlarms(0, 10, a1, a2, a3)
        attrs = combined.get_attributes()
        assert "source" in attrs
        assert "32012" in attrs["source"]


class TestACChargerReadWrite:
    def test_ac_charger_status(self, mock_config):
        sensor = ACChargerStatus(plant_index=0, device_address=10)
        sensor.configure_mqtt_topics("test_device")
        assert sensor["name"] == "AC Charger Stop/Start"
        assert sensor._payloads["on"] == "start"
        assert sensor._values["on"] == 0

        attrs = sensor.get_attributes()
        assert "comment" in attrs
        assert "0:Start" in attrs["comment"]

    def test_ac_charger_output_current(self, mock_config):
        sensor = ACChargerOutputCurrent(plant_index=0, device_address=10, input_breaker=32.0, rated_current=16.0)
        sensor.configure_mqtt_topics("test_device")
        assert sensor["name"] == "Output Current"
        assert sensor["max"] == 16.0
        assert sensor["min"] == 6.0

        attrs = sensor.get_attributes()
        assert "comment" in attrs
