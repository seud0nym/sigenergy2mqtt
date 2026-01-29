import logging
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.sensors.base import DerivedSensor, ReadableSensorMixin, Sensor


@pytest.fixture(autouse=True)
def mock_config():
    old_modbus = getattr(Config, "modbus", [])
    old_ha = getattr(Config, "home_assistant", None)
    old_path = getattr(Config, "persistent_state_path", None)

    Config.modbus = [types.SimpleNamespace(registers={}, disable_chunking=False)]
    Config.home_assistant = types.SimpleNamespace(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
    )
    Config.persistent_state_path = Path(".")

    yield

    Config.modbus = old_modbus
    Config.home_assistant = old_ha
    Config.persistent_state_path = old_path


@pytest.fixture(autouse=True)
def cleanup_registry():
    DeviceRegistry._devices.clear()
    yield
    DeviceRegistry._devices.clear()


class DummyDerived(DerivedSensor):
    def __init__(self, unique_id, protocol_version=Protocol.N_A):
        dict.__init__(self)  # Initialize dict!
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "protocol_version", protocol_version)
        object.__setattr__(self, "debug_logging", True)
        object.__setattr__(self, "_derived_sensors", {})

    def add_derived_sensor(self, sensor):
        pass

    def apply_sensor_overrides(self, registers):
        pass

    def configure_mqtt_topics(self, device_id):
        pass

    @property
    def name(self):
        return self.unique_id


class DummySensor(ReadableSensorMixin):
    def __init__(self, unique_id, protocol_version=Protocol.N_A):
        dict.__init__(self)  # Initialize dict!
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "protocol_version", protocol_version)
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "scan_interval", 60)
        object.__setattr__(self, "address", 0)
        object.__setattr__(self, "count", 1)
        object.__setattr__(self, "device_address", 1)
        object.__setattr__(self, "input_type", "holding")
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "_publishable", True)

    def add_derived_sensor(self, sensor):
        pass

    def apply_sensor_overrides(self, registers):
        pass

    def configure_mqtt_topics(self, device_id):
        pass

    @property
    def name(self):
        return self.unique_id

    async def publish(self, *args, **kwargs):
        pass


def test_add_derived_sensor_skips_newer_protocol(caplog):
    """Test that a derived sensor with newer protocol version than device is skipped."""
    caplog.set_level(logging.DEBUG)

    device = Device("test_dev", 0, "test_id", "manu", "model", protocol_version=Protocol.V1_8)

    # Create a sensor with newer protocol
    sensor = DummyDerived("newer_sensor", protocol_version=Protocol.V2_0)
    source = DummySensor("source", protocol_version=Protocol.V1_8)

    # Add source
    device._add_read_sensor(source)

    # Try to add derived sensor
    device._add_derived_sensor(sensor, source)

    # Should verify it was NOT added to all_sensors
    # This assertion is expected to FAIL with the current bug as it will be added
    if "newer_sensor" in device.all_sensors:
        pytest.fail("newer_sensor was added but should have been skipped due to protocol version mismatch")

    assert "skipped adding DummyDerived - Protocol version" in caplog.text


def test_add_derived_sensor_skips_newer_source_protocol(caplog):
    """Test that if a source sensor has newer protocol, the derived sensor is skipped."""
    caplog.set_level(logging.DEBUG)

    device = Device("test_dev", 0, "test_id", "manu", "model", protocol_version=Protocol.V1_8)

    sensor = DummyDerived("ok_sensor", protocol_version=Protocol.V1_8)
    source = DummySensor("newer_source", protocol_version=Protocol.V2_0)

    device._add_read_sensor(source)

    device._add_derived_sensor(sensor, source)

    if "ok_sensor" in device.all_sensors:
        pytest.fail("ok_sensor was added but should have been skipped due to source sensor protocol version mismatch")

    assert "skipped adding DummyDerived - one or more source sensors have Protocol version" in caplog.text


def test_add_derived_sensor_ok_protocol(caplog):
    """Test that compatible protocol versions allow adding."""
    device = Device("test_dev", 0, "test_id", "manu", "model", protocol_version=Protocol.V2_0)

    sensor = DummyDerived("ok_sensor", protocol_version=Protocol.V1_8)
    source = DummySensor("source", protocol_version=Protocol.V1_8)

    device._add_read_sensor(source)

    device._add_derived_sensor(sensor, source)

    assert "ok_sensor" in device.all_sensors
