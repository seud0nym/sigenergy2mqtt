import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock circular dependencies
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.common.types"] = mock_types

from pymodbus.client import AsyncModbusTcpClient as ModbusClient  # noqa: E402

from sigenergy2mqtt.common import Protocol  # noqa: E402
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, AlarmSensor, EnergyLifetimeAccumulationSensor, ReadOnlySensor, Sensor  # noqa: E402
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass  # noqa: E402


@pytest.fixture(autouse=True)
def mock_config_all():
    with patch("sigenergy2mqtt.sensors.base.Config") as mock_config:
        mock_config.home_assistant.unique_id_prefix = "sigenergy"
        mock_config.home_assistant.entity_id_prefix = "sigenergy"
        mock_config.home_assistant.enabled = True
        mock_config.sensor_overrides = {}
        mock_config.persistent_state_path = "."
        yield mock_config


class TestResettableAccumulation:
    def test_resettable_accumulation_negative_increase(self, tmp_path):
        with patch("sigenergy2mqtt.sensors.base.Config.persistent_state_path", str(tmp_path)):
            source = MagicMock(spec=ReadOnlySensor)
            source.unique_id = "src"
            source.latest_interval = 100.0

            with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
                sensor = EnergyLifetimeAccumulationSensor("Accumulated", "sigenergy_acc", "sigenergy_acc", source, ModbusClient.DATATYPE.UINT32, "kWh", DeviceClass.ENERGY, StateClass.TOTAL, "mdi:energy", 1.0, 2)
                sensor._current_total = 100.0

                # Negative power values
                values = [(1000.0, -10.0), (1100.0, -20.0)]

                with patch("asyncio.run_coroutine_threadsafe"), patch("asyncio.get_running_loop"):
                    sensor.set_source_values(source, values)
                    assert sensor._current_total == 100.0


class TestAlarmSensors:
    def test_alarm_sensor_binary(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteAlarm(AlarmSensor):
                def decode_alarm_bit(self, bit_position: int) -> str | None:
                    return "Error"

            sensor = ConcreteAlarm("Alarm", "sigenergy_alarm", 0, 1, 30001, Protocol.V2_4, "Equipment")

            # AlarmSensor defines NO_ALARM = "No Alarm"
            assert sensor.state2raw("No Alarm") == 0
            assert sensor.state2raw(1) == 1

    @pytest.mark.asyncio
    async def test_alarm_combined_sensor(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ProxyAlarm(AlarmSensor):
                def __init__(self, name, oid, addr):
                    self["name"] = name
                    self["unique_id"] = oid
                    self.device_address = 1
                    self.address = addr
                    self.count = 1
                    self.scan_interval = 10
                    self._publishable = True
                    self._states = []

                def decode_alarm_bit(self, bit_position):
                    return "Error"

                @property
                def latest_raw_state(self):
                    return self._states[-1][1] if self._states else 0

                @latest_raw_state.setter
                def latest_raw_state(self, value):
                    if self._states:
                        latest = self._states.pop()
                        self._states.append((latest[0], value))
                    else:
                        self._states.append((0, value))

                async def get_state(self, raw: bool = False, republish: bool = False, **kwargs):
                    reading = self.latest_raw_state
                    return "No Alarm" if reading == 0 else "Error"

            a1 = ProxyAlarm("A1", "sigenergy_a1", 30001)
            a2 = ProxyAlarm("A2", "sigenergy_a2", 30002)

            sensor = AlarmCombinedSensor("Combined", "sigenergy_combined", "sigenergy_combined", a1, a2)

            assert await sensor.get_state() == "No Alarm"

            # Update a1
            a1._states.append((0, 1))
            assert await sensor.get_state() == "Error"
