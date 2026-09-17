"""Contract tests for BatteryControlPort implementations."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.community_adapter import CommunityCloudAdapter
from sigenergy2mqtt.cloud.exceptions import (
    BatteryControlRejectedError,
    BatteryControlUnsupportedError,
)
from sigenergy2mqtt.cloud.models import (
    ControlFeature,
    InstantControlMode,
    InstantOverrideCommand,
)
from sigenergy2mqtt.cloud.port import BatteryControlPort
from sigenergy2mqtt.cloud.registry import BatteryControlRegistry
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import InstantManualMode
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
        current_operational_mode=AsyncMock(return_value="TOU"),
    )
    return adapter


def test_community_adapter_satisfies_port_and_reports_capabilities(
    community_adapter: CommunityCloudAdapter,
) -> None:
    assert isinstance(community_adapter, BatteryControlPort)
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
    assert await community_adapter.current_strategy_label() == "TOU"


@pytest.mark.asyncio
async def test_port_clears_override(community_adapter: CommunityCloudAdapter) -> None:
    await community_adapter.clear_instant_override()
    community_adapter._client.disable_instant_manual_control.assert_awaited_once()  # type: ignore[reportPrivateUsage]


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
