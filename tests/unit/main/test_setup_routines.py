import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.config import active_config, Config
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.devices import Inverter
from sigenergy2mqtt.sensors.plant_read_write import ActivePowerFixedAdjustmentTargetValue, ReactivePowerFixedAdjustmentTargetValue


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
    
    with patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]), \
         patch("sigenergy2mqtt.main.main.thread_config_registry.get_all", return_value=[]):
        
        # we will break the inner loop immediately by making connect fail to avoid complex mocking
        # Wait, if connect fails, sys.exit(1) is called (line 438). So we need to mock ModbusClient.
        with patch("sigenergy2mqtt.main.main.ModbusClient", autospec=True) as mock_mc:
            # mock async context manager
            mock_client = AsyncMock()
            mock_client.connected = False
            mock_mc.return_value = mock_client
            mock_client.__aenter__.return_value = mock_client
            
            with pytest.raises(SystemExit):
                await main_mod.setup_devices(set())
                
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
    mock_modbus.pss = []
    mock_modbus.pid = []
    
    with patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]), \
         patch("sigenergy2mqtt.main.main.thread_config_registry.get_all", return_value=[]), \
         patch("sigenergy2mqtt.main.main.ModbusClient", autospec=True) as mock_mc:
        
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        
        mock_plant = MagicMock()
        mock_plant.protocol_version = Protocol.V1_8
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
        
        with patch("sigenergy2mqtt.main.main.make_plant_and_inverter", new_callable=AsyncMock) as make_pi, \
             patch("sigenergy2mqtt.main.main.validate_publishable_sensors", new_callable=AsyncMock), \
             patch("sigenergy2mqtt.main.main.bind_cross_device_sensors"), \
             patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
            
            make_pi.return_value = (mock_inverter, mock_plant)
            
            # Case 1: get_state returns a value
            mock_get_state.return_value = 5000
            
            config_mock = MagicMock()
            config_mock.devices = [mock_inverter]
            with patch("sigenergy2mqtt.main.main.ThreadConfig.create", return_value=config_mock):
                await main_mod.setup_devices(set())
                
            # Verify get_state was called for RatedActivePower
            mock_get_state.assert_called_with("mock_sensor", mock_client, "inverter", raw=True)
            
            # Verify apply_min_max was called on the mock sensors
            active_power_sensor.apply_min_max.assert_called_once_with(-5000, 5000)
            reactive_power_sensor.apply_min_max.assert_called_once_with(-300000, 300000)

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
    mock_modbus.pss = []
    mock_modbus.pid = []
    
    with patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]), \
         patch("sigenergy2mqtt.main.main.thread_config_registry.get_all", return_value=[]), \
         patch("sigenergy2mqtt.main.main.ModbusClient", autospec=True) as mock_mc:
        
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        
        mock_plant = MagicMock()
        mock_plant.protocol_version = Protocol.V1_8
        mock_plant.has_battery = True
        mock_plant.sensors = {}
        
        mock_inverter = MagicMock(spec=Inverter)
        mock_inverter.unique_id = "inv1"
        mock_inverter.plant_index = 0
        mock_inverter.log_identity = "Inverter1"
        
        with patch("sigenergy2mqtt.main.main.make_plant_and_inverter", new_callable=AsyncMock) as make_pi, \
             patch("sigenergy2mqtt.main.main.validate_publishable_sensors", new_callable=AsyncMock), \
             patch("sigenergy2mqtt.main.main.bind_cross_device_sensors"), \
             patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
            
            make_pi.return_value = (mock_inverter, mock_plant)
            
            # Case 2: get_sensor returns None
            mock_inverter.get_sensor.return_value = None
            
            config_mock = MagicMock()
            config_mock.devices = [mock_inverter]
            with patch("sigenergy2mqtt.main.main.ThreadConfig.create", return_value=config_mock):
                await main_mod.setup_devices(set())
                
            assert "RatedActivePower sensor not found - cannot set bounds" in caplog.text
            
            # Case 3: get_state returns None
            mock_inverter.get_sensor.return_value = "mock_sensor"
            mock_get_state.return_value = None
            
            with patch("sigenergy2mqtt.main.main.ThreadConfig.create", return_value=config_mock):
                await main_mod.setup_devices(set())
                
            assert "Failed to acquire RatedActivePower" in caplog.text


# ---------------------------------------------------------------------------
# _setup_dc_chargers missing associated inverter test (lines 731-732)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_dc_chargers_missing_inverter(caplog):
    mock_device = MagicMock()
    mock_device.dc_chargers = [1]
    
    inverters = {} # 1 is missing
    
    res = await main_mod._setup_dc_chargers(0, mock_device, MagicMock(), MagicMock(), inverters, MagicMock(), 0, 1)
    
    assert res == 0 # Sequence number unchanged
    assert "DC charger at address 1 has no associated inverter" in caplog.text


# ---------------------------------------------------------------------------
# setup_signals sighup reload exception and no loop (lines 621-622, 629-630)
# ---------------------------------------------------------------------------

def test_setup_signals_sighup_reload_exception():
    configs = []
    
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        
        main_mod.setup_signals(configs)
        
        # Manually invoke the registered signal handler for SIGHUP
        sighup_handler = mock_loop.add_signal_handler.call_args[0][1]
        
        # Test 1: Active_config.reload throws Exception
        with patch("sigenergy2mqtt.config.active_config.reload", new_callable=AsyncMock) as mock_reload, \
             patch("sigenergy2mqtt.main.main.restart_controller.request") as mock_request:
            mock_reload.side_effect = Exception("Reload failed")
            
            sighup_handler()
            
            # The handler creates a task. We need to extract and await the task directly to test the async inner function
            task_coro = mock_loop.create_task.call_args[0][0]
            
            # Since it's a coroutine object, we can run it in a new event loop just for testing its logic
            loop = asyncio.new_event_loop()
            loop.run_until_complete(task_coro)
            
            # Exception should be caught and request should be called in finally
            mock_request.assert_called_once_with("signal SIGHUP")


def test_setup_signals_no_event_loop_for_sighup_handler(caplog):
    configs = []
    
    # Force get_running_loop to raise RuntimeError
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
        main_mod.setup_signals(configs)
        
        # Even if we can't register with loop.add_signal_handler, signal.signal is registered.
        # Let's get the sighup handler from the signal module mock
        pass

    # We need to test the inner reload_on_signal catching RuntimeError from get_running_loop
    # Let's mock signal.signal to capture the handler
    with patch("signal.signal") as mock_signal, \
         patch("asyncio.get_running_loop", return_value=MagicMock()):
        
        main_mod.setup_signals(configs)
        
        # Find the SIGHUP handler
        sighup_handler = None
        for call in mock_signal.call_args_list:
            if call[0][0] == signal.SIGHUP:
                sighup_handler = call[0][1]
                break
                
        # Now call it while get_running_loop raises RuntimeError
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("No loop")):
            sighup_handler()
            
        assert "No running event loop to handle SIGHUP reload" in caplog.text


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
    mock_plant.protocol_version = Protocol.V1_8
    
    with patch("sigenergy2mqtt.main.main.make_dc_charger", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main.validate_publishable_sensors", new_callable=AsyncMock) as mock_validate:
        mock_make.return_value = mock_charger
        
        res = await main_mod._setup_dc_chargers(
            plant_index=0,
            device=mock_device,
            plant=mock_plant,
            modbus_client=MagicMock(),
            inverters=inverters,
            config=mock_config,
            sequence_start=0,
            total_count=1,
            inverter_firmware_versions=None,
        )
        
        assert res == 1
        mock_config.add_device.assert_called_once_with(mock_charger)
        mock_validate.assert_called_once()

# ---------------------------------------------------------------------------
# _setup_pid (lines 765-786)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_pid_normal():
    mock_device = MagicMock()
    mock_device.pid = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    mock_config = MagicMock()
    mock_pid = MagicMock()
    mock_plant = MagicMock()
    
    with patch("sigenergy2mqtt.main.main.make_pid", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main.validate_publishable_sensors", new_callable=AsyncMock) as mock_validate:
        mock_make.return_value = mock_pid
        
        res = await main_mod._setup_pid(
            plant_index=0,
            device=mock_device,
            plant=mock_plant,
            seen_serial_numbers=set(),
            modbus_client=MagicMock(),
            config=mock_config,
            protocol_version=Protocol.V2_9,
            sequence_start=0,
            total_count=1,
        )
        
        assert res == 1
        mock_config.add_device.assert_called_once_with(mock_pid)
        mock_validate.assert_called_once()

@pytest.mark.asyncio
async def test_setup_pid_exception_grid_outage(caplog):
    mock_device = MagicMock()
    mock_device.pid = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    with patch("sigenergy2mqtt.main.main.make_pid", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main._is_grid_outage", new_callable=AsyncMock) as mock_outage, \
         patch("sigenergy2mqtt.main.main._schedule_restart_on_grid_restore") as mock_schedule:
        
        mock_make.side_effect = Exception("Outage error")
        mock_outage.return_value = True
        
        res = await main_mod._setup_pid(
            0, mock_device, MagicMock(), set(), MagicMock(), MagicMock(), Protocol.V2_9, 0, 1
        )
        
        assert res == 1
        mock_schedule.assert_called_once()
        assert "initialization failed during grid outage" in caplog.text

@pytest.mark.asyncio
async def test_setup_pid_exception_normal(caplog):
    mock_device = MagicMock()
    mock_device.pid = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    with patch("sigenergy2mqtt.main.main.make_pid", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main._is_grid_outage", new_callable=AsyncMock) as mock_outage:
        
        mock_make.side_effect = Exception("Other error")
        mock_outage.return_value = False
        
        res = await main_mod._setup_pid(
            0, mock_device, MagicMock(), set(), MagicMock(), MagicMock(), Protocol.V2_9, 0, 1
        )
        
        assert res == 1
        assert "Failed to initialize PID device at address 1" in caplog.text
