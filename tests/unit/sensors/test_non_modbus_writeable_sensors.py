"""Tests for transport-independent writable sensor mixins."""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.config.sensors import ApplicationLogLevel
from sigenergy2mqtt.sensors.base import (
    NumericSensorMixin,
    SelectSensorMixin,
    Sensor,
    SwitchSensorMixin,
    WriteableSensorMixin,
    WriteOnlySensorMixin,
)


class _NonModbusWriteableSensor(WriteableSensorMixin, Sensor):
    """A writable sensor backed by an in-memory service rather than Modbus."""

    async def _update_internal_state(self, **kwargs):
        return False

    async def _write_value(self, modbus_client, mqtt_client, value, source, handler):
        self.written_value = value
        self.written_source = source
        return True


class NonModbusNumericSensor(NumericSensorMixin, _NonModbusWriteableSensor):
    pass


class NonModbusSelectSensor(SelectSensorMixin, _NonModbusWriteableSensor):
    pass


class NonModbusSwitchSensor(SwitchSensorMixin, _NonModbusWriteableSensor):
    pass


class NonModbusWriteOnlySensor(WriteOnlySensorMixin, _NonModbusWriteableSensor):
    pass


@pytest.fixture(autouse=True)
def config():
    cfg = Config()
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.sensor_overrides = {}
    with _swap_active_config(cfg):
        yield


@pytest.fixture(autouse=True)
def reset_sensor_ids():
    with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        yield


def sensor_kwargs(name: str) -> dict:
    return {
        "name": name,
        "unique_id": f"sigen_{name}",
        "object_id": f"sigen_{name}",
        "unit": None,
        "device_class": None,
        "state_class": None,
        "icon": "mdi:test-tube",
        "gain": 1,
        "precision": 0,
        "protocol_version": ProtocolVersion.V2_4,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor_class", "extra_kwargs", "command", "expected"),
    [
        (NonModbusNumericSensor, {"minimum": 0, "maximum": 100}, "12", 12),
        (NonModbusSelectSensor, {"options": ["Automatic", "Manual"]}, "Manual", 1),
        (NonModbusSwitchSensor, {}, "1", 1),
        (NonModbusWriteOnlySensor, {}, "on", 1),
        (NonModbusWriteOnlySensor, {}, "off", 0),
    ],
)
async def test_writable_entity_mixins_dispatch_commands_without_modbus(sensor_class, extra_kwargs, command, expected):
    sensor = sensor_class(**sensor_kwargs(f"{sensor_class.__name__.lower()}_{command}"), **extra_kwargs)
    sensor.configure_mqtt_topics("test-device")

    assert await sensor.set_value(None, MagicMock(), command, sensor.command_topic, MagicMock()) is True
    assert sensor.written_value == expected
    assert sensor.written_source == sensor.command_topic
    assert not hasattr(sensor, "address")


def test_switch_mixin_sets_binary_raw_sanity_bounds():
    sensor = NonModbusSwitchSensor(**sensor_kwargs("switch_bounds"))

    assert sensor.sanity_check.min_raw == 0
    assert sensor.sanity_check.max_raw == 1


def test_settings_writeable_sensor_configures_command_topic():
    sensor = ApplicationLogLevel()

    sensor.configure_mqtt_topics("test-device")

    assert sensor.command_topic == "sigenergy2mqtt/config/log_level/set"


@pytest.mark.asyncio
async def test_numeric_mixin_matches_modbus_range_validation_and_state_clamping():
    sensor = NonModbusNumericSensor(**sensor_kwargs("numeric_range"), minimum=(-10.0, -5.0), maximum=(5.0, 10.0))
    sensor.set_latest_state(-4.0)

    assert await sensor.value_is_valid(None, -7) is True
    assert await sensor.value_is_valid(None, -4) is False
    assert await sensor.value_is_valid(None, 7) is True
    assert await sensor.value_is_valid(None, 4) is False
    assert await sensor.get_state(republish=True) == -10.0


@pytest.mark.asyncio
async def test_select_mixin_matches_modbus_state_conversion():
    sensor = NonModbusSelectSensor(**sensor_kwargs("select_state"), options=["Automatic", "Manual"])
    sensor.set_latest_state(1)

    assert await sensor.get_state(republish=True) == "Manual"
    assert await sensor.get_state(raw=True, republish=True) == 1


def test_write_only_mixin_discovery_components():
    sensor = NonModbusWriteOnlySensor(**sensor_kwargs("btn_test"))
    comps = sensor.get_discovery_components()

    assert f"{sensor.unique_id}_on" in comps
    assert f"{sensor.unique_id}_off" in comps
    assert comps[f"{sensor.unique_id}_on"]["payload_press"] == "on"
    assert comps[f"{sensor.unique_id}_off"]["payload_press"] == "off"
    assert comps[f"{sensor.unique_id}_on"]["platform"] == "button"
    assert comps[f"{sensor.unique_id}_off"]["platform"] == "button"


@pytest.mark.asyncio
async def test_write_only_mixin_validation_and_raw2state():
    sensor = NonModbusWriteOnlySensor(**sensor_kwargs("btn_valid"))

    assert await sensor._update_internal_state() is False
    assert await sensor.value_is_valid(None, 1) is True
    assert await sensor.value_is_valid(None, 0) is True
    assert await sensor.value_is_valid(None, 2) is False
    assert sensor._raw2state("0") == "Power Off"
    assert sensor._raw2state(0) == "Power Off"
    assert sensor._raw2state("off") == "Power Off"
    assert sensor._raw2state("1") == "Power On"
    assert sensor._raw2state(1) == "Power On"
    assert sensor._raw2state("on") == "Power On"
    assert sensor._raw2state("unknown") == "unknown"


def test_write_only_mixin_validates_icons():
    with pytest.raises(ValueError, match="on icon.*does not start with 'mdi:'"):
        NonModbusWriteOnlySensor(**sensor_kwargs("bad_on"), icon_on="invalid")

    with pytest.raises(ValueError, match="off icon.*does not start with 'mdi:'"):
        NonModbusWriteOnlySensor(**sensor_kwargs("bad_off"), icon_off="invalid")
