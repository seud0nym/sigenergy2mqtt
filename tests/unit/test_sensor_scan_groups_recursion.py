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
from sigenergy2mqtt.sensors.base import (
    AlarmCombinedSensor,
    ModbusSensorMixin,
    ReadableSensorMixin,
    Sensor,
)
from sigenergy2mqtt.sensors.const import InputType


class DummyModbusSensor(ModbusSensorMixin, ReadableSensorMixin):
    def __init__(self, name, plant_index, device_address, address, count=1, scan_interval=10):
        super().__init__(
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=count,
            unique_id_override=f"sigen_uid_{address}",
            name=name,
            unique_id=f"sigen_uid_{address}",
            object_id=f"sigen_oid_{address}",
            scan_interval=scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:test",
            gain=None,
            precision=None,
        )
        self._publishable = True

    async def _update_internal_state(self, **kwargs) -> bool:
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        self["state_topic"] = f"stat/{device_id}/{self.unique_id}"
        return ""

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None = None, republish: bool = False) -> bool:
        await self._update_internal_state()
        self._states.append((time.time(), 1))
        return True


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


@pytest.fixture
def mock_config():
    conf = cast(Any, Config)
    original_devices = conf.modbus if hasattr(conf, "modbus") else []
    original_ha = conf.home_assistant if hasattr(conf, "home_assistant") else None

    # Clear used IDs between tests
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

    class D:
        registers = {}
        disable_chunking = False
        scan_interval = types.SimpleNamespace(low=600, medium=60, high=10, realtime=5)

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
        enabled_by_default=True,
    )
    conf.persistent_state_path = Path(".")

    yield conf

    conf.modbus = original_devices
    if original_ha:
        conf.home_assistant = original_ha
    DeviceRegistry._devices.clear()
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


class TestSensorScanGroupsRecursion:
    def test_recursive_sensor_grouping(self, mock_config):
        """Verify that sensors from child and grandchild devices are grouped by the root device."""
        root = Device("root", 0, "root_uid", "mf", "mdl", Protocol.V1_8)
        child = Device("child", 0, "child_uid", "mf", "mdl", Protocol.V1_8)
        grandchild = Device("grandchild", 0, "grandchild_uid", "mf", "mdl", Protocol.V1_8)

        s_root = DummyModbusSensor("s_root", 0, 1, 30100)
        s_child = DummyModbusSensor("s_child", 0, 1, 30101)
        s_grandchild = DummyModbusSensor("s_grandchild", 0, 1, 30102)

        root._add_read_sensor(s_root)
        child._add_read_sensor(s_child)
        grandchild._add_read_sensor(s_grandchild)

        child._add_child_device(grandchild)
        root._add_child_device(child)

        # Act
        groups = root._create_sensor_scan_groups()

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
        s3 = DummyModbusSensor("s3", 0, 1, 30607)  # Additional sensor to trigger 'multiple'

        combined = AlarmCombinedSensor("Combined Alarms", "sigen_comb_uid", "sigen_comb_oid", a1, a2, plant_index=0)
        root._add_read_sensor(combined)
        root._add_read_sensor(s3)

        # Verify grouping
        groups = root._create_sensor_scan_groups()
        assert len(groups) == 1
        group_name = list(groups.keys())[0]
        assert combined in groups[group_name]
        assert s3 in groups[group_name]

        # Verify publish_updates triggers read_ahead
        modbus_client = MagicMock(spec=ModbusClient)
        modbus_client.read_ahead_registers = AsyncMock(return_value=0)
        mqtt_client = MagicMock(spec=mqtt.Client)

        with patch("sigenergy2mqtt.devices.device.ModbusLockFactory") as mock_lock_factory:
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

            await root.publish_updates(modbus_client, mqtt_client, group_name, combined, s3)

        # Check read_ahead was called with combined range
        # Total range: starts at combined (30605), count=3 (a1+a2=2, s3=1)
        modbus_client.read_ahead_registers.assert_called_with(30605, count=3, device_id=1, input_type=InputType.INPUT, trace=False)
