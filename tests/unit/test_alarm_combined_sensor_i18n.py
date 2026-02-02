from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor


@pytest.mark.asyncio
async def test_alarm_combined_sensor_translation_bug():
    # Setup mocks
    # We use MagicMock for the alarms to avoid initialization issues with the complex Sensor hierarchy
    alarm1 = MagicMock(spec=AlarmSensor)
    alarm1.scan_interval = 60
    alarm1.device_address = 1
    alarm1.address = 30100
    alarm1.count = 1
    alarm1.protocol_version = 0.0
    alarm1.publishable = True
    alarm1.plant_index = 0

    alarm2 = MagicMock(spec=AlarmSensor)
    alarm2.scan_interval = 60
    alarm2.device_address = 1
    alarm2.address = 30101  # Contiguous address
    alarm2.count = 1
    alarm2.protocol_version = 0.0
    alarm2.publishable = True
    alarm2.plant_index = 0

    combined = AlarmCombinedSensor("combined", "sigen.test_combined_1", "sigen_test_combined_1", alarm1, alarm2)

    # Mock _t to simulate non-English translation
    # When "No Alarm" is translated, it returns "Aucune Alarme"
    def mock_translation(key, default, debugging=False):
        if key == "AlarmSensor.no_alarm":
            return "Aucune Alarme"
        return default

    with patch("sigenergy2mqtt.sensors.base._t", side_effect=mock_translation):
        # Both alarms have "Aucune Alarme" state (simulated by get_state returning what base.AlarmSensor would return if translated)
        # However, AlarmCombinedSensor logic previously used AlarmSensor.NO_ALARM ("No Alarm") for comparison
        # The fix ensures it uses the translated "Aucune Alarme" for comparison.

        async def async_return_alarm1(*args, **kwargs):
            return "Aucune Alarme"

        async def async_return_alarm2(*args, **kwargs):
            return "Aucune Alarme"

        alarm1.get_state = MagicMock(side_effect=async_return_alarm1)
        alarm2.get_state = MagicMock(side_effect=async_return_alarm2)

        # Execute
        state = await combined.get_state()

        # assert
        # verification: The fix should ensure it returns "Aucune Alarme" (the translated no_alarm string)
        # when all alarms are in that state.
        assert state == "Aucune Alarme"
