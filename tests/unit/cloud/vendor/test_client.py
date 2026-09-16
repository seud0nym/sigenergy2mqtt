"""High-level client endpoint tests."""

from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import (
    InstantManualMode,
    SigenergyCloudClient,
    is_unlimited_power,
)


@pytest.mark.asyncio
async def test_prediction_data_uses_station_path() -> None:
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    try:
        with aioresponses() as mocked:
            mocked.post(
                "https://api-eu.sigencloud.com/auth/oauth/token",
                payload={
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/owner/station/home",
                payload={
                    "code": 0,
                    "data": {
                        "stationId": "12025061000219",
                        "acSnList": [],
                        "dcSnList": [],
                    },
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/prediction/predictData/get/predictData/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "nowTime": "2026-05-19 21:46",
                        "pvList": [
                            {
                                "time": "2026-05-20 12:00",
                                "timestamp": 1779192000,
                                "value": 10.5,
                            }
                        ],
                    },
                },
            )

            await client.connect()
            data = await client.prediction_data()

        assert data["nowTime"] == "2026-05-19 21:46"
        assert data["pvList"][0]["value"] == 10.5
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_instant_manual_control_endpoints() -> None:
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    try:
        with aioresponses() as mocked:
            mocked.post(
                "https://api-eu.sigencloud.com/auth/oauth/token",
                payload={
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/owner/station/home",
                payload={
                    "code": 0,
                    "data": {
                        "stationId": "12025061000219",
                        "acSnList": [],
                        "dcSnList": [],
                    },
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "enable": True,
                        "mode": "0",
                        "endTime": "1776471497",
                    },
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal/display/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "batteryPower": 6.7,
                        "batterySoc": 11.1,
                    },
                },
            )
            mocked.put(
                "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal",
                payload={"code": 0, "data": True},
            )

            await client.connect()
            control = await client.instant_manual_control()
            display = await client.instant_manual_display()
            result = await client.set_instant_manual_control(
                InstantManualMode.CHARGING,
                duration_minutes=120,
            )

        assert control.enabled is True
        assert control.mode is InstantManualMode.CHARGING
        assert control.end_time == 1776471497
        assert display["batteryPower"] == 6.7
        assert result["data"] is True

        put_request = mocked.requests[
            (
                "PUT",
                URL(
                    "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal"
                ),
            )
        ][0]
        assert put_request.kwargs["json"] == {
            "enable": True,
            "stationId": 12025061000219,
            "mode": "0",
            "duration": "120",
            "powerLimitation": "4294967.295",
        }
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("duration_minutes", [1, 1440])
async def test_instant_manual_control_accepts_full_custom_duration_range(
    duration_minutes: int,
) -> None:
    client = SigenergyCloudClient("user", "password")
    client.station_id = "12025061000219"
    client._envelope = AsyncMock(return_value={"data": True})
    try:
        await client.set_instant_manual_control(
            InstantManualMode.HOLD_BATTERY,
            duration_minutes=duration_minutes,
        )
        assert client._envelope.await_args.kwargs["json"]["duration"] == str(
            duration_minutes
        )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_disable_instant_manual_control() -> None:
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    try:
        with aioresponses() as mocked:
            mocked.post(
                "https://api-eu.sigencloud.com/auth/oauth/token",
                payload={
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/owner/station/home",
                payload={
                    "code": 0,
                    "data": {
                        "stationId": "12025061000219",
                        "acSnList": [],
                        "dcSnList": [],
                    },
                },
            )
            mocked.put(
                "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal",
                payload={"code": 0, "data": True},
            )

            await client.connect()
            result = await client.disable_instant_manual_control()

        assert result["data"] is True
        put_request = mocked.requests[
            (
                "PUT",
                URL(
                    "https://api-eu.sigencloud.com/device/energy-profile/instant/manunal"
                ),
            )
        ][0]
        assert put_request.kwargs["json"] == {
            "enable": False,
            "stationId": 12025061000219,
            "mode": "",
            "duration": "",
            "powerLimitation": "",
        }
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_electricity_tax_and_fee_endpoints() -> None:
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    try:
        with aioresponses() as mocked:
            mocked.post(
                "https://api-eu.sigencloud.com/auth/oauth/token",
                payload={
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/device/owner/station/home",
                payload={
                    "code": 0,
                    "data": {
                        "stationId": "12025061000219",
                        "acSnList": [],
                        "dcSnList": [],
                    },
                },
            )
            mocked.get(
                "https://api-eu.sigencloud.com/electricity-price/api/tax-and-fee/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "buyTaxAndFee": {
                            "taxSettings": {"fixedTaxRate": 25.0},
                            "additionalFeeList": [],
                        },
                        "sellTaxAndFee": {
                            "taxSettings": {"fixedTaxRate": 0.0},
                            "additionalFeeList": [],
                        },
                    },
                },
            )
            mocked.post(
                "https://api-eu.sigencloud.com/electricity-price/api/tax-and-fee",
                payload={"code": 0, "msg": "success", "data": True},
            )
            mocked.get(
                "https://api-eu.sigencloud.com/prediction/aipv/elecPrice/get/priceCost?stationId=12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "buyElecCost": 0.0,
                        "sellElecCost": 4.12,
                        "buyPriceCoefficient": 1.25,
                        "sellPriceCoefficient": 1.0,
                    },
                },
            )

            await client.connect()
            tax_fee = await client.electricity_tax_and_fee()
            assert tax_fee["buyTaxAndFee"]["taxSettings"]["fixedTaxRate"] == 25.0

            buy_payload = {
                "taxSettings": {
                    "enableNegativePriceTax": False,
                    "negativePriceTaxRate": 0.0,
                    "taxMode": 0,
                    "fixedTaxRate": 25.0,
                    "touSchedule": [],
                },
                "additionalFeeList": [
                    {
                        "feeName": "Energy tax",
                        "feeType": 0,
                        "applyTax": True,
                        "fixedValue": 36.0,
                        "touSchedule": [],
                    }
                ],
            }
            saved = await client.set_electricity_tax_and_fee(1, buy_payload)
            assert saved["data"] is True

            cost = await client.electricity_price_cost()
            assert cost["buyPriceCoefficient"] == 1.25
    finally:
        await session.close()


def _mock_login(mocked: aioresponses) -> None:
    mocked.post(
        "https://api-eu.sigencloud.com/auth/oauth/token",
        payload={
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        },
    )
    mocked.get(
        "https://api-eu.sigencloud.com/device/owner/station/home",
        payload={
            "code": 0,
            "data": {"stationId": "12025061000219", "acSnList": [], "dcSnList": []},
        },
    )


def _json_body(mocked: aioresponses, method: str, url: str) -> dict:
    (request,) = mocked.requests[(method, URL(url))]
    return request.kwargs["json"]


@pytest.mark.asyncio
async def test_grid_connection_limit_endpoints() -> None:
    """Max Grid Connection Current (A) maps to energy-profile/parallel/off/grid (HAR 2026-09-10)."""
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    try:
        with aioresponses() as mocked:
            _mock_login(mocked)
            mocked.get(
                "https://api-eu.sigencloud.com/device/energy-profile/parallel/off/grid/12025061000219",
                payload={
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "enable": True,
                        "currentLimitation": "13.7",
                        "ownerSetLimitation": "13.7",
                        "installerSetLimitation": "13.8",
                    },
                },
            )
            mocked.put(
                "https://api-eu.sigencloud.com/device/energy-profile/parallel/off/grid",
                payload={"code": 0, "msg": "success", "data": True},
            )

            await client.connect()
            limit = await client.grid_connection_limit()
            assert limit["installerSetLimitation"] == "13.8"

            saved = await client.set_grid_connection_limit(13.7)
            assert saved["data"] is True
            body = _json_body(
                mocked,
                "PUT",
                "https://api-eu.sigencloud.com/device/energy-profile/parallel/off/grid",
            )
            assert body == {
                "stationId": 12025061000219,
                "enable": True,
                "ownerSetLimitation": "13.7",
                "installerSetLimitation": None,
            }
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_power_limit_and_backup_reserve_endpoints() -> None:
    session = aiohttp.ClientSession()
    client = SigenergyCloudClient("user", "password", session=session)
    base = "https://api-eu.sigencloud.com/"
    try:
        with aioresponses() as mocked:
            _mock_login(mocked)
            mocked.get(
                base + "device/energy-profile/battery/limit/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "batteryMaxChargingPower": "4294967.295",
                        "batteryMaxDischargingPower": "5.000",
                    },
                },
            )
            mocked.put(
                base + "device/energy-profile/battery/limit",
                payload={"code": 0, "data": True},
            )
            mocked.get(
                base + "device/energy-profile/solar/limit/12025061000219",
                payload={"code": 0, "data": {"powerLimit": "4294967.295"}},
            )
            mocked.put(
                base + "device/energy-profile/solar/limit",
                payload={"code": 0, "data": True},
            )
            mocked.get(
                base + "device/setting/backup/reserve/12025061000219",
                payload={
                    "code": 0,
                    "data": {
                        "stationId": 12025061000219,
                        "backupReserve": 3,
                        "operationMode": 1,
                    },
                },
            )
            mocked.put(
                base + "device/setting/backup/reserve",
                payload={"code": 0, "data": True},
            )
            mocked.get(
                base + "device/gateway/12025061000219",
                payload={
                    "code": 0,
                    "data": {"snCode": "120B12C30057", "gridSideInfoList": []},
                },
            )
            mocked.get(
                base
                + "device/station/grid-connection-point/support-devices?stationId=12025061000219",
                payload={
                    "code": 0,
                    "data": [{"snCode": "120B12C30057", "deviceType": 8}],
                },
            )

            await client.connect()

            battery = await client.battery_power_limit()
            assert is_unlimited_power(battery["batteryMaxChargingPower"])
            assert not is_unlimited_power(battery["batteryMaxDischargingPower"])

            await client.set_battery_power_limit(max_charge_kw=None, max_discharge_kw=5)
            assert _json_body(
                mocked, "PUT", base + "device/energy-profile/battery/limit"
            ) == {
                "stationId": 12025061000219,
                "batteryMaxChargingPower": "4294967.295",
                "batteryMaxDischargingPower": "5.000",
            }

            assert (await client.solar_power_limit())["powerLimit"] == "4294967.295"
            await client.set_solar_power_limit(6.5)
            assert _json_body(
                mocked, "PUT", base + "device/energy-profile/solar/limit"
            ) == {
                "powerLimit": "6.500",
                "stationId": 12025061000219,
            }

            assert (await client.backup_reserve())["backupReserve"] == 3
            await client.set_backup_reserve(10)
            assert _json_body(
                mocked, "PUT", base + "device/setting/backup/reserve"
            ) == {
                "backupReserve": 10,
                "stationId": 12025061000219,
            }
            with pytest.raises(ValueError):
                await client.set_backup_reserve(101)

            assert (await client.gateway_info())["snCode"] == "120B12C30057"
            devices = await client.grid_connection_point_devices()
            assert devices[0]["deviceType"] == 8
    finally:
        await session.close()
