import sys
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import UnitOfPower


# Fixtures for mocking circular dependencies
@pytest.fixture(scope="module", autouse=True)
def mock_modules():
    # Mock circular dependencies before importing sensors.base
    mock_types = MagicMock()

    class MockHybridInverter:
        pass

    class MockPVInverter:
        pass

    mock_types.HybridInverter = MockHybridInverter
    mock_types.PVInverter = MockPVInverter

    with patch.dict(sys.modules, {"sigenergy2mqtt.common.types": mock_types}):
        yield


from sigenergy2mqtt.common import (  # noqa: E402
    DeviceClass,
    Protocol,  # noqa: E402
    StateClass,
)
from sigenergy2mqtt.sensors.base import Sensor  # noqa: E402


# Concrete sensor for testing
class MockSensor(Sensor):
    def __init__(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            super().__init__(
                name="Test MQTT Sensor",
                unique_id="sigenergy_mqtt_test",
                object_id="sigenergy_mqtt_test",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
            self._test_state = 100.5

    async def _update_internal_state(self, **kwargs):
        # Simulate updating state
        self._states.append((1234567890.0, self._test_state))
        return True


@pytest.mark.asyncio
async def test_sensor_publish_basic():
    """Test that a sensor publishes state to MQTT correctly."""
    sensor = MockSensor()

    # Configure MQTT topics
    sensor.configure_mqtt_topics(device_id="test_device")

    # Mock MQTT client
    mqtt_client = MagicMock()
    published_messages = []

    def capture_publish(topic, payload, qos=0, retain=False):
        published_messages.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        msg = MagicMock()
        msg.wait_for_publish.return_value = None
        msg.is_published.return_value = True
        msg.rc = 0
        return msg

    mqtt_client.publish = capture_publish

    # Mock Modbus client (not needed for this test)
    modbus_client = MagicMock()
    modbus_client.connected = True

    # Publish the sensor
    result = await sensor.publish(mqtt_client, modbus_client)

    # Verify publish was successful
    assert result is True

    # Verify one message was published
    assert len(published_messages) == 1

    # Verify message details
    msg = published_messages[0]
    assert msg["topic"] == sensor["state_topic"]
    assert msg["payload"] == "100.5"
    assert msg["qos"] == 0
    assert msg["retain"] is False


@pytest.mark.asyncio
async def test_sensor_publish_raw():
    """Test that a sensor publishes raw state when enabled."""
    sensor = MockSensor()
    sensor.publish_raw = True

    # Configure MQTT topics
    sensor.configure_mqtt_topics(device_id="test_device")

    # Mock MQTT client
    mqtt_client = MagicMock()
    published_messages = []

    def capture_publish(topic, payload, qos=0, retain=False):
        published_messages.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        msg = MagicMock()
        msg.wait_for_publish.return_value = None
        msg.is_published.return_value = True
        msg.rc = 0
        return msg

    mqtt_client.publish = capture_publish

    # Mock Modbus client
    modbus_client = MagicMock()
    modbus_client.connected = True

    # Publish the sensor
    result = await sensor.publish(mqtt_client, modbus_client)

    # Verify publish was successful
    assert result is True

    # Verify two messages were published (state + raw)
    assert len(published_messages) == 2

    # Verify state message
    state_msg = published_messages[0]
    assert state_msg["topic"] == sensor["state_topic"]
    assert state_msg["payload"] == "100.5"

    # Verify raw message
    raw_msg = published_messages[1]
    assert raw_msg["topic"] == sensor["raw_state_topic"]
    assert raw_msg["payload"] == "100.5"


@pytest.mark.asyncio
async def test_sensor_publish_unpublishable():
    """Test that an unpublishable sensor does not publish."""
    sensor = MockSensor()
    sensor.publishable = False

    # Configure MQTT topics
    sensor.configure_mqtt_topics(device_id="test_device")

    # Mock MQTT client
    mqtt_client = MagicMock()
    published_messages = []

    def capture_publish(topic, payload, qos=0, retain=False):
        published_messages.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        msg = MagicMock()
        msg.wait_for_publish.return_value = None
        msg.is_published.return_value = True
        msg.rc = 0
        return msg

    mqtt_client.publish = capture_publish

    # Mock Modbus client
    modbus_client = MagicMock()
    modbus_client.connected = True

    # Publish the sensor
    result = await sensor.publish(mqtt_client, modbus_client)

    # Verify publish was not successful
    assert result is False

    # Verify no messages were published
    assert len(published_messages) == 0
