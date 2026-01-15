import asyncio
from unittest.mock import MagicMock, call

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.mqtt.mqtt import MqttHandler


class TestMqttMultiplexing:
    """Tests for MqttHandler multiplexing and collision avoidance."""

    @pytest.fixture
    def mqtt_handler(self):
        loop = asyncio.new_event_loop()
        handler = MqttHandler("test_client", None, loop)
        yield handler
        loop.close()

    def test_shared_topic_multiplexing(self, mqtt_handler):
        """Verify that multiple handlers registered for the same topic all receive the message."""
        mock_client = MagicMock(spec=mqtt.Client)
        topic = "homeassistant/status"

        callback1 = MagicMock()
        callback2 = MagicMock()

        # Register two handlers for the same topic
        mqtt_handler.register(mock_client, topic, callback1)
        mqtt_handler.register(mock_client, topic, callback2)

        # Simulate incoming message
        payload = "online"
        mqtt_handler.on_message(mock_client, topic, payload)

        # Verify both callbacks were called
        callback1.assert_called_once()
        callback2.assert_called_once()

        # Verify arguments passed to callbacks
        # Signature: (modbus_client, mqtt_client, value, topic, handler)
        args1 = callback1.call_args
        assert args1[0][2] == payload
        assert args1[0][3] == topic

        args2 = callback2.call_args
        assert args2[0][2] == payload
        assert args2[0][3] == topic

    def test_topic_collision_avoidance(self, mqtt_handler):
        """Verify that messages are routed ONLY to the correct topic handler."""
        mock_client = MagicMock(spec=mqtt.Client)
        topic_a = "cmd/sensor_a"
        topic_b = "cmd/sensor_b"

        callback_a = MagicMock()
        callback_b = MagicMock()

        mqtt_handler.register(mock_client, topic_a, callback_a)
        mqtt_handler.register(mock_client, topic_b, callback_b)

        # Message on Topic A
        mqtt_handler.on_message(mock_client, topic_a, "val_a")
        callback_a.assert_called_once()
        callback_b.assert_not_called()

        callback_a.reset_mock()

        # Message on Topic B
        mqtt_handler.on_message(mock_client, topic_b, "val_b")
        callback_b.assert_called_once()
        callback_a.assert_not_called()

    def test_reconnect_resubscribes_all(self, mqtt_handler):
        """Verify that all registered topics are resubscribed to upon reconnection."""
        mock_client = MagicMock(spec=mqtt.Client)
        topics = ["topic/one", "topic/two", "topic/three"]

        # Register a dummy handler for multiple topics
        # Note: In reality, we'd register handlers. The implementation stores topics in self._topics keys.
        dummy_cb = MagicMock()
        for t in topics:
            mqtt_handler.register(mock_client, t, dummy_cb)

        mock_client.reset_mock()

        # Simulate Reconnect
        mqtt_handler.on_reconnect(mock_client)

        # Verify subscribe calls
        # Note: logic behaves such that it unsubscribes then subscribes
        assert mock_client.subscribe.call_count == len(topics)

        # Verify specific calls
        expected_calls = [call(t) for t in topics]
        mock_client.subscribe.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    async def test_async_callback_execution(self, mqtt_handler):
        """Verify that async callbacks are scheduled correctly."""
        mock_client = MagicMock(spec=mqtt.Client)
        topic = "async/test"

        future = asyncio.Future()

        async def async_cb(*args):
            future.set_result(True)
            return True

        mqtt_handler.register(mock_client, topic, async_cb)

        # We need to run the loop to process the async callback
        # The handler uses asyncio.run_coroutine_threadsafe(..., self._loop)
        # Since we created a loop in the fixture but we are in an async test (which has its own loop),
        # we need to ensure the handler's loop is running or use the current loop if we can inject it.
        # Actually, fixture creates a new loop. Let's use the current running loop for simplicity.

        mqtt_handler._loop = asyncio.get_running_loop()

        mqtt_handler.on_message(mock_client, topic, "payload")

        # Wait for the future
        result = await asyncio.wait_for(future, timeout=1.0)
        assert result is True
