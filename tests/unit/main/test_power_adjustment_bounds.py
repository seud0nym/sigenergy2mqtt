"""Bounds applied to the fixed power adjustment targets from the plant's rated power."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import Inverter
from sigenergy2mqtt.main.device_setup import _apply_power_adjustment_bounds
from sigenergy2mqtt.sensors.base import AvailabilityMixin, DiscoveryKeys, Sensor
from sigenergy2mqtt.sensors.inverter.read_only import RatedActivePower
from sigenergy2mqtt.sensors.plant.read_write import (
    ActivePowerFixedAdjustmentTargetValue,
    IndependentPhasePowerControl,
    PhaseActivePowerFixedAdjustmentTargetValue,
    PhaseReactivePowerFixedAdjustmentTargetValue,
    ReactivePowerFixedAdjustmentTargetValue,
    RemoteEMSControlMode,
)


@pytest.fixture(autouse=True)
def clear_sensor_registry():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


@pytest.fixture
def mock_config():
    cfg = Config()
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.enabled = True
    cfg.modbus = [MagicMock()]
    cfg.modbus[0].scan_interval.high = 10
    cfg.modbus[0].scan_interval.realtime = 5
    cfg.modbus[0].scan_interval.low = 600
    cfg.modbus[0].scan_interval.medium = 60
    with _swap_active_config(cfg):
        yield cfg


def _plant_sensors() -> dict[str, Sensor]:
    remote_ems = MagicMock(spec=AvailabilityMixin)
    remote_ems_mode = MagicMock(spec=RemoteEMSControlMode)
    phase_control = MagicMock(spec=IndependentPhasePowerControl)
    sensors: list[Sensor] = [
        ActivePowerFixedAdjustmentTargetValue(0, remote_ems, remote_ems_mode),
        ReactivePowerFixedAdjustmentTargetValue(0, remote_ems, remote_ems_mode),
        PhaseActivePowerFixedAdjustmentTargetValue(0, remote_ems_mode, phase_control, 2, "A"),
        PhaseReactivePowerFixedAdjustmentTargetValue(0, remote_ems_mode, phase_control, 2, "A"),
    ]
    return {s.unique_id: s for s in sensors}


def _inverter(raw_rated_watts: int | None, device_address: int = 1) -> MagicMock:
    """An inverter whose RatedActivePower register holds *raw_rated_watts* (gain 1000)."""
    rated = RatedActivePower(0, device_address)

    async def get_state(raw: bool = False, **kwargs):
        if raw_rated_watts is None:
            raise ValueError("read failed")
        return raw_rated_watts if raw else raw_rated_watts / rated.gain

    rated.get_state = AsyncMock(side_effect=get_state)  # type: ignore[method-assign]
    inverter = MagicMock(spec=Inverter)
    inverter.plant_index = 0
    inverter.log_identity = f"Inverter{device_address}"
    inverter.get_sensor.return_value = rated
    return inverter


def _bounds(sensor: Sensor) -> tuple[float | None, float | None, float | None, float | None]:
    return sensor.get(DiscoveryKeys.MIN), sensor.get(DiscoveryKeys.MAX), sensor.sanity_check.min_raw, sensor.sanity_check.max_raw  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_bounds_for_10kw_plant(mock_config):
    """10 kW rated (raw 10000 W) gives ±10.0 kW active and ±6.0 kvar reactive, not ±10000 / ±600000."""
    plant = MagicMock()
    plant.sensors = _plant_sensors()
    config = MagicMock()
    config.devices = [_inverter(10000)]

    await _apply_power_adjustment_bounds(0, plant, MagicMock(), config)

    by_class = {type(s): s for s in plant.sensors.values()}
    for cls in (ActivePowerFixedAdjustmentTargetValue, PhaseActivePowerFixedAdjustmentTargetValue):
        assert _bounds(by_class[cls]) == (-10.0, 10.0, -10000, 10000)
    for cls in (ReactivePowerFixedAdjustmentTargetValue, PhaseReactivePowerFixedAdjustmentTargetValue):
        assert _bounds(by_class[cls]) == (-6.0, 6.0, -6000, 6000)


@pytest.mark.asyncio
async def test_bounds_validate_written_values(mock_config):
    plant = MagicMock()
    plant.sensors = _plant_sensors()
    config = MagicMock()
    config.devices = [_inverter(10000)]
    await _apply_power_adjustment_bounds(0, plant, MagicMock(), config)

    by_class = {type(s): s for s in plant.sensors.values()}
    active = by_class[ActivePowerFixedAdjustmentTargetValue]
    reactive = by_class[ReactivePowerFixedAdjustmentTargetValue]
    active._remote_ems_mode = None
    reactive._remote_ems_mode = None
    assert await active.value_is_valid(None, 10000) is True
    assert await active.value_is_valid(None, 10010) is False
    assert await reactive.value_is_valid(None, -6000) is True
    assert await reactive.value_is_valid(None, 6010) is False


@pytest.mark.asyncio
async def test_bounds_sum_all_inverters_of_the_plant(mock_config):
    plant = MagicMock()
    plant.sensors = _plant_sensors()
    other_plant_inverter = _inverter(50000, device_address=3)
    other_plant_inverter.plant_index = 1
    config = MagicMock()
    config.devices = [_inverter(10000, 1), _inverter(5000, 2), other_plant_inverter]

    await _apply_power_adjustment_bounds(0, plant, MagicMock(), config)

    by_class = {type(s): s for s in plant.sensors.values()}
    assert _bounds(by_class[ActivePowerFixedAdjustmentTargetValue]) == (-15.0, 15.0, -15000, 15000)
    assert _bounds(by_class[ReactivePowerFixedAdjustmentTargetValue]) == (-9.0, 9.0, -9000, 9000)


@pytest.mark.asyncio
async def test_unreadable_rated_power_leaves_no_misleading_range(mock_config, caplog):
    """Without a rated power there is no literal fallback such as ±60 kvar."""
    plant = MagicMock()
    plant.sensors = _plant_sensors()
    config = MagicMock()
    config.devices = [_inverter(None)]

    await _apply_power_adjustment_bounds(0, plant, MagicMock(), config)

    assert "Failed to acquire RatedActivePower" in caplog.text
    for sensor in plant.sensors.values():
        assert DiscoveryKeys.MIN not in sensor
        assert DiscoveryKeys.MAX not in sensor
