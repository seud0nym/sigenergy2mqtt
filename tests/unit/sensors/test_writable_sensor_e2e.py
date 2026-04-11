from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from pymodbus.client.mixin import ModbusClientMixin

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import NumericSensor, SelectSensor, SwitchSensor, WritableSensorMixin, WriteOnlySensor
from sigenergy2mqtt.sensors.base.constants import DiscoveryKeys
from sigenergy2mqtt.sensors.plant_read_write import MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit, RemoteEMSLimit
from tests.utils.modbus_sensors import get_sensor_instances


REMOTE_EMS_LIMIT_TYPES = (MaxChargingLimit, MaxDischargingLimit, PVMaxPowerLimit)


async def _get_writable_sensors() -> list[WritableSensorMixin]:
    cfg = Config()
    cfg.home_assistant.enabled = True
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.ems_mode_check = True

    with _swap_active_config(cfg):
        sensors = await get_sensor_instances(home_assistant_enabled=True, concrete_sensor_check=False)

    return [sensor for sensor in sensors.values() if isinstance(sensor, WritableSensorMixin)]


def _build_modbus() -> MagicMock:
    modbus = MagicMock()
    modbus.DATATYPE = ModbusClientMixin.DATATYPE
    modbus.convert_to_registers = MagicMock(side_effect=lambda value, data_type: ModbusClientMixin.convert_to_registers(int(value), data_type))
    ok = MagicMock()
    ok.isError.return_value = False
    modbus.write_register = AsyncMock(return_value=ok)
    modbus.write_registers = AsyncMock(return_value=ok)
    return modbus


def _ensure_command_topic(sensor: WritableSensorMixin) -> str:
    if DiscoveryKeys.COMMAND_TOPIC not in sensor:
        sensor.configure_mqtt_topics("e2e")
    return str(sensor[DiscoveryKeys.COMMAND_TOPIC])


def _pick_numeric_values(sensor: NumericSensor) -> tuple[float, float]:
    minimum = sensor.get(DiscoveryKeys.MIN)
    maximum = sensor.get(DiscoveryKeys.MAX)

    if isinstance(minimum, (float, int)) and isinstance(maximum, (float, int)):
        return float(minimum), float(maximum) + 1

    if isinstance(minimum, tuple) and isinstance(maximum, tuple):
        return float(minimum[0]), 0.0

    if isinstance(maximum, (float, int)):
        return float(maximum), float(maximum) + 1

    if isinstance(minimum, (float, int)):
        return float(minimum), float(minimum) - 1

    return 1.0, -1.0






def _set_latest_raw_state(sensor: Any, value: float | int | str) -> None:
    sensor._states = [(0.0, value)]

async def _find_invalid_numeric_value(sensor: NumericSensor, valid: float, topic: str, mqtt: MagicMock, handler: MagicMock) -> float | None:
    minimum = sensor.get(DiscoveryKeys.MIN)
    maximum = sensor.get(DiscoveryKeys.MAX)
    if isinstance(minimum, (int, float)):
        return float(minimum) - 1
    if isinstance(maximum, (int, float)):
        return float(maximum) + 1
    if isinstance(minimum, tuple) and isinstance(maximum, tuple):
        return 0.0
    return None


def _prepare_sensor_for_valid_write(sensor: WritableSensorMixin) -> None:
    control = getattr(sensor, "_availability_control_sensor", None)
    if control is not None:
        _set_latest_raw_state(control, 1)

    if isinstance(sensor, REMOTE_EMS_LIMIT_TYPES):
        mode = getattr(sensor, "_remote_ems_mode", None)
        if mode is not None:
            if sensor.__class__.__name__ in {"MaxChargingLimit", "PVMaxPowerLimit"}:
                _set_latest_raw_state(mode, 3)
            else:
                _set_latest_raw_state(mode, 5)

def test_all_writable_sensor_types_write_expected_registers_and_set_force_publish() -> None:
    async def _run() -> None:
        writable = await _get_writable_sensors()
        assert writable

        mqtt = MagicMock()
        handler = MagicMock()

        for sensor in writable:
            modbus = _build_modbus()
            topic = _ensure_command_topic(sensor)
            _prepare_sensor_for_valid_write(sensor)

            if isinstance(sensor, NumericSensor):
                valid, _ = _pick_numeric_values(sensor)
                invalid = await _find_invalid_numeric_value(sensor, valid, topic, mqtt, handler)
                assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True

                gain = sensor.gain or 1
                expected_raw = int(float(valid) * gain)
                expected_registers = ModbusClientMixin.convert_to_registers(expected_raw, sensor.data_type)
                if len(expected_registers) == 1:
                    modbus.write_register.assert_awaited_with(sensor.address, expected_registers[0], device_id=sensor.device_address, no_response_expected=False)
                else:
                    modbus.write_registers.assert_awaited_with(sensor.address, expected_registers, device_id=sensor.device_address, no_response_expected=False)

                if invalid is not None:
                    assert sensor.force_publish is True
                    sensor.force_publish = False
                    try:
                        await sensor.set_value(modbus, mqtt, invalid, topic, handler)
                    except Exception:
                        pass
                    assert sensor.force_publish is True

            elif isinstance(sensor, SelectSensor):
                options = [option for option in sensor[DiscoveryKeys.OPTIONS] if option != ""]
                assert options
                valid = options[0]
                invalid: Any = "" if "" in sensor[DiscoveryKeys.OPTIONS] else "__invalid_option__"

                assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
                expected_index = sensor[DiscoveryKeys.OPTIONS].index(valid)
                modbus.write_register.assert_awaited_with(sensor.address, expected_index, device_id=sensor.device_address, no_response_expected=False)

                if invalid is not None:
                    assert sensor.force_publish is True
                    sensor.force_publish = False
                    assert await sensor.set_value(modbus, mqtt, invalid, topic, handler) is False
                    assert sensor.force_publish is True

            elif isinstance(sensor, SwitchSensor):
                valid = sensor[DiscoveryKeys.PAYLOAD_ON]
                assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
                modbus.write_register.assert_awaited_with(sensor.address, int(valid), device_id=sensor.device_address, no_response_expected=False)

                assert sensor.force_publish is True
                sensor.force_publish = False
                assert await sensor.set_value(modbus, mqtt, 2, topic, handler) is False
                assert sensor.force_publish is True

            elif isinstance(sensor, WriteOnlySensor):
                valid = sensor._payloads["on"]
                assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
                modbus.write_register.assert_awaited_with(sensor.address, sensor._values["on"], device_id=sensor.device_address, no_response_expected=False)

                assert sensor.force_publish is True
                sensor.force_publish = False
                assert await sensor.set_value(modbus, mqtt, "__invalid_payload__", topic, handler) is False
                assert sensor.force_publish is True

    asyncio.run(_run())


def test_availability_control_sensor_gates_writes_for_non_remote_ems_sensors() -> None:
    async def _run() -> None:
        writable = await _get_writable_sensors()
        targets = [
            sensor
            for sensor in writable
            if isinstance(sensor, SelectSensor)
            and hasattr(sensor, "_availability_control_sensor")
            and getattr(sensor, "_availability_control_sensor") is not None
            and not isinstance(sensor, RemoteEMSLimit)
        ]
        assert targets

        mqtt = MagicMock()
        handler = MagicMock()

        for sensor in targets:
            control = getattr(sensor, "_availability_control_sensor")
            assert control is not None
            valid = sensor[DiscoveryKeys.OPTIONS][0] if sensor[DiscoveryKeys.OPTIONS][0] != "" else sensor[DiscoveryKeys.OPTIONS][1]
            topic = _ensure_command_topic(sensor)

            modbus = _build_modbus()
            _set_latest_raw_state(control, 1)
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
            assert sensor.force_publish is True

            modbus = _build_modbus()
            _set_latest_raw_state(control, 0)
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is False
            assert sensor.force_publish is True

    asyncio.run(_run())


def test_remote_ems_limit_requires_both_checks_when_availability_control_is_set() -> None:
    async def _run() -> None:
        writable = await _get_writable_sensors()
        remote_limits = [sensor for sensor in writable if isinstance(sensor, REMOTE_EMS_LIMIT_TYPES)]
        assert remote_limits

        mqtt = MagicMock()
        handler = MagicMock()

        for sensor in remote_limits:
            valid, _ = _pick_numeric_values(sensor)
            topic = _ensure_command_topic(sensor)

            control = getattr(sensor, "_availability_control_sensor")
            mode = getattr(sensor, "_remote_ems_mode")
            assert control is not None
            assert mode is not None

            modbus = _build_modbus()
            _set_latest_raw_state(control, 0)
            _set_latest_raw_state(mode, 0)
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is False
            assert sensor.force_publish is True

            modbus = _build_modbus()
            _set_latest_raw_state(control, 1)
            _set_latest_raw_state(mode, 0)
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is False
            assert sensor.force_publish is True

            modbus = _build_modbus()
            _set_latest_raw_state(control, 1)
            _set_latest_raw_state(mode, 3 if sensor.__class__.__name__ in {"MaxChargingLimit", "PVMaxPowerLimit"} else 5)
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
            assert sensor.force_publish is True

    asyncio.run(_run())


def test_remote_ems_limit_skips_checks_when_availability_control_sensor_is_none() -> None:
    async def _run() -> None:
        writable = await _get_writable_sensors()
        remote_limits = [sensor for sensor in writable if isinstance(sensor, REMOTE_EMS_LIMIT_TYPES)]
        assert remote_limits

        mqtt = MagicMock()
        handler = MagicMock()

        for sensor in remote_limits:
            valid, _ = _pick_numeric_values(sensor)
            topic = _ensure_command_topic(sensor)

            sensor._availability_control_sensor = None
            sensor._remote_ems_mode = SimpleNamespace(_latest_raw_state=0, latest_raw_state=0)

            modbus = _build_modbus()
            sensor.force_publish = False
            assert await sensor.set_value(modbus, mqtt, valid, topic, handler) is True
            assert sensor.force_publish is True

    asyncio.run(_run())
