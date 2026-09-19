"""Contract tests for CloudControlPort implementations."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.community_adapter import CommunityCloudAdapter
from sigenergy2mqtt.cloud.exceptions import (
    BatteryControlAuthError,
    BatteryControlRateLimitedError,
    BatteryControlRejectedError,
    BatteryControlUnavailableError,
    BatteryControlUnsupportedError,
)
from sigenergy2mqtt.cloud.models import (
    ControlFeature,
    InstantControlMode,
    InstantOverrideCommand,
)
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.cloud.registry import BatteryControlRegistry
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import InstantManualMode
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


def test_community_adapter_satisfies_port_and_reports_capabilities(
    community_adapter: CommunityCloudAdapter,
) -> None:
    assert isinstance(community_adapter, CloudControlPort)
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
    with pytest.raises(BatteryControlUnsupportedError):
        await community_adapter.set_instant_override(command)


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [0, 1441])
async def test_port_rejects_duration_outside_capabilities(
    community_adapter: CommunityCloudAdapter,
    minutes: int,
) -> None:
    with pytest.raises(BatteryControlRejectedError):
        await community_adapter.set_instant_override(
            InstantOverrideCommand(
                InstantControlMode.HOLD,
                timedelta(minutes=minutes),
            )
        )


def test_registry_requires_explicit_unofficial_api_opt_in() -> None:
    registry = BatteryControlRegistry()
    config = CloudConfig(username="user", password="password", region="eu")

    with pytest.raises(ValueError, match="accept-unofficial-api-risk"):
        registry.configure(config)


@pytest.mark.asyncio
async def test_registry_owns_selected_adapter_lifecycle() -> None:
    registry = BatteryControlRegistry()
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
    registry = BatteryControlRegistry()
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
        (SigenergyCloudAuthError("bad credentials"), BatteryControlAuthError),
        (SigenergyCloudRateLimitError("slow down"), BatteryControlRateLimitedError),
        (SigenergyCloudError("offline"), BatteryControlUnavailableError),
        (OSError("network"), BatteryControlUnavailableError),
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
            BatteryControlRateLimitedError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudAuthError("expired"),
            BatteryControlAuthError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudAPIError("rejected"),
            BatteryControlRejectedError,
        ),
        (
            "set_instant_manual_control",
            SigenergyCloudError("offline"),
            BatteryControlUnavailableError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudRateLimitError("limited"),
            BatteryControlRateLimitedError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudAuthError("expired"),
            BatteryControlAuthError,
        ),
        (
            "disable_instant_manual_control",
            SigenergyCloudError("offline"),
            BatteryControlUnavailableError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudRateLimitError("limited"),
            BatteryControlRateLimitedError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudAuthError("expired"),
            BatteryControlAuthError,
        ),
        (
            "instant_manual_control",
            SigenergyCloudError("offline"),
            BatteryControlUnavailableError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudRateLimitError("limited"),
            BatteryControlRateLimitedError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudAuthError("expired"),
            BatteryControlAuthError,
        ),
        (
            "get_operational_mode",
            SigenergyCloudError("offline"),
            BatteryControlUnavailableError,
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


def test_official_adapter_is_explicitly_unavailable() -> None:
    from sigenergy2mqtt.cloud.official_adapter import OfficialCloudAdapter

    with pytest.raises(NotImplementedError, match="not available"):
        OfficialCloudAdapter()
