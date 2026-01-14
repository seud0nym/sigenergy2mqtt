import asyncio
import time
from typing import cast
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from pymodbus import ModbusException

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.devices.device import Device, DeviceRegistry
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, ReadableSensorMixin, Sensor
from sigenergy2mqtt.sensors.const import InputType

# Capture original sleep
real_sleep = asyncio.sleep


class MockModbusClient:
    def __init__(self):
        self.connected = False
        self.trigger_error = False
        self.connect = AsyncMock()
        self.close = MagicMock()
        self.read_ahead_registers = AsyncMock(return_value=0)

        async def mock_connect():
            self.connected = True

        self.connect.side_effect = mock_connect


class DummyModbusSensor(ModbusSensorMixin, ReadableSensorMixin):
    def __init__(self, unique_id: str, address: int, device_address: int = 1):
        self["unique_id"] = unique_id
        self["object_id"] = unique_id
        self["platform"] = "sensor"
        object.__setattr__(self, "unique_id", unique_id)
        object.__setattr__(self, "address", address)
        object.__setattr__(self, "count", 1)
        object.__setattr__(self, "device_address", device_address)
        # Set a large scan interval to ensure it only scans once by itself,
        # plus any force_publish triggers.
        object.__setattr__(self, "scan_interval", 1000)
        object.__setattr__(self, "input_type", InputType.HOLDING)
        object.__setattr__(self, "_publishable", True)
        object.__setattr__(self, "_states", [])
        object.__setattr__(self, "_derived_sensors", {})
        object.__setattr__(self, "sleeper_task", None)
        object.__setattr__(self, "debug_logging", False)
        object.__setattr__(self, "force_publish", False)

    async def _update_internal_state(self, **kwargs) -> bool:
        return False

    def configure_mqtt_topics(self, device_id: str) -> str:
        self["state_topic"] = f"state/{device_id}/{self.unique_id}"
        return self["state_topic"]

    async def publish(self, mqtt_client, modbus_client=None, republish: bool = False) -> bool:
        if modbus_client and getattr(modbus_client, "trigger_error", False):
            modbus_client.trigger_error = False  # Reset so next attempt succeeds
            raise ModbusException("Simulated error")
        self._states.append((time.time(), 1))
        return True


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.devices.device.Config") as mock_conf:
        mock_conf.home_assistant.device_name_prefix = ""
        mock_conf.home_assistant.unique_id_prefix = "sigen"
        mock_conf.home_assistant.entity_id_prefix = "sigen"
        mock_conf.home_assistant.enabled = False
        mock_conf.devices = [MagicMock()]
        mock_conf.devices[0].disable_chunking = False
        yield mock_conf
    DeviceRegistry._devices.clear()
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


async def fast_sleep(duration):
    await real_sleep(0)


@pytest.mark.asyncio
async def test_modbus_exception_recovery(mock_config):
    dev = Device("test", 0, "sigen_uid", "mf", "mdl", Protocol.V1_8)
    sensor = DummyModbusSensor("sigen_s1", address=100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    modbus_client = MockModbusClient()
    modbus_client.trigger_error = True

    # Mock the lock
    async_cm = AsyncMock()
    mock_lock = MagicMock()
    mock_lock.lock.return_value = async_cm

    with patch("sigenergy2mqtt.devices.device.ModbusLockFactory.get", return_value=mock_lock), patch("sigenergy2mqtt.devices.device.asyncio.sleep", side_effect=fast_sleep):
        dev._online = True
        sensor.force_publish = True

        task = asyncio.create_task(dev.publish_updates(modbus_client, mqtt_client, "test", sensor))

        # Give it cycles to run:
        # 1. First scan (fails -> ModbusException)
        # 2. Reconnection loop (calls lock(timeout=None))
        # 3. Second scan (succeeds)
        for _ in range(30):
            await real_sleep(0)

        dev._online = False
        await asyncio.wait_for(task, timeout=1.0)

    # Verify calls
    assert modbus_client.close.called
    assert modbus_client.connect.called
    assert len(sensor._states) > 0

    # Check that lock was called both with and without timeout
    calls = mock_lock.lock.call_args_list
    assert call() in calls  # Normal scan
    assert call(timeout=None) in calls  # Reconnection


@pytest.mark.asyncio
async def test_reconnection_interruption_on_offline(mock_config):
    dev = Device("test", 0, "sigen_uid2", "mf", "mdl", Protocol.V1_8)
    sensor = DummyModbusSensor("sigen_s2", address=100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    modbus_client = MockModbusClient()
    modbus_client.trigger_error = True

    async_cm = AsyncMock()
    mock_lock = MagicMock()
    mock_lock.lock.return_value = async_cm

    async def mock_sleep_offline(duration):
        dev._online = False
        await real_sleep(0)

    with patch("sigenergy2mqtt.devices.device.ModbusLockFactory.get", return_value=mock_lock), patch("sigenergy2mqtt.devices.device.asyncio.sleep", side_effect=mock_sleep_offline):
        dev._online = True
        sensor.force_publish = True

        await asyncio.wait_for(dev.publish_updates(modbus_client, mqtt_client, "test", sensor), timeout=1.0)

    assert dev.online is False
