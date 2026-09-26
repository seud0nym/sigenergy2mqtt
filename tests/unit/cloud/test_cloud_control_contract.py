"""Contract tests for CloudControlPort implementations."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientPayloadError, ServerDisconnectedError

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
from sigenergy2mqtt.cloud.mysigen_adapter import MySigenCloudAdapter
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
def mysigen_adapter() -> MySigenCloudAdapter:
    adapter = MySigenCloudAdapter("delegated@example.com", "secret", "eu")
    adapter._client = SimpleNamespace(  # type: ignore[reportPrivateUsage]
        base_url="https://api.sigenergy.cloud/",
        region="testing",
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
        gateway_info=AsyncMock(return_value={"snCode": "GATEWAY"}),
        iter_topology_nodes=SigenergyCloudClient.iter_topology_nodes,
        topology_node_is_offline=SigenergyCloudClient.topology_node_is_offline,
        available_operational_modes=AsyncMock(return_value={"defaultWorkingModes": [], "energyProfileItems": []}),
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


@pytest.mark.asyncio
async def test_connect_normalizes_aiohttp_transport_errors(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    mysigen_adapter._client.connect.side_effect = ServerDisconnectedError()  # type: ignore[reportPrivateUsage]

    with pytest.raises(CloudControlUnavailableError):
        await mysigen_adapter.connect()


@pytest.mark.asyncio
async def test_connect_records_login_timing(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    with (
        patch("sigenergy2mqtt.cloud.mysigen_adapter.time.monotonic", side_effect=[10.0, 10.25]),
        patch("sigenergy2mqtt.cloud.mysigen_adapter.Metrics.cloud_connection", new_callable=AsyncMock) as connection_metric,
        patch("sigenergy2mqtt.cloud.mysigen_adapter.Metrics.cloud_connection_attempt", new_callable=AsyncMock) as timing_metric,
    ):
        await mysigen_adapter.connect()

    connection_metric.assert_awaited_once_with(connected=True)
    timing_metric.assert_awaited_once_with(0.25)


@pytest.mark.asyncio
async def test_operation_normalizes_aiohttp_transport_errors(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    mysigen_adapter._connected = True  # type: ignore[reportPrivateUsage]
    mysigen_adapter._client.get_operational_mode.side_effect = ClientPayloadError(  # type: ignore[reportPrivateUsage]
        "truncated response"
    )

    with patch("sigenergy2mqtt.cloud.mysigen_adapter.Metrics.cloud_availability", new_callable=AsyncMock) as availability_metric:
        with pytest.raises(CloudControlUnavailableError, match="truncated response"):
            await mysigen_adapter.get_operational_mode()

    assert mysigen_adapter._connected is True  # type: ignore[reportPrivateUsage]
    availability_metric.assert_awaited_once_with(False)

    mysigen_adapter._client.get_operational_mode.side_effect = None  # type: ignore[reportPrivateUsage]
    mysigen_adapter._client.get_operational_mode.return_value = (2, -1)  # type: ignore[reportPrivateUsage]
    assert await mysigen_adapter.get_operational_mode() == (2, -1)
    mysigen_adapter._client.connect.assert_not_awaited()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_unexpected_operation_error_is_counted(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    mysigen_adapter._connected = True  # type: ignore[reportPrivateUsage]
    mysigen_adapter._client.get_operational_mode.side_effect = KeyError("missing field")  # type: ignore[reportPrivateUsage]

    with (
        patch("sigenergy2mqtt.cloud.mysigen_adapter.Metrics.cloud_query", new_callable=AsyncMock) as query_metric,
        patch("sigenergy2mqtt.cloud.mysigen_adapter.Metrics.cloud_query_error", new_callable=AsyncMock) as error_metric,
    ):
        with pytest.raises(KeyError, match="missing field"):
            await mysigen_adapter.get_operational_mode()

    query_metric.assert_awaited_once()
    error_metric.assert_awaited_once_with()


async def test_device_list_uses_official_api_shape(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    assert await mysigen_adapter.device_list() == [
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


def test_mysigen_adapter_satisfies_port_and_reports_capabilities(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    assert isinstance(mysigen_adapter, CloudControlPort)
    assert mysigen_adapter.model == "mySigen Cloud (unofficial)"
    assert mysigen_adapter.capabilities.features == frozenset()
    assert mysigen_adapter.capabilities.min_duration == timedelta(minutes=1)
    assert mysigen_adapter.capabilities.max_duration == timedelta(minutes=1440)
    assert not mysigen_adapter.capabilities.supports(ControlFeature.SCHEDULING)


@pytest.mark.asyncio
async def test_gateway_info_delegates_to_cloud_client(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    assert await mysigen_adapter.gateway_info() == {"snCode": "GATEWAY"}
    mysigen_adapter._client.gateway_info.assert_awaited_once_with()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_lifecycle_is_idempotent(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    await mysigen_adapter.connect()
    await mysigen_adapter.connect()
    mysigen_adapter._client.connect.assert_awaited_once()  # type: ignore[reportPrivateUsage]

    await mysigen_adapter.close()
    mysigen_adapter._client.close.assert_awaited_once()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_translates_command_and_authoritative_status(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    await mysigen_adapter.set_instant_override(
        InstantOverrideCommand(
            InstantControlMode.CHARGE,
            timedelta(minutes=75),
        )
    )
    mysigen_adapter._client.set_instant_manual_control.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        InstantManualMode.CHARGING,
        duration_minutes=75,
    )

    status = await mysigen_adapter.instant_control_status()
    assert status.enabled is True
    assert status.mode is InstantControlMode.DISCHARGE
    assert status.ends_at == 1_800_000_000.0
    assert await mysigen_adapter.available_operational_modes() == {
        "defaultWorkingModes": [],
        "energyProfileItems": [],
    }
    assert await mysigen_adapter.get_operational_mode() == (2, -1)
    assert await mysigen_adapter.set_operational_mode(9, 7) == {"ok": True}
    mysigen_adapter._client.set_operational_mode.assert_awaited_once_with(9, 7)  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_clears_override(mysigen_adapter: MySigenCloudAdapter) -> None:
    await mysigen_adapter.clear_instant_override()
    mysigen_adapter._client.disable_instant_manual_control.assert_awaited_once()  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_port_delegates_all_limit_operations(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    assert await mysigen_adapter.grid_export_limit() == {"enable": True}
    assert await mysigen_adapter.set_grid_export_limit(4.5, enabled=False) == {"ok": True}
    assert await mysigen_adapter.grid_import_limit() == {"enable": True}
    assert await mysigen_adapter.set_grid_import_limit(6.5) == {"ok": True}
    assert await mysigen_adapter.grid_connection_limit() == {"enable": True}
    assert await mysigen_adapter.set_grid_connection_limit(32.0) == {"ok": True}
    assert await mysigen_adapter.battery_power_limit() == {"batteryMaxChargingPower": "5"}
    assert await mysigen_adapter.set_battery_power_limit(max_charge_kw=3.0, max_discharge_kw=None) == {"ok": True}
    assert await mysigen_adapter.solar_power_limit() == {"powerLimit": "6"}
    assert await mysigen_adapter.set_solar_power_limit(None) == {"ok": True}
    assert await mysigen_adapter.battery_export_limitation() == {
        "currentEnable": False,
        "ownerSetEnable": None,
        "installerSetEnable": None,
        "nearModify": None,
    }
    assert await mysigen_adapter.set_battery_export_limitation(False) == {"ok": True}

    mysigen_adapter._client.set_grid_export_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        4.5, enabled=False
    )
    mysigen_adapter._client.set_grid_import_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        6.5, enabled=True
    )
    mysigen_adapter._client.set_grid_connection_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        32.0, enabled=True
    )
    mysigen_adapter._client.set_battery_power_limit.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        max_charge_kw=3.0, max_discharge_kw=None
    )
    mysigen_adapter._client.set_battery_export_limitation.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
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
    mysigen_adapter: MySigenCloudAdapter,
    command: InstantOverrideCommand,
) -> None:
    with pytest.raises(CloudControlUnsupportedError):
        await mysigen_adapter.set_instant_override(command)


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [0, 1441])
async def test_port_rejects_duration_outside_capabilities(
    mysigen_adapter: MySigenCloudAdapter,
    minutes: int,
) -> None:
    with pytest.raises(CloudControlRejectedError):
        await mysigen_adapter.set_instant_override(
            InstantOverrideCommand(
                InstantControlMode.HOLD,
                timedelta(minutes=minutes),
            )
        )


def test_registry_requires_explicit_unofficial_api_opt_in() -> None:
    registry = CloudControlRegistry()
    config = CloudConfig(username="user", password="password", region="eu")  # pyright: ignore[reportCallIssue]

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
            **{"accept-unofficial-api-risk": True},  # pyright: ignore[reportArgumentType]
        )
    )
    assert registry.provider == "mysigen"
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
            **{"accept-unofficial-api-risk": True},  # pyright: ignore[reportArgumentType]
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
    mysigen_adapter: MySigenCloudAdapter,
    vendor_error: Exception,
    domain_error: type[Exception],
) -> None:
    mysigen_adapter._client.connect.side_effect = vendor_error  # type: ignore[reportPrivateUsage]

    with pytest.raises(domain_error):
        await mysigen_adapter.connect()


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
    mysigen_adapter: MySigenCloudAdapter,
    method_name: str,
    vendor_error: Exception,
    domain_error: type[Exception],
) -> None:
    mysigen_adapter._connected = True  # type: ignore[reportPrivateUsage]
    getattr(mysigen_adapter._client, method_name).side_effect = vendor_error  # type: ignore[reportPrivateUsage]

    with pytest.raises(domain_error):
        if method_name == "set_instant_manual_control":
            await mysigen_adapter.set_instant_override(InstantOverrideCommand(InstantControlMode.CHARGE, timedelta(minutes=30)))
        elif method_name == "disable_instant_manual_control":
            await mysigen_adapter.clear_instant_override()
        elif method_name == "instant_manual_control":
            await mysigen_adapter.instant_control_status()
        else:
            await mysigen_adapter.get_operational_mode()

    if isinstance(vendor_error, SigenergyCloudAuthError):
        assert mysigen_adapter._connected is False  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "invoke", "recovered_value"),
    [
        (
            "set_instant_manual_control",
            lambda adapter: adapter.set_instant_override(InstantOverrideCommand(InstantControlMode.CHARGE, timedelta(minutes=30))),
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
    mysigen_adapter: MySigenCloudAdapter,
    method_name: str,
    invoke,
    recovered_value,
) -> None:
    mysigen_adapter._connected = True  # type: ignore[reportPrivateUsage]
    mysigen_adapter._connection_generation = 1  # type: ignore[reportPrivateUsage]
    operation = getattr(mysigen_adapter._client, method_name)  # type: ignore[reportPrivateUsage]
    operation.side_effect = [SigenergyCloudAuthError("session terminated"), recovered_value]

    result = await invoke(mysigen_adapter)

    assert mysigen_adapter._connected is True  # type: ignore[reportPrivateUsage]
    assert mysigen_adapter._connection_generation == 2  # type: ignore[reportPrivateUsage]
    mysigen_adapter._client.connect.assert_awaited_once()  # type: ignore[reportPrivateUsage]
    assert operation.await_count == 2
    if method_name == "instant_manual_control":
        assert result.mode is InstantControlMode.CHARGE
        assert result.ends_at == 1_800_000_001.0
    else:
        assert result == recovered_value


@pytest.mark.asyncio
async def test_stale_authentication_failure_does_not_invalidate_new_connection(
    mysigen_adapter: MySigenCloudAdapter,
) -> None:
    mysigen_adapter._connected = True  # type: ignore[reportPrivateUsage]
    mysigen_adapter._connection_generation = 1  # type: ignore[reportPrivateUsage]
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

    mysigen_adapter._client.get_operational_mode.side_effect = (  # type: ignore[reportPrivateUsage]
        get_operational_mode
    )
    stale_operation = asyncio.create_task(mysigen_adapter.get_operational_mode())
    await stale_retry_started.wait()

    assert await mysigen_adapter.get_operational_mode() == (2, -1)
    allow_stale_retry_to_fail.set()
    with pytest.raises(CloudControlAuthError, match="stale retry rejected"):
        await stale_operation

    assert mysigen_adapter._connected is True  # type: ignore[reportPrivateUsage]
    assert mysigen_adapter._connection_generation == 3  # type: ignore[reportPrivateUsage]
    assert mysigen_adapter._client.connect.await_count == 2  # type: ignore[reportPrivateUsage]


def test_official_adapter_is_explicitly_unavailable() -> None:
    from sigenergy2mqtt.cloud.official_adapter import OfficialCloudAdapter

    with pytest.raises(NotImplementedError, match="not available"):
        OfficialCloudAdapter()
