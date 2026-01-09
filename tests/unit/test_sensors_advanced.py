import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock circular dependencies before importing sensors.base
mock_types = MagicMock()


class MockHybridInverter:
    pass


class MockPVInverter:
    pass


mock_types.HybridInverter = MockHybridInverter
mock_types.PVInverter = MockPVInverter
sys.modules["sigenergy2mqtt.devices.types"] = mock_types

from sigenergy2mqtt.config import Protocol  # noqa: E402
from sigenergy2mqtt.sensors.base import Sensor  # noqa: E402
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass  # noqa: E402


# Concrete implementation of Sensor for testing
class ConcreteSensor(Sensor):
    def __init__(self, test_id="test_sensor"):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            super().__init__(
                name=f"Test Sensor {test_id}",
                unique_id=f"sigenergy_{test_id}",
                object_id=f"sigenergy_{test_id}",
                unit="W",
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:power",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
            self._test_value: float | None = None

    async def _update_internal_state(self, **kwargs):
        if self._test_value is not None:
            self._states.append((1234567890.0, self._test_value))
            return True
        return False


class TestSensorStateManagement:
    """Tests for Sensor state management methods."""

    @pytest.mark.asyncio
    async def test_get_state_success(self):
        """Test successful state retrieval."""
        sensor = ConcreteSensor()
        sensor._test_value = 100.5

        state = await sensor.get_state()

        assert state == 100.5
        assert sensor.latest_raw_state == 100.5

    @pytest.mark.asyncio
    async def test_get_state_raw(self):
        """Test raw state retrieval."""
        sensor = ConcreteSensor()
        sensor._gain = 10.0
        sensor._test_value = 1000.0

        state = await sensor.get_state(raw=True)

        assert state == 1000.0

    @pytest.mark.asyncio
    async def test_get_state_no_update(self):
        """Test get_state when update returns False."""
        sensor = ConcreteSensor()
        # _test_value is None, so _update_internal_state will return False

        state = await sensor.get_state()

        assert state is None

    def test_set_latest_state(self):
        """Test set_latest_state method."""
        sensor = ConcreteSensor()

        sensor.set_latest_state(42.7)

        assert sensor.latest_raw_state == 42.7
        assert len(sensor._states) == 1

    def test_state2raw(self):
        """Test state2raw conversion."""
        sensor = ConcreteSensor()
        sensor._gain = 10.0

        raw = sensor.state2raw(100.0)

        # state * gain = 100 * 10 = 1000
        assert raw == 1000.0

    def test_state2raw_with_precision(self):
        """Test state2raw applies precision during conversion."""
        sensor = ConcreteSensor()
        sensor._gain = 1.0
        sensor.precision = 2

        raw = sensor.state2raw(42.123456)

        # state2raw applies precision based on data type
        assert raw == 42


class TestSensorProperties:
    """Tests for Sensor property getters and setters."""

    def test_latest_time(self):
        """Test latest_time property."""
        sensor = ConcreteSensor()
        sensor.set_latest_state(100.0)

        latest_time = sensor.latest_time

        # latest_time uses actual time.time(), just verify it exists
        assert latest_time is not None
        assert isinstance(latest_time, float)

    def test_latest_interval_no_states(self):
        """Test latest_interval with no previous states."""
        sensor = ConcreteSensor()

        interval = sensor.latest_interval

        # Returns None when there's insufficient data
        assert interval is None

    def test_latest_interval_with_states(self):
        """Test latest_interval with multiple states."""
        sensor = ConcreteSensor()
        sensor._states = [(1000.0, 10.0), (2000.0, 20.0)]

        interval = sensor.latest_interval

        assert interval == 1000.0

    def test_device_class_property(self):
        """Test device_class property."""
        sensor = ConcreteSensor()

        assert sensor.device_class == DeviceClass.POWER

    def test_state_class_property(self):
        """Test state_class property."""
        sensor = ConcreteSensor()

        assert sensor.state_class == StateClass.MEASUREMENT

    def test_name_property(self):
        """Test name property."""
        sensor = ConcreteSensor()

        assert "Test Sensor" in sensor.name

    def test_unit_property(self):
        """Test unit property."""
        sensor = ConcreteSensor()

        assert sensor.unit == "W"


class TestSensorMqttTopics:
    """Tests for Sensor MQTT topic generation."""

    def test_state_topic_property(self):
        """Test state_topic property."""
        sensor = ConcreteSensor()
        sensor.configure_mqtt_topics(device_id="test_device")

        state_topic = sensor.state_topic

        assert "sigenergy_test_sensor" in state_topic
        assert state_topic == sensor["state_topic"]

    def test_raw_state_topic_property(self):
        """Test raw_state_topic property."""
        sensor = ConcreteSensor()
        sensor.configure_mqtt_topics(device_id="test_device")

        raw_topic = sensor.raw_state_topic

        assert "sigenergy_test_sensor" in raw_topic
        assert raw_topic == sensor["raw_state_topic"]


class TestSensorErrorHandling:
    """Tests for Sensor error handling."""

    @pytest.mark.asyncio
    async def test_get_state_republish(self):
        """Test get_state with republish flag."""
        sensor = ConcreteSensor()
        sensor._test_value = 50.0
        await sensor.get_state()  # First call to populate state

        # Republish should return previous state without calling _update_internal_state
        sensor._test_value = None  # Would cause update to fail
        state = await sensor.get_state(republish=True)

        assert state == 50.0
