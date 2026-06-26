import logging
import pytest
from types import SimpleNamespace
from sigenergy2mqtt.sensors.plant_ess_preheating_read_write import (
    ESSPreHeatingEnable,
    ESSPreHeatingMode,
    ESSPreHeatingAdvanceEnable,
    ESSPreHeatingTOUTimeStart,
    ESSPreHeatingTOUTimeEnd,
)

# Patch active_config used for entity_id_prefix
@pytest.fixture(autouse=True)
def patch_active_config(monkeypatch):
    cfg = SimpleNamespace(home_assistant=SimpleNamespace(entity_id_prefix="test_prefix"))
    monkeypatch.setattr("sigenergy2mqtt.config.active_config", cfg)
    yield

def test_ess_preheating_enable_attributes():
    sensor = ESSPreHeatingEnable(plant_index=0)
    sensor.configure_mqtt_topics("device_id")
    attrs = sensor.get_attributes()
    assert attrs["comment"] == "0: Disable, 1: Enable"

def test_ess_preheating_mode_attributes():
    sensor = ESSPreHeatingMode(plant_index=0)
    sensor.configure_mqtt_topics("device_id")
    attrs = sensor.get_attributes()
    assert attrs["comment"] == "0: Automatic, 1: Manual"

def test_ess_preheating_advance_enable_attributes(monkeypatch):
    mode = ESSPreHeatingMode(plant_index=0)
    sensor = ESSPreHeatingAdvanceEnable(plant_index=0, preheating_mode=mode)
    sensor.configure_mqtt_topics("device_id")
    attrs = sensor.get_attributes()
    assert attrs["comment"] == "0: Disable, 1: Enable. Takes effect when Preheating Mode is Manual."

@pytest.mark.asyncio
async def test_ess_preheating_advance_enable_invalid(monkeypatch, caplog):
    # Simulate mode sensor in Automatic (latest_raw_state == 0)
    fake_mode = ESSPreHeatingMode(plant_index=0)
    fake_mode.configure_mqtt_topics("device_id")
    sensor = ESSPreHeatingAdvanceEnable(plant_index=0, preheating_mode=fake_mode)
    caplog.set_level(logging.ERROR)
    valid = await sensor.value_is_valid(modbus_client=None, raw_value=2)
    assert not valid
    assert any("Failed to write value" in rec.message for rec in caplog.records)

def test_ess_preheating_tou_time_raw2state_and_attributes():
    sensor = ESSPreHeatingTOUTimeStart(plant_index=0, slot=1, address=50010)
    sensor.configure_mqtt_topics("device_id")
    # raw2state converts epoch seconds to HH:MM:SS
    assert sensor._raw2state(3600) == "01:00:00"
    attrs = sensor.get_attributes()
    assert "comment" in attrs
    assert "Epoch seconds" in attrs["comment"]

@pytest.mark.asyncio
async def test_ess_preheating_tou_time_get_state(monkeypatch):
    sensor = ESSPreHeatingTOUTimeStart(plant_index=0, slot=1, address=50010)
    async def fake_get_state(self, raw=False, republish=False, **kwargs):
        return 7200  # epoch seconds
    monkeypatch.setattr(
        "sigenergy2mqtt.sensors.base.NumericSensor.get_state",
        fake_get_state,
        raising=False,
    )
    # raw=False should format to HH:MM:SS
    state = await sensor.get_state(raw=False)
    assert state == "02:00:00"
    # raw=True returns raw epoch
    raw_state = await sensor.get_state(raw=True)
    assert raw_state == 7200

def test_ess_preheating_tou_time_attributes_exact():
    sensor = ESSPreHeatingTOUTimeStart(plant_index=0, slot=1, address=50010)
    sensor.configure_mqtt_topics("device_id")
    attrs = sensor.get_attributes()
    expected = "Epoch seconds with timezone; local time interpretation depends on the device."
    assert attrs["comment"] == expected

def test_ess_preheating_tou_time_raw2state_non_numeric():
    sensor = ESSPreHeatingTOUTimeStart(plant_index=0, slot=1, address=50010)
    # Non-numeric input should be returned unchanged via super implementation
    assert sensor._raw2state("non-numeric") == "non-numeric"

@pytest.mark.asyncio
async def test_ess_preheating_tou_time_get_state_variations(monkeypatch):
    sensor = ESSPreHeatingTOUTimeStart(plant_index=0, slot=1, address=50010)
    async def fake_get_state(self, raw=False, republish=False, **kwargs):
        return 3661  # 01:01:01 UTC
    monkeypatch.setattr(
        "sigenergy2mqtt.sensors.base.NumericSensor.get_state",
        fake_get_state,
        raising=False,
    )
    # raw=True should return the raw epoch integer
    raw_val = await sensor.get_state(raw=True)
    assert raw_val == 3661
    # raw=False should format to HH:MM:SS
    formatted = await sensor.get_state(raw=False)
    assert formatted == "01:01:01"
