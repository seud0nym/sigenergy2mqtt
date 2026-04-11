import asyncio
import time
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.common import Constants, InputType, Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device, DeviceRegistry
from sigenergy2mqtt.devices.base.poller import SensorGroupPoller
from sigenergy2mqtt.devices.base.scan_groups import create_sensor_scan_groups
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, ModbusSensorMixin, ReadableSensorMixin, ReservedSensor, Sensor


class DummyModbusSensor(ModbusSensorMixin, ReadableSensorMixin):
    """Minimal Modbus sensor for testing."""

    def __init__(self, unique_id: str, address: int, count: int = 1, device_address: int = 1, scan_interval: int = 10):
        self["unique_id"] = unique_id
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "device_address", device_address)
        object.__setattr__(self, "scan_interval", scan_interval)
        object.__setattr__(self, "input_type", InputType.INPUT)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None = None, republish: bool = False) -> bool:
        self._states.append((time.time(), 1))
        return True

    async def _update_internal_state(self, **kwargs) -> bool:
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        self["state_topic"] = f"stat/{device_id}/{self.unique_id}"
        return ""


class DummyAlarmSensor(ModbusSensorMixin, ReadableSensorMixin):
    def __init__(self, name, plant_index, device_address, address, protocol_version=Protocol.V2_4):
        super().__init__(
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            unique_id_override=f"sigen_alarm_{address}",
            name=name,
            unique_id=f"sigen_alarm_{address}",
            object_id=f"sigen_alarm_{address}",
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:test",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
        )
        self._publishable = True

    async def _update_internal_state(self, **kwargs) -> bool:
        self.set_state("No Alarm")
        return True

    def set_state(self, state):
        self._states.append((time.time(), state))

    async def get_state(self, **kwargs):
        return "No Alarm"


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
        object.__setattr__(self, "input_type", InputType.INPUT)
        object.__setattr__(self, "_publishable", False)
        object.__setattr__(self, "debug_logging", False)


@pytest.fixture
def mock_config():
    from sigenergy2mqtt.config import _swap_active_config
    from sigenergy2mqtt.config.settings import ModbusConfig

    cfg = Config()

    mc = ModbusConfig(host="127.0.0.1", port=502, inverters=[1])
    cfg.modbus = [mc]

    # Set scan intervals on the first Modbus device for testing purposes
    cfg.modbus[0].scan_interval.low = 600
    cfg.modbus[0].scan_interval.medium = 60
    cfg.modbus[0].scan_interval.high = 10
    cfg.modbus[0].scan_interval.realtime = 5

    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.enabled = False
    cfg.home_assistant.republish_discovery_interval = 0
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.edit_percentage_with_box = False
    cfg.home_assistant.enabled_by_default = True
    cfg.persistent_state_path = Path(".")

    # Clear used IDs between tests
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

    with _swap_active_config(cfg):
        yield cfg

    DeviceRegistry.clear()
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


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

        groups = create_sensor_scan_groups(dev)

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

        groups = create_sensor_scan_groups(dev)

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

        groups = create_sensor_scan_groups(dev)

        # Should be in separate groups due to address gap
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) == 2

    def test_respects_max_registers(self, mock_config):
        """Groups should be split when exceeding Constants.MAX_MODBUS_REGISTERS_PER_REQUEST."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        # Create sensors that exceed the max register limit
        sensors = []
        address = 100
        total_count = 0
        while total_count < Constants.MAX_MODBUS_REGISTERS_PER_REQUEST + 10:
            s = DummyModbusSensor(f"s{address}", address=address, count=5, device_address=1, scan_interval=10)
            sensors.append(s)
            dev._add_read_sensor(cast(Sensor, s))
            address += 5
            total_count += 5

        groups = create_sensor_scan_groups(dev)

        # Should be split into multiple groups
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]
        assert len(modbus_groups) >= 2

    def test_handles_reserved_sensors(self, mock_config):
        """Reserved sensors should not start or end a group."""

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

        groups = create_sensor_scan_groups(dev)

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

        groups = create_sensor_scan_groups(dev)
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

        groups = create_sensor_scan_groups(dev)
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be in 1 group
        assert len(modbus_groups) == 1
        assert len(modbus_groups[0]) == 2

    def test_named_groups_ignore_disable_chunking(self, mock_config):
        """Verify that sensors in a named group REMAIN grouped even when disable_chunking is True."""
        mock_config.modbus[0].disable_chunking = True
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        s1 = DummyModbusSensor("s1", address=100, count=1, device_address=1)
        s2 = DummyModbusSensor("s2", address=101, count=1, device_address=1)

        # Add both to the same named group
        dev._add_read_sensor(cast(Sensor, s1), group="MyGroup")
        dev._add_read_sensor(cast(Sensor, s2), group="MyGroup")

        groups = create_sensor_scan_groups(dev)

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
        with patch("sigenergy2mqtt.devices.base.poller.ModbusLockFactory") as mock_lock_factory:
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

            poller = SensorGroupPoller(dev)
            # This will run briefly and exit when online becomes False
            await poller.run(modbus_client, mqtt_client, "test_group", fast, slow)

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

        with patch("sigenergy2mqtt.devices.base.poller.ModbusLockFactory") as mock_lock_factory:
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

            poller = SensorGroupPoller(dev)
            await poller.run(modbus_client, mqtt_client, "test_group", sensor)

        # Should have published due to force_publish
        assert len(sensor._states) >= 1
        # force_publish should be reset
        assert not sensor.force_publish


class TestSensorScanGroupsRecursion:
    def test_recursive_sensor_grouping(self, mock_config):
        """Verify that sensors from child and grandchild devices are grouped by the root device."""
        root = Device("root", 0, "root_uid", "mf", "mdl", Protocol.V1_8)
        child = Device("child", 0, "child_uid", "mf", "mdl", Protocol.V1_8)
        grandchild = Device("grandchild", 0, "grandchild_uid", "mf", "mdl", Protocol.V1_8)

        s_root = DummyModbusSensor("s_root", 30100)
        s_child = DummyModbusSensor("s_child", 30101)
        s_grandchild = DummyModbusSensor("s_grandchild", 30102)

        root._add_read_sensor(s_root)
        child._add_read_sensor(s_child)
        grandchild._add_read_sensor(s_grandchild)

        child._add_child_device(grandchild)
        root._add_child_device(child)

        # Act
        groups = create_sensor_scan_groups(root)

        # Assert
        # All sensors should be in one group because they are contiguous and have the same device address
        assert len(groups) == 1
        group_sensors = list(groups.values())[0]
        assert len(group_sensors) == 3
        assert s_root in group_sensors
        assert s_child in group_sensors
        assert s_grandchild in group_sensors

    @pytest.mark.asyncio
    async def test_alarm_combined_sensor_read_ahead(self, mock_config):
        """Verify that AlarmCombinedSensor triggers read-ahead for its entire range."""
        root = Device("root", 0, "root_uid", "mf", "mdl", Protocol.V1_8)

        a1 = DummyAlarmSensor("a1", 0, 1, 30605)
        a2 = DummyAlarmSensor("a2", 0, 1, 30606)
        s3 = DummyModbusSensor("s3", 30607)  # Additional sensor to trigger 'multiple'

        combined = AlarmCombinedSensor("Combined Alarms", "sigen_comb_uid", "sigen_comb_oid", a1, a2, plant_index=0)
        root._add_read_sensor(combined)
        root._add_read_sensor(s3)

        # Verify grouping
        groups = create_sensor_scan_groups(root)
        assert len(groups) == 1
        group_name = list(groups.keys())[0]
        assert combined in groups[group_name]
        assert s3 in groups[group_name]

        # Verify publish_updates triggers read_ahead
        modbus_client = MagicMock(spec=ModbusClient)
        modbus_client.read_ahead_registers = AsyncMock(return_value=0)
        mqtt_client = MagicMock(spec=mqtt.Client)

        with patch("sigenergy2mqtt.devices.base.poller.ModbusLockFactory") as mock_lock_factory:
            async_cm = AsyncMock()
            async_cm.__aenter__ = AsyncMock(return_value=None)
            async_cm.__aexit__ = AsyncMock(return_value=False)

            mock_lock = MagicMock()
            mock_lock.lock = MagicMock(return_value=async_cm)
            mock_lock.waiters = 0
            mock_lock_factory.get.return_value = mock_lock

            root._online = True
            combined.force_publish = True
            s3.force_publish = True

            # Use a short sleep or immediate exit
            async def stop_soon():
                await asyncio.sleep(0.1)
                root._online = False

            asyncio.create_task(stop_soon())

            poller = SensorGroupPoller(root)
            await poller.run(modbus_client, mqtt_client, group_name, combined, s3)

        # Check read_ahead was called with combined range
        # Total range: starts at combined (30605), count=3 (a1+a2=2, s3=1)
        modbus_client.read_ahead_registers.assert_called_with(30605, count=3, device_id=1, input_type=InputType.INPUT, trace=False)


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

        groups = create_sensor_scan_groups(dev)
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be 2 groups because 101 is missing and not bridged
        assert len(modbus_groups) == 2
        assert len(modbus_groups[0]) == 1
        assert len(modbus_groups[1]) == 1

    def test_max_registers_boundary_exact(self, mock_config):
        """Verify grouping behavior exactly at and exceeding the MAX_MODBUS_REGISTERS_PER_REQUEST limit."""
        dev = Device("test", 0, "uid", "mf", "mdl", Protocol.V1_8)

        sensors_exact = []
        for i in range(Constants.MAX_MODBUS_REGISTERS_PER_REQUEST):
            s = DummyModbusSensor(f"s_exact_{i}", address=100 + i, count=1)
            sensors_exact.append(s)
            dev._add_read_sensor(cast(Sensor, s))

        groups = create_sensor_scan_groups(dev)
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should be exactly 1 group
        assert len(modbus_groups) == 1
        assert len(modbus_groups[0]) == Constants.MAX_MODBUS_REGISTERS_PER_REQUEST

        # Scenario 2: MAX + 1 registers
        # Add one more contiguous sensor
        s_extra = DummyModbusSensor("s_extra", address=100 + Constants.MAX_MODBUS_REGISTERS_PER_REQUEST, count=1)
        dev._add_read_sensor(cast(Sensor, s_extra))

        groups = create_sensor_scan_groups(dev)
        modbus_groups = [g for g in groups.values() if any(isinstance(s, ModbusSensorMixin) for s in g)]

        # Should now be 2 groups
        assert len(modbus_groups) == 2
        # First group should still be full
        assert len(modbus_groups[0]) == Constants.MAX_MODBUS_REGISTERS_PER_REQUEST
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

        groups = create_sensor_scan_groups(dev)

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
        count = Constants.MAX_MODBUS_REGISTERS_PER_REQUEST + 5

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
        with patch("sigenergy2mqtt.devices.base.poller.ModbusLockFactory") as mock_lock_factory:
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
            poller = SensorGroupPoller(dev)
            await poller.run(modbus_client, mqtt_client, "BigGroup", s_start, s_end)

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

        groups = create_sensor_scan_groups(dev)

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
