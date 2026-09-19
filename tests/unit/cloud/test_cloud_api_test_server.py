"""Tests for the stateful cloud API facsimile used by integration tests."""

from aiohttp.test_utils import TestClient, TestServer

from tests.utils.modbus_test_server import CloudApiTestServer


async def test_cloud_api_test_server_exposes_all_limit_endpoints() -> None:
    api = CloudApiTestServer(None, None)
    api.access_token = "test-token"
    headers = {"Authorization": "Bearer test-token"}

    async with TestClient(TestServer(api.app())) as client:
        response = await client.get(
            "/device/energy-profile/grid/limitation/export/1", headers=headers
        )
        assert (await response.json())["data"]["maxLimitation"] == "10.000"

        response = await client.put(
            "/device/energy-profile/grid/limitation/export",
            headers=headers,
            json={
                "stationId": 1,
                "enable": True,
                "maxLimitationOwner": "7.500",
                "maxLimitationInstaller": None,
            },
        )
        assert response.status == 200
        assert api.grid_export_limit["maxLimitation"] == "7.500"

        response = await client.put(
            "/device/energy-profile/parallel/off/grid",
            headers=headers,
            json={
                "stationId": 1,
                "enable": True,
                "ownerSetLimitation": "40.0",
                "installerSetLimitation": None,
            },
        )
        assert response.status == 200
        assert api.grid_connection_limit["currentLimitation"] == "40.0"

        response = await client.put(
            "/device/energy-profile/battery/limit",
            headers=headers,
            json={
                "stationId": 1,
                "batteryMaxChargingPower": "4.000",
                "batteryMaxDischargingPower": "6.000",
            },
        )
        assert response.status == 200
        assert api.battery_power_limit["batteryMaxChargingPower"] == "4.000"

        response = await client.put(
            "/device/energy-profile/solar/limit",
            headers=headers,
            json={"stationId": 1, "powerLimit": "8.000"},
        )
        assert response.status == 200
        assert api.solar_power_limit["powerLimit"] == "8.000"

        response = await client.put(
            "/device/energy-profile/battery/export/limitation",
            headers=headers,
            json={
                "stationId": 1,
                "installerSetEnable": None,
                "ownerSetEnable": False,
            },
        )
        assert response.status == 200
        assert api.battery_export_limitation == {
            "currentEnable": False,
            "ownerSetEnable": False,
            "installerSetEnable": None,
            "nearModify": None,
        }
