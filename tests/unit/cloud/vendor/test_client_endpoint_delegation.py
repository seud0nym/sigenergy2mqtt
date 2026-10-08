"""Endpoint delegation and validation for the vendored cloud client."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import (
    BatteryLevelSettings,
    SigenergyCloudClient,
    is_unlimited_power,
)


@pytest.fixture
def client() -> SigenergyCloudClient:
    instance = SigenergyCloudClient("user", "password")
    instance.station_id = "123"
    instance.dc_sns = ("DC1",)
    instance._data = AsyncMock(return_value={"value": 1})  # type: ignore[method-assign]
    instance._station_data = AsyncMock(return_value={"value": 1})  # type: ignore[method-assign]
    instance._dc_data = AsyncMock(return_value={"value": 1})  # type: ignore[method-assign]
    instance._envelope = AsyncMock(return_value={"ok": True})  # type: ignore[method-assign]
    return instance


def test_power_helpers_and_dc_serial_property(client: SigenergyCloudClient) -> None:
    assert client.dc_sn == "DC1"
    client.dc_sns = ()
    assert client.dc_sn is None
    assert is_unlimited_power("not-a-number") is False


@pytest.mark.asyncio
async def test_client_closes_owned_session(client: SigenergyCloudClient) -> None:
    session = AsyncMock()
    client._owned_session = session  # type: ignore[reportPrivateUsage]

    await client.close()

    session.close.assert_awaited_once()
    assert client._owned_session is None  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_energy_flow_falls_back_but_preserves_rate_limit(
    client: SigenergyCloudClient,
) -> None:
    from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.errors import (
        SigenergyCloudAPIError,
        SigenergyCloudRateLimitError,
    )

    client._station_data.side_effect = SigenergyCloudAPIError("async unavailable")  # type: ignore[reportPrivateUsage]
    assert await client.energy_flow() == {"value": 1}
    client._data.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        "GET", "device/sigen/station/energyflow", params={"id": "123"}
    )

    client._station_data.side_effect = SigenergyCloudRateLimitError("limited")  # type: ignore[reportPrivateUsage]
    with pytest.raises(SigenergyCloudRateLimitError):
        await client.energy_flow()


@pytest.mark.asyncio
async def test_operational_mode_labels_default_profile_and_unknown(
    client: SigenergyCloudClient,
) -> None:
    client._operational_modes = {  # type: ignore[reportPrivateUsage]
        "defaultWorkingModes": [{"value": "2", "label": "Self Consumption"}],
        "energyProfileItems": [{"profileId": 7, "name": "TOU"}],
    }
    client._station_data.side_effect = [  # type: ignore[reportPrivateUsage]
        {"currentMode": 2, "currentProfileId": -1},
        {"currentMode": 9, "currentProfileId": 7},
        {"currentMode": 8, "currentProfileId": -1},
    ]

    assert await client.current_operational_mode() == "Self Consumption"
    assert await client.current_operational_mode() == "TOU"
    assert await client.current_operational_mode() == "Unknown mode"


@pytest.mark.asyncio
async def test_get_operational_mode_returns_mode_and_profile_ids(
    client: SigenergyCloudClient,
) -> None:
    client._station_data.return_value = {  # type: ignore[reportPrivateUsage]
        "currentMode": 9,
        "currentProfileId": 7,
    }

    assert await client.get_operational_mode() == (9, 7)
    client._station_data.assert_awaited_once_with(  # type: ignore[reportPrivateUsage]
        "GET", "device/energy-profile/mode/current/{station_id}"
    )


@pytest.mark.asyncio
async def test_read_endpoints_delegate_to_expected_helpers(
    client: SigenergyCloudClient,
) -> None:
    station_reads = [
        (
            client.grid_export_limit,
            "device/energy-profile/grid/limitation/export/{station_id}",
        ),
        (
            client.grid_import_limit,
            "device/energy-profile/grid/limitation/import/{station_id}",
        ),
        (
            client.grid_connection_limit,
            "device/energy-profile/parallel/off/grid/{station_id}",
        ),
        (
            client.battery_power_limit,
            "device/energy-profile/battery/limit/{station_id}",
        ),
        (client.solar_power_limit, "device/energy-profile/solar/limit/{station_id}"),
        (client.backup_reserve, "device/setting/backup/reserve/{station_id}"),
        (client.gateway_info, "device/gateway/{station_id}"),
        (
            client.battery_export_limitation,
            "device/energy-profile/battery/export/limitation/{station_id}",
        ),
        (
            client.instant_manual_display,
            "device/energy-profile/instant/manunal/display/{station_id}",
        ),
    ]
    for operation, path in station_reads:
        client._station_data.reset_mock()  # type: ignore[reportPrivateUsage]
        assert await operation() == {"value": 1}
        client._station_data.assert_awaited_once_with("GET", path)  # type: ignore[reportPrivateUsage]

    dc_reads = [
        (client.dc_charge_mode, "device/charge/mode/dc"),
        (client.dc_charge_setting, "device/dcevse/charge/setting"),
        (client.dc_status, "device/dcevse/status"),
        (client.dc_charge_realtime, "device/dcevse/charge/realtime"),
        (client.dc_discharge_realtime, "device/dcevse/discharge/realtime"),
        (client.dc_energy_totals, "data-process/dcevse/energy"),
        (client.dc_ocpp_status, "device/dcevse/ocpp/status"),
    ]
    for operation, path in dc_reads:
        client._dc_data.reset_mock()  # type: ignore[reportPrivateUsage]
        assert await operation() == {"value": 1}
        client._dc_data.assert_awaited_once_with("GET", path, None)  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_write_endpoints_build_payloads_and_validate_ranges(
    client: SigenergyCloudClient,
) -> None:
    assert await client.set_operational_mode(9, 7) == {"ok": True}
    assert await client.set_battery_levels(BatteryLevelSettings(10, 20, 30, 40)) == {
        "ok": True
    }
    assert await client.set_grid_export_limit(5.5) == {"ok": True}
    assert await client.set_grid_import_limit(6.5, enabled=False) == {"ok": True}
    assert await client.set_grid_connection_limit(25.0) == {"ok": True}
    assert await client.set_battery_power_limit(
        max_charge_kw=None, max_discharge_kw=4.5
    ) == {"ok": True}
    assert await client.set_solar_power_limit(None) == {"ok": True}
    assert await client.set_backup_reserve(0) == {"ok": True}
    assert await client.set_backup_reserve(100) == {"ok": True}
    assert await client.set_battery_export_limitation(True) == {"ok": True}
    assert await client.set_dc_charge_mode(
        2, enable_from_pack=False, cutoff_soc_from_pack=80
    ) == {"ok": True}
    assert await client.set_dc_charge_setting(
        allowed_charge_power=11, vehicle_charging_cutoff_soc=90
    ) == {"ok": True}
    assert await client.set_dc_charge_enabled(True) == {"ok": True}
    assert await client.set_v2x_discharge_enabled(True) == {"ok": True}
    assert await client.start_v2x_discharge(duration_minutes=30, power_cap_kw=5) == {
        "ok": True
    }
    assert await client.stop_v2x_discharge() == {"ok": True}

    with pytest.raises(ValueError, match="power limit"):
        await client.set_solar_power_limit(-1)
    with pytest.raises(ValueError, match="backup reserve"):
        await client.set_backup_reserve(101)
    with pytest.raises(ValueError, match="direction"):
        await client.set_electricity_tax_and_fee(3, {})


@pytest.mark.asyncio
async def test_dc_response_normalization_and_history_query(
    client: SigenergyCloudClient,
) -> None:
    for response, expected in [
        (True, True),
        (None, None),
        ({"pluggedIn": 0}, False),
        ({"status": 1}, True),
        ("connected", True),
    ]:
        client._dc_data.return_value = response  # type: ignore[reportPrivateUsage]
        assert await client.dc_plug_status() is expected

    client._dc_data.return_value = {"records": []}  # type: ignore[reportPrivateUsage]
    result = await client.dc_session_records(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 2, 3),
        page=2,
        page_size=20,
    )
    assert result == {"records": []}
    client._dc_data.assert_awaited_with(  # type: ignore[reportPrivateUsage]
        "GET",
        "data-process/dcevse/record/page",
        None,
        params={
            "current": 2,
            "size": 20,
            "startTime": "20260102",
            "endTime": "20260203",
        },
    )
