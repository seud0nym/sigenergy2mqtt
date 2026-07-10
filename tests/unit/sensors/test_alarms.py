import pytest
from unittest.mock import MagicMock, patch

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config, _swap_active_config, active_config
from sigenergy2mqtt.sensors.base.alarms import AlarmSensor, AlarmCombinedSensor, RunningStateSensor
from sigenergy2mqtt.sensors.base import Sensor

@pytest.fixture(autouse=True)
def setup_configs():
    cfg = Config()
    cfg.home_assistant.enabled = True
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.sensor_overrides = {}

    mock_device = MagicMock()
    mock_device.scan_interval.realtime = 5
    mock_device.scan_interval.high = 5
    cfg.modbus = [mock_device]

    with _swap_active_config(cfg):
        yield

@pytest.fixture(autouse=True)
def clear_sensor_registries():
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()
    yield
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

class DummyAlarmSensor(AlarmSensor):
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        super().decode_alarm_bit(bit_position) # Cover line 74
        if bit_position == 1:
            return "Alarm One"
        if bit_position == 2:
            raise TypeError("Test exception")
        return None

@pytest.mark.asyncio
async def test_alarm_sensor_coverage():
    sensor = DummyAlarmSensor("Dummy", "sigen_dummy", 0, 1, 30000, Protocol.V2_5, "Dummy")
    
    # Test state2raw
    assert sensor.state2raw(AlarmSensor.NO_ALARM) == 0
    with pytest.raises(ValueError):
        sensor.state2raw("Alarm One")
    
    # Mock super get_state
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state") as mock_super_get_state:
        # Test TypeError branch (bit 2 is 1 -> 4)
        mock_super_get_state.return_value = 4 # bit 2
        state = await sensor.get_state()
        assert state == "Unknown Alarm 4"
        
        # Test truncate alarms
        mock_super_get_state.return_value = 2 # bit 1 -> "Alarm One"
        state = await sensor.get_state(max_length=5)
        # "Alarm One" compressed -> "Alarm One", length 9 > 5 -> "Al..." -> wait, 5 - 3 = 2 -> "Al..."
        # Wait, the compression regex removes numbers, colons, underscores:
        # "Alarm One" -> "Alarm One". length 9.
        # max_len is 5.
        # compressed[:2] + "..." -> "Al..."
        assert state.endswith("...") or len(state) <= 5

@pytest.mark.asyncio
async def test_alarm_combined_sensor_coverage():
    alarm1 = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, Protocol.V2_5, "Dummy")
    alarm2 = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, Protocol.V2_5, "Dummy")
    
    # Test init exceptions
    with pytest.raises(ValueError, match="At least one alarm sensor required"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb")
        
    alarm_diff_dev = DummyAlarmSensor("A3", "sigen_a3", 0, 2, 30002, Protocol.V2_5, "Dummy")
    with pytest.raises(ValueError, match="same device address"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm_diff_dev)
        
    alarm_non_contig = DummyAlarmSensor("A4", "sigen_a4", 0, 1, 30003, Protocol.V2_5, "Dummy")
    with pytest.raises(ValueError, match="contiguous address ranges"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm_non_contig)
        
    # Valid init
    combined = AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm2)
    
    # Test update_internal_state
    assert await combined._update_internal_state() is True
    
    # Test protocol_version setter
    with pytest.raises(NotImplementedError):
        combined.protocol_version = Protocol.V2_5
        
    # Test state2raw
    assert combined.state2raw(AlarmSensor.NO_ALARM) == 0
    assert combined.state2raw("Some Alarm") == "Some Alarm"
    
    # Test compress alarm string logic
    long_alarm = "A" * 300
    compressed = combined._compress_alarm_string(long_alarm)
    assert len(compressed) <= 255
    assert compressed.endswith("...")
    
    # Test get_state with very long strings that get compressed
    class LongAlarmSensor(AlarmSensor):
        def decode_alarm_bit(self, bit_position: int) -> str | None:
            return "Very long string with lots of text " * 10
            
    long_alarm1 = LongAlarmSensor("LA1", "sigen_la1", 0, 1, 30100, Protocol.V2_5, "Dummy")
    long_alarm2 = LongAlarmSensor("LA2", "sigen_la2", 0, 1, 30101, Protocol.V2_5, "Dummy")
    comb_long = AlarmCombinedSensor("CL", "sigen_cl", "sigen_cl", long_alarm1, long_alarm2)
    
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state") as mock_super_get_state:
        # If active_config.home_assistant.enabled is True
        mock_super_get_state.return_value = 1 # bit 0
        state = await comb_long.get_state()
        assert len(state) <= 255

@pytest.mark.asyncio
async def test_running_state_sensor_coverage():
    sensor = RunningStateSensor("Run", "sigen_run", 0, 1, 30000, Protocol.V2_5)
    
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state") as mock_super_get_state:
        # Test raw=True
        mock_super_get_state.return_value = 1
        assert await sensor.get_state(raw=True) == 1
        
        # Test out of bounds int
        mock_super_get_state.return_value = 100
        assert await sensor.get_state() == "Unknown State code: 100"
        
        # Test non-int value
        mock_super_get_state.return_value = [1, 2]
        assert await sensor.get_state() == "Unknown State code: [1, 2]"
