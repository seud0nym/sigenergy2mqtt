"""Tests for dynamically discovered cloud gateway sensors."""

from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.devices.cloud import SigenergyCloudControl, SigenergyGateway
from sigenergy2mqtt.sensors.base import DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.read_only import (
    GatewayCommunicationStatus,
    GatewayGridCurrent,
    GatewayGridFrequency,
    GatewayGridPower,
    GatewayGridReactivePower,
    GatewayGridText,
    GatewayGridVoltage,
)
from tests.unit.sensors.test_cloud_instant_control import FakeCloudControlPort


GATEWAY_INFO = {
    "deviceModel": "Sigen Gateway SP AU",
    "snCode": "GW-SN",
    "softVersion": "V100R001C00",
    "communicationStatus": 2,
    "gridSideInfoList": [
        {"paramKey": "Phase A Voltage", "paramValue": "233.29 V"},
        {"paramKey": "Phase A Current", "paramValue": "10.76 A"},
        {"paramKey": "Voltage Frequency", "paramValue": "49.99 Hz"},
        {"paramKey": "Total Active Power", "paramValue": "2.444 kW"},
        {"paramKey": "Total Reactive Power", "paramValue": "-0.406 kVar"},
        {"paramKey": "Grid Side Contactor Status", "paramValue": "Close"},
        # Duplicate keys cannot provide stable distinct entity IDs and are ignored.
        {"paramKey": "Phase A Voltage", "paramValue": "999.00 V"},
    ],
}


def test_cloud_control_adds_gateway_child_with_dynamic_sensors() -> None:
    device = SigenergyCloudControl(0, FakeCloudControlPort(), GATEWAY_INFO)

    assert len(device.children) == 1
    gateway = device.children[0]
    assert isinstance(gateway, SigenergyGateway)
    assert gateway["model"] == "Sigen Gateway SP AU"
    assert gateway["sn"] == "GW-SN"
    assert gateway["hw"] == "V100R001C00"
    assert gateway.via_device == device.unique_id
    assert [type(sensor) for sensor in gateway.sensors.values()] == [
        GatewayCommunicationStatus,
        GatewayGridVoltage,
        GatewayGridCurrent,
        GatewayGridFrequency,
        GatewayGridPower,
        GatewayGridReactivePower,
        GatewayGridText,
    ]
    reactive = next(
        sensor
        for sensor in gateway.sensors.values()
        if isinstance(sensor, GatewayGridReactivePower)
    )
    assert reactive[DiscoveryKeys.UNIT_OF_MEASUREMENT] == "kvar"


@pytest.mark.asyncio
async def test_gateway_sensors_share_one_endpoint_read_per_refresh() -> None:
    port = FakeCloudControlPort()
    port.gateway_info = AsyncMock(return_value=GATEWAY_INFO)
    gateway = SigenergyGateway(
        0,
        port.station_id,
        model="model",
        sn="serial",
        hw="firmware",
        grid_side_info=GATEWAY_INFO["gridSideInfoList"],
    )
    sensors = list(gateway.sensors.values())
    coordinator = sensors[0]._polling_coordinator  # type: ignore[attr-defined]

    coordinator.begin_refresh()
    values = [await sensor._read_cloud_state(port) for sensor in sensors]  # type: ignore[attr-defined]

    assert values == ["Online", 233.29, 10.76, 49.99, 2.444, -0.406, "Close"]
    port.gateway_info.assert_awaited_once_with()
