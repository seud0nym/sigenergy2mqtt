import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import sigenergy2mqtt.main.main as main_mod


@pytest.mark.asyncio
async def test_watch_grid_restore_requests_restart(monkeypatch):
    class FakeModbus:
        def __init__(self, *args, **kwargs):
            self.connected = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main_mod, "ModbusClient", FakeModbus)
    monkeypatch.setattr(main_mod, "_is_grid_outage", AsyncMock(side_effect=[True, False]))
    request_mock = MagicMock()
    monkeypatch.setattr(main_mod.restart_controller, "request", request_mock)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await main_mod._watch_grid_restore_and_request_restart("127.0.0.1", 502, 1, 0, 0)

    assert request_mock.called


@pytest.mark.asyncio
async def test_setup_ac_chargers_schedules_restart_watcher_on_outage_skip(monkeypatch):
    mock_modbus_cfg = MagicMock(ac_chargers=[1], host="h", port=502, timeout=1, retries=0)
    mock_plant = MagicMock()
    mock_config = MagicMock()

    monkeypatch.setattr(main_mod, "make_ac_charger", AsyncMock(side_effect=RuntimeError("unreachable")))
    monkeypatch.setattr(main_mod, "_is_grid_outage", AsyncMock(return_value=True))
    schedule_mock = MagicMock()
    monkeypatch.setattr(main_mod, "_schedule_restart_on_grid_restore", schedule_mock)

    await main_mod._setup_ac_chargers(0, mock_modbus_cfg, mock_plant, AsyncMock(), mock_config, main_mod.Protocol.V2_8, 0, 1)

    schedule_mock.assert_called_once_with(mock_modbus_cfg, 0)
