"""End-to-end tests for the cloud API bundled with the Modbus test server."""

import asyncio
import socket
from dataclasses import replace
from datetime import timedelta

import pytest

from sigenergy2mqtt.cloud.community_adapter import CommunityCloudAdapter
from sigenergy2mqtt.cloud.models import InstantControlMode, InstantOverrideCommand
from sigenergy2mqtt.config import Config, _swap_active_config
from tests.utils.modbus_test_server import run_async_server, wait_for_server_start


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.integration
async def test_community_cloud_adapter_against_test_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modbus_port = _free_port()
    cloud_port = _free_port()
    monkeypatch.setenv("MODBUS_TEST_SERVER_CLOUD_USERNAME", "cloud-user")
    monkeypatch.setenv("MODBUS_TEST_SERVER_CLOUD_PASSWORD", "cloud-password")
    monkeypatch.setenv(
        "SIGENERGY2MQTT_CLOUD_TESTING_URL", f"http://127.0.0.1:{cloud_port}/"
    )
    task = asyncio.create_task(
        run_async_server(
            None,
            None,
            use_simplified_topics=True,
            host="127.0.0.1",
            port=modbus_port,
            cloud_port=cloud_port,
        )
    )
    assert await wait_for_server_start("127.0.0.1", modbus_port)
    assert await wait_for_server_start("127.0.0.1", cloud_port)

    adapter: CommunityCloudAdapter | None = None
    try:
        with _swap_active_config(Config()):
            adapter = CommunityCloudAdapter(
                "cloud-user", "cloud-password", "testing"
            )
            status = await adapter.instant_control_status()
            assert status.enabled is False
            assert status.mode is InstantControlMode.DISCHARGE
            assert status.ends_at is None

            # Expire the locally cached token so the next request exercises the
            # refresh-token grant rather than authenticating with credentials.
            tokens = adapter._client._auth._tokens
            assert tokens is not None
            initial_access_token = tokens.access_token
            adapter._client._auth._tokens = replace(tokens, expires_at=0)
            status = await adapter.instant_control_status()
            refreshed_tokens = adapter._client._auth._tokens
            assert refreshed_tokens is not None
            assert refreshed_tokens.access_token != initial_access_token
            assert status.enabled is False

            modes = await adapter.available_operational_modes()
            assert len(modes["defaultWorkingModes"]) == 6
            assert await adapter.device_list() == [
                {
                    "systemId": "10000000000001",
                    "serialNumber": "INV-TEST",
                    "deviceType": "Inverter",
                    "status": "Normal",
                    "pn": "PN-INV",
                    "firmwareVersion": "V100R001C00",
                    "attrMap": {"ratedActivePower": 6.0},
                }
            ]
            assert await adapter.get_operational_mode() == (0, -1)
            await adapter.set_operational_mode(7)
            assert await adapter.get_operational_mode() == (7, -1)

            await adapter.set_instant_override(
                InstantOverrideCommand(
                    mode=InstantControlMode.CHARGE,
                    duration=timedelta(minutes=5),
                )
            )
            status = await adapter.instant_control_status()
            assert status.enabled is True
            assert status.mode is InstantControlMode.CHARGE
            assert status.ends_at is not None
            await adapter.clear_instant_override()
            assert (await adapter.instant_control_status()).enabled is False
    finally:
        if adapter is not None:
            await adapter.close()
        task.cancel()
        await task
