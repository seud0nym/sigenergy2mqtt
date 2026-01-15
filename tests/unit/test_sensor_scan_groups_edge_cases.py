import asyncio
import types
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

    async def publish(self, mqtt_client: Any, modbus_client: Any | None = None, republish: bool = False) -> bool:
        return True


@pytest.fixture
def mock_config():
    """Setup minimal Config for Device tests."""
    conf = cast(Any, Config)
    original_devices = conf.devices if hasattr(conf, "devices") else []
    original_ha = conf.home_assistant if hasattr(conf, "home_assistant") else None

    class D:
        registers = {}
        disable_chunking = False

    conf.devices = [D()]
    conf.home_assistant = types.SimpleNamespace(
        device_name_prefix="",
        unique_id_prefix="sigen",
        discovery_prefix="homeassistant",
        enabled=False,
        republish_discovery_interval=0,
    )
    # Set logging to see debug messages if needed
    conf.sensor_debug_logging = True

    yield conf

    conf.devices = original_devices
    if original_ha:
        conf.home_assistant = original_ha
    DeviceRegistry._devices.clear()


class TestSensorScanGroupsEdgeCases:
    """Tests for complex register grouping edge cases."""

    def test_splits_on_single_register_gap(self, mock_config):
        """Verify that a gap of even 1 register causes a split."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Gap of 1 register:
        # Sensor 1: 100 (count 1)
        # Gap: 101
        # Sensor 2: 102 (count 1)
        s1 = DummyModbusSensor("s1", address=100, count=1)
        s2 = DummyModbusSensor("s2", address=102, count=1)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2))

        groups = dev._create_sensor_scan_groups()
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be 2 groups because 101 is missing and not bridged
        assert len(modbus_groups) == 2
        assert len(modbus_groups[0]) == 1
        assert len(modbus_groups[1]) == 1

    def test_max_registers_boundary_exact(self, mock_config):
        """Verify grouping behavior exactly at and exceeding the MAX_MODBUS_REGISTERS_PER_REQUEST limit."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        sensors_exact = []
        for i in range(MAX_MODBUS_REGISTERS_PER_REQUEST):
            s = DummyModbusSensor(f"s_exact_{i}", address=100 + i, count=1)
            sensors_exact.append(s)
            dev._add_read_sensor(cast(Sensor, s))

        groups = dev._create_sensor_scan_groups()
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be exactly 1 group
        assert len(modbus_groups) == 1
        assert len(modbus_groups[0]) == MAX_MODBUS_REGISTERS_PER_REQUEST

        # Scenario 2: MAX + 1 registers
        # Add one more contiguous sensor
        s_extra = DummyModbusSensor("s_extra", address=100 + MAX_MODBUS_REGISTERS_PER_REQUEST, count=1)
        dev._add_read_sensor(cast(Sensor, s_extra))

        groups = dev._create_sensor_scan_groups()
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should now be 2 groups
        assert len(modbus_groups) == 2
        # First group should still be full
        assert len(modbus_groups[0]) == MAX_MODBUS_REGISTERS_PER_REQUEST
        # Second group has the extra one
        assert len(modbus_groups[1]) == 1

    def test_named_groups_interaction(self, mock_config):
        """Verify interaction between named groups and auto-grouped sensors."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Define 3 contiguous sensors
        # s1: 100
        # s2: 101 <- Assigned to named group "GroupA"
        # s3: 102

        s1 = DummyModbusSensor("s1", address=100)
        s2 = DummyModbusSensor("s2", address=101)
        s3 = DummyModbusSensor("s3", address=102)

        # Add s2 to a specifically named group
        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2), group="GroupA")
        dev._add_read_sensor(cast(Sensor, s3))

        groups = dev._create_sensor_scan_groups()

        # "GroupA" should exist separately
        assert "GroupA" in groups
        assert len(groups["GroupA"]) == 1
        assert groups["GroupA"][0] == s2

        # Auto Modbus groups (excluding GroupA)
        modbus_groups = [g for name, g in groups.items() if name != "GroupA" and any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Due to "named group bridging", s1 and s3 should be in ONE group
        # because s2 (at 101) bridges the gap.
        assert len(modbus_groups) == 1
        auto_group = modbus_groups[0]

        assert len(auto_group) == 2
        assert s1 in auto_group
        assert s3 in auto_group
        assert s2 not in auto_group

    @pytest.mark.asyncio
    async def test_oversized_named_group_skips_preread(self, mock_config):
        """Verify that a named group exceeding MAX_MODBUS_REGISTERS_PER_REQUEST skips read_ahead_registers."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Create sensors for a named group "BigGroup" that is oversized
        # MAX = 125, so let's make it 130 registers
        start_addr = 1000
        count = MAX_MODBUS_REGISTERS_PER_REQUEST + 5

        # Just create one start and one end sensor to span the range, but put them in same named group
        # Note: In reality they need to be contiguous or bridged to be a valid *optimized* read,
        # but here we are forcing them into a named group, so the code treats them as one unit for processing.
        # device.py calculates `count` based on min/max of the group.

        s_start = DummyModbusSensor("s_start", address=start_addr, count=1)
        # s_end at start + count - 1
        s_end = DummyModbusSensor("s_end", address=start_addr + count - 1, count=1)

        # Force publish to ensure they are "due"
        s_start.force_publish = True
        s_end.force_publish = True

        dev._add_read_sensor(cast(Sensor, s_start), group="BigGroup")
        dev._add_read_sensor(cast(Sensor, s_end), group="BigGroup")

        # Mock Modbus Client
        modbus_client = MagicMock(spec=ModbusClient)
        modbus_client.read_ahead_registers = AsyncMock(return_value=0)
        mqtt_client = MagicMock(spec=mqtt.Client)

        # Mock Lock
        with patch("sigenergy2mqtt.devices.device.ModbusLockFactory") as mock_lock_factory:
            async_cm = AsyncMock()
            async_cm.__aenter__ = AsyncMock(return_value=None)
            async_cm.__aexit__ = AsyncMock(return_value=False)
            mock_lock = MagicMock()
            mock_lock.lock = MagicMock(return_value=async_cm)
            mock_lock_factory.get.return_value = mock_lock

            dev._online = True

            async def stop_after_delay():
                await asyncio.sleep(0.1)
                dev._online = False

            asyncio.create_task(stop_after_delay())

            # Run publish_updates for "BigGroup"
            await dev.publish_updates(modbus_client, mqtt_client, "BigGroup", s_start, s_end)

        # Verify read_ahead_registers was NOT called
        modbus_client.read_ahead_registers.assert_not_called()

        # Verify that publish() was called for both sensors (fallback to individual reads)
        # We can't easily check internal calls to modbus_client.read_holding_registers here
        # because DummyModbusSensor.publish is mocked to return True without doing IO.
        # But we can check that force_publish was cleared, meaning it attempted to publish.
        assert not s_start.force_publish
        assert not s_end.force_publish

    def test_named_sensors_bridge_gap_different_groups(self, mock_config):
        """Verify that sensors in DIFFERENT named groups bridge gaps for auto-grouped sensors."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Scenario:
        # S1 (Auto) @ 100
        # S2 (GroupA) @ 101
        # S3 (GroupB) @ 102
        # S4 (Auto) @ 103

        # S1 and S4 should be in the SAME auto group because S2 and S3 bridge the gap.

        s1 = DummyModbusSensor("s1", address=100)
        s2 = DummyModbusSensor("s2", address=101)
        s3 = DummyModbusSensor("s3", address=102)
        s4 = DummyModbusSensor("s4", address=103)

        dev._add_read_sensor(cast(Sensor, s1))
        dev._add_read_sensor(cast(Sensor, s2), group="GroupA")
        dev._add_read_sensor(cast(Sensor, s3), group="GroupB")
        dev._add_read_sensor(cast(Sensor, s4))

        groups = dev._create_sensor_scan_groups()

        # Verify named groups exist
        assert "GroupA" in groups
        assert len(groups["GroupA"]) == 1
        assert "GroupB" in groups
        assert len(groups["GroupB"]) == 1

        # Verify auto group
        modbus_groups = [g for name, g in groups.items() if name not in ["GroupA", "GroupB"] and any(isinstance(s, ModbusSensorMixin) for s in g)]

        assert len(modbus_groups) == 1
        auto_group = modbus_groups[0]

        # Both auto sensors should be in this group
        assert len(auto_group) == 2
        assert s1 in auto_group
        assert s4 in auto_group
