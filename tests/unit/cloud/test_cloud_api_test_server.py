"""Tests for the stateful cloud API facsimile used by integration tests."""

from aiohttp.test_utils import TestClient, TestServer

from tests.utils.modbus_test_server import CloudApiTestServer
from tests.utils.modbus_sensors import (
    AC_CHARGER_SERIAL,
    DC_CHARGER_SERIAL,
    FIRMWARE_VERSION,
    HYBRID_INVERTER_MODEL,
    HYBRID_INVERTER_SERIAL,
    PV_INVERTER_MODEL,
    PV_INVERTER_SERIAL,
)


async def test_cloud_api_test_server_exposes_all_limit_endpoints() -> None:
    api = CloudApiTestServer(None, None)
    api.access_token = "test-token"
    headers = {"Authorization": "Bearer test-token"}

    async with TestClient(TestServer(api.app())) as client:
        response = await client.get("/device/owner/station/home", headers=headers)
        assert (await response.json())["data"] == {
            "stationId": api.device_topology["stationId"],
            "acSnList": [AC_CHARGER_SERIAL],
            "dcSnList": [DC_CHARGER_SERIAL],
        }

        response = await client.get(
            "/device/energy-profile/grid/limitation/export/1", headers=headers
        )
        assert (await response.json())["data"]["maxLimitation"] == "10.000"

        response = await client.get(
            "/device/devicetreepanel/topology",
            headers=headers,
            params={"stationId": 1},
        )
        topology = (await response.json())["data"]
        assert topology["stationId"] == api.device_topology["stationId"]
        inverter_nodes = [
            node
            for root in topology["nodeList"]
            for node in [root, *root["nodeList"]]
            if node["deviceType"] == 3
        ]
        assert inverter_nodes == [
            {
                "stationId": api.device_topology["stationId"],
                "snCode": HYBRID_INVERTER_SERIAL,
                "deviceType": 3,
                "deviceStatus": 1,
                "communicateStatus": 2,
                "deviceCode": HYBRID_INVERTER_MODEL,
                "modelVersionStr": FIRMWARE_VERSION,
                "ratedActivePower": 12.0,
                "nodeList": [],
            },
            {
                "stationId": api.device_topology["stationId"],
                "snCode": PV_INVERTER_SERIAL,
                "deviceType": 3,
                "deviceStatus": 1,
                "communicateStatus": 2,
                "deviceCode": PV_INVERTER_MODEL,
                "modelVersionStr": FIRMWARE_VERSION,
                "ratedActivePower": 5.0,
                "nodeList": [],
            },
        ]

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
