from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.base.alarms import (
    AlarmCombinedSensor,
    AlarmSensor,
    RunningStateSensor,
)


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


class CompleteAlarmSensor(AlarmSensor):
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        return f"Alarm {bit_position}" if 0 <= bit_position < 16 else None

@pytest.mark.asyncio
async def test_alarm_sensor_coverage():
    sensor = DummyAlarmSensor("Dummy", "sigen_dummy", 0, 1, 30000, ProtocolVersion.V2_5, "Dummy")
    
    # Test state2raw
    assert sensor.state2raw(AlarmSensor.NO_ALARM) == 0
    with pytest.raises(TypeError):
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
async def test_65535_is_unknown_when_decoder_does_not_cover_all_bits():
    sensor = DummyAlarmSensor("Dummy", "sigen_dummy", 0, 1, 30000, ProtocolVersion.V2_5, "Dummy")
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state", return_value=65535):
        assert await sensor.get_state() == "Unknown"
        assert await sensor.get_state(raw=True) == 65535


@pytest.mark.asyncio
async def test_65535_decodes_when_decoder_covers_all_bits():
    sensor = CompleteAlarmSensor("Complete", "sigen_complete", 0, 1, 30000, ProtocolVersion.V2_5, "Dummy")
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state", return_value=65535):
        state = await sensor.get_state()
    assert state.count("Alarm ") == 16
    assert sensor._is_no_alarm(65535) is False


def test_alarm_has_no_additional_availability_topic():
    sensor = DummyAlarmSensor("Dummy", "sigen_dummy", 0, 1, 30000, ProtocolVersion.V2_5, "Dummy")
    sensor.configure_mqtt_topics("device")
    assert len(sensor["availability"]) == 1

@pytest.mark.asyncio
async def test_alarm_combined_sensor_coverage():
    alarm1 = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, ProtocolVersion.V2_5, "Dummy")
    alarm2 = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, ProtocolVersion.V2_5, "Dummy")
    
    # Test init exceptions
    with pytest.raises(ValueError, match="At least one alarm sensor required"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb")
        
    alarm_diff_dev = DummyAlarmSensor("A3", "sigen_a3", 0, 2, 30002, ProtocolVersion.V2_5, "Dummy")
    with pytest.raises(ValueError, match="same device address"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm_diff_dev)
        
    alarm_non_contig = DummyAlarmSensor("A4", "sigen_a4", 0, 1, 30003, ProtocolVersion.V2_5, "Dummy")
    with pytest.raises(ValueError, match="contiguous address ranges"):
        AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm_non_contig)
        
    # Valid init
    combined = AlarmCombinedSensor("Comb", "sigen_comb", "sigen_comb", alarm1, alarm2)
    
    # Test update_internal_state
    assert await combined._update_internal_state() is True
    
    # Test protocol_version setter
    with pytest.raises(NotImplementedError):
        combined.protocol_version = ProtocolVersion.V2_5
        
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
            
    long_alarm1 = LongAlarmSensor("LA1", "sigen_la1", 0, 1, 30100, ProtocolVersion.V2_5, "Dummy")
    long_alarm2 = LongAlarmSensor("LA2", "sigen_la2", 0, 1, 30101, ProtocolVersion.V2_5, "Dummy")
    comb_long = AlarmCombinedSensor("CL", "sigen_cl", "sigen_cl", long_alarm1, long_alarm2)
    
    with patch("sigenergy2mqtt.sensors.base.readable.ReadOnlySensor.get_state") as mock_super_get_state:
        # If active_config.home_assistant.enabled is True
        mock_super_get_state.return_value = 1 # bit 0
        state = await comb_long.get_state()
        assert len(state) <= 255


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_state", "second_state", "expected"),
    [
        ("No Alarm", "Unknown", "Unknown"),
        ("Active inverter alarm", "Unknown", "Active inverter alarm, Unknown"),
    ],
)
async def test_combined_alarm_includes_unknown_for_invalid_child(first_state, second_state, expected):
    first = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, ProtocolVersion.V2_5, "Inverter")
    second = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, ProtocolVersion.V2_5, "Inverter")
    first.get_state = AsyncMock(return_value=first_state)
    second.get_state = AsyncMock(return_value=second_state)
    combined = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", first, second)

    assert await combined.get_state() == expected
    assert combined._has_invalid_alarm is True
    combined.configure_mqtt_topics("device")
    assert len(combined["availability"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("active_state", "expected"),
    [
        ("No Alarm", "Unknown (2)"),
        ("Active inverter alarm", "Active inverter alarm, Unknown (2)"),
    ],
)
async def test_combined_alarm_counts_multiple_invalid_children(active_state, expected):
    first = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, ProtocolVersion.V2_5, "Inverter")
    second = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, ProtocolVersion.V2_5, "Inverter")
    third = DummyAlarmSensor("A3", "sigen_a3", 0, 1, 30002, ProtocolVersion.V2_5, "Inverter")
    first.get_state = AsyncMock(return_value=active_state)
    second.get_state = AsyncMock(return_value="Unknown")
    third.get_state = AsyncMock(return_value="Unknown")
    combined = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", first, second, third)

    assert await combined.get_state() == expected


@pytest.mark.asyncio
async def test_combined_alarm_counts_none_and_unknown_as_one_invalid_group():
    first = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, ProtocolVersion.V2_5, "Inverter")
    second = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, ProtocolVersion.V2_5, "Inverter")
    first.get_state = AsyncMock(return_value="Active inverter alarm")
    second.get_state = AsyncMock(return_value=None)
    third = DummyAlarmSensor("A3", "sigen_a3", 0, 1, 30002, ProtocolVersion.V2_5, "Inverter")
    third.get_state = AsyncMock(return_value="Unknown")
    combined = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", first, second, third)

    assert await combined.get_state() == "Active inverter alarm, Unknown (2)"


@pytest.mark.asyncio
async def test_combined_alarm_compresses_text_but_preserves_unknown_count():
    children = [
        DummyAlarmSensor(f"A{i}", f"sigen_a{i}", 0, 1, 30000 + i, ProtocolVersion.V2_5, "Inverter")
        for i in range(4)
    ]
    children[0].get_state = AsyncMock(return_value="First active alarm description " * 8)
    children[1].get_state = AsyncMock(return_value="Second active alarm description " * 8)
    children[2].get_state = AsyncMock(return_value="Unknown")
    children[3].get_state = AsyncMock(return_value=None)
    combined = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", *children)

    state = await combined.get_state()

    assert len(state) <= 255
    assert state.endswith("Unknown (2)")


@pytest.mark.asyncio
async def test_combined_alarm_republish_checks_cached_child_availability():
    first = DummyAlarmSensor("A1", "sigen_a1", 0, 1, 30000, ProtocolVersion.V2_5, "Inverter")
    second = DummyAlarmSensor("A2", "sigen_a2", 0, 1, 30001, ProtocolVersion.V2_5, "Inverter")
    first.get_state = AsyncMock(return_value="A previously active alarm")
    second.get_state = AsyncMock(return_value=None)
    combined = AlarmCombinedSensor("Combined", "sigen_combined", "sigen_combined", first, second)
    combined._states.append((0, "A previously active alarm"))
    combined.configure_mqtt_topics("device")

    assert await combined.get_state(republish=True) == "A previously active alarm, Unknown"

@pytest.mark.asyncio
async def test_running_state_sensor_coverage():
    sensor = RunningStateSensor("Run", "sigen_run", 0, 1, 30000, ProtocolVersion.V2_5)
    
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
