"""Daily accumulation sensors must not carry a previous day's state across a restart."""

import asyncio
import json
import time
from unittest.mock import patch

import pytest

from sigenergy2mqtt.common import InputType, ProtocolVersion, StateClass, UnitOfEnergy
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.config.models.persistence import PersistenceConfig
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.persistence import state_store
from sigenergy2mqtt.sensors.base import (
    EnergyDailyAccumulationSensor,
    ReadOnlySensor,
    ResettableAccumulationSensor,
    Sensor,
)
from sigenergy2mqtt.sensors.base.accumulation import SimpleEnergyDailyAccumulationSensor


class _Source(ReadOnlySensor):
    def __init__(self, obj_id: str):
        super().__init__(
            name="Source",
            object_id=obj_id,
            input_type=InputType.HOLDING,
            plant_index=0,
            device_address=1,
            address=30100,
            count=2,
            data_type=ModbusDataType.UINT32,
            scan_interval=10,
            protocol_version=ProtocolVersion.V1_8,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class="energy",
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:flash",
            gain=1000,
            precision=2,
            unique_id_override=obj_id,
        )


@pytest.fixture
def state_dir(tmp_path):
    cfg = Config()
    cfg.persistent_state_path = tmp_path
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        asyncio.run(state_store.initialise(tmp_path, PersistenceConfig(mqtt_redundancy=False)))
        yield tmp_path / "sensor"
        state_store.shutdown()


def _write(path, value: str, ts: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"v": value, "ts": int(ts), "ver": "1.0.0"}))


NOW = time.mktime((2026, 11, 16, 22, 40, 0, 0, 0, -1))
EARLIER_TODAY = time.mktime((2026, 11, 16, 0, 0, 30, 0, 0, -1))
LATE_YESTERDAY = time.mktime((2026, 11, 15, 23, 0, 0, 0, 0, -1))  # less than 24 hours before NOW
TWO_DAYS_AGO = NOW - 2 * 86400


def _simple_daily() -> SimpleEnergyDailyAccumulationSensor:
    return SimpleEnergyDailyAccumulationSensor(name="Daily", unique_id="sigen_simple_daily", object_id="sigen_simple_daily", source=_Source("sigen_simple_source"))


@pytest.mark.parametrize("written", [LATE_YESTERDAY, TWO_DAYS_AGO])
def test_simple_daily_does_not_restore_a_previous_days_total(state_dir, written):
    _write(state_dir / "sigen_simple_daily.state", "7777.0", written)
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=NOW):
        sensor = _simple_daily()
    assert sensor._current_total == 0.0


def test_simple_daily_restores_todays_total(state_dir):
    _write(state_dir / "sigen_simple_daily.state", "7777.0", EARLIER_TODAY)
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=NOW):
        sensor = _simple_daily()
    assert sensor._current_total == 7777.0


def test_lifetime_accumulation_still_restores_old_totals(state_dir):
    """Only daily sensors are day-bound; lifetime totals are restored whatever their age."""
    _write(state_dir / "sigen_lifetime.state", "7777.0", TWO_DAYS_AGO)
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=NOW):
        sensor = ResettableAccumulationSensor(
            name="Lifetime",
            unique_id="sigen_lifetime",
            object_id="sigen_lifetime",
            source=_Source("sigen_lifetime_source"),
            data_type=ModbusDataType.UINT32,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class="energy",
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:counter",
            gain=1000,
            precision=2,
        )
    assert sensor._current_total == 7777.0


def _daily() -> EnergyDailyAccumulationSensor:
    return EnergyDailyAccumulationSensor(name="Daily", unique_id="sigen_daily", object_id="sigen_daily", source=_Source("sigen_daily_source"))


def test_midnight_baseline_from_yesterday_is_discarded_within_24_hours(state_dir):
    """A baseline written at 23:00 yesterday must not be restored at 22:40 today."""
    path = state_dir / "sigen_daily_source.atmidnight"
    _write(path, "4000.0", LATE_YESTERDAY)
    sensor = _daily()
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=NOW):
        sensor.on_added_to_device()
    assert sensor._state_at_midnight is None
    assert not path.exists()


def test_midnight_baseline_from_today_is_restored(state_dir):
    _write(state_dir / "sigen_daily_source.atmidnight", "4000.0", EARLIER_TODAY)
    sensor = _daily()
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=NOW):
        sensor.on_added_to_device()
    assert sensor._state_at_midnight == 4000.0
