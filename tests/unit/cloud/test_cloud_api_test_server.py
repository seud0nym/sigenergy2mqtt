"""Tests for the stateful cloud API facsimile used by integration tests."""

import asyncio

import pytest
from aiohttp.test_utils import TestClient, TestServer
from pymodbus.client.mixin import ModbusClientMixin

from sigenergy2mqtt.sensors.inverter.read_only import (
    InverterModel,
    InverterSerialNumber,
    RatedActivePower,
)
from tests.utils.modbus_sensors import (
    AC_CHARGER_SERIAL,
    DC_CHARGER_SERIAL,
    FIRMWARE_VERSION,
    HYBRID_INVERTER_MODEL,
    HYBRID_INVERTER_RATED_ACTIVE_POWER,
    HYBRID_INVERTER_SERIAL,
    PV_INVERTER_MODEL,
    PV_INVERTER_RATED_ACTIVE_POWER,
    PV_INVERTER_SERIAL,
)
from tests.utils.modbus_test_server import (
    CLOUD_TEST_GATEWAY_SERIAL,
    CloudApiTestServer,
    CustomDataBlock,
    LatencyBudget,
    simulate_internet_outage,
)


async def test_cloud_api_test_server_rejects_requests_during_internet_outage() -> None:
    api = CloudApiTestServer(None, None)
    api.internet_available = False
    api.internet_outage_status = 502

    async with TestClient(TestServer(api.app())) as client:
        response = await client.get("/device/owner/station/home")
        assert response.status == 502
        assert await response.json() == {
            "code": 502,
            "msg": "Cloud API unavailable due to simulated internet outage",
        }


async def test_simulate_internet_outage_cycles_and_restores_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = CloudApiTestServer(None, None)
    availability_during_sleeps: list[bool] = []

    async def record_sleep(_seconds: int) -> None:
        availability_during_sleeps.append(api.internet_available)

    monkeypatch.setattr(asyncio, "sleep", record_sleep)
    await simulate_internet_outage(
        api,
        wait_for_seconds=10,
        duration_seconds=20,
        repeated=False,
        status_code=502,
    )

    assert availability_during_sleeps == [True, False]
    assert api.internet_available is True
    assert api.internet_outage_status == 502


async def test_simulate_internet_outage_rejects_non_server_error() -> None:
    with pytest.raises(ValueError, match="between 500 and 599"):
        await simulate_internet_outage(
            CloudApiTestServer(None, None),
            wait_for_seconds=0,
            duration_seconds=0,
            repeated=False,
            status_code=404,
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

        response = await client.get(
            f"/device/gateway/{api.device_topology['stationId']}", headers=headers
        )
        gateway = (await response.json())["data"]
        assert gateway["snCode"] == CLOUD_TEST_GATEWAY_SERIAL
        assert gateway["deviceModel"] == "Sigen Gateway TP"
        grid_values = {
            item["paramKey"]: item["paramValue"]
            for item in gateway["gridSideInfoList"]
        }
        assert grid_values["Phase A Voltage"] == "233.29 V"
        assert grid_values["Phase B Voltage"] == "232.81 V"
        assert grid_values["Phase C Voltage"] == "233.04 V"
        assert grid_values["Phase A Current"] == "10.76 A"
        assert grid_values["Phase B Current"] == "10.31 A"
        assert grid_values["Phase C Current"] == "10.54 A"

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


def test_cloud_topology_matches_synthesized_modbus_identity_registers() -> None:
    api = CloudApiTestServer(None, None)
    topology_inverters = {
        node["snCode"]: node
        for root in api.device_topology["nodeList"]
        for node in [root, *root["nodeList"]]
        if node["deviceType"] == 3
    }

    for address, model, serial, rated_power in (
        (
            1,
            HYBRID_INVERTER_MODEL,
            HYBRID_INVERTER_SERIAL,
            HYBRID_INVERTER_RATED_ACTIVE_POWER,
        ),
        (
            3,
            PV_INVERTER_MODEL,
            PV_INVERTER_SERIAL,
            PV_INVERTER_RATED_ACTIVE_POWER,
        ),
    ):
        block = CustomDataBlock(address, None, LatencyBudget())
        modbus_values = {}
        for key, sensor in {
            "deviceCode": InverterModel(0, address),
            "snCode": InverterSerialNumber(0, address),
            "ratedActivePower": RatedActivePower(0, address),
        }.items():
            block.add_sensor(sensor)
            registers = [
                block._initial_registers[sensor.address + offset]
                for offset in range(sensor.count)
            ]
            raw_value = ModbusClientMixin.convert_from_registers(
                registers, sensor.data_type
            )
            modbus_values[key] = (
                raw_value / sensor.gain
                if isinstance(raw_value, (int, float)) and sensor.gain is not None
                else raw_value
            )
        cloud_node = topology_inverters[serial]
        assert {
            key: cloud_node[key]
            for key in ("deviceCode", "snCode", "ratedActivePower")
        } == modbus_values
