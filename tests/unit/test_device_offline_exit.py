import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceType, Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device, ModbusDevice
from sigenergy2mqtt.sensors.base import ModbusSensorMixin, ReadableSensorMixin, Sensor


class MockSensor(ReadableSensorMixin):
    def __init__(self, unique_id, scan_interval=1):
        super().__init__(
            name="Mock Sensor",
            unique_id=unique_id,
            object_id=unique_id,
            unit=None,
            device_class=None,
            state_class=None,
            icon=None,
            gain=None,
            precision=None,
            scan_interval=scan_interval,
        )
        self.address = 30000
        self.count = 1
        self.device_address = 247
        self.plant_index = 0
        self.input_type = 1

    async def _update_internal_state(self, **kwargs):
        return True


class ConcreteDevice(Device):
    pass


@pytest.fixture
def mock_config():
    with patch("sigenergy2mqtt.devices.device.Config") as mock:
        mock.modbus = [MagicMock()]
        mock.modbus[0].registers = MagicMock()
        mock.modbus[0].disable_chunking = False
        mock.home_assistant.device_name_prefix = ""
        mock.home_assistant.enabled = True
        mock.home_assistant.discovery_prefix = "homeassistant"
        mock.home_assistant.unique_id_prefix = "sigen"
        mock.home_assistant.entity_id_prefix = "sigen"

        # Clear sensor registration to avoid ID conflicts between tests
        Sensor._used_unique_ids.clear()
        Sensor._used_object_ids.clear()

        yield mock


@pytest.mark.asyncio
async def test_device_offline_exits_loop(mock_config):
    # Setup device and sensors
    device = ConcreteDevice("Test Device 1", 0, "sigen_test_1", "Sigenergy", "Model", Protocol.V2_4)
    sensor = MockSensor("sigen_test_sensor_1")
    device._add_read_sensor(sensor)

    # Set online (via Future)
    future = asyncio.Future()
    device.online = future
    assert device.online is True

    # Mock MQTT and Modbus
    mqtt_client = MagicMock()
    modbus_client = AsyncMock()

    # Start publish_updates loop
    loop_task = asyncio.create_task(device.publish_updates(modbus_client, mqtt_client, "test_group_1", sensor))

    # Give it a moment to start
    await asyncio.sleep(0.1)

    # Set offline
    device.online = False
    assert device.online is False

    # Task should exit
    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("publish_updates loop did not exit after device set to offline")


@pytest.mark.asyncio
async def test_device_offline_cancels_child_sensors(mock_config):
    # Setup parent and child devices
    parent = ConcreteDevice("Parent 2", 0, "sigen_parent_2", "Sigenergy", "Model", Protocol.V2_4)
    child = ConcreteDevice("Child 2", 0, "sigen_child_2", "Sigenergy", "Model", Protocol.V2_4)

    # Add child sensor
    child_sensor = MockSensor("sigen_child_sensor_2", scan_interval=60)
    child._add_read_sensor(child_sensor)

    # Link child to parent
    parent._add_child_device(child)

    # Set BOTH parent and child online using the SAME future
    future = asyncio.Future()
    parent.online = future
    child.online = future

    assert parent.online is True
    assert child.online is True

    # Start loop in parent using child sensor
    mqtt_client = MagicMock()
    modbus_client = AsyncMock()
    loop_task = asyncio.create_task(parent.publish_updates(modbus_client, mqtt_client, "test_group_2", child_sensor))

    await asyncio.sleep(0.1)
    # sensor.sleeper_task should now be set
    assert child_sensor.sleeper_task is not None

    # Set parent offline
    parent.online = False

    # Verify child is also offline (propagation)
    assert child.online is False

    # Verify loop exits promptly because child sensor's sleeper task was cancelled
    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("publish_updates loop stuck waiting for child sensor sleeper_task")


@pytest.mark.asyncio
async def test_device_offline_exits_reconnect_loop(mock_config):
    # Setup device
    device = ConcreteDevice("Test Device 3", 0, "sigen_test_3", "Sigenergy", "Model", Protocol.V2_4)
    sensor = MockSensor("sigen_test_sensor_3")
    device._add_read_sensor(sensor)

    # Set online
    device.online = asyncio.Future()

    # Mock Modbus client that is "disconnected" and fails to connect
    modbus_client = AsyncMock()
    modbus_client.connected = False
    modbus_client.connect.side_effect = lambda: asyncio.sleep(0.1)  # Simulate slow connect

    # We need to mock isinstance to make our MockSensor look like a ModbusSensorMixin
    # so that the reconnect logic is triggered in publish_updates.
    # Note: we must use a real lambda here because we are patching a builtin-like behavior locally.

    mqtt_client = MagicMock()

    with patch("sigenergy2mqtt.devices.device.isinstance", side_effect=lambda obj, cls: True if cls == ModbusSensorMixin else isinstance(obj, cls)):
        # Start loop
        loop_task = asyncio.create_task(device.publish_updates(modbus_client, mqtt_client, "test_group_3", sensor))

        # Wait for it to hit the reconnect loop
        await asyncio.sleep(0.2)

        # Set offline during reconnection attempt
        device.online = False

        # Reconnect loop should check self.online and exit
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("publish_updates loop stuck in Modbus reconnection loop")


@pytest.mark.asyncio
async def test_device_offline_cancels_device_sleeper_task(mock_config):
    # Setup device
    device = ConcreteDevice("Test Device 4", 0, "sigen_test_4", "Sigenergy", "Model", Protocol.V2_4)

    # Set online
    device.online = asyncio.Future()

    # Simulate a service loop using device.sleeper_task
    async def service_loop():
        while device.online:
            try:
                task = asyncio.create_task(asyncio.sleep(60))
                device.sleeper_task = task
                await task
            except asyncio.CancelledError:
                break
            finally:
                device.sleeper_task = None

    loop_task = asyncio.create_task(service_loop())
    await asyncio.sleep(0.1)

    assert device.sleeper_task is not None

    # Set offline
    device.online = False

    # Loop should exit promptly
    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Service loop using device.sleeper_task did not exit promptly")
