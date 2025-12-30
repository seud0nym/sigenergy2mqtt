import asyncio
import time
import pytest
import ssl
from unittest.mock import MagicMock, patch, AsyncMock
from sigenergy2mqtt.mqtt.mqtt import MqttHandler, on_connect, on_disconnect, on_message, on_publish, on_subscribe, on_unsubscribe, MqttClient
import paho.mqtt.client as mqtt


class TestMqttHandler:
    """Tests for MqttHandler class."""

    def test_init(self):
        """Test MqttHandler initialization."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()

        handler = MqttHandler("test_client", modbus, loop)

        assert handler.client_id == "test_client"
        assert handler._modbus == modbus
        assert handler._loop == loop
        assert handler.connected is False
        assert handler._topics == {}
        assert handler._mids == {}

        loop.close()

    def test_register_topic(self):
        """Test registering a message handler for a topic."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_client.subscribe.return_value = (0, 1)
        mock_handler = MagicMock()
        mock_handler.__self__ = MagicMock()
        mock_handler.__self__.__class__.__name__ = "TestClass"
        mock_handler.__name__ = "test_method"

        result = handler.register(mock_client, "test/topic", mock_handler)

        assert "test/topic" in handler._topics
        assert mock_handler in handler._topics["test/topic"]
        assert result == (0, 1)
        mock_client.subscribe.assert_called_once_with("test/topic")

        loop.close()

    def test_on_reconnect_first_connection(self):
        """Test on_reconnect with first connection."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_client.subscribe.return_value = (0, 1)
        mock_client.unsubscribe.return_value = (0, 1)

        # Register a topic first
        mock_handler = MagicMock()
        mock_handler.__self__ = MagicMock()
        mock_handler.__self__.__class__.__name__ = "TestClass"
        mock_handler.__name__ = "test_method"
        handler.register(mock_client, "test/topic", mock_handler)

        # Reset mocks
        mock_client.reset_mock()

        # Trigger reconnect
        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 1883
            handler.on_reconnect(mock_client)

        assert handler.connected is True
        mock_client.unsubscribe.assert_called_once_with("test/topic")
        mock_client.subscribe.assert_called_once_with("test/topic")

        loop.close()

    def test_on_message_with_handler(self):
        """Test on_message dispatching to registered handler."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_handler_func = MagicMock()
        mock_handler_func.__self__ = MagicMock()
        mock_handler_func.__self__.__class__.__name__ = "TestClass"
        mock_handler_func.__name__ = "test_method"

        handler._topics["test/topic"] = [mock_handler_func]

        handler.on_message(mock_client, "test/topic", "test_payload")

        # Synchronous handler should be called directly
        mock_handler_func.assert_called_once()

        loop.close()

    def test_on_message_empty_payload(self):
        """Test on_message with empty payload is ignored."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_handler_func = MagicMock()
        handler._topics["test/topic"] = [mock_handler_func]

        handler.on_message(mock_client, "test/topic", "")

        # Handler should not be called for empty payload
        mock_handler_func.assert_not_called()

        loop.close()

    def test_on_message_no_handler(self):
        """Test on_message with unregistered topic."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()

        # Should not raise, just log warning
        handler.on_message(mock_client, "unknown/topic", "test_payload")

        loop.close()

    def test_on_response_with_handler(self):
        """Test on_response calling registered handler."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_response_handler = MagicMock()

        # Register a response handler
        handler._mids[123] = MagicMock(now=time.time(), handler=mock_response_handler)

        handler.on_response(123, "publish", mock_client)

        mock_response_handler.assert_called_once_with(mock_client, "publish")
        assert 123 not in handler._mids

        loop.close()

    def test_on_response_expired_cleanup(self):
        """Test on_response cleans up expired MIDs."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()

        # Add an expired MID (over 60 seconds old)
        old_time = time.time() - 120
        handler._mids[999] = MagicMock(now=old_time, handler=None)

        # Trigger on_response with new MID
        handler.on_response(123, "publish", mock_client)

        # Old MID should be cleaned up
        assert 999 not in handler._mids

        loop.close()

    def test_on_message_async_handler(self):
        """Test on_message with an async handler."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        mock_client = MagicMock()

        async_handler = AsyncMock()
        async_handler.__self__ = MagicMock()
        async_handler.__self__.__class__.__name__ = "TestClass"
        async_handler.__name__ = "async_method"

        handler._topics["test/topic"] = [async_handler]

        with patch("sigenergy2mqtt.mqtt.mqtt.asyncio.run_coroutine_threadsafe") as mock_run:
            handler.on_message(mock_client, "test/topic", "test_payload")
            mock_run.assert_called_once()

        loop.close()

    def test_on_response_async_handler(self):
        """Test on_response with an async handler."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        mock_client = MagicMock()

        async_handler = AsyncMock()
        handler._mids[123] = MagicMock(now=time.time(), handler=async_handler)

        with patch("sigenergy2mqtt.mqtt.mqtt.asyncio.run_coroutine_threadsafe") as mock_run:
            handler.on_response(123, "publish", mock_client)
            mock_run.assert_called_once()

        loop.close()

    @pytest.mark.asyncio
    async def test_wait_for_success(self):
        """Test wait_for successful acknowledgement."""
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, asyncio.get_running_loop())

        mock_info = MagicMock(spec=mqtt.MQTTMessageInfo)
        mock_info.mid = 123

        mock_method = MagicMock(return_value=mock_info)
        mock_method.__name__ = "test_method"

        # Simulate response after a short delay
        async def simulate_response():
            await asyncio.sleep(0.1)
            handler.on_response(123, "publish", MagicMock())

        asyncio.create_task(simulate_response())

        result = await handler.wait_for(1.0, "Test", mock_method)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_timeout(self):
        """Test wait_for timeout scenario."""
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, asyncio.get_running_loop())

        mock_info = MagicMock(spec=mqtt.MQTTMessageInfo)
        mock_info.mid = 123

        mock_method = MagicMock(return_value=mock_info)
        mock_method.__name__ = "test_method"

        # No response simulation
        result = await handler.wait_for(0.2, "Test", mock_method)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_already_acknowledged(self):
        """Test wait_for when MID is already in mids list (handled before loop)."""
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, asyncio.get_running_loop())

        # Pre-populate MID as if it was already acknowledged
        handler._mids[123] = MagicMock(now=time.time(), handler=None)

        mock_info = MagicMock(spec=mqtt.MQTTMessageInfo)
        mock_info.mid = 123

        mock_method = MagicMock(return_value=mock_info)
        mock_method.__name__ = "test_method"

        # This will hit lines 98-100
        result = await handler.wait_for(1.0, "Test", mock_method)
        # Note: wait_for returns True because it was already acknowledged
        assert result is True
        assert 123 not in handler._mids

    @pytest.mark.asyncio
    async def test_wait_for_invalid_return(self):
        """Test wait_for when method doesn't return MQTTMessageInfo."""
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, asyncio.get_running_loop())

        mock_method = MagicMock(return_value=None)
        mock_method.__name__ = "test_method"

        result = await handler.wait_for(1.0, "Test", mock_method)
        assert result is False


class TestMqttCallbacks:
    """Tests for MQTT callback functions."""

    def test_on_connect_success(self):
        """Test on_connect callback with successful connection."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()

        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 1883
            mock_config.mqtt.username = "test_user"

            on_connect(mock_client, handler, {}, 0, {})

        assert handler.connected is True  # on_reconnect always sets connected=True

        loop.close()

    def test_on_disconnect(self):
        """Test on_disconnect callback."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        handler.connected = True

        mock_client = MagicMock()

        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 1883

            on_disconnect(mock_client, handler, {}, 0, {})

        assert handler.connected is False

        loop.close()

    def test_on_message_callback(self):
        """Test on_message callback wrapper."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = "test/topic"
        mock_message.payload = b"test_payload"

        mock_handler_func = MagicMock()
        mock_handler_func.__self__ = MagicMock()
        mock_handler_func.__self__.__class__.__name__ = "TestClass"
        mock_handler_func.__name__ = "test_method"
        handler._topics["test/topic"] = [mock_handler_func]

        on_message(mock_client, handler, mock_message)

        mock_handler_func.assert_called_once()

        loop.close()

    def test_on_publish_callback(self):
        """Test on_publish callback."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)

        mock_client = MagicMock()

        on_publish(mock_client, handler, 123, [], {})

        # Should register the MID
        assert 123 in handler._mids

        loop.close()

    def test_on_connect_failure(self):
        """Test on_connect callback with failure."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        mock_client = MagicMock()

        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 1883

            with patch("os._exit") as mock_exit:
                on_connect(mock_client, handler, {}, 5, {})  # Reason code 5 = connection refused
                mock_exit.assert_called_once_with(2)

        loop.close()

    def test_on_subscribe_callbacks(self):
        """Test on_subscribe with different reason codes."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        mock_client = MagicMock()

        # Success (reason_codes empty)
        on_subscribe(mock_client, handler, 1, [], {})
        assert 1 in handler._mids  # Registered as received

        # Success with reason code 0
        on_subscribe(mock_client, handler, 2, [0], {})
        assert 2 in handler._mids

        # Failure with reason code 128
        on_subscribe(mock_client, handler, 3, [128], {})
        # Note: on_response is NOT called for failure >= 128 in current implementation
        # except it is called for each result. Wait.
        # current code:
        # for result in reason_codes:
        #    if result >= 128: error log
        #    else: on_response

        loop.close()

    def test_on_unsubscribe_callbacks(self):
        """Test on_unsubscribe with different reason codes."""
        loop = asyncio.new_event_loop()
        modbus = MagicMock()
        handler = MqttHandler("test_client", modbus, loop)
        mock_client = MagicMock()

        # Success (reason_codes empty)
        on_unsubscribe(mock_client, handler, 1, [], {})
        assert 1 in handler._mids

        # Success with reason code 0
        on_unsubscribe(mock_client, handler, 2, [0], {})
        assert 2 in handler._mids

        # Failure >= 128
        on_unsubscribe(mock_client, handler, 3, [128], {})

        loop.close()


class TestMqttClient:
    """Tests for MqttClient class."""

    def test_mqtt_client_init_no_tls(self):
        """Test MqttClient initialization without TLS."""
        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.tls = False
            handler = MagicMock()
            _client = MqttClient(client_id="test_client", userdata=handler)
            assert _client._userdata == handler

    def test_mqtt_client_init_tls_secure(self):
        """Test MqttClient initialization with secure TLS."""
        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.tls = True
            mock_config.mqtt.tls_insecure = False
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 8883

            with patch("ssl.create_default_context") as mock_ssl:
                handler = MagicMock()
                _client = MqttClient(client_id="test_client", userdata=handler)
                mock_ssl.assert_called_once()
                context = mock_ssl.return_value
                assert context.check_hostname is True
                assert context.verify_mode == ssl.CERT_REQUIRED

    def test_mqtt_client_init_tls_insecure(self):
        """Test MqttClient initialization with insecure TLS."""
        with patch("sigenergy2mqtt.mqtt.mqtt.Config") as mock_config:
            mock_config.mqtt.tls = True
            mock_config.mqtt.tls_insecure = True
            mock_config.mqtt.broker = "test_broker"
            mock_config.mqtt.port = 8883

            with patch("ssl.create_default_context") as mock_ssl:
                handler = MagicMock()
                _client = MqttClient(client_id="test_client", userdata=handler)
                mock_ssl.assert_called_once()
                context = mock_ssl.return_value
                assert context.check_hostname is False
                assert context.verify_mode == ssl.CERT_NONE
