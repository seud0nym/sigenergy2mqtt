"""
Unit tests for inverter_read_only.py module.
Tests cover firmware version detection, output type mapping, power factor calculation, and charger state display.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.inverter_read_only import (
    DCChargerRunningState,
    InverterFirmwareVersion,
    OutputType,
    PowerFactor,
    RatedActivePower,
)


@pytest.fixture
def mock_config():
    """Mock the global Config object using a fresh instance."""
    from sigenergy2mqtt.config import _swap_active_config
    from sigenergy2mqtt.config.settings import HomeAssistantConfig

    cfg = Config()
    ha = HomeAssistantConfig(unique_id_prefix="test", entity_id_prefix="test", enabled_by_default=False)
    cfg.home_assistant = ha
    cfg.modbus = []

    with _swap_active_config(cfg):
        yield cfg


class TestInverterFirmwareVersion:
    """Test InverterFirmwareVersion sensor."""

    @pytest.mark.asyncio
    async def test_firmware_version_no_change(self, mock_config):
        """Test get_state when firmware version hasn't changed."""
        sensor = InverterFirmwareVersion(plant_index=0, device_address=1)

        # Mock parent get_state and parent_device
        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = "v2.0.1"
            sensor.parent_device = MagicMock()
            sensor.parent_device.__getitem__ = MagicMock(return_value="v2.0.1")
            sensor.parent_device.name = "TestDevice"

            result = await sensor.get_state()
            assert result == "v2.0.1"

    @pytest.mark.asyncio
    async def test_firmware_version_none_value(self, mock_config):
        """Test get_state when firmware version is None."""
        sensor = InverterFirmwareVersion(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = None

            result = await sensor.get_state()
            assert result is None

    @pytest.mark.asyncio
    async def test_firmware_version_no_parent_device(self, mock_config):
        """Test get_state when parent_device attribute doesn't exist."""
        sensor = InverterFirmwareVersion(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = "v2.0.5"
            # Don't set parent_device

            result = await sensor.get_state()
            assert result == "v2.0.5"


class TestOutputType:
    """Test OutputType sensor enum state display."""

    @pytest.mark.asyncio
    async def test_output_type_raw_mode(self, mock_config):
        """Test get_state with raw=True returns raw numeric value."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 1

            result = await sensor.get_state(raw=True)
            assert result == 1

    @pytest.mark.asyncio
    async def test_output_type_none_value(self, mock_config):
        """Test get_state returns None when value is None."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = None

            result = await sensor.get_state(raw=False)
            assert result is None

    @pytest.mark.asyncio
    async def test_output_type_valid_index_0(self, mock_config):
        """Test get_state with valid index 0 (L/N)."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 0

            result = await sensor.get_state(raw=False)
            assert result == "L/N"

    @pytest.mark.asyncio
    async def test_output_type_valid_index_1(self, mock_config):
        """Test get_state with valid index 1 (L1/L2/L3)."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 1

            result = await sensor.get_state(raw=False)
            assert result == "L1/L2/L3"

    @pytest.mark.asyncio
    async def test_output_type_valid_index_2(self, mock_config):
        """Test get_state with valid index 2 (L1/L2/L3/N)."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 2

            result = await sensor.get_state(raw=False)
            assert result == "L1/L2/L3/N"

    @pytest.mark.asyncio
    async def test_output_type_valid_index_3(self, mock_config):
        """Test get_state with valid index 3 (L1/L2/N)."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 3

            result = await sensor.get_state(raw=False)
            assert result == "L1/L2/N"

    @pytest.mark.asyncio
    async def test_output_type_invalid_index_negative(self, mock_config):
        """Test get_state with invalid negative index."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = -1

            result = await sensor.get_state(raw=False)
            assert result == "Unknown Output Type: -1"

    @pytest.mark.asyncio
    async def test_output_type_invalid_index_out_of_range(self, mock_config):
        """Test get_state with index out of valid range."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 99

            result = await sensor.get_state(raw=False)
            assert result == "Unknown Output Type: 99"

    @pytest.mark.asyncio
    async def test_output_type_non_numeric_value(self, mock_config):
        """Test get_state with non-numeric string value."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = "invalid"

            result = await sensor.get_state(raw=False)
            assert result == "Unknown Output Type: invalid"

    @pytest.mark.asyncio
    async def test_output_type_float_value(self, mock_config):
        """Test get_state with float value converts to int."""
        sensor = OutputType(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 2.5

            result = await sensor.get_state(raw=False)
            assert result == "L1/L2/L3/N"  # Converts 2.5 to int 2


class TestPowerFactor:
    """Test PowerFactor sensor calculation logic."""

    @pytest.mark.asyncio
    async def test_power_factor_set_state_success(self, mock_config):
        """Test set_state with valid power factor."""
        active_power = MagicMock()
        reactive_power = MagicMock()

        sensor = PowerFactor(plant_index=0, device_address=1, active_power=active_power, reactive_power=reactive_power)

        # Mock parent set_state to not raise
        with patch.object(sensor.__class__.__bases__[0], "set_state") as mock_parent_set_state:
            sensor.set_state(0.95)
            mock_parent_set_state.assert_called_once_with(0.95)

    @pytest.mark.asyncio
    async def test_power_factor_calculated_from_active_reactive(self, mock_config, caplog):
        """Test power factor calculation when parent set_state fails."""
        active_power = MagicMock()
        active_power.latest_raw_state = 3000  # 3 kW
        active_power.latest_time = 1000.0

        reactive_power = MagicMock()
        reactive_power.latest_raw_state = 4000  # 4 kVAR
        reactive_power.latest_time = 1000.0

        sensor = PowerFactor(plant_index=0, device_address=1, active_power=active_power, reactive_power=reactive_power)
        sensor.gain = 1000
        sensor.debug_logging = False

        # Mock parent set_state to raise ValueError
        with patch.object(sensor.__class__.__bases__[0], "set_state") as mock_parent_set_state:
            mock_parent_set_state.side_effect = ValueError("Invalid value")

            # Second call should succeed (calculation bypass)
            call_count = [0]

            def side_effect(value):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ValueError("Invalid value")

            mock_parent_set_state.side_effect = side_effect

            with caplog.at_level(logging.INFO):
                sensor.set_state(999)  # Invalid value triggers fallback

            # Verify calculated power factor was used
            # sqrt(3000^2 + 4000^2) = 5000, abs(3000)/5000 * 1000 = 600
            assert mock_parent_set_state.call_count == 2

    @pytest.mark.asyncio
    async def test_power_factor_zero_apparent_power(self, mock_config):
        """Test power factor when apparent power is zero."""
        active_power = MagicMock()
        active_power.latest_raw_state = 0
        active_power.latest_time = 1000.0

        reactive_power = MagicMock()
        reactive_power.latest_raw_state = 0
        reactive_power.latest_time = 1000.0

        sensor = PowerFactor(plant_index=0, device_address=1, active_power=active_power, reactive_power=reactive_power)
        sensor.gain = 1000

        with patch.object(sensor.__class__.__bases__[0], "set_state") as mock_parent_set_state:
            mock_parent_set_state.side_effect = [ValueError("Invalid"), None]

            sensor.set_state(999)
            # When apparent_power == 0, should set power_factor = 0
            calls = mock_parent_set_state.call_args_list
            assert calls[-1][0][0] == 0

    @pytest.mark.asyncio
    async def test_power_factor_none_active_power(self, mock_config):
        """Test power factor when active_power is None."""
        active_power = MagicMock()
        active_power.latest_raw_state = None

        reactive_power = MagicMock()
        reactive_power.latest_raw_state = 1000

        sensor = PowerFactor(plant_index=0, device_address=1, active_power=active_power, reactive_power=reactive_power)

        original_error = ValueError("Original error")
        with patch.object(sensor.__class__.__bases__[0], "set_state") as mock_parent_set_state:
            mock_parent_set_state.side_effect = original_error

            with pytest.raises(ValueError) as exc_info:
                sensor.set_state(999)

            assert exc_info.value is original_error

    @pytest.mark.asyncio
    async def test_power_factor_negative_active_power(self, mock_config):
        """Test power factor with negative active power."""
        active_power = MagicMock()
        active_power.latest_raw_state = -3000  # Negative (discharging)
        active_power.latest_time = 1000.0

        reactive_power = MagicMock()
        reactive_power.latest_raw_state = 4000
        reactive_power.latest_time = 1000.0

        sensor = PowerFactor(plant_index=0, device_address=1, active_power=active_power, reactive_power=reactive_power)
        sensor.gain = 1000

        with patch.object(sensor.__class__.__bases__[0], "set_state") as mock_parent_set_state:
            mock_parent_set_state.side_effect = [ValueError("Invalid"), None]

            sensor.set_state(999)
            # abs(-3000) / 5000 * 1000 = 600 (still positive due to abs())
            calls = mock_parent_set_state.call_args_list
            assert calls[-1][0][0] == 600


class TestDCChargerRunningState:
    """Test DCChargerRunningState sensor enum display."""

    @pytest.mark.asyncio
    async def test_charger_state_raw_mode(self, mock_config):
        """Test get_state with raw=True returns raw numeric value."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 3

            result = await sensor.get_state(raw=True)
            assert result == 3

    @pytest.mark.asyncio
    async def test_charger_state_none_value(self, mock_config):
        """Test get_state returns None when value is None."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = None

            result = await sensor.get_state(raw=False)
            assert result is None

    @pytest.mark.asyncio
    async def test_charger_state_idle(self, mock_config):
        """Test charger state 0 (Idle)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 0

            result = await sensor.get_state(raw=False)
            assert result == "Idle"

    @pytest.mark.asyncio
    async def test_charger_state_occupied(self, mock_config):
        """Test charger state 1 (Occupied)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 1

            result = await sensor.get_state(raw=False)
            assert result == "Occupied (Charging Gun plugged in but not detected)"

    @pytest.mark.asyncio
    async def test_charger_state_preparing(self, mock_config):
        """Test charger state 2 (Preparing)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 2

            result = await sensor.get_state(raw=False)
            assert result == "Preparing (Establishing communication)"

    @pytest.mark.asyncio
    async def test_charger_state_charging(self, mock_config):
        """Test charger state 3 (Charging)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 3

            result = await sensor.get_state(raw=False)
            assert result == "Charging"

    @pytest.mark.asyncio
    async def test_charger_state_fault(self, mock_config):
        """Test charger state 4 (Fault)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 4

            result = await sensor.get_state(raw=False)
            assert result == "Fault"

    @pytest.mark.asyncio
    async def test_charger_state_scheduled(self, mock_config):
        """Test charger state 5 (Scheduled)."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 5

            result = await sensor.get_state(raw=False)
            assert result == "Scheduled"

    @pytest.mark.asyncio
    async def test_charger_state_unknown_index(self, mock_config):
        """Test charger with unknown state code."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = 99

            result = await sensor.get_state(raw=False)
            assert result == "Unknown State code: 99"

    @pytest.mark.asyncio
    async def test_charger_state_non_numeric(self, mock_config):
        """Test charger with non-numeric value."""
        sensor = DCChargerRunningState(plant_index=0, device_address=1)

        with patch.object(sensor.__class__.__bases__[0], "get_state", new_callable=AsyncMock) as mock_parent_get_state:
            mock_parent_get_state.return_value = "badvalue"

            result = await sensor.get_state(raw=False)
            assert result == "Unknown State code: badvalue"


class TestRatedActivePower:
    """Test RatedActivePower basic sensor initialization."""

    def test_initialization(self, mock_config):
        """Test RatedActivePower initializes with correct parameters."""
        sensor = RatedActivePower(plant_index=0, device_address=1)

        assert sensor.name == "Rated Active Power"
        assert sensor.address == 30540
        assert sensor.count == 2
        assert sensor.gain == 1000
        assert sensor.precision == 2
        assert sensor["entity_category"] == "diagnostic"
