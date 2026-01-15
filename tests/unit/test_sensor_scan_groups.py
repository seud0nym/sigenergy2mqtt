"""Tests for sensor scan group creation and publish_updates per-sensor timing."""

import asyncio
import time
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, ReadableSensorMixin, Sensor
from sigenergy2mqtt.sensors.const import MAX_MODBUS_REGISTERS_PER_REQUEST, InputType


class DummyModbusSensor(ModbusSensorMixin, ReadableSensorMixin):
    """Minimal Modbus sensor for testing."""

    def __init__(self, unique_id: str, address: int, count: int = 1, device_address: int = 1, scan_interval: int = 10):
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "input_type", InputType.HOLDING)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)

    async def _update_internal_state(self, **kwargs) -> bool:
        return False

    def configure_mqtt_topics(self, device_id: str) -> str:
        return ""

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None = None, republish: bool = False) -> bool:
        self._states.append((time.time(), 1))
        return True


@pytest.fixture
def mock_config():
    """Setup minimal Config for Device tests."""
    conf = cast(Any, Config)
    original_devices = conf.modbus if hasattr(conf, "devices") else []
    original_ha = conf.home_assistant if hasattr(conf, "home_assistant") else None

    class D:
        registers = {}
        disable_chunking = False

    conf.modbus = [D()]
    conf.home_assistant = types.SimpleNamespace(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
        entity_id_prefix="sigen",
        use_simplified_topics=False,
        edit_percentage_with_box=False,
    )
    conf.persistent_state_path = Path(".")

    yield conf

    conf.modbus = original_devices
    if original_ha:
        conf.home_assistant = original_ha
    DeviceRegistry._devices.clear()


class TestCreateSensorScanGroups:
    """Tests for _create_sensor_scan_groups."""

    def test_ignores_scan_interval(self, mock_config):
        """Sensors with different scan_intervals but same device_address and contiguous addresses should be grouped together."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Create sensors with different scan_intervals but contiguous addresses
        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1, scan_interval=5)
        s2 = DummyModbusSensor("s2", address=101, count=1, device_address=1, scan_interval=10)
        s3 = DummyModbusSensor("s3", address=102, count=1, device_address=1, scan_interval=60)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))
        dev._add_read_sensor(cast(Sensor, s3))

        groups = dev._create_sensor_scan_groups()

        # All three sensors should be in the same group
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) == 1
        assert len(modbus_groups[0]) == 3

    def test_splits_by_device_address(self, mock_config):
        """Sensors with different device_address should be in separate groups."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1, scan_interval=10)
        s2 = DummyModbusSensor("s2", address=101, count=1, device_address=2, scan_interval=10)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))

        groups = dev._create_sensor_scan_groups()

        # Should be in separate groups due to different device_address
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) == 2

    def test_splits_on_address_gap(self, mock_config):
        """Sensors with non-contiguous addresses should be in separate groups."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1, scan_interval=10)
        s2 = DummyModbusSensor("s2", address=200, count=1, device_address=1, scan_interval=10)  # Gap

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))

        groups = dev._create_sensor_scan_groups()

        # Should be in separate groups due to address gap
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) == 2

    def test_respects_max_registers(self, mock_config):
        """Groups should be split when exceeding MAX_MODBUS_REGISTERS_PER_REQUEST."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Create sensors that exceed the max register limit
        sensors = []
        address = 100
        total_count = 0
        while total_count < MAX_MODBUS_REGISTERS_PER_REQUEST + 10:
            s = DummyModbusSensor(f"s{address}", address=address, count=5, device_address=1, scan_interval=10)
            sensors.append(s)
            dev._add_read_sensor(cast(Sensor, s))
            address += 5
            total_count += 5

        groups = dev._create_sensor_scan_groups()

        # Should be split into multiple groups
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) >= 2

    def test_handles_reserved_sensors(self, mock_config):
        """Reserved sensors should not start or end a group."""
        from sigenergy2mqtt.devices.device import ReservedSensor

        class DummyReservedSensor(ReservedSensor):
            def __init__(self, address: int):
                self["unique_id"] = f"reserved_{address}"
                self["object_id"] = f"reserved_{address}"
                self["platform"] = "sensor"
                object.__setattr__(self, "unique_id", f"reserved_{address}")
                object.__setattr__(self, "object_id", f"reserved_{address}")
                object.__setattr__(self, "address", address)
                object.__setattr__(self, "count", 1)
                object.__setattr__(self, "device_address", 1)
                object.__setattr__(self, "scan_interval", 10)
                object.__setattr__(self, "input_type", InputType.HOLDING)
                object.__setattr__(self, "_publishable", False)
                object.__setattr__(self, "debug_logging", False)

        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Create sequence: Reserved, Real, Reserved, Real, Reserved
        r1 = DummyReservedSensor(100)
        s1 = DummyModbusSensor("s1", address=101, count=1, device_address=1, scan_interval=10)
        r2 = DummyReservedSensor(102)
        s2 = DummyModbusSensor("s2", address=103, count=1, device_address=1, scan_interval=10)
        r3 = DummyReservedSensor(104)

        dev._add_read_sensor(cast(Sensor, r1))
        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, r2))
        dev._add_read_sensor(cast(Sensor, s2))
        dev._add_read_sensor(cast(Sensor, r3))

        groups = dev._create_sensor_scan_groups()

        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) == 1
        group = modbus_groups[0]

        # r1 is skipped (start of group)
        # r3 is trimmed (end of group)
        # r2 remains (middle of group)
        assert len(group) == 3
        assert group[0] == s1
        assert group[1] == r2
        assert group[2] == s2

    def test_respects_disable_chunking_true(self, mock_config):
        """Verify that contiguous sensors are NOT grouped when disable_chunking is True."""
        mock_config.modbus[0].disable_chunking = True
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1)
        s2 = DummyModbusSensor("s2", address=101, count=1, device_address=1)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))

        groups = dev._create_sensor_scan_groups()
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be split into 2 groups despite being contiguous
        assert len(modbus_groups) == 2
        assert len(modbus_groups[0]) == 1
        assert len(modbus_groups[1]) == 1

    def test_respects_disable_chunking_false(self, mock_config):
        """Verify that contiguous sensors ARE grouped when disable_chunking is False."""
        mock_config.modbus[0].disable_chunking = False
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1)
        s2 = DummyModbusSensor("s2", address=101, count=1, device_address=1)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))

        groups = dev._create_sensor_scan_groups()
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be in 1 group
        assert len(modbus_groups) == 1
        assert len(modbus_groups[0]) == 2

    def test_named_groups_ignore_disable_chunking(self, mock_config):
        """Verify that sensors in a named group REMAIN grouped even when disable_chunking is True."""
        mock_config.modbus[0].disable_chunking = True
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100)
        s2 = DummyModbusSensor("s2", address=101)

        # Add both to the same named group
        dev._add_read_sensor(cast(Sensor, s1), group="MyGroup")
        dev._add_read_sensor(cast(Sensor, s2), group="MyGroup")

        groups = dev._create_sensor_scan_groups()

        # "MyGroup" should exist and contain both sensors
        assert "MyGroup" in groups
        assert len(groups["MyGroup"]) == 2
        assert s1 in groups["MyGroup"]
        assert s2 in groups["MyGroup"]


class TestPublishUpdates:
    """Tests for publish_updates per-sensor timing."""

    @pytest.mark.asyncio
    async def test_respects_individual_scan_intervals(self, mock_config):
        """Sensors with different scan_intervals should publish at their own rates."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Fast sensor (1s) and slow sensor (5s) - both with force_publish to trigger immediate publish
        fast = DummyModbusSensor("fast", address=100, count=1, device_address=1, scan_interval=1)
        slow = DummyModbusSensor("slow", address=101, count=1, device_address=1, scan_interval=5)
        fast.force_publish = True  # Force immediate publish
        slow.force_publish = True  # Force immediate publish

        dev._add_read_sensor(cast(Sensor, fast))
        dev._add_read_sensor(cast(Sensor, slow))

        modbus_client = MagicMock(spec=ModbusClient)
        modbus_client.read_ahead_registers = AsyncMock(return_value=0)
        mqtt_client = MagicMock(spec=mqtt.Client)

        # Mock the lock with proper async context manager
        with patch("sigenergy2mqtt.devices.device.ModbusLockFactory") as mock_lock_factory:
            # Create a proper async context manager for the lock
            async_cm = AsyncMock()
            async_cm.__aenter__ = AsyncMock(return_value=None)
            async_cm.__aexit__ = AsyncMock(return_value=False)

            mock_lock = MagicMock()
            mock_lock.lock = MagicMock(return_value=async_cm)
            mock_lock.waiters = 0
            mock_lock_factory.get.return_value = mock_lock

            # Run for a short time then stop
            dev._online = True

            async def stop_after_delay():
                await asyncio.sleep(0.2)
                dev._online = False

            asyncio.create_task(stop_after_delay())

            # This will run briefly and exit when online becomes False
            await dev.publish_updates(modbus_client, mqtt_client, "test_group", fast, slow)

        # Both sensors should have been published at least once
        assert len(fast._states) >= 1, f"Fast sensor not published: {fast._states}"
        assert len(slow._states) >= 1, f"Slow sensor not published: {slow._states}"

    @pytest.mark.asyncio
    async def test_handles_force_publish(self, mock_config):
        """Setting force_publish should cause immediate publishing."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        sensor = DummyModbusSensor("s1", address=100, count=1, device_address=1, scan_interval=60)
        sensor.force_publish = True  # Force immediate publish

        dev._add_read_sensor(cast(Sensor, sensor))

        modbus_client = MagicMock(spec=ModbusClient)
        modbus_client.read_ahead_registers = AsyncMock(return_value=0)
        mqtt_client = MagicMock(spec=mqtt.Client)

        with patch("sigenergy2mqtt.devices.device.ModbusLockFactory") as mock_lock_factory:
            # Create a proper async context manager for the lock
            async_cm = AsyncMock()
            async_cm.__aenter__ = AsyncMock(return_value=None)
            async_cm.__aexit__ = AsyncMock(return_value=False)

            mock_lock = MagicMock()
            mock_lock.lock = MagicMock(return_value=async_cm)
            mock_lock.waiters = 0
            mock_lock_factory.get.return_value = mock_lock

            dev._online = True

            async def stop_after_delay():
                await asyncio.sleep(0.1)
                dev._online = False

            asyncio.create_task(stop_after_delay())

            await dev.publish_updates(modbus_client, mqtt_client, "test_group", sensor)

        # Should have published due to force_publish
        assert len(sensor._states) >= 1
        # force_publish should be reset
        assert not sensor.force_publish
