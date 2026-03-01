import logging
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import InputType, Protocol
from sigenergy2mqtt.config import Config, _swap_active_config, active_config
from sigenergy2mqtt.main import main as main_mod


@pytest.fixture
def clean_config_augment(monkeypatch):
    """Fixture to ensure Config is clean and mocked appropriately."""
    cfg = Config()
    mock_modbus = MagicMock()
    mock_modbus.scan_interval.low = 600
    mock_modbus.scan_interval.medium = 60
    mock_modbus.scan_interval.high = 10
    mock_modbus.scan_interval.realtime = 5
    cfg.modbus = [mock_modbus]
    cfg.home_assistant.enabled = False
    cfg.pvoutput.enabled = False
    cfg.pvoutput.log_level = logging.WARNING
    cfg.influxdb.enabled = False
    cfg.metrics_enabled = False
    cfg.log_level = logging.INFO
    cfg.clean = False
    cfg.persistent_state_path = "/tmp"
    cfg.mqtt.anonymous = True
    cfg.mqtt.log_level = logging.WARNING

    with _swap_active_config(cfg):
        # Bypass validation since we often test with empty modbus
        monkeypatch.setattr(cfg, "validate", lambda: None)
        monkeypatch.setattr(cfg, "get_modbus_log_level", lambda: logging.WARNING)
        yield cfg


@pytest.mark.asyncio
async def test_read_registers_none_client():
    with pytest.raises(ValueError, match="modbus_client cannot be None"):
        await main_mod.read_registers(None, 0, 1, 1, InputType.HOLDING)


@pytest.mark.asyncio
async def test_async_main_connection_failure(clean_config_augment, monkeypatch):
    mock_device = MagicMock()
    mock_device.registers.read_only = True
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    clean_config_augment.modbus = [mock_device]

    mock_instance = AsyncMock(connected=False)
    mock_instance.__aenter__.return_value = mock_instance
    monkeypatch.setattr(main_mod, "ModbusClient", MagicMock(return_value=mock_instance))

    with pytest.raises(SystemExit) as cm:
        await main_mod.async_main()
    assert cm.value.code == 1


@pytest.mark.asyncio
async def test_async_main_full_coverage(clean_config_augment, monkeypatch):
    mock_device = MagicMock()
    mock_device.registers.read_only = True
    mock_device.host = "1.2.3.4"
    mock_device.port = 502
    mock_device.timeout = 1
    mock_device.retries = 1
    mock_device.inverters = []
    mock_device.dc_chargers = []
    mock_device.ac_chargers = [1]  # Trigger AC charger warning if protocol is low
    mock_device.ac_chargers = [1]  # Trigger AC charger warning if protocol is low
    mock_device.log_level = logging.WARNING
    clean_config_augment.modbus = [mock_device]
    clean_config_augment.metrics_enabled = True
    clean_config_augment.pvoutput.enabled = True
    clean_config_augment.influxdb.enabled = True
    clean_config_augment.log_level = logging.DEBUG
    clean_config_augment.home_assistant.enabled = True

    mock_instance = AsyncMock(connected=True)
    mock_instance.__aenter__.return_value = mock_instance
    monkeypatch.setattr(main_mod, "ModbusClient", MagicMock(return_value=mock_instance))

    mock_plant = MagicMock(protocol_version=Protocol.V1_8)
    monkeypatch.setattr(main_mod, "make_plant_and_inverter", AsyncMock(return_value=(MagicMock(), mock_plant)))
    monkeypatch.setattr(main_mod, "get_pvoutput_services", lambda *a: [MagicMock()])
    monkeypatch.setattr(main_mod, "get_influxdb_services", lambda *a: [MagicMock()])
    monkeypatch.setattr(main_mod, "start", AsyncMock())

    signals = {}

    def mock_signal(sig, handler):
        signals[sig] = handler

    monkeypatch.setattr(signal, "signal", mock_signal)

    await main_mod.async_main()

    if signal.SIGINT in signals:
        signals[signal.SIGINT](signal.SIGINT, None)
    if signal.SIGUSR1 in signals:
        signals[signal.SIGUSR1](signal.SIGUSR1, None)
    if signal.SIGHUP in signals:
        with patch.object(active_config, "reload") as mock_reload:
            signals[signal.SIGHUP](signal.SIGHUP, None)
            assert mock_reload.called
