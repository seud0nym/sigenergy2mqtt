import asyncio
from datetime import timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import FirmwareVersion, InputType, Protocol
from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.config import active_config, Config

@pytest.fixture(autouse=True)
def clean_config():
    """Ensure active_config is set up correctly."""
    from sigenergy2mqtt.config import _swap_active_config
    cfg = Config()
    cfg.consumption = main_mod.ConsumptionMethod.CALCULATED
    _swap_active_config(cfg)
    yield
    _swap_active_config(Config())

# ---------------------------------------------------------------------------
# read_registers tests (line 180)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_registers_holding():
    mock_client = AsyncMock()
    mock_client.read_holding_registers.return_value = "holding_result"
    
    res = await main_mod.read_registers(mock_client, 100, 2, 1, InputType.HOLDING)
    assert res == "holding_result"
    mock_client.read_holding_registers.assert_called_once_with(100, count=2, device_id=1)

# ---------------------------------------------------------------------------
# make_pid tests (lines 287-301)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_make_pid_duplicate_sn():
    mock_client = AsyncMock()
    mock_plant = MagicMock()
    mock_plant.protocol_version = Protocol.V1_8
    mock_plant.unique_id = "plant_unique_id"
    
    mock_pid = MagicMock()
    
    with patch("sigenergy2mqtt.devices.PID.create", new_callable=AsyncMock) as mock_pid_create, \
         patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
        
        mock_pid_create.return_value = mock_pid
        mock_get_state.return_value = "DUPLICATE_SN"
        
        seen_sn = {"DUPLICATE_SN"}
        
        res = await main_mod.make_pid(1, mock_client, 2, mock_plant, seen_sn)
        
        assert res is None
        assert mock_pid.via_device == "plant_unique_id"

@pytest.mark.asyncio
async def test_make_pid_new_sn():
    mock_client = AsyncMock()
    mock_plant = MagicMock()
    mock_plant.protocol_version = Protocol.V1_8
    mock_plant.unique_id = "plant_unique_id"
    
    mock_pid = MagicMock()
    
    with patch("sigenergy2mqtt.devices.PID.create", new_callable=AsyncMock) as mock_pid_create, \
         patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
        
        mock_pid_create.return_value = mock_pid
        mock_get_state.return_value = "NEW_SN"
        
        seen_sn = {"OTHER_SN"}
        
        res = await main_mod.make_pid(1, mock_client, 2, mock_plant, seen_sn)
        
        assert res is mock_pid
        assert "NEW_SN" in seen_sn

# ---------------------------------------------------------------------------
# make_pss tests (lines 382-397)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_make_pss_duplicate_sn():
    mock_client = AsyncMock()
    mock_plant = MagicMock()
    mock_plant.protocol_version = Protocol.V1_8
    mock_plant.unique_id = "plant_unique_id"
    
    mock_pss = MagicMock()
    
    with patch("sigenergy2mqtt.devices.PSS.create", new_callable=AsyncMock) as mock_pss_create, \
         patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
        
        mock_pss_create.return_value = mock_pss
        mock_get_state.return_value = "DUPLICATE_SN"
        
        seen_sn = {"DUPLICATE_SN"}
        
        res = await main_mod.make_pss(1, mock_client, 2, mock_plant, seen_sn)
        
        assert res is None
        assert mock_pss.via_device == "plant_unique_id"

@pytest.mark.asyncio
async def test_make_pss_new_sn():
    mock_client = AsyncMock()
    mock_plant = MagicMock()
    mock_plant.protocol_version = Protocol.V1_8
    mock_plant.unique_id = "plant_unique_id"
    
    mock_pss = MagicMock()
    
    with patch("sigenergy2mqtt.devices.PSS.create", new_callable=AsyncMock) as mock_pss_create, \
         patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock) as mock_get_state:
        
        mock_pss_create.return_value = mock_pss
        mock_get_state.return_value = "NEW_SN"
        
        seen_sn = {"OTHER_SN"}
        
        res = await main_mod.make_pss(1, mock_client, 2, mock_plant, seen_sn)
        
        assert res is mock_pss
        assert "NEW_SN" in seen_sn

# ---------------------------------------------------------------------------
# make_plant_and_inverter tests (lines 333-345)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_make_plant_and_inverter_missing_tz_offset():
    mock_client = AsyncMock()
    seen_sn = set()
    
    def mock_get_state_side_effect(*args, **kwargs):
        if "InverterSerialNumber" in str(args[0].__class__): return "SN1"
        if "InverterModel" in str(args[0].__class__): return "MDL1"
        if "PACKBCUCount" in str(args[0].__class__): return 1
        if "SystemTimeZone" in str(args[0].__class__): return None
        if "InverterFirmwareVersion" in str(args[0].__class__): return "V122R001C00SPC112B701P"
        if "OutputType" in str(args[0].__class__): return 1
        if "ESSPreHeatingEnable" in str(args[0].__class__): return 1
        return None

    with patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock, side_effect=mock_get_state_side_effect), \
         patch("sigenergy2mqtt.main.main.probe_optional_interface", new_callable=AsyncMock, return_value=False), \
         patch("sigenergy2mqtt.main.main.probe_protocol", new_callable=AsyncMock, return_value=Protocol.V2_8), \
         patch("sigenergy2mqtt.devices.PowerPlant.create", new_callable=AsyncMock) as mock_plant_create, \
         patch("sigenergy2mqtt.devices.Inverter.create", new_callable=AsyncMock):
        
        mock_plant = MagicMock()
        mock_plant.unique_id = "plant1"
        mock_plant_create.return_value = mock_plant
        
        await main_mod.make_plant_and_inverter(1, mock_client, 2, None, seen_sn)
        
        mock_plant_create.assert_called_once()
        assert mock_plant_create.call_args[0][4] == timezone.utc

@pytest.mark.asyncio
async def test_make_plant_and_inverter_tz_exception():
    mock_client = AsyncMock()
    seen_sn = set()
    
    def mock_get_state_side_effect(*args, **kwargs):
        if "SystemTimeZone" in str(args[0].__class__): raise Exception("Read error")
        if "InverterSerialNumber" in str(args[0].__class__): return "SN1"
        if "InverterModel" in str(args[0].__class__): return "MDL1"
        if "PACKBCUCount" in str(args[0].__class__): return 1
        if "InverterFirmwareVersion" in str(args[0].__class__): return "V122R001C00SPC112B701P"
        if "OutputType" in str(args[0].__class__): return 1
        if "ESSPreHeatingEnable" in str(args[0].__class__): return 1
        return None

    with patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock, side_effect=mock_get_state_side_effect), \
         patch("sigenergy2mqtt.main.main.probe_optional_interface", new_callable=AsyncMock, return_value=False), \
         patch("sigenergy2mqtt.main.main.probe_protocol", new_callable=AsyncMock, return_value=Protocol.V2_8), \
         patch("sigenergy2mqtt.devices.PowerPlant.create", new_callable=AsyncMock) as mock_plant_create, \
         patch("sigenergy2mqtt.devices.Inverter.create", new_callable=AsyncMock):
        
        mock_plant = MagicMock()
        mock_plant.unique_id = "plant1"
        mock_plant_create.return_value = mock_plant
        
        await main_mod.make_plant_and_inverter(1, mock_client, 2, None, seen_sn)
        
        mock_plant_create.assert_called_once()
        assert mock_plant_create.call_args[0][4] == timezone.utc

@pytest.mark.asyncio
async def test_make_plant_and_inverter_protocol_override():
    mock_client = AsyncMock()
    seen_sn = set()
    
    def mock_get_state_side_effect(*args, **kwargs):
        if "InverterSerialNumber" in str(args[0].__class__): return "SN1"
        if "InverterModel" in str(args[0].__class__): return "MDL1"
        if "PACKBCUCount" in str(args[0].__class__): return 1
        if "SystemTimeZone" in str(args[0].__class__): return 60
        if "InverterFirmwareVersion" in str(args[0].__class__): return "V122R001C00SPC114B701P"
        if "OutputType" in str(args[0].__class__): return 1
        if "ESSPreHeatingEnable" in str(args[0].__class__): return 1
        return None

    with patch("sigenergy2mqtt.main.main.get_state", new_callable=AsyncMock, side_effect=mock_get_state_side_effect), \
         patch("sigenergy2mqtt.main.main.probe_optional_interface", new_callable=AsyncMock, return_value=False), \
         patch("sigenergy2mqtt.main.main.probe_protocol", new_callable=AsyncMock, return_value=Protocol.V2_8), \
         patch("sigenergy2mqtt.devices.PowerPlant.create", new_callable=AsyncMock) as mock_plant_create, \
         patch("sigenergy2mqtt.devices.Inverter.create", new_callable=AsyncMock):
        
        mock_plant = MagicMock()
        mock_plant.unique_id = "plant1"
        mock_plant_create.return_value = mock_plant
        
        await main_mod.make_plant_and_inverter(1, mock_client, 2, None, seen_sn)
        
        mock_plant_create.assert_called_once()
        assert mock_plant_create.call_args[0][3] == Protocol.V2_9
