"""DC charger and Surplus PV endpoints added from mySigen web app captures (issue #355)."""

import copy
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import SigenergyCloudClient
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.errors import (
    SigenergyCloudAPIError,
)

UNLIMITED = "4294967.295"
EVERY_DAY = [{"whichDay": "1,2,3,4,5,6,7", "startTime": "00:00", "endTime": "24:00"}]


def _entry(loads_type: int, sg_device_type: int | None, priority: int, status: int) -> dict:
    return {
        "loadsType": loads_type,
        "sgDeviceType": sg_device_type,
        "smartLoadsPath": None,
        "smartLoadsName": "",
        "smartLoadsKey": None,
        "smartLoadsStatus": None,
        "priority": priority,
        "status": status,
        "isGroup": False,
        "priorityGroupList": [],
    }


# GET device/energy-profile/setting/{stationId}, as captured with the DC charger first
CAPTURED_PROFILE = {
    "profileId": None,
    "name": "remote ems",
    "note": "default",
    "batteryGlobalActive": False,
    "batteryAutomationGroupVOList": [
        {
            "name": "Battery Automation",
            "activeStatus": 1,
            "maxChargePower": UNLIMITED,
            "maxDischargePower": UNLIMITED,
            "g2BMaxChargePower": UNLIMITED,
            "b2GMaxDischargePower": UNLIMITED,
            "chargeCutOffSoc": "100.0",
            "dischargeCutOffSoc": "0.0",
            "priorityList": ["pv", "grid"],
            "winMode": 3,
            "itemVOList": EVERY_DAY,
        }
    ],
    "gridGlobalActive": False,
    "gridAutomationGroupVOList": [
        {
            "name": "Grid Automation",
            "activeStatus": 1,
            "maxBuyPower": UNLIMITED,
            "maxSellPower": UNLIMITED,
            "priorityList": ["pv", "battery"],
            "winMode": 0,
            "itemVOList": EVERY_DAY,
        }
    ],
    "activeStatus": 0,
    "pvPriority": [_entry(4, None, 5, 2), _entry(3, None, 4, 2), _entry(1, 5, 2, 0), _entry(1, 4, 1, 0)],
    "batteryDischargePriority": ["grid", "pv"],
    "exportLimitation": True,
    "importLimitation": False,
    "maxExportLimitation": "1.500",
    "maxImportLimitation": "",
    "powerLimit": UNLIMITED,
    "chargeSOC": "100.0",
    "dischargeSOC": "0.0",
    "backupSOC": "0.0",
    "batteryMaxChargingPower": UNLIMITED,
    "batteryMaxDischargingPower": UNLIMITED,
    "peakShavingVO": {"controlMode": 0, "shavingSOC": 0.0, "settingList": []},
    "packPreheatingInfoVO": {
        "packPreheatingVOList": [],
        "packPreheatingSwitch": 0,
        "preheatingMode": 1,
        "preHeatingEnablesSwitch": None,
        "isIndustry": False,
        "isAutoModeValid": False,
    },
    "isIndustry": False,
}

# PUT device/energy-profile/setting, as captured when the app set "house" (battery) first
CAPTURED_BATTERY_FIRST_PUT = {
    "name": "remote ems",
    "profileId": None,
    "note": "default",
    "activeStatus": 0,
    "pvPriority": [
        {"loadsType": 1, "sgDeviceType": 4, "smartLoadsPath": None, "priority": 2},
        {"loadsType": 1, "sgDeviceType": 5, "smartLoadsPath": None, "priority": 1},
    ],
    "batteryGlobalActive": False,
    "batteryAutomationGroupVOList": CAPTURED_PROFILE["batteryAutomationGroupVOList"],
    "gridGlobalActive": False,
    "gridAutomationGroupVOList": CAPTURED_PROFILE["gridAutomationGroupVOList"],
    "stationId": 123,
    "maxExportLimitation": "1.500",
    "exportLimitation": True,
    "maxImportLimitation": "",
    "importLimitation": False,
    "powerLimit": UNLIMITED,
    "chargeSOC": "100.0",
    "dischargeSOC": "0.0",
    "backupSOC": "0.0",
    "batteryMaxChargingPower": UNLIMITED,
    "batteryMaxDischargingPower": UNLIMITED,
    "batteryDischargePriority": ["grid", "pv"],
    "peakShavingVO": {"controlMode": 0, "shavingSOC": 0, "settingList": []},
    "packPreheatingInfoVO": {
        "packPreheatingVOList": [],
        "packPreheatingSwitch": 0,
        "preheatingMode": None,
        "preHeatingEnablesSwitch": None,
        "isIndustry": False,
        "isAutoModeValid": False,
    },
}


@pytest.fixture
def client() -> SigenergyCloudClient:
    instance = SigenergyCloudClient("user", "password")
    instance.station_id = "123"
    instance.dc_sns = ("DC1",)
    instance._data = AsyncMock(return_value={"value": 1})  # type: ignore[method-assign]
    instance._station_data = AsyncMock(return_value=copy.deepcopy(CAPTURED_PROFILE))  # type: ignore[method-assign]
    instance._dc_data = AsyncMock(return_value={"value": 1})  # type: ignore[method-assign]
    instance._envelope = AsyncMock(return_value={"code": 0, "data": True})  # type: ignore[method-assign]
    return instance


async def test_charge_mode_capability_reads(client: SigenergyCloudClient) -> None:
    client._dc_data.return_value = True  # type: ignore[attr-defined]
    assert await client.dc_charge_mode_supported() is True
    client._dc_data.assert_awaited_with("GET", "device/charge/mode/support", None, params={"deviceType": 5})  # type: ignore[attr-defined]

    client._dc_data.return_value = ["0", "1", "x", None, "3"]  # type: ignore[attr-defined]
    assert await client.dc_supported_charge_modes("DC1") == [0, 1, 3]
    client._dc_data.assert_awaited_with("GET", "device/charge/mode/support/mode", "DC1", params={"deviceType": 5})  # type: ignore[attr-defined]

    client._dc_data.return_value = None  # type: ignore[attr-defined]
    assert await client.dc_supported_charge_modes() == []


async def test_other_dc_reads(client: SigenergyCloudClient) -> None:
    client._dc_data.return_value = {"chargeMode": 2, "maxPowerFromPack": -0.001}  # type: ignore[attr-defined]
    assert (await client.dc_surplus_pv_charge_mode())["chargeMode"] == 2
    client._dc_data.assert_awaited_with("GET", "device/dcevse/charge/mode", None)  # type: ignore[attr-defined]

    client._dc_data.return_value = [{"brand": "MG"}, "junk"]  # type: ignore[attr-defined]
    assert await client.dc_vehicles() == [{"brand": "MG"}]
    client._dc_data.assert_awaited_with("GET", "device/user-car-info/select", None)  # type: ignore[attr-defined]
    client._dc_data.return_value = None  # type: ignore[attr-defined]
    assert await client.dc_vehicles() == []

    client._dc_data.return_value = 0  # type: ignore[attr-defined]
    assert await client.dc_status() == 0


def test_surplus_pv_priority_order() -> None:
    assert SigenergyCloudClient.surplus_pv_priority_order(CAPTURED_PROFILE) == [5, 4]
    battery_first = copy.deepcopy(CAPTURED_PROFILE)
    battery_first["pvPriority"][2]["priority"], battery_first["pvPriority"][3]["priority"] = 1, 2
    assert SigenergyCloudClient.surplus_pv_priority_order(battery_first) == [4, 5]
    assert SigenergyCloudClient.surplus_pv_priority_order({"pvPriority": [{"loadsType": 1}, "x"]}) == []
    assert SigenergyCloudClient.surplus_pv_priority_order({}) == []


async def test_set_surplus_pv_priority_sends_the_captured_request(client: SigenergyCloudClient) -> None:
    await client.set_surplus_pv_priority(4)

    client._station_data.assert_awaited_once_with("GET", "device/energy-profile/setting/{station_id}")  # type: ignore[attr-defined]
    client._envelope.assert_awaited_once_with("PUT", "device/energy-profile/setting", json=CAPTURED_BATTERY_FIRST_PUT)  # type: ignore[attr-defined]


async def test_set_surplus_pv_priority_rejects_unknown_device_and_bad_profile(client: SigenergyCloudClient) -> None:
    with pytest.raises(ValueError, match="sgDeviceType 6"):
        await client.set_surplus_pv_priority(6)
    client._station_data.return_value = None  # type: ignore[attr-defined]
    with pytest.raises(SigenergyCloudAPIError):
        await client.set_surplus_pv_priority(5)
    client._envelope.assert_not_awaited()  # type: ignore[attr-defined]
