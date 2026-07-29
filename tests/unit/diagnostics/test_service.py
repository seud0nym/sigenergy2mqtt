import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import paho.mqtt.client as mqtt

from sigenergy2mqtt.diagnostics.service import DiagnosticsService


@pytest.fixture
def diagnostics_service() -> DiagnosticsService:
    return DiagnosticsService()


@pytest.mark.asyncio
async def test_schedule(diagnostics_service: DiagnosticsService) -> None:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    coros = diagnostics_service.schedule(None, mqtt_client)
    assert len(coros) == 1
    # We won't await it here as it starts a server loop which may block or fail
    coros[0].close()



@pytest.mark.asyncio
async def test_run_without_crashing_the_thread_success(diagnostics_service: DiagnosticsService) -> None:
    with patch("sigenergy2mqtt.diagnostics.service.diagnostics_server.run", new_callable=AsyncMock) as mock_run:
        await diagnostics_service._run_without_crashing_the_thread()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_without_crashing_the_thread_handles_oserror(diagnostics_service: DiagnosticsService) -> None:
    with patch("sigenergy2mqtt.diagnostics.service.diagnostics_server.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = OSError("Address already in use")
        # Should not raise exception
        await diagnostics_service._run_without_crashing_the_thread()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_without_crashing_the_thread_handles_runtimeerror(diagnostics_service: DiagnosticsService) -> None:
    with patch("sigenergy2mqtt.diagnostics.service.diagnostics_server.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = RuntimeError("Something bad")
        # Should not raise exception
        await diagnostics_service._run_without_crashing_the_thread()
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_without_crashing_the_thread_propagates_cancel(diagnostics_service: DiagnosticsService) -> None:
    with patch("sigenergy2mqtt.diagnostics.service.diagnostics_server.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await diagnostics_service._run_without_crashing_the_thread()
        mock_run.assert_called_once()
