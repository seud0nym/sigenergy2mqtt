import pytest
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from sigenergy2mqtt.main.main import configure_logging, get_state


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configure_logging_sets_root_level(self):
        """Test that configure_logging sets the root logger level."""
        with patch("sigenergy2mqtt.main.main.Config") as mock_config:
            mock_config.log_level = logging.DEBUG
            mock_config.get_modbus_log_level.return_value = logging.INFO
            mock_config.mqtt.log_level = logging.WARNING
            mock_config.pvoutput.log_level = logging.ERROR

            # Reset loggers to known state
            logging.getLogger("root").setLevel(logging.NOTSET)
            logging.getLogger("pymodbus").setLevel(logging.NOTSET)
            logging.getLogger("paho.mqtt").setLevel(logging.NOTSET)
            logging.getLogger("pvoutput").setLevel(logging.NOTSET)

            configure_logging()

            assert logging.getLogger("root").level == logging.DEBUG
            assert logging.getLogger("pymodbus").level == logging.INFO
            assert logging.getLogger("paho.mqtt").level == logging.WARNING
            assert logging.getLogger("pvoutput").level == logging.ERROR

    def test_configure_logging_updates_existing_level(self):
        """Test that configure_logging updates logger level if already set."""
        with patch("sigenergy2mqtt.main.main.Config") as mock_config:
            mock_config.log_level = logging.INFO
            mock_config.get_modbus_log_level.return_value = logging.INFO
            mock_config.mqtt.log_level = logging.INFO
            mock_config.pvoutput.log_level = logging.INFO

            # Set initial level
            logging.getLogger("root").setLevel(logging.DEBUG)

            # Change config
            mock_config.log_level = logging.WARNING

            configure_logging()

            assert logging.getLogger("root").level == logging.WARNING


class TestGetState:
    """Tests for the get_state helper function."""

    @pytest.mark.asyncio
    async def test_get_state_success(self):
        """Test successful state retrieval."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(return_value=42.5)
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await get_state(mock_sensor, mock_modbus, "test_device")

        assert sensor == mock_sensor
        assert state == 42.5
        mock_sensor.get_state.assert_called_once_with(raw=False, modbus=mock_modbus)

    @pytest.mark.asyncio
    async def test_get_state_with_raw(self):
        """Test state retrieval with raw=True."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(return_value=100)
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await get_state(mock_sensor, mock_modbus, "test_device", raw=True)

        assert state == 100
        mock_sensor.get_state.assert_called_once_with(raw=True, modbus=mock_modbus)

    @pytest.mark.asyncio
    async def test_get_state_exception_returns_default(self):
        """Test that exceptions return the default value."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(side_effect=Exception("Connection failed"))
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await get_state(mock_sensor, mock_modbus, "test_device", default_value=999)

        assert sensor == mock_sensor
        assert state == 999

    @pytest.mark.asyncio
    async def test_get_state_exception_returns_none_if_no_default(self):
        """Test that exceptions return None when no default provided."""
        mock_sensor = MagicMock()
        mock_sensor.get_state = AsyncMock(side_effect=Exception("Connection failed"))
        mock_sensor.__class__.__name__ = "TestSensor"

        mock_modbus = MagicMock()
        mock_modbus.comm_params.host = "192.168.1.1"
        mock_modbus.comm_params.port = 502

        sensor, state = await get_state(mock_sensor, mock_modbus, "test_device")

        assert sensor == mock_sensor
        assert state is None
