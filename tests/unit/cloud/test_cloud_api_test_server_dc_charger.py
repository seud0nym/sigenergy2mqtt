"""DC charger endpoints of the cloud API facsimile, exercised by the real adapter."""

import copy
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from aiohttp.test_utils import TestClient, TestServer

from sigenergy2mqtt.cloud.exceptions import CloudControlRejectedError
from sigenergy2mqtt.cloud.mysigen_adapter import MySigenCloudAdapter
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.cloud import (
    CloudDcCharger,
    CloudDiscovery,
    DcChargerDiscovery,
    discover_dc_chargers,
)
from sigenergy2mqtt.sensors.cloud.dc_charger import (
    DcChargerBatteryBoost,
    DcChargerBatteryBoostCutoffSoc,
    DcChargerChargingMode,
    DcChargerLifetimeChargedEnergy,
    DcChargerOcppLinkStatus,
    DcChargerPrimaryVehicle,
    DcChargerStatusCode,
    DcChargerSurplusPvPriority,
    DcChargerV2xDischargeEnabled,
)
from tests.utils.modbus_sensors import DC_CHARGER_SERIAL
from tests.utils.modbus_test_server import CLOUD_TEST_STATION_ID, CloudApiTestServer

STATION = str(CLOUD_TEST_STATION_ID)
HEADERS = {"Authorization": "Bearer test-token"}


def _api() -> CloudApiTestServer:
    api = CloudApiTestServer("cloud-user", "cloud-password")
    api.access_token = "test-token"
    return api


@asynccontextmanager
async def _adapter(api: CloudApiTestServer) -> AsyncIterator[MySigenCloudAdapter]:
    """Run the real adapter (and vendored client) against the facsimile."""
    async with TestServer(api.app()) as server:
        config = Config()
        config.cloud.testing_url = str(server.make_url("/"))
        with _swap_active_config(config):
            adapter = MySigenCloudAdapter("cloud-user", "cloud-password", "testing")
            try:
                yield adapter
            finally:
                await adapter.close()


def _pv_order(api: CloudApiTestServer) -> list[tuple[int, int | None, int]]:
    return [(entry["loadsType"], entry["sgDeviceType"], entry["priority"]) for entry in api.energy_profile_setting["pvPriority"]]


async def test_dc_charger_reads_match_captured_responses() -> None:
    api = _api()
    async with _adapter(api) as adapter:
        assert await adapter.dc_charge_mode_supported(DC_CHARGER_SERIAL) is True
        assert await adapter.dc_supported_charge_modes(DC_CHARGER_SERIAL) == [0, 1, 3]
        assert await adapter.dc_charge_mode_soc_range() == {"socUpperLimit": 100.0, "socLowerLimit": 0.0}
        assert (await adapter.dc_charge_mode(DC_CHARGER_SERIAL))["chargeMode"] == 1
        assert await adapter.dc_status(DC_CHARGER_SERIAL) == 0
        assert (await adapter.dc_energy_totals(DC_CHARGER_SERIAL))["lifetimeEnergy"] == 781.68
        assert (await adapter.dc_ocpp_status(DC_CHARGER_SERIAL))["ocppLinkStatus"] == 0
        assert (await adapter.v2x_discharge_settings(DC_CHARGER_SERIAL))["dischargeEnable"] == 0
        assert [vehicle["model"] for vehicle in await adapter.dc_vehicles(DC_CHARGER_SERIAL)] == ["MG4", "7x"]
        assert (await adapter.energy_profile_setting())["name"] == "remote ems"


async def test_dc_charge_mode_write_round_trips_through_adapter() -> None:
    api = _api()
    async with _adapter(api) as adapter:
        await adapter.set_dc_charge_mode(1, dc_sn=DC_CHARGER_SERIAL, enable_from_pack=True, cutoff_soc_from_pack=5)
        assert api.dc_charge_mode["enableFromPack"] is True
        assert api.dc_charge_mode["cutoffSocFromPack"] == 5.0
        # Fields the app does not send are unchanged
        assert api.dc_charge_mode["allowsDischargePower"] == 12.5

        with pytest.raises(CloudControlRejectedError):
            await adapter.set_dc_charge_mode(2, dc_sn=DC_CHARGER_SERIAL, enable_from_pack=True, cutoff_soc_from_pack=5)
        with pytest.raises(CloudControlRejectedError):
            await adapter.set_dc_charge_mode(1, dc_sn=DC_CHARGER_SERIAL, enable_from_pack=True, cutoff_soc_from_pack=101)
        with pytest.raises(CloudControlRejectedError):
            await adapter.set_dc_charge_mode(1, dc_sn="OTHER", enable_from_pack=True, cutoff_soc_from_pack=5)
        assert api.dc_charge_mode["chargeMode"] == 1


async def test_surplus_pv_priority_write_matches_recorded_behaviour() -> None:
    api = _api()
    before = copy.deepcopy(api.energy_profile_setting)
    async with _adapter(api) as adapter:
        await adapter.connect()
        assert (await adapter._client.dc_surplus_pv_charge_mode(DC_CHARGER_SERIAL))["chargeMode"] == 1

        await adapter.set_surplus_pv_priority(4)
        # Only the Sigenergy devices are reordered; the other loads are kept
        assert _pv_order(api) == [(4, None, 5), (3, None, 4), (1, 4, 2), (1, 5, 1)]
        assert (await adapter._client.dc_surplus_pv_charge_mode(DC_CHARGER_SERIAL))["chargeMode"] == 2
        # Everything else in the profile survives the whole-document write
        after = copy.deepcopy(api.energy_profile_setting)
        after.pop("pvPriority")
        expected = copy.deepcopy(before)
        expected.pop("pvPriority")
        assert after == expected

        await adapter.set_surplus_pv_priority(5)
        assert _pv_order(api) == [(4, None, 5), (3, None, 4), (1, 5, 2), (1, 4, 1)]

        with pytest.raises(CloudControlRejectedError):
            await adapter.set_surplus_pv_priority(6)


async def test_dc_charger_endpoints_reject_unknown_charger_station_and_token() -> None:
    api = _api()
    async with TestClient(TestServer(api.app())) as client:
        for path in ("/device/charge/mode/dc", "/device/dcevse/status", "/data-process/dcevse/energy", "/device/user-car-info/select"):
            response = await client.get(path, params={"stationId": STATION, "snCode": "OTHER"}, headers=HEADERS)
            assert response.status == 400, path
            response = await client.get(path, params={"stationId": "1", "snCode": DC_CHARGER_SERIAL}, headers=HEADERS)
            assert response.status == 400, path
            response = await client.get(path, params={"stationId": STATION, "snCode": DC_CHARGER_SERIAL})
            assert response.status == 401, path

        response = await client.get("/device/charge/mode/support", params={"stationId": STATION, "snCode": DC_CHARGER_SERIAL, "deviceType": "6"}, headers=HEADERS)
        assert response.status == 400
        response = await client.get("/device/energy-profile/setting/1", headers=HEADERS)
        assert response.status == 400

        body = {"stationId": STATION, "pvPriority": [{"loadsType": 1, "sgDeviceType": 9, "smartLoadsPath": None, "priority": 3}]}
        response = await client.put("/device/energy-profile/setting", json=body, headers=HEADERS)
        assert response.status == 400


async def test_dc_charger_state_is_editable_through_dashboard() -> None:
    api = _api()
    async with TestClient(TestServer(api.app())) as client:
        state = await (await client.get("/cloud-api-test/state")).json()
        assert state["dc_supported_charge_modes"] == ["0", "1", "3"]
        assert state["energy_profile_setting"]["pvPriority"][2]["sgDeviceType"] == 5

        response = await client.put("/cloud-api-test/state/dc_status", json={"value": 2})
        assert response.status == 200
        response = await client.put("/cloud-api-test/state/dc_vehicles", json={"value": {}})
        assert response.status == 400

        response = await client.get("/device/dcevse/status", params={"stationId": STATION, "snCode": DC_CHARGER_SERIAL}, headers=HEADERS)
        assert (await response.json())["data"] == 2


async def test_dc_charger_device_sensors_read_and_write_against_server() -> None:
    api = _api()
    async with _adapter(api) as adapter:
        discovery = await discover_dc_chargers(adapter, CloudDiscovery(device_list=await adapter.device_list()))
        assert discovery.dc_chargers == (DcChargerDiscovery(DC_CHARGER_SERIAL, (0, 1, 3), (0.0, 100.0), (5, 4)),)

        device = CloudDcCharger(0, adapter.station_id, discovery.dc_chargers[0])

        def sensor(sensor_type):
            found = device.get_sensor(sensor_type)
            assert found is not None
            return found

        assert await sensor(DcChargerChargingMode)._read_cloud_state(adapter) == 1
        assert await sensor(DcChargerBatteryBoost)._read_cloud_state(adapter) == 0
        assert await sensor(DcChargerBatteryBoostCutoffSoc)._read_cloud_state(adapter) == 5.0
        assert await sensor(DcChargerSurplusPvPriority)._read_cloud_state(adapter) == 0
        assert await sensor(DcChargerStatusCode)._read_cloud_state(adapter) == 0
        assert await sensor(DcChargerLifetimeChargedEnergy)._read_cloud_state(adapter) == 781.68
        assert await sensor(DcChargerOcppLinkStatus)._read_cloud_state(adapter) == 0
        assert await sensor(DcChargerV2xDischargeEnabled)._read_cloud_state(adapter) == "Off"
        assert await sensor(DcChargerPrimaryVehicle)._read_cloud_state(adapter) == "MG MG4 (2026)"

        assert await sensor(DcChargerBatteryBoost)._write_cloud_value(adapter, 1)
        assert await sensor(DcChargerBatteryBoostCutoffSoc)._write_cloud_value(adapter, 20)
        assert await sensor(DcChargerChargingMode)._write_cloud_value(adapter, 2)
        assert api.dc_charge_mode["chargeMode"] == 3
        assert api.dc_charge_mode["enableFromPack"] is True
        assert api.dc_charge_mode["cutoffSocFromPack"] == 20.0

        assert await sensor(DcChargerSurplusPvPriority)._write_cloud_value(adapter, 1)
        assert _pv_order(api)[2:] == [(1, 4, 2), (1, 5, 1)]
