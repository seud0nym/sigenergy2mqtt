import asyncio
import logging
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import (
    EnergyDailyAccumulationSensor,
    ReadOnlySensor,
    ResettableAccumulationSensor,
    Sensor,
)
from sigenergy2mqtt.sensors.const import InputType


class MockSource(ReadOnlySensor):
    def __init__(self, obj_id):
        super().__init__(
            name="Source",
            object_id=obj_id,
            input_type=InputType.HOLDING,
            plant_index=0,
            device_address=1,
            address=30100,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=10,
            protocol_version=Protocol.V1_8,
            unit="W",
            device_class="power",
            state_class="measurement",
            icon="mdi:flash",
            gain=1.0,
            precision=2,
            unique_id_override=obj_id,
        )
        # Initialize _states with at least two values to provide a latest_interval
        now = time.time()
        self._states = [(now - 3600, 1000.0), (now, 1000.0)]
        self.latest_raw_state = 1000.0


@pytest.fixture
def mock_config(tmp_path):
    old_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.DEBUG)
    with patch("sigenergy2mqtt.config.Config") as mock_conf, patch("sigenergy2mqtt.sensors.base.Config", mock_conf):
        mock_conf.persistent_state_path = tmp_path
        mock_conf.home_assistant.enabled = True
        mock_conf.home_assistant.discovery_prefix = "homeassistant"
        mock_conf.home_assistant.unique_id_prefix = "sigen"
        mock_conf.home_assistant.entity_id_prefix = "sigen"
        yield mock_conf

    logging.getLogger().setLevel(old_level)
    # Cleanup global state
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


@pytest.mark.asyncio
async def test_accumulation_sensor_persistence(mock_config, tmp_path):
    source = MockSource("sigen_source_1")
    sensor = ResettableAccumulationSensor(
        name="Accumulated",
        unique_id="sigen_accum_1",
        object_id="sigen_accum_1",
        source=source,
        data_type=ModbusDataType.UINT16,
        unit="Wh",
        device_class="energy",
        state_class="total_increasing",
        icon="mdi:counter",
        gain=1.0,
        precision=2,
    )

    # Initial state should be 0 or loaded from disk (none here)
    assert sensor._current_total == 0.0

    # Simulate accumulation: 1000W for 1 hour = 1000Wh
    # Trapazoidal rule: 0.5 * (prev + curr) * hours = 0.5 * (1000 + 1000) * 1 = 1000
    sensor.set_source_values(source, [(time.time() - 3600, 1000.0), (time.time(), 1000.0)])

    # Small sleep to allow background persistence task to run
    await asyncio.sleep(0.5)

    assert sensor._current_total == 1000.0

    # Verify file exists
    fpath = Path(tmp_path, "sigen_accum_1.state")
    assert fpath.exists()
    assert fpath.read_text() == "1000.0"

    # Re-initialize sensor and verify restoration
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()
    new_sensor = ResettableAccumulationSensor(
        name="Accumulated",
        unique_id="sigen_accum_1",
        object_id="sigen_accum_1",
        source=source,
        data_type=ModbusDataType.UINT16,
        unit="Wh",
        device_class="energy",
        state_class="total_increasing",
        icon="mdi:counter",
        gain=1.0,
        precision=2,
    )
    assert new_sensor._current_total == 1000.0


@pytest.mark.asyncio
async def test_energy_daily_accumulation_reset(mock_config, tmp_path):
    source = MockSource("sigen_source_2")
    # Set initial raw state
    source.latest_raw_state = 5000.0

    sensor = EnergyDailyAccumulationSensor(name="Daily Energy", unique_id="sigen_daily_1", object_id="sigen_daily_1", source=source)

    # Simulate values around midnight
    was_time = time.struct_time((2024, 1, 1, 23, 59, 50, 0, 1, 0))
    now_time = time.struct_time((2024, 1, 2, 0, 0, 10, 1, 2, 0))

    was_ts = time.mktime(was_time)
    now_ts = time.mktime(now_time)

    # Use a list of values to simulate set_source_values
    values = [(was_ts, 5000.0), (now_ts, 5100.0)]

    with patch("time.localtime") as mock_localtime:
        # Mocking time.localtime to simulate day change
        # Sensor calls it multiple times in its logic
        mock_localtime.side_effect = lambda t=None: was_time if (t is not None and t < now_ts - 5) else now_time

        sensor.set_source_values(source, values)

        # Allow background persistence task to run
        await asyncio.sleep(0.5)

    # Should have reset: base becomes the latest value (5100.0)
    assert sensor._state_at_midnight == 5100.0
    assert sensor._state_now == 0.0

    # Verify .atmidnight file
    fpath = Path(tmp_path, "sigen_source_2.atmidnight")
    assert fpath.exists(), f"Persistence file {fpath} does not exist. Current total: {getattr(sensor, '_current_total', 'N/A')}"
    assert fpath.read_text() == "5100.0"


@pytest.mark.asyncio
async def test_midnight_state_file_stale(mock_config, tmp_path):
    source = MockSource("sigen_source_3")
    fpath = Path(tmp_path, "sigen_source_3.atmidnight")

    # Create a "yesterday" file
    # We use a fixed past date in our mock
    yesterday_struct = time.struct_time((2024, 1, 1, 12, 0, 0, 0, 1, 0))
    today_struct = time.struct_time((2024, 1, 2, 12, 0, 0, 1, 2, 0))

    # We must ensure the file's mtime reflects "yesterday"
    # mtime is in seconds since epoch.
    yesterday_ts = time.mktime(yesterday_struct)

    fpath.write_text("4000.0")
    os.utime(fpath, (yesterday_ts, yesterday_ts))

    # Initialize sensor - it should detect stale file and unlink it
    with patch("time.localtime") as mock_localtime:
        # If t is None, it's asking for "now" -> today_struct
        # If t is provided, it's the file mtime -> yesterday_struct
        mock_localtime.side_effect = lambda t=None: today_struct if t is None else time.struct_from_ts_somehow(t)

        # Actually simpler:
        def side_effect(t=None):
            if t is None:
                return today_struct
            return time.gmtime(t)  # or whatever preserves the date

        # Let's just use a more robust mock:
        mock_localtime.side_effect = lambda t=None: today_struct if (t is None or t > yesterday_ts + 10) else yesterday_struct

        sensor = EnergyDailyAccumulationSensor(name="Daily Energy", unique_id="sigen_daily_2", object_id="sigen_daily_2", source=source)

    assert sensor._state_at_midnight is None
    assert not fpath.exists(), f"Stale file {fpath} still exists. mtime date: {time.localtime(fpath.stat().st_mtime)}"


@pytest.mark.asyncio
async def test_accumulation_sensor_optimization(mock_config, tmp_path):
    source = MockSource("sigen_source_opt")
    sensor = ResettableAccumulationSensor(
        name="Accumulated Opt",
        unique_id="sigen_accum_opt",
        object_id="sigen_accum_opt",
        source=source,
        data_type=ModbusDataType.UINT16,
        unit="Wh",
        device_class="energy",
        state_class="total_increasing",
        icon="mdi:counter",
        gain=1.0,
        precision=2,
    )

    # Initial state
    assert sensor._current_total == 0.0

    # 1. First update: Change value -> Should persist
    # 1000W for 1 hour = 1000Wh
    # Trapazoidal rule: 0.5 * (1000 + 1000) * 1 = 1000
    sensor.set_source_values(source, [(time.time() - 3600, 1000.0), (time.time(), 1000.0)])
    await asyncio.sleep(0.5)

    fpath = Path(tmp_path, "sigen_accum_opt.state")
    assert fpath.exists()
    assert fpath.read_text() == "1000.0"

    # Get initial mtime
    initial_mtime = fpath.stat().st_mtime

    # 2. Second update: No Change in Total -> Should NOT persist (optimization check)
    # 0W for 1 hour = 0Wh increment
    # Trapazoidal rule: 0.5 * (0 + 0) * 1 = 0
    # New total is 1000 + 0 = 1000 (same as before)
    # We simulate this by passing 0.0 power readings
    await asyncio.sleep(1.2)  # Wait > 1s to ensure mtime diff if written
    sensor.set_source_values(source, [(time.time(), 0.0), (time.time() + 3600, 0.0)])
    await asyncio.sleep(0.5)

    assert sensor._current_total == 1000.0  # Total is still 1000.0

    # Verify mtime is UNCHANGED
    current_mtime = fpath.stat().st_mtime
    assert current_mtime == initial_mtime, f"File was rewritten despite no change! {initial_mtime} != {current_mtime}"

    # 3. Third update: Change value -> Should persist
    # 1000W for 1 hour = 1000Wh increment
    # New total = 2000.0
    sensor.set_source_values(source, [(time.time() + 3600, 1000.0), (time.time() + 7200, 1000.0)])
    await asyncio.sleep(0.5)

    assert sensor._current_total == 2000.0
    assert fpath.read_text() == "2000.0"
    assert fpath.stat().st_mtime > initial_mtime
