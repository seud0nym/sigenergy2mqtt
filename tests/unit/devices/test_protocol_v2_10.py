"""Tests for Sigenergy Modbus Protocol V2.10 support.

V2.10 (2026-11-03) changes:
  * Added [Grid sensor] phase A/B/C current (30292~30296) and voltage (30298~30302)
  * Added Reactive power regulation gradient (40160)
  * Added Remote EMS power limit global enable (40162), which changes when the
    ESS max charging/discharging limits and PV max power limit (40032~40036) apply
  * Removed PSS and PID devices
"""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from sigenergy2mqtt.common import (
    InputType,
    ProtocolApplies,
    ProtocolVersion,
    RegisterAccess,
)
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.config.models import ModbusConfig
from sigenergy2mqtt.config.settings import Settings
from sigenergy2mqtt.main.protocol_probe import probe_protocol
from sigenergy2mqtt.sensors.plant.read_only import (
    GridPhaseCurrent,
    GridPhaseVoltage,
    GridStatus,
    Reserved30287,
)
from sigenergy2mqtt.sensors.plant.read_write import (
    MaxChargingLimit,
    MaxDischargingLimit,
    PVMaxPowerLimit,
    ReactivePowerRegulationGradient,
    RemoteEMS,
    RemoteEMSPowerLimitGlobalEnable,
)
from tests.utils import modbus_test_server as server
from tests.utils.modbus_sensors import get_sensor_instances

# ---------------------------------------------------------------------------
# ProtocolVersion ordering
# ---------------------------------------------------------------------------


class TestProtocolVersion:
    def test_v2_10_orders_after_v2_9(self):
        assert ProtocolVersion.V2_10 > ProtocolVersion.V2_9
        assert ProtocolVersion.V2_10 > ProtocolVersion.V2_4
        assert ProtocolVersion.V2_9 < ProtocolVersion.V2_10
        assert ProtocolVersion.V2_10 >= ProtocolVersion.V2_10
        assert ProtocolVersion.V2_10 <= ProtocolVersion.V2_10

    def test_latest_version(self):
        assert max(ProtocolVersion) is ProtocolVersion.V2_10
        assert min(ProtocolVersion) is ProtocolVersion.N_A
        assert list(ProtocolVersion) == sorted(ProtocolVersion)

    def test_value_and_lookup(self):
        assert ProtocolVersion.V2_10.value == "2.10"
        assert f"V{ProtocolVersion.V2_10.value}" == "V2.10"
        assert ProtocolVersion("2.10") is ProtocolVersion.V2_10
        assert ProtocolVersion["V2_10"] is ProtocolVersion.V2_10
        assert ProtocolApplies(ProtocolVersion.V2_10) == "2026-11-03"

    def test_comparison_with_non_protocol_version_is_unsupported(self):
        with pytest.raises(TypeError):
            _ = ProtocolVersion.V2_10 < 3  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Protocol probe
# ---------------------------------------------------------------------------


class _RR:
    def __init__(self, error: bool):
        self._error = error
        self.exception_code = 2 if error else None

    def isError(self) -> bool:
        return self._error


@pytest.mark.asyncio
async def test_probe_protocol_detects_v2_10_with_holding_register(monkeypatch):
    calls = []

    async def fake_read(_client, register, count, device_id, input_type):
        calls.append((register, input_type))
        return _RR(error=False)

    monkeypatch.setattr("sigenergy2mqtt.main.protocol_probe.read_registers", fake_read)
    assert await probe_protocol(AsyncMock()) is ProtocolVersion.V2_10
    assert calls == [(ReactivePowerRegulationGradient.ADDRESS, InputType.HOLDING)]


@pytest.mark.asyncio
async def test_probe_protocol_falls_back_to_v2_9(monkeypatch):
    v2_10_registers = {ReactivePowerRegulationGradient.ADDRESS, RemoteEMSPowerLimitGlobalEnable.ADDRESS, GridPhaseCurrent.PHASE_A_ADDRESS}
    calls = []

    async def fake_read(_client, register, count, device_id, input_type):
        calls.append(register)
        return _RR(error=register in v2_10_registers)

    monkeypatch.setattr("sigenergy2mqtt.main.protocol_probe.read_registers", fake_read)
    assert await probe_protocol(AsyncMock()) is ProtocolVersion.V2_9
    assert set(calls[:3]) == v2_10_registers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("supported", "input_type"),
    [(RemoteEMSPowerLimitGlobalEnable.ADDRESS, InputType.HOLDING), (GridPhaseCurrent.PHASE_A_ADDRESS, InputType.INPUT)],
)
async def test_probe_protocol_detects_v2_10_without_40160(monkeypatch, supported, input_type):
    """Firmware may serve only some of the V2.10 registers."""
    seen = {}

    async def fake_read(_client, register, count, device_id, input_type):
        seen[register] = input_type
        return _RR(error=register != supported)

    monkeypatch.setattr("sigenergy2mqtt.main.protocol_probe.read_registers", fake_read)
    assert await probe_protocol(AsyncMock()) is ProtocolVersion.V2_10
    assert seen[supported] == input_type


# ---------------------------------------------------------------------------
# Sensor graph at V2.10 vs V2.9
# ---------------------------------------------------------------------------


def _by_class(sensors: dict, cls: type) -> list:
    return [s for s in sensors.values() if type(s) is cls]


@pytest.mark.asyncio
async def test_v2_10_sensors_registered():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)

    currents = _by_class(sensors, GridPhaseCurrent)
    voltages = _by_class(sensors, GridPhaseVoltage)
    assert sorted(s.address for s in currents) == [30292, 30294, 30296]
    assert sorted(s.address for s in voltages) == [30298, 30300, 30302]
    assert all(s.device_address == 247 and s.gain == 100 for s in currents + voltages)
    assert {s.parent_device.__class__.__name__ for s in currents + voltages} == {"GridSensor"}
    assert len(_by_class(sensors, ReactivePowerRegulationGradient)) == 1
    assert len(_by_class(sensors, RemoteEMSPowerLimitGlobalEnable)) == 1
    assert len(_by_class(sensors, Reserved30287)) == 1


@pytest.mark.asyncio
async def test_v2_10_sensors_not_registered_on_v2_9():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_9)

    for cls in (GridPhaseCurrent, GridPhaseVoltage, ReactivePowerRegulationGradient, RemoteEMSPowerLimitGlobalEnable, Reserved30287):
        assert _by_class(sensors, cls) == [], cls.__name__


@pytest.mark.asyncio
async def test_grid_sensor_phase_sensors_follow_output_type():
    # output_type 0 = L/N (single phase)
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10, output_type=0)

    assert [s.address for s in _by_class(sensors, GridPhaseCurrent)] == [GridPhaseCurrent.PHASE_A_ADDRESS]
    assert [s.address for s in _by_class(sensors, GridPhaseVoltage)] == [GridPhaseVoltage.PHASE_A_ADDRESS]


@pytest.mark.asyncio
async def test_power_limits_not_gated_on_remote_ems_from_v2_10():
    # Default simulated firmware is SPC112, so before V2.10 the limits were gated on Remote EMS
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)
        for cls in (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit):
            (limit,) = _by_class(sensors, cls)
            assert limit._availability_control_sensor is None, cls.__name__
            assert limit._remote_ems_mode is None, cls.__name__
            assert isinstance(limit._global_enable, RemoteEMSPowerLimitGlobalEnable), cls.__name__
            assert "40162" in limit.get_attributes()["comment"], cls.__name__
            assert "40031" not in limit.get_attributes()["comment"], cls.__name__


@pytest.mark.asyncio
async def test_power_limits_still_gated_before_v2_10():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_9)
        for cls in (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit):
            (limit,) = _by_class(sensors, cls)
            assert isinstance(limit._availability_control_sensor, RemoteEMS), cls.__name__
            assert limit._remote_ems_mode is not None, cls.__name__
            assert limit._global_enable is None, cls.__name__
            assert "40162" not in limit.get_attributes()["comment"], cls.__name__


@pytest.mark.asyncio
async def test_power_limit_writable_without_remote_ems_from_v2_10():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)
        (limit,) = _by_class(sensors, MaxChargingLimit)
        (remote_ems,) = _by_class(sensors, RemoteEMS)
        remote_ems.set_latest_state(0)
        assert await limit.value_is_valid(None, 1000) is True


@pytest.mark.asyncio
async def test_new_holding_register_definitions():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)
        (gradient,) = _by_class(sensors, ReactivePowerRegulationGradient)
        (global_enable,) = _by_class(sensors, RemoteEMSPowerLimitGlobalEnable)

    assert gradient.address == 40160 and gradient.count == 2 and gradient.gain == 1000
    assert gradient.unit == "%/s"
    assert gradient["max"] == 5000
    assert global_enable.address == 40162 and global_enable.count == 1
    assert global_enable.input_type == InputType.HOLDING


@pytest.mark.asyncio
async def test_no_remote_ems_hides_global_enable():
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)
        (global_enable,) = _by_class(sensors, RemoteEMSPowerLimitGlobalEnable)
        (gradient,) = _by_class(sensors, ReactivePowerRegulationGradient)
        global_enable.apply_device_overrides(RegisterAccess(no_remote_ems=True))
        gradient.apply_device_overrides(RegisterAccess(no_remote_ems=True))

    assert global_enable.publishable is False
    assert gradient.publishable is True


# ---------------------------------------------------------------------------
# Removed PSS/PID configuration
# ---------------------------------------------------------------------------


def test_modbus_config_ignores_removed_pss_pid(caplog):
    with caplog.at_level(logging.WARNING):
        cfg = ModbusConfig.model_validate({"host": "127.0.0.1", "pss": [242], "pid": [241]})
    assert not hasattr(cfg, "pss") and not hasattr(cfg, "pid")
    assert cfg.inverters == [1]
    assert "Ignoring modbus 'pss' configuration" in caplog.text
    assert "Ignoring modbus 'pid' configuration" in caplog.text


def test_auto_discovery_exclude_ignores_removed_pss_pid(caplog):
    with caplog.at_level(logging.WARNING):
        assert Settings.validate_excludes("PID, PSS, DCCharger") == ["DCCharger"]
    assert "PID devices are no longer supported" in caplog.text
    assert "PSS devices are no longer supported" in caplog.text


def test_removed_env_vars_warn(monkeypatch, caplog):
    from sigenergy2mqtt.config.sources import EnvSettingsSource

    monkeypatch.setenv("SIGENERGY2MQTT_MODBUS_HOST", "127.0.0.1")
    monkeypatch.setenv("SIGENERGY2MQTT_MODBUS_PSS_DEVICE_ID", "242")
    with caplog.at_level(logging.WARNING):
        EnvSettingsSource(Settings)()
    assert "Ignoring SIGENERGY2MQTT_MODBUS_PSS_DEVICE_ID" in caplog.text


# ---------------------------------------------------------------------------
# Modbus test server (simulator)
# ---------------------------------------------------------------------------


def _grid_sensor(cls: type, phase: str):
    with _swap_active_config(Config()):
        return cls(0, phase)


def test_simulator_initial_grid_sensor_values():
    block = server.CustomDataBlock(device_address=247, mqtt_client=None, latency_budget=server.LatencyBudget())
    for phase in ("A", "B", "C"):
        value, source = block._get_initial_value(_grid_sensor(GridPhaseVoltage, phase))
        assert source == "grid_sensor_phase_voltage"
        assert 225.0 <= value <= 245.0
        value, source = block._get_initial_value(_grid_sensor(GridPhaseCurrent, phase))
        assert source == "grid_sensor_phase_current"
        assert -20.0 <= value <= 20.0


def test_simulator_grid_outage_zeroes_and_restores_grid_sensor_registers():
    async def _run():
        block = server.CustomDataBlock(device_address=247, mqtt_client=None, latency_budget=server.LatencyBudget())
        block.addresses[GridStatus.ADDRESS] = SimpleNamespace(address=GridStatus.ADDRESS, count=1, publishable=True, debug_logging=False)
        voltage = _grid_sensor(GridPhaseVoltage, "A")
        block.addresses[voltage.address] = voltage
        registers: dict[int, int] = {voltage.address: 0, voltage.address + 1: 23000, GridStatus.ADDRESS: 0}
        history: list[tuple[int, list[int]]] = []

        async def set_values(_unit, _fc, addr, vals):
            history.append((addr, list(vals)))
            for i, v in enumerate(vals):
                registers[addr + i] = v

        async def get_values(_unit, _fc, addr, count):
            return [registers.get(addr + i, 0) for i in range(count)]

        block._server = Mock()
        block._server.context = Mock()
        block._server.context.async_setValues = AsyncMock(side_effect=set_values)
        block._server.context.async_getValues = AsyncMock(side_effect=get_values)

        await asyncio.wait_for(server.simulate_grid_outage(block, wait_for_seconds=0, duration_seconds=0, repeated=False), timeout=5)

        assert history == [
            (GridStatus.ADDRESS, [1]),
            (voltage.address, [0, 0]),
            (voltage.address, [0, 23000]),
            (GridStatus.ADDRESS, [0]),
        ]

    asyncio.run(_run())


@pytest.mark.asyncio
async def test_power_limits_use_v2_9_rules_when_v2_10_firmware_lacks_global_enable(monkeypatch):
    """V2.10 can be detected from other registers; without 40162 the V2.9 gating still applies."""
    from sigenergy2mqtt.common import HybridInverter
    from tests.utils import modbus_sensors

    def hybrid_without_global_enable(**kwargs):
        kwargs["has_remote_ems_power_limit_global_enable"] = False
        return HybridInverter(**kwargs)

    monkeypatch.setattr(modbus_sensors, "HybridInverter", hybrid_without_global_enable)
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10)
        assert _by_class(sensors, RemoteEMSPowerLimitGlobalEnable) == []
        assert len(_by_class(sensors, GridPhaseCurrent)) == 3  # Other V2.10 sensors are unaffected
        for cls in (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit):
            (limit,) = _by_class(sensors, cls)
            assert isinstance(limit._availability_control_sensor, RemoteEMS), cls.__name__
            assert limit._remote_ems_mode is not None, cls.__name__
            assert limit._global_enable is None, cls.__name__
            assert "40162" not in limit.get_attributes()["comment"], cls.__name__


@pytest.mark.parametrize(
    ("firmware", "expected"),
    [("V100R001C00SPC112B107G", False), ("V100R001C00SPC113", True), ("V100R001C00SPC115B100", True), ("V100R001C00SPC116", True), ("V100R001C00SPC117", False), ("V100R001C00SPC118", False)],
)
def test_firmware_has_global_power_limits(firmware, expected):
    from sigenergy2mqtt.common import FirmwareVersion

    assert FirmwareVersion(firmware).has_global_power_limits is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(("firmware", "gated"), [("V100R001C00SPC116", False), ("V100R001C00SPC117", True), ("V100R001C00SPC118", True)])
async def test_power_limit_gating_by_firmware_without_global_enable(monkeypatch, firmware, gated):
    """SPC113 to SPC116 applied the limits globally; SPC117 and later require Remote EMS again unless 40162 is available."""
    from sigenergy2mqtt.common import HybridInverter
    from tests.utils import modbus_sensors

    def hybrid_without_global_enable(**kwargs):
        kwargs["has_remote_ems_power_limit_global_enable"] = False
        return HybridInverter(**kwargs)

    monkeypatch.setattr(modbus_sensors, "HybridInverter", hybrid_without_global_enable)
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10, firmware_version=firmware)
        for cls in (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit):
            (limit,) = _by_class(sensors, cls)
            assert isinstance(limit._availability_control_sensor, RemoteEMS) is gated, cls.__name__
            assert (limit._remote_ems_mode is not None) is gated, cls.__name__
            assert limit._global_enable is None, cls.__name__


@pytest.mark.asyncio
async def test_global_enable_takes_precedence_over_firmware(monkeypatch):
    """With 40162 available, the V2.10 rules apply whatever the firmware service pack."""
    with _swap_active_config(Config()):
        sensors = await get_sensor_instances(protocol_version=ProtocolVersion.V2_10, firmware_version="V100R001C00SPC117")
        (limit,) = _by_class(sensors, MaxChargingLimit)
        assert limit._availability_control_sensor is None
        assert isinstance(limit._global_enable, RemoteEMSPowerLimitGlobalEnable)


# ---------------------------------------------------------------------------
# Home Assistant availability of the power limits (protocol V2.10)
# ---------------------------------------------------------------------------


async def _ha_sensors() -> dict:
    cfg = Config()
    cfg.home_assistant.enabled = True
    with _swap_active_config(cfg):
        return await get_sensor_instances(home_assistant_enabled=True, protocol_version=ProtocolVersion.V2_10)


@pytest.mark.asyncio
async def test_power_limits_availability_uses_combined_topic():
    sensors = await _ha_sensors()
    (global_enable,) = _by_class(sensors, RemoteEMSPowerLimitGlobalEnable)
    (remote_ems,) = _by_class(sensors, RemoteEMS)
    assert remote_ems.power_limit_global_enable is global_enable
    assert global_enable.power_limits_active_topic and global_enable.power_limits_active_topic.endswith("/power_limits_active")
    for cls in (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit):
        (limit,) = _by_class(sensors, cls)
        topics = [a["topic"] for a in limit["availability"]]
        assert global_enable.power_limits_active_topic in topics, cls.__name__
        assert remote_ems["state_topic"] not in topics, cls.__name__  # Not gated on Remote EMS alone


@pytest.mark.asyncio
@pytest.mark.parametrize(("remote_ems_state", "global_enable_state", "expected"), [(0, 0, "0"), (1, 0, "1"), (0, 1, "1"), (1, 1, "1"), (None, None, "0")])
async def test_power_limits_active_published_when_either_switch_is_on(remote_ems_state, global_enable_state, expected):
    sensors = await _ha_sensors()
    (global_enable,) = _by_class(sensors, RemoteEMSPowerLimitGlobalEnable)
    (remote_ems,) = _by_class(sensors, RemoteEMS)
    for sensor, state in ((remote_ems, remote_ems_state), (global_enable, global_enable_state)):
        sensor._states.clear()
        if state is not None:
            sensor._states.append((0.0, state))

    cfg = Config()
    cfg.home_assistant.enabled = True
    mqtt_client = Mock()
    with _swap_active_config(cfg):
        global_enable.publish_power_limits_active(mqtt_client)
    mqtt_client.publish.assert_called_once()
    topic, payload = mqtt_client.publish.call_args.args[:2]
    assert topic == global_enable.power_limits_active_topic
    assert payload == expected


@pytest.mark.asyncio
async def test_remote_ems_publish_updates_combined_topic(monkeypatch):
    sensors = await _ha_sensors()
    (global_enable,) = _by_class(sensors, RemoteEMSPowerLimitGlobalEnable)
    (remote_ems,) = _by_class(sensors, RemoteEMS)
    calls = []
    monkeypatch.setattr(global_enable, "publish_power_limits_active", lambda client: calls.append(client))

    from sigenergy2mqtt.sensors.base.writeable import SwitchSensor

    async def fake_super_publish(self, mqtt_client, transport, republish=False):
        return True

    monkeypatch.setattr(SwitchSensor, "publish", fake_super_publish)
    client = Mock()
    assert await remote_ems.publish(client, None) is True
    assert await global_enable.publish(client, None) is True
    assert calls == [client, client]  # Published after either switch publishes
