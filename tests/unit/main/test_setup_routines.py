import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Inverter
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.main.device_setup import (
    _setup_dc_chargers,
    setup_devices,
)
from sigenergy2mqtt.sensors.plant.read_write import (
    ActivePowerFixedAdjustmentTargetValue,
    ReactivePowerFixedAdjustmentTargetValue,
)


@pytest.fixture(autouse=True)
def clean_config():
    """Ensure active_config is set up correctly."""
    from sigenergy2mqtt.config import _swap_active_config

    cfg = Config()
    _swap_active_config(cfg)
    yield
    _swap_active_config(Config())


# ---------------------------------------------------------------------------
# setup_devices read-only mode test (line 417)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_devices_read_only_mode(caplog):
    mock_modbus = MagicMock()
    mock_modbus.host = "127.0.0.1"
    mock_modbus.port = 502
    mock_modbus.registers.read_only = True
    mock_modbus.registers.read_write = False
    mock_modbus.registers.write_only = False

    with (
        patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]),
        patch("sigenergy2mqtt.main.main.thread_config_registry.get_all", return_value=[]),
        patch("sigenergy2mqtt.main.device_setup.ModbusClient", autospec=True) as mock_mc,
    ):
        # mock async context manager
        mock_client = AsyncMock()
        mock_client.connected = False
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        # Setup now waits for Modbus instead of exiting; stop the wait to end the test
        with patch("sigenergy2mqtt.main.device_setup._wait_for_modbus", AsyncMock(side_effect=asyncio.CancelledError)), pytest.raises(asyncio.CancelledError):
            await setup_devices(set())

    assert "Read-only mode enabled: No write operations can be performed." in caplog.text


# ---------------------------------------------------------------------------
# setup_devices RatedActivePower min/max bounds tests (lines 533-546)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_devices_active_power_bounds(caplog):
    mock_modbus = MagicMock()
    mock_modbus.host = "127.0.0.1"
    mock_modbus.port = 502
    mock_modbus.registers.read_only = False
    mock_modbus.registers.read_write = True
    mock_modbus.registers.write_only = False
    mock_modbus.inverters = [1]
    mock_modbus.ac_chargers = []
    mock_modbus.dc_chargers = []

    with (
        patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]),
        patch("sigenergy2mqtt.main.main.thread_config_registry.get_all", return_value=[]),
        patch("sigenergy2mqtt.main.device_setup.ModbusClient", autospec=True) as mock_mc,
    ):
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_plant = MagicMock()
        mock_plant.protocol_version = ProtocolVersion.V1_8
        mock_plant.has_battery = True
        active_power_sensor = MagicMock(spec=ActivePowerFixedAdjustmentTargetValue)
        reactive_power_sensor = MagicMock(spec=ReactivePowerFixedAdjustmentTargetValue)
        mock_plant.sensors = {"active": active_power_sensor, "reactive": reactive_power_sensor}

        mock_inverter = MagicMock(spec=Inverter)
        mock_inverter.unique_id = "inv1"
        mock_inverter.plant_index = 0
        mock_inverter.log_identity = "Inverter1"

        # We need get_sensor to return a mock sensor or None
        def mock_get_sensor(sensor_cls, search_children=False):
            if "RatedActivePower" in str(sensor_cls):
                return "mock_sensor"
            return None

        mock_inverter.get_sensor.side_effect = mock_get_sensor

        with (
            patch("sigenergy2mqtt.main.device_setup.make_plant_and_inverter", new_callable=AsyncMock) as make_pi,
            patch("sigenergy2mqtt.main.device_setup.validate_publishable_sensors", new_callable=AsyncMock),
            patch("sigenergy2mqtt.main.device_setup.bind_cross_device_sensors"),
            patch("sigenergy2mqtt.main.device_setup.get_state", new_callable=AsyncMock) as mock_get_state,
        ):
            make_pi.return_value = (mock_inverter, mock_plant)

            # Case 1: get_state returns the rated power in display units (kW)
            mock_get_state.return_value = 5.0

            config_mock = MagicMock()
            config_mock.devices = [mock_inverter]
            with patch("sigenergy2mqtt.main.device_setup.ThreadConfig.create", return_value=config_mock):
                await main_mod.setup_devices(set())

            # Verify get_state was called for RatedActivePower
            mock_get_state.assert_called_with("mock_sensor", mock_client, "inverter")

            # Verify apply_min_max was called on the mock sensors: ±rated kW and ±60% of rated kW
            active_power_sensor.apply_min_max.assert_called_once_with(-5.0, 5.0)
            reactive_power_sensor.apply_min_max.assert_called_once_with(-3.0, 3.0)


@pytest.mark.asyncio
async def test_setup_devices_active_power_bounds_missing(caplog):
    import logging

    caplog.set_level(logging.WARNING)
    mock_modbus = MagicMock()
    mock_modbus.host = "127.0.0.1"
    mock_modbus.port = 502
    mock_modbus.registers.read_only = False
    mock_modbus.registers.read_write = True
    mock_modbus.registers.write_only = False
    mock_modbus.inverters = [1]
    mock_modbus.ac_chargers = []
    mock_modbus.dc_chargers = []

    with (
        patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]),
        patch("sigenergy2mqtt.main.device_setup.thread_config_registry.get_all", return_value=[]),
        patch("sigenergy2mqtt.main.device_setup.ModbusClient", autospec=True) as mock_mc,
    ):
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client

        mock_plant = MagicMock()
        mock_plant.protocol_version = ProtocolVersion.V1_8
        mock_plant.has_battery = True
        mock_plant.sensors = {}

        mock_inverter = MagicMock(spec=Inverter)
        mock_inverter.unique_id = "inv1"
        mock_inverter.plant_index = 0
        mock_inverter.log_identity = "Inverter1"

        with (
            patch("sigenergy2mqtt.main.device_setup.make_plant_and_inverter", new_callable=AsyncMock) as make_pi,
            patch("sigenergy2mqtt.main.device_setup.validate_publishable_sensors", new_callable=AsyncMock),
            patch("sigenergy2mqtt.main.device_setup.bind_cross_device_sensors"),
            patch("sigenergy2mqtt.main.device_setup.get_state", new_callable=AsyncMock) as mock_get_state,
        ):
            make_pi.return_value = (mock_inverter, mock_plant)

            # Case 2: get_sensor returns None
            mock_inverter.get_sensor.return_value = None

            config_mock = MagicMock()
            config_mock.devices = [mock_inverter]
            with patch("sigenergy2mqtt.main.device_setup.ThreadConfig.create", return_value=config_mock):
                await setup_devices(set())

            assert "RatedActivePower sensor not found - cannot set bounds" in caplog.text

            # Case 3: get_state returns None
            mock_inverter.get_sensor.return_value = "mock_sensor"
            mock_get_state.return_value = None

            with patch("sigenergy2mqtt.main.device_setup.ThreadConfig.create", return_value=config_mock):
                await setup_devices(set())

            assert "Failed to acquire RatedActivePower" in caplog.text


# ---------------------------------------------------------------------------
# _setup_dc_chargers missing associated inverter test (lines 731-732)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_dc_chargers_missing_inverter(caplog):
    mock_device = MagicMock()
    mock_device.dc_chargers = [1]

    inverters = {}  # 1 is missing

    res = await _setup_dc_chargers(0, mock_device, MagicMock(), MagicMock(), inverters, MagicMock(), 0, 1)

    assert res == 0  # Sequence number unchanged
    assert "DC charger at address 1 has no associated inverter" in caplog.text


# ---------------------------------------------------------------------------
# setup_signals sighup reload exception and no loop (lines 621-622, 629-630)
# ---------------------------------------------------------------------------


def test_setup_signals_sighup_requests_restart_from_loop_handler():
    """SIGHUP is dispatched through the event loop and only requests the restart.

    The configuration is not reloaded by the handler: that would replace the
    live settings underneath the running threads. async_main reloads once the
    restart has taken them offline.
    """
    configs = []

    with patch("asyncio.get_running_loop") as mock_get_loop, patch("signal.signal"):
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        main_mod.setup_signals(configs)

        sighup_handler = mock_loop.add_signal_handler.call_args[0][1]

        with patch("sigenergy2mqtt.config.active_config.reload", new_callable=AsyncMock) as mock_reload, patch("sigenergy2mqtt.main.main.restart_controller.request") as mock_request:
            sighup_handler()

            mock_request.assert_called_once_with("signal SIGHUP")
            mock_reload.assert_not_called()
            mock_loop.create_task.assert_not_called()


def test_setup_signals_sighup_handler_works_without_event_loop():
    """Without a running loop the handler registered with signal.signal still requests the restart."""
    configs = []

    with patch("signal.signal") as mock_signal, patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
        main_mod.setup_signals(configs)

        sighup_handler = next(call[0][1] for call in mock_signal.call_args_list if call[0][0] == signal.SIGHUP)

        with patch("sigenergy2mqtt.main.main.restart_controller.request") as mock_request:
            sighup_handler(signal.SIGHUP, None)

        mock_request.assert_called_once_with("signal SIGHUP")


# ---------------------------------------------------------------------------
# setup_signals loop.add_signal_handler NotImplementedError (lines 645-646)
# ---------------------------------------------------------------------------


def test_setup_signals_add_signal_handler_not_implemented():
    configs = []

    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        # Make add_signal_handler raise NotImplementedError
        mock_loop.add_signal_handler.side_effect = NotImplementedError("Not implemented on Windows")
        mock_get_loop.return_value = mock_loop

        # Should not raise exception
        main_mod.setup_signals(configs)


def test_setup_signals_add_signal_handler_attribute_error():
    configs = []

    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        # Make add_signal_handler raise AttributeError
        mock_loop.add_signal_handler.side_effect = AttributeError("No add_signal_handler")
        mock_get_loop.return_value = mock_loop

        # Should not raise exception
        main_mod.setup_signals(configs)


# ---------------------------------------------------------------------------
# _setup_dc_chargers normal flow (lines 731-741)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_dc_chargers_normal():
    mock_device = MagicMock()
    mock_device.dc_chargers = [1]

    inverters = {1: "inv1"}

    mock_config = MagicMock()
    mock_charger = MagicMock()
    mock_plant = MagicMock()
    mock_plant.protocol_version = ProtocolVersion.V1_8

    with (
        patch("sigenergy2mqtt.main.device_setup.make_dc_charger", new_callable=AsyncMock) as mock_make,
        patch("sigenergy2mqtt.main.device_setup.validate_publishable_sensors", new_callable=AsyncMock) as mock_validate,
    ):
        mock_make.return_value = mock_charger

        res = await _setup_dc_chargers(
            plant_index=0,
            device=mock_device,
            plant=mock_plant,
            modbus_client=AsyncMock(),
            inverters=inverters,
            config=mock_config,
            sequence_start=0,
            total_count=1,
            inverter_firmware_versions=None,
        )

        assert res == 1
        mock_config.add_device.assert_called_once_with(mock_charger)
        mock_validate.assert_called_once()
