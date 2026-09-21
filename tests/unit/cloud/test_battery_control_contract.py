"""Contract tests for CloudControlPort implementations."""

import asyncio

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.community_adapter import CommunityCloudAdapter
from sigenergy2mqtt.cloud.exceptions import (
    CloudControlAuthError,
    CloudControlRateLimitedError,
    CloudControlRejectedError,
    CloudControlUnavailableError,
    CloudControlUnsupportedError,
)
from sigenergy2mqtt.cloud.models import (
    ControlFeature,
    InstantControlMode,
    InstantOverrideCommand,
)
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.cloud.registry import CloudControlRegistry
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import (
    InstantManualMode,
    SigenergyCloudClient,
)
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.errors import (
    SigenergyCloudAPIError,
    SigenergyCloudAuthError,
    SigenergyCloudError,
    SigenergyCloudRateLimitError,
)
from sigenergy2mqtt.config.models.cloud import CloudConfig


@pytest.fixture
def community_adapter() -> CommunityCloudAdapter:
    adapter = CommunityCloudAdapter("delegated@example.com", "secret", "eu")
    adapter._client = SimpleNamespace(  # type: ignore[reportPrivateUsage]
        connect=AsyncMock(),
        close=AsyncMock(),
        set_instant_manual_control=AsyncMock(),
        disable_instant_manual_control=AsyncMock(),
        instant_manual_control=AsyncMock(
            return_value=SimpleNamespace(
                enabled=True,
                mode=InstantManualMode.DISCHARGING,
                end_time=1_800_000_000,
            )
        ),
        device_topology=AsyncMock(
            return_value={
                "stationId": 123,
                "nodeList": [
                    {
                        "stationId": 123,
                        "snCode": "AIO",
                        "deviceType": 2,
                        "deviceStatus": 1,
                        "communicateStatus": 2,
                        "nodeList": [
                            {
                                "stationId": 123,
                                "snCode": "INV",
                                "deviceType": 3,
                                "deviceStatus": 1,
                                "communicateStatus": 2,
                                "deviceCode": "PN1",
                                "modelVersionStr": "FW1",
                                "ratedActivePower": 8.0,
                                "nodeList": [],
                            },
                            {
                                "stationId": 123,
                                "snCode": "BAT",
                                "deviceType": 4,
                                "deviceStatus": 4,
                                "communicateStatus": 1,
                                "modelVersionStr": "FW2",
                                "nodeList": [],
                            },
                        ],
                    }
                ],
            }
        ),
        iter_topology_nodes=SigenergyCloudClient.iter_topology_nodes,
        topology_node_is_offline=SigenergyCloudClient.topology_node_is_offline,
        available_operational_modes=AsyncMock(
            return_value={"defaultWorkingModes": [], "energyProfileItems": []}
        ),
        get_operational_mode=AsyncMock(return_value=(2, -1)),
        set_operational_mode=AsyncMock(return_value={"ok": True}),
        grid_export_limit=AsyncMock(return_value={"enable": True}),
        set_grid_export_limit=AsyncMock(return_value={"ok": True}),
        grid_import_limit=AsyncMock(return_value={"enable": True}),
        set_grid_import_limit=AsyncMock(return_value={"ok": True}),
        grid_connection_limit=AsyncMock(return_value={"enable": True}),
        set_grid_connection_limit=AsyncMock(return_value={"ok": True}),
        battery_power_limit=AsyncMock(return_value={"batteryMaxChargingPower": "5"}),
        set_battery_power_limit=AsyncMock(return_value={"ok": True}),
        solar_power_limit=AsyncMock(return_value={"powerLimit": "6"}),
        set_solar_power_limit=AsyncMock(return_value={"ok": True}),
        battery_export_limitation=AsyncMock(
            return_value={
                "currentEnable": False,
                "ownerSetEnable": None,
                "installerSetEnable": None,
                "nearModify": None,
            }
        ),
        set_battery_export_limitation=AsyncMock(return_value={"ok": True}),
    )
    return adapter


async def test_device_list_uses_official_api_shape(
    community_adapter: CommunityCloudAdapter,
) -> None:
    assert await community_adapter.device_list() == [
        {
            "systemId": "123",
            "serialNumber": "INV",
            "deviceType": "Inverter",
            "status": "Normal",
            "pn": "PN1",
            "firmwareVersion": "FW1",
            "attrMap": {"ratedActivePower": 8.0},
        },
        {
            "systemId": "123",
            "serialNumber": "BAT",
            "deviceType": "Battery",
            "status": "Offline",
            "pn": "",
            "firmwareVersion": "FW2",
            "attrMap": {},
        },
    ]


def test_community_adapter_satisfies_port_and_reports_capabilities(
    community_adapter: CommunityCloudAdapter,
) -> None:
    assert isinstance(community_adapter, CloudControlPort)
    assert community_adapter.model == "mySigen Cloud (unofficial)"
    assert community_adapter.capabilities.features == frozenset()
    assert community_adapter.capabilities.min_duration == timedelta(minutes=1)
    assert community_adapter.capabilities.max_duration == timedelta(minutes=1440)
    assert not community_adapter.capabilities.supports(ControlFeature.SCHEDULING)


@pytest.mark.asyncio
async def test_port_lifecycle_is_idempotent(
    community_adapter: CommunityCloudAdapter,
) -> None:
    await community_adapter.connect()
    await community_adapter.connect()
    community_adapter._client.connect.assert_awaited_once()  # type: ignore[reportPrivateUsage]

    await community_adapter.close()
    community_adapter._client.close.assert_awaited_once()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_translates_command_and_authoritative_status(
    community_adapter: CommunityCloudAdapter,
) -> None:
    await community_adapter.set_instant_override(
        InstantOverrideCommand(
            InstantControlMode.CHARGE,
            timedelta(minutes=75),
        )
    )
    community_adapter._client.set_instant_manual_control.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        InstantManualMode.CHARGING,
        duration_minutes=75,
    )

    status = await community_adapter.instant_control_status()
    assert status.enabled is True
    assert status.mode is InstantControlMode.DISCHARGE
    assert status.ends_at == 1_800_000_000.0
    assert await community_adapter.available_operational_modes() == {
        "defaultWorkingModes": [],
        "energyProfileItems": [],
    }
    assert await community_adapter.get_operational_mode() == (2, -1)
    assert await community_adapter.set_operational_mode(9, 7) == {"ok": True}
    community_adapter._client.set_operational_mode.assert_awaited_once_with(9, 7)  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_clears_override(community_adapter: CommunityCloudAdapter) -> None:
    await community_adapter.clear_instant_override()
    community_adapter._client.disable_instant_manual_control.assert_awaited_once()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_delegates_all_limit_operations(
    community_adapter: CommunityCloudAdapter,
) -> None:
    assert await community_adapter.grid_export_limit() == {"enable": True}
    assert await community_adapter.set_grid_export_limit(4.5, enabled=False) == {
        "ok": True
    }
    assert await community_adapter.grid_import_limit() == {"enable": True}
    assert await community_adapter.set_grid_import_limit(6.5) == {"ok": True}
    assert await community_adapter.grid_connection_limit() == {"enable": True}
    assert await community_adapter.set_grid_connection_limit(32.0) == {"ok": True}
    assert await community_adapter.battery_power_limit() == {
        "batteryMaxChargingPower": "5"
    }
    assert await community_adapter.set_battery_power_limit(
        max_charge_kw=3.0, max_discharge_kw=None
    ) == {"ok": True}
    assert await community_adapter.solar_power_limit() == {"powerLimit": "6"}
    assert await community_adapter.set_solar_power_limit(None) == {"ok": True}
    assert await community_adapter.battery_export_limitation() == {
        "currentEnable": False,
        "ownerSetEnable": None,
        "installerSetEnable": None,
        "nearModify": None,
    }
    assert await community_adapter.set_battery_export_limitation(False) == {"ok": True}

    community_adapter._client.set_grid_export_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        4.5, enabled=False
    )
    community_adapter._client.set_grid_import_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        6.5, enabled=True
    )
    community_adapter._client.set_grid_connection_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        32.0, enabled=True
    )
    community_adapter._client.set_battery_power_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        max_charge_kw=3.0, max_discharge_kw=None
    )
    community_adapter._client.set_battery_export_limitation.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        InstantOverrideCommand(
            InstantControlMode.CHARGE,
            timedelta(minutes=30),
            power_kw=5,
        ),
        InstantOverrideCommand(
            InstantControlMode.CHARGE,
            timedelta(minutes=30),
            starts_at=1_800_000_000,
        ),
        InstantOverrideCommand(
            InstantControlMode.CHARGE,
            timedelta(minutes=30),
            charge_priority="pv",
        ),
    ],
)
async def test_port_rejects_unsupported_features(
    community_adapter: CommunityCloudAdapter,
    command: InstantOverrideCommand,
) -> None:
    with pytest.raises(CloudControlUnsupportedError):
        await community_adapter.set_instant_override(command)


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [0, 1441])
async def test_port_rejects_duration_outside_capabilities(
    community_adapter: CommunityCloudAdapter,
    minutes: int,
) -> None:
    with pytest.raises(CloudControlRejectedError):
        await community_adapter.set_instant_override(
            InstantOverrideCommand(
                InstantControlMode.HOLD,
                timedelta(minutes=minutes),
            )
        )


def test_registry_requires_explicit_unofficial_api_opt_in() -> None:
    registry = CloudControlRegistry()
    config = CloudConfig(username="user", password="password", region="eu")

    with pytest.raises(ValueError, match="accept-unofficial-api-risk"):
        registry.configure(config)


@pytest.mark.asyncio
async def test_registry_owns_selected_adapter_lifecycle() -> None:
    registry = CloudControlRegistry()
    registry.configure(
        CloudConfig(
            username="user",
            password="password",
            region="eu",
            **{"accept-unofficial-api-risk": True},
        )
    )
    assert registry.provider == "community"
    assert registry.active is not None
    registry.active.connect = AsyncMock()  # type: ignore[method-assign]
    registry.active.close = AsyncMock()  # type: ignore[method-assign]

    assert await registry.transport_factory() is registry.active
    registry.active.connect.assert_awaited_once()
    await registry.close()
    registry.active.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_registry_closes_partially_connected_adapter() -> None:
    registry = CloudControlRegistry()
    registry.configure(
        CloudConfig(
            username="user",
            password="password",
            region="eu",
            **{"accept-unofficial-api-risk": True},
        )
    )
    assert registry.active is not None
    registry.active.connect = AsyncMock(side_effect=RuntimeError("discovery failed"))  # type: ignore[method-assign]
    registry.active.close = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="discovery failed"):
        await registry.transport_factory()

    registry.active.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("vendor_error", "domain_error"),
    [
        (SigenergyCloudAuthError("bad credentials"), CloudControlAuthError),
        (SigenergyCloudRateLimitError("slow down"), CloudControlRateLimitedError),
        (SigenergyCloudError("offline"), CloudControlUnavailableError),
        (OSError("network"), CloudControlUnavailableError),
    ],
)
async def test_connect_translates_vendor_errors(
    community_adapter: CommunityCloudAdapter,
    vendor_error: Exception,
    domain_error: type[Exception],
) -> None:
    community_adapter._client.connect.side_effect = vendor_error  # type: ignore[reportPrivateUsage]

    with pytest.raises(domain_error):
        await community_adapter.connect()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "vendor_error", "domain_error"),
    [
        (
            "set_instant_manual_control",
            SigenergyCloudRateLimitError("limited"),
            CloudControlRateLimitedError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudAuthError("expired"),
            CloudControlAuthError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudAPIError("rejected"),
            CloudControlRejectedError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudError("offline"),
            CloudControlUnavailableError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudRateLimitError("limited"),
            CloudControlRateLimitedError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudAuthError("expired"),
            CloudControlAuthError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudError("offline"),
            CloudControlUnavailableError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudRateLimitError("limited"),
            CloudControlRateLimitedError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudAuthError("expired"),
            CloudControlAuthError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudError("offline"),
            CloudControlUnavailableError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudRateLimitError("limited"),
            CloudControlRateLimitedError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudAuthError("expired"),
            CloudControlAuthError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudError("offline"),
            CloudControlUnavailableError,
        ),
    ],
)
async def test_operations_translate_vendor_errors(
    community_adapter: CommunityCloudAdapter,
    method_name: str,
    vendor_error: Exception,
    domain_error: type[Exception],
) -> None:
    community_adapter._connected = True  # type: ignore[reportPrivateUsage]
    getattr(community_adapter._client, method_name).side_effect = vendor_error  # type: ignore[reportPrivateUsage]

    with pytest.raises(domain_error):
        if method_name == "set_instant_manual_control":
            await community_adapter.set_instant_override(
                InstantOverrideCommand(InstantControlMode.CHARGE, timedelta(minutes=30))
            )
        elif method_name == "disable_instant_manual_control":
            await community_adapter.clear_instant_override()
        elif method_name == "instant_manual_control":
            await community_adapter.instant_control_status()
        else:
            await community_adapter.get_operational_mode()

    if isinstance(vendor_error, SigenergyCloudAuthError):
        assert community_adapter._connected is False  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "invoke", "recovered_value"),
    [
        (
            "set_instant_manual_control",
            lambda adapter: adapter.set_instant_override(
                InstantOverrideCommand(
                    InstantControlMode.CHARGE, timedelta(minutes=30)
                )
            ),
            None,
        ),
        (
            "instant_manual_control",
            lambda adapter: adapter.instant_control_status(),
            SimpleNamespace(
                enabled=True,
                mode=InstantManualMode.CHARGING,
                end_time=1_800_000_001,
            ),
        ),
        (
            "get_operational_mode",
            lambda adapter: adapter.get_operational_mode(),
            (2, -1),
        ),
    ],
)
async def test_operations_reauthenticate_and_retry_after_session_termination(
    community_adapter: CommunityCloudAdapter,
    method_name: str,
    invoke,
    recovered_value,
) -> None:
    community_adapter._connected = True  # type: ignore[reportPrivateUsage]
    community_adapter._connection_generation = 1  # type: ignore[reportPrivateUsage]
    operation = getattr(community_adapter._client, method_name)  # type: ignore[reportPrivateUsage]
    operation.side_effect = [SigenergyCloudAuthError("session terminated"), recovered_value]

    result = await invoke(community_adapter)

    assert community_adapter._connected is True  # type: ignore[reportPrivateUsage]
    assert community_adapter._connection_generation == 2  # type: ignore[reportPrivateUsage]
    community_adapter._client.connect.assert_awaited_once()  # type: ignore[reportPrivateUsage]
    assert operation.await_count == 2
    if method_name == "instant_manual_control":
        assert result.mode is InstantControlMode.CHARGE
        assert result.ends_at == 1_800_000_001.0
    else:
        assert result == recovered_value


@pytest.mark.asyncio
async def test_stale_authentication_failure_does_not_invalidate_new_connection(
    community_adapter: CommunityCloudAdapter,
) -> None:
    community_adapter._connected = True  # type: ignore[reportPrivateUsage]
    community_adapter._connection_generation = 1  # type: ignore[reportPrivateUsage]
    stale_retry_started = asyncio.Event()
    allow_stale_retry_to_fail = asyncio.Event()
    call_count = 0

    async def get_operational_mode() -> tuple[int, int]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SigenergyCloudAuthError("old session terminated")
        if call_count == 2:
            stale_retry_started.set()
            await allow_stale_retry_to_fail.wait()
            raise SigenergyCloudAuthError("stale retry rejected")
        if call_count == 3:
            raise SigenergyCloudAuthError("replacement session terminated")
        return (2, -1)

    community_adapter._client.get_operational_mode.side_effect = (  # type: ignore[reportPrivateUsage]
        get_operational_mode
    )
    stale_operation = asyncio.create_task(community_adapter.get_operational_mode())
    await stale_retry_started.wait()

    assert await community_adapter.get_operational_mode() == (2, -1)
    allow_stale_retry_to_fail.set()
    with pytest.raises(CloudControlAuthError, match="stale retry rejected"):
        await stale_operation

    assert community_adapter._connected is True  # type: ignore[reportPrivateUsage]
    assert community_adapter._connection_generation == 3  # type: ignore[reportPrivateUsage]
    assert community_adapter._client.connect.await_count == 2  # type: ignore[reportPrivateUsage]


def test_official_adapter_is_explicitly_unavailable() -> None:
    from sigenergy2mqtt.cloud.official_adapter import OfficialCloudAdapter

    with pytest.raises(NotImplementedError, match="not available"):
        OfficialCloudAdapter()
