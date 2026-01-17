import asyncio
import logging
import signal
import types
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceType, HybridInverter, Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.sensors.const import InputType


@pytest.fixture
def clean_config(monkeypatch):
    """Fixture to ensure Config is clean and mocked appropriately for tests."""
    monkeypatch.setattr(Config, "modbus", [], raising=False)
    monkeypatch.setattr(Config, "pvoutput", Config.pvoutput, raising=False)
    Config.pvoutput.enabled = False
    monkeypatch.setattr(Config, "home_assistant", Config.home_assistant, raising=False)
    Config.home_assistant.enabled = False
    monkeypatch.setattr(Config, "metrics_enabled", False, raising=False)
    monkeypatch.setattr(Config, "clean", False, raising=False)
    monkeypatch.setattr(Config, "log_level", logging.INFO, raising=False)

    # Mock validation and logging config to avoid side effects
    monkeypatch.setattr(Config, "validate", classmethod(lambda cls: None), raising=False)
    monkeypatch.setattr(Config, "get_modbus_log_level", classmethod(lambda cls: logging.INFO), raising=False)
    monkeypatch.setattr(main_mod, "configure_logging", lambda: None)
    monkeypatch.setattr(main_mod, "pymodbus_apply_logging_config", lambda *a: None)

    return Config


@pytest.mark.asyncio
async def test_async_main_with_full_device_flow(clean_config, monkeypatch):
    """Test the full device probing loop with plant, inverter, and chargers."""

    # Mock Modbus Device Config
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.timeout = 1
    mock_device.retries = 0
    mock_device.inverters = [1]
    mock_device.dc_chargers = [1]
    mock_device.ac_chargers = [6]
    mock_device.registers.read_only = True

    monkeypatch.setattr(clean_config, "modbus", [mock_device], raising=False)

    # Mock dependencies
    mock_thread_config = MagicMock()
    mock_thread_config.devices = []
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [mock_thread_config])

    mock_modbus = AsyncMock()
    mock_modbus.__aenter__.return_value = mock_modbus
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: mock_modbus)

    # Mock make_plant_and_inverter result
    mock_plant = MagicMock()
    mock_plant.protocol_version = Protocol.V2_8
    mock_plant.has_battery = True
    mock_plant.unique_id = "plant_uid"
    # Mock get_sensor for plant to avoid errors when disabling sensors
    mock_si_sensor = MagicMock()
    mock_plant.get_sensor.return_value = mock_si_sensor
    mock_plant.sensors = {f"{clean_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}

    mock_inverter = MagicMock()
    mock_inverter.unique_id = "inv_uid"

    async def fake_make_plant(*args, **kwargs):
        # Return inverter only if it matches our list
        addr = args[2]
        if addr in mock_device.inverters:
            return mock_inverter, mock_plant
        return None, mock_plant

    monkeypatch.setattr(main_mod, "make_plant_and_inverter", fake_make_plant)

    # Mock helpers
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "make_dc_charger", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(main_mod, "make_ac_charger", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(main_mod, "start", AsyncMock())

    # Mock signal to avoid runtime errors
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Verify ThreadConfig interactions
    assert mock_thread_config.add_device.call_count >= 3  # Plant/Inv, DC Charger, AC Charger

    # Verify device creation calls
    main_mod.make_dc_charger.assert_called_once()
    main_mod.make_ac_charger.assert_called_once()


@pytest.mark.asyncio
async def test_async_main_with_no_battery(clean_config, monkeypatch):
    """Test plant without battery modules disables charging sensors."""
    mock_device = MagicMock()
    mock_device.inverters = [1]
    mock_device.dc_chargers = []
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    monkeypatch.setattr(clean_config, "modbus", [mock_device], raising=False)

    mock_thread_config = MagicMock()
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [mock_thread_config])

    mock_modbus = AsyncMock()
    mock_modbus.__aenter__.return_value = mock_modbus
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: mock_modbus)

    mock_plant = MagicMock()
    mock_plant.has_battery = False  # NO BATTERY
    mock_plant.sensors = {f"{clean_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_si_sensor = MagicMock()
    mock_si_sensor.publishable = True
    mock_plant.get_sensor.return_value = mock_si_sensor

    async def fake_make_plant(*args, **kwargs):
        return MagicMock(), mock_plant

    monkeypatch.setattr(main_mod, "make_plant_and_inverter", fake_make_plant)
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Verify sensors were checked and disabled
    assert mock_plant.get_sensor.call_count >= 2
    assert mock_si_sensor.publishable is False


@pytest.mark.asyncio
async def test_async_main_with_no_dc_chargers(clean_config, monkeypatch):
    """Test plant without DC chargers disables DC stats sensors."""
    mock_device = MagicMock()
    mock_device.inverters = [1]
    mock_device.dc_chargers = []  # Empty
    mock_device.ac_chargers = []
    mock_device.registers.read_only = True
    monkeypatch.setattr(clean_config, "modbus", [mock_device], raising=False)

    mock_thread_config = MagicMock()
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [mock_thread_config])

    mock_modbus = AsyncMock()
    mock_modbus.__aenter__.return_value = mock_modbus
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: mock_modbus)

    mock_plant = MagicMock()
    mock_plant.has_battery = True
    mock_plant.sensors = {f"{clean_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_si_sensor = MagicMock()
    mock_plant.get_sensor.return_value = mock_si_sensor

    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(MagicMock(), mock_plant)))
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Verify DC sensors disabled (registers 30252, 30256)
    calls = [f"{clean_config.home_assistant.unique_id_prefix}_0_247_30252", f"{clean_config.home_assistant.unique_id_prefix}_0_247_30256"]
    # Check that get_sensor was called for these
    for call_arg in calls:
        found = any(c[0][0] == call_arg for c in mock_plant.get_sensor.call_args_list)
        assert found, f"Expected get_sensor call for {call_arg}"
    assert mock_si_sensor.publishable is False


@pytest.mark.asyncio
async def test_async_main_with_no_ac_chargers(clean_config, monkeypatch):
    """Test plant without AC chargers disables AC stats sensors."""
    mock_device = MagicMock()
    mock_device.inverters = [1]
    mock_device.dc_chargers = [1]
    mock_device.ac_chargers = []  # Empty
    mock_device.registers.read_only = True
    monkeypatch.setattr(clean_config, "modbus", [mock_device], raising=False)

    mock_thread_config = MagicMock()
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_config", lambda *a: mock_thread_config)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [mock_thread_config])

    mock_modbus = AsyncMock()
    mock_modbus.__aenter__.return_value = mock_modbus
    monkeypatch.setattr(main_mod, "ModbusClient", lambda *a, **k: mock_modbus)

    mock_plant = MagicMock()
    mock_plant.has_battery = True
    mock_plant.sensors = {f"{clean_config.home_assistant.unique_id_prefix}_0_247_40029": MagicMock()}
    mock_si_sensor = MagicMock()
    mock_plant.get_sensor.return_value = mock_si_sensor

    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(MagicMock(), mock_plant)))
    monkeypatch.setattr(main_mod, "make_dc_charger", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(main_mod, "test_for_0x02_ILLEGAL_DATA_ADDRESS", AsyncMock())
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Verify AC sensor disabled (register 30232)
    ac_call = f"{clean_config.home_assistant.unique_id_prefix}_0_247_30232"
    found = any(c[0][0] == ac_call for c in mock_plant.get_sensor.call_args_list)
    assert found
    assert mock_si_sensor.publishable is False


@pytest.mark.asyncio
async def test_async_main_with_disabled_registers(clean_config, monkeypatch):
    """Test ignored modbus host when all registers are disabled."""
    mock_device = MagicMock()
    mock_device.host = "1.2.3.4"
    mock_device.registers.read_only = False
    mock_device.registers.read_write = False
    mock_device.registers.write_only = False

    monkeypatch.setattr(clean_config, "modbus", [mock_device], raising=False)

    mock_modbus_cls = MagicMock()
    monkeypatch.setattr(main_mod, "ModbusClient", mock_modbus_cls)
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [])
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Modbus client should NOT be instantiated
    mock_modbus_cls.assert_not_called()


@pytest.mark.asyncio
async def test_async_main_with_services_enabled(clean_config, monkeypatch):
    """Test initialization of MetricsService, PVOutput, and MonitorService."""
    # Enable services
    monkeypatch.setattr(clean_config, "metrics_enabled", True, raising=False)
    monkeypatch.setattr(clean_config.pvoutput, "enabled", True, raising=False)
    monkeypatch.setattr(clean_config, "log_level", logging.DEBUG, raising=False)

    # Mock mocks
    mock_thread_config = MagicMock()
    mock_thread_config.has_devices = False  # Start false, becomes true

    def fake_add_device(*args):
        mock_thread_config.has_devices = True

    mock_thread_config.add_device = fake_add_device

    # We need separate thread configs for main and services to track them
    configs_list = []

    def fake_thread_config(*args, **kwargs):
        cfg = MagicMock()
        cfg.has_devices = False
        cfg.add_device = lambda *a, **k: setattr(cfg, "has_devices", True)
        configs_list.append(cfg)
        return cfg

    monkeypatch.setattr(main_mod, "ThreadConfig", fake_thread_config)
    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [])

    # Create Mock classes for services
    mock_metrics_svc = MagicMock()
    mock_monitor_svc = MagicMock()

    # When instantiated (called), return an instance
    monkeypatch.setattr(main_mod, "MetricsService", MagicMock(return_value=mock_metrics_svc))
    monkeypatch.setattr(main_mod, "MonitorService", MagicMock(return_value=mock_monitor_svc))

    mock_get_pvoutput = MagicMock(return_value=[MagicMock()])
    monkeypatch.setattr(main_mod, "get_pvoutput_services", mock_get_pvoutput)
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    await main_mod.async_main()

    # Verify services were added
    main_mod.MetricsService.assert_called_once()
    mock_get_pvoutput.assert_called_once()
    main_mod.MonitorService.assert_called_once()


@pytest.mark.asyncio
async def test_async_main_version_upgrade_errors(clean_config, monkeypatch, tmp_path):
    """Test version file read/write error handling."""
    monkeypatch.setattr(clean_config, "persistent_state_path", tmp_path, raising=False)
    clean_config.home_assistant.enabled = True

    # Test Read Error
    cur_file = tmp_path / ".current-version"
    cur_file.write_text("old")

    # Mock open to raise exception on read
    m_open = MagicMock(side_effect=Exception("Read Error"))

    # We need to selectively mock path.open or just creating a file that is unreadable is hard in tmp
    # Easier to mock Path.open on the specific instance if possible?
    # patching Path.open globally is risky.
    # Let's patch logging.error to detect the error logging

    mock_log_error = MagicMock()
    monkeypatch.setattr(logging, "error", mock_log_error)

    def mock_version():
        return "new"

    monkeypatch.setattr(clean_config, "version", staticmethod(mock_version), raising=False)

    monkeypatch.setattr(main_mod.ThreadConfigFactory, "get_configs", lambda: [])
    monkeypatch.setattr(main_mod, "start", AsyncMock())
    monkeypatch.setattr(signal, "signal", lambda *a: None)

    # To trigger read error, we can make the file unreadable or mock the read call logic?
    # The code uses: with current_version_file.open("r") as f:

    # Let's try to mock just the file property or something?
    # Actually, if we just want to hit the exception handler, we can assume the file exists check passes
    # but the open fails.

    # Let's use a wrapper around Path
    real_path_cls = Path

    class FakePath(type(Path("."))):
        def open(self, mode="r", **kwargs):
            if mode == "r" and self.name == ".current-version":
                raise Exception("Read Fail")
            if mode == "w" and self.name == ".current-version":
                raise Exception("Write Fail")
            return super().open(mode, **kwargs)

    # This is getting complicated to mock Path nicely.
    # Alternative: The code has a specific Try/Except block.
    # We can trust that Path.open raises Exception on error.
    # Let's verify the write error path by making the directory unwritable?
    # Or simple mock of Config.persistent_state_path to return a mock object?

    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.open.side_effect = Exception("IO Error")
    monkeypatch.setattr(clean_config, "persistent_state_path", mock_path, raising=False)
    # We also need to patch Path constructor in main.py?
    # The code does: current_version_file = Path(Config.persistent_state_path, ".current-version")
    # If Config.persistent_state_path is a Mock, Path(Mock, ...) might fail or behave oddly

    # Let's mock Path in main.py
    with patch("sigenergy2mqtt.main.main.Path") as mock_path_cls:
        mock_file_obj = MagicMock()
        mock_file_obj.exists.return_value = True
        mock_file_obj.open.side_effect = Exception("Simulated IO Error")
        mock_path_cls.return_value = mock_file_obj

        await main_mod.async_main()

        assert mock_log_error.call_count >= 1
        assert "Simulated IO Error" in str(mock_log_error.call_args_list)


@pytest.mark.asyncio
async def test_make_plant_and_inverter_edge_cases(clean_config, monkeypatch):
    """Test edge cases for make_plant_and_inverter."""

    # Setup dependencies
    mock_client = AsyncMock()

    # 1. Test Duplicate Serial detection
    monkeypatch.setattr(main_mod, "serial_numbers", ["DUPE123"])

    async def fake_get_state_serial(*args, **kwargs):
        if "InverterSerialNumber" in args[0].__class__.__name__:
            return args[0], "DUPE123"
        return args[0], None

    monkeypatch.setattr(main_mod, "get_state", fake_get_state_serial)

    inv, plant = await main_mod.make_plant_and_inverter(0, mock_client, 1, None)
    assert inv is None
    assert plant is None

    # Reset serials
    monkeypatch.setattr(main_mod, "serial_numbers", [])

    # 2. Test Output variants and Grid Code logic

    # Prepare mocked return values for get_state
    async def fake_get_state(sensor, client, device, raw=False, default_value=None):
        name = sensor.__class__.__name__
        if name == "InverterSerialNumber":
            return sensor, "SN_NEW"
        if name == "InverterModel":
            return sensor, "MOD_HYBRID"
        if name == "InverterFirmwareVersion":
            return sensor, "FW_1"
        if name == "PVStringCount":
            return sensor, 2.0
        if name == "OutputType":
            return sensor, 0  # Case 0: L/N -> 1 phase
        if name == "PACKBCUCount":
            return sensor, 1
        if name == "PlantRatedChargingPower":
            return sensor, 5000.0
        if name == "PlantRatedDischargingPower":
            return sensor, 5000.0
        if name == "GridCodeRatedFrequency":
            return sensor, 50.0
        return sensor, default_value

    monkeypatch.setattr(main_mod, "get_state", fake_get_state)

    # Mock DeviceType to return Hybrid with Grid Code
    mock_dt_hybrid = MagicMock(spec=HybridInverter)
    mock_dt_hybrid.has_grid_code_interface = True
    monkeypatch.setattr(DeviceType, "create", lambda x: mock_dt_hybrid)

    # Mock Protocol Probing to fail (trigger default V1.8)
    # read_input_registers returns a result object (rr)
    rr_error = MagicMock()
    rr_error.isError.return_value = True
    mock_client.read_input_registers.return_value = rr_error

    # Run
    monkeypatch.setattr(main_mod, "PowerPlant", MagicMock())
    monkeypatch.setattr(main_mod, "Inverter", MagicMock())

    # Ensure Config.consumption has a name attribute via Enum
    # Use real Enum member instead of Mock to avoid issues
    from sigenergy2mqtt.common import ConsumptionMethod

    monkeypatch.setattr(Config, "consumption", ConsumptionMethod.TOTAL, raising=False)

    await main_mod.make_plant_and_inverter(0, mock_client, 1, None)

    # Verify Protocol defaulted to V1.8 and Consumption forced to CALCULATED
    assert main_mod.PowerPlant.call_args[0][2] == Protocol.V1_8
    assert Config.consumption == main_mod.ConsumptionMethod.CALCULATED
    # OutputType=0 means phases=1
    assert main_mod.PowerPlant.call_args[0][4] == 1

    # 3. Test Protocol V2.8 and Grid Code Interface
    # Reset config
    monkeypatch.setattr(Config, "consumption", ConsumptionMethod.TOTAL, raising=False)
    # Reset serials to avoid "already detected"
    monkeypatch.setattr(main_mod, "serial_numbers", [])
    main_mod.PowerPlant.reset_mock()

    # Mock Probing to succeed for V2.8 (first attempt)
    rr_success = MagicMock()
    rr_success.isError.return_value = False
    mock_client.read_input_registers.return_value = rr_success

    await main_mod.make_plant_and_inverter(0, mock_client, 2, None)

    assert main_mod.PowerPlant.call_args[0][2] == Protocol.V2_8
    # Grid Code frequency should be fetched (mocked to 50.0)
    assert main_mod.PowerPlant.call_args[0][7] == 50.0


@pytest.mark.asyncio
async def test_illegal_data_address_unknown_input_type(clean_config, monkeypatch):
    """Test test_for_0x02_ILLEGAL_DATA_ADDRESS with unknown input type."""
    mock_client = AsyncMock()
    mock_device = MagicMock()
    # Fix formatting error by using int for device_address
    mock_device.device_address = 247

    # Create sensor with invalid input type
    # Must be instance of ModbusSensorMixin to trigger check
    from sigenergy2mqtt.sensors.base import ModbusSensorMixin

    mock_sensor = MagicMock()
    mock_sensor.__class__ = ModbusSensorMixin
    mock_sensor.publishable = True
    mock_sensor.input_type = "INVALID_TYPE"
    mock_sensor.name = "BadSensor"
    mock_sensor.__getitem__ = MagicMock(return_value="val")

    mock_device.get_sensor.return_value = mock_sensor

    # Patch logging to verify error logged
    mock_log = MagicMock()
    monkeypatch.setattr(main_mod.logging, "info", mock_log)

    await main_mod.test_for_0x02_ILLEGAL_DATA_ADDRESS(mock_client, 0, mock_device, 12345)

    # Should catch exception and unpublish
    assert mock_sensor.publishable is False
    assert mock_log.call_count > 0
    assert "Unknown input type" in str(mock_log.call_args)
