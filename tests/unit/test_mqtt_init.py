import asyncio
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.mqtt import mqtt_setup


class TestMqttInit:
    """Tests for sigenergy2mqtt.mqtt package initialization."""

    @patch("sigenergy2mqtt.mqtt.MqttClient")
    @patch("sigenergy2mqtt.mqtt.MqttHandler")
    @pytest.mark.asyncio
    async def test_mqtt_setup_anonymous(self, mock_handler_class, mock_client_class):
        """Test mqtt_setup with anonymous connection."""
        mock_client = mock_client_class.return_value
        loop = asyncio.new_event_loop()
        modbus = MagicMock()

        with _swap_active_config(Config()) as cfg:
            cfg.mqtt.broker = "test_broker"
            cfg.mqtt.port = 1883
            cfg.mqtt.anonymous = True
            cfg.mqtt.keepalive = 60

            client, handler = await mqtt_setup("test_client", modbus, loop)

            assert client == mock_client
            assert handler == mock_handler_class.return_value
            mock_client.connect.assert_called_once_with("test_broker", port=1883, keepalive=60)
            mock_client.loop_start.assert_called_once()
            mock_client.username_pw_set.assert_not_called()

        loop.close()

    @patch("sigenergy2mqtt.mqtt.MqttClient")
    @patch("sigenergy2mqtt.mqtt.MqttHandler")
    @pytest.mark.asyncio
    async def test_mqtt_setup_authenticated(self, mock_handler_class, mock_client_class):
        """Test mqtt_setup with authenticated connection."""
        mock_client = mock_client_class.return_value
        loop = asyncio.new_event_loop()
        modbus = MagicMock()

        with _swap_active_config(Config()) as cfg:
            cfg.mqtt.broker = "test_broker"
            cfg.mqtt.port = 1883
            cfg.mqtt.anonymous = False
            cfg.mqtt.username = "user"
            cfg.mqtt.password = "pass"
            cfg.mqtt.keepalive = 60

            client, handler = await mqtt_setup("test_client", modbus, loop)

            assert client == mock_client
            mock_client.username_pw_set.assert_called_once_with("user", "pass")

        loop.close()

    @patch("sigenergy2mqtt.mqtt.MqttClient")
    @patch("sigenergy2mqtt.mqtt.MqttHandler")
    @patch("sigenergy2mqtt.mqtt.sleep")
    @patch("time.sleep")
    @pytest.mark.asyncio
    async def test_mqtt_setup_retry_logic(self, mock_time_sleep, mock_sleep, mock_handler_class, mock_client_class):
        """Test mqtt_setup retry logic on connection failure."""
        mock_client = mock_client_class.return_value
        loop = asyncio.new_event_loop()
        modbus = MagicMock()

        # Side effect: fail twice, then succeed
        mock_client.connect.side_effect = [Exception("Fail 1"), Exception("Fail 2"), None]

        with _swap_active_config(Config()) as cfg:
            cfg.mqtt.broker = "test_broker"
            cfg.mqtt.port = 1883
            cfg.mqtt.keepalive = 10
            cfg.mqtt.retry_delay = 1

            client, handler = await mqtt_setup("test_client", modbus, loop)

            assert client == mock_client
            assert mock_client.connect.call_count == 3
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(1)

        loop.close()

    @patch("sigenergy2mqtt.mqtt.MqttClient")
    @patch("sigenergy2mqtt.mqtt.MqttHandler")
    @patch("sigenergy2mqtt.mqtt.sleep")
    @patch("time.sleep")
    @pytest.mark.asyncio
    async def test_mqtt_setup_critical_failure(self, mock_time_sleep, mock_sleep, mock_handler_class, mock_client_class):
        """Test mqtt_setup raises exception after 3 failed attempts."""
        mock_client = mock_client_class.return_value
        loop = asyncio.new_event_loop()
        modbus = MagicMock()

        # Side effect: always fail
        mock_client.connect.side_effect = Exception("Permanent Fail")

        with _swap_active_config(Config()) as cfg:
            cfg.mqtt.broker = "test_broker"
            cfg.mqtt.port = 1883

            with pytest.raises(Exception, match="Permanent Fail"):
                await mqtt_setup("test_client", modbus, loop)

            assert mock_client.connect.call_count == 3
            assert mock_sleep.call_count == 2

        loop.close()

    @pytest.mark.asyncio
    async def test_mqtt_setup_invalid_id(self):
        """Test mqtt_setup with invalid client ID."""
        with pytest.raises(ValueError, match="mqtt_client_id must not be None or an empty string"):
            await mqtt_setup("", MagicMock(), MagicMock())
