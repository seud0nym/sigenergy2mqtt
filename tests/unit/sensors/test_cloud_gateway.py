"""Tests for dynamically discovered cloud gateway sensors."""

from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.common import DeviceClass, ScanIntervalDefault
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.cloud import (
    CloudControl,
    CloudDiscovery,
    Gateway,
    discover_cloud,
)
from sigenergy2mqtt.devices.cloud.sigen_device import CloudBattery, CloudInverter
from sigenergy2mqtt.sensors.base import DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.device_info import (
    DeviceInfoSensor,
    DeviceInfoSnapshot,
)
from sigenergy2mqtt.sensors.cloud.read_only import (
    GatewayCommunicationStatus,
    GatewayFirmwareVersion,
    GatewayGridCurrent,
    GatewayGridFrequency,
    GatewayGridPower,
    GatewayGridReactivePower,
    GatewayGridText,
    GatewayGridVoltage,
    GatewayModel,
    GatewaySerialNumber,
)
from tests.unit.sensors.test_cloud_sensors import FakeCloudControlPort

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


@pytest.fixture(autouse=True)
def enable_cloud_inverter_discovery():
    previous = active_config.cloud.discover_inverters
    active_config.cloud.discover_inverters = True
    yield
    active_config.cloud.discover_inverters = previous


@pytest.mark.parametrize(
    ("api_unit", "ha_unit"),
    [("℃", "°C"), ("°C", "°C"), ("℉", "°F"), ("°F", "°F")],
)
def test_device_temperature_sensor_supports_celsius_and_fahrenheit_units(api_unit: str, ha_unit: str) -> None:
    sensor = DeviceInfoSensor(
        0,
        FakeCloudControlPort.station_id,
        "INV-1",
        "Internal Temperature",
        api_unit,
        DeviceInfoSnapshot(3, "INV-1", False),
        static=False,
    )

    assert sensor[DiscoveryKeys.UNIT_OF_MEASUREMENT] == ha_unit
    assert sensor[DiscoveryKeys.DEVICE_CLASS] == DeviceClass.TEMPERATURE


def test_cloud_control_adds_each_inverter_and_battery_as_child() -> None:
    devices = [
        {"deviceType": "Inverter", "serialNumber": "INV-1", "attrMap": {}},
        {
            "deviceType": "Battery",
            "serialNumber": "BAT-1",
            "attrMap": {"batPosition": 2},
        },
    ]
    dynamic = {
        "realTimeInfo": [
            {
                "paramKey": "Phase B Voltage",
                "paramValueText": "231.2",
                "paramValueUnit": "V",
            }
        ]
    }
    static = {
        "paramInfoVOList": [
            {
                "paramKey": "Device Model",
                "paramValue": "SigenStor EC 10.0 TP",
                "paramValueText": "model",
                "paramValueUnit": "",
            }
        ]
    }
    discovery = CloudDiscovery(
        device_list=devices,
        device_info={"INV-1": (dynamic, static), "BAT-1": (dynamic, static)},
    )

    control = CloudControl(0, FakeCloudControlPort(), discovery)

    assert [type(child) for child in control.children] == [CloudInverter, CloudBattery]
    assert control.children[0]["name"] == "SigenStor EC 10.0 TP INV-1"
    assert control.children[0]["sn"] == "INV-1"
    assert control.children[1]["name"] == "SigenStor EC 10.0 TP 2"
    assert control.children[1].unique_id == "sigen_0_cloud_station-123_battery_BAT-1"
    static_sensor = list(control.children[0].sensors.values())[1]
    assert static_sensor[DiscoveryKeys.ENTITY_CATEGORY] == "diagnostic"
    assert static_sensor.scan_interval == ScanIntervalDefault.LOW


def test_cloud_device_names_fall_back_when_device_model_is_missing() -> None:
    devices = [
        {"deviceType": "Inverter", "serialNumber": "INV-1", "attrMap": {}},
        {
            "deviceType": "Battery",
            "serialNumber": "BAT-1",
            "attrMap": {"batPosition": 2},
        },
    ]
    dynamic = {"realTimeInfo": [{"paramKey": "Battery SOC", "paramValueText": "50", "paramValueUnit": "%"}]}
    discovery = CloudDiscovery(
        device_list=devices,
        device_info={"INV-1": (dynamic, {}), "BAT-1": (dynamic, {})},
    )

    control = CloudControl(0, FakeCloudControlPort(), discovery)

    assert [child["name"] for child in control.children] == [
        "SigenStor Inverter INV-1",
        "SigenStor Battery 2",
    ]


def test_batteries_without_positions_use_serials_for_distinct_identities() -> None:
    devices = [{"deviceType": "Battery", "serialNumber": sn, "attrMap": {}} for sn in ("BAT-1", "BAT-2")]
    discovery = CloudDiscovery(
        device_list=devices,
        device_info={
            sn: (
                {
                    "realTimeInfo": [
                        {
                            "paramKey": "Battery SOC",
                            "paramValueText": "50",
                            "paramValueUnit": "%",
                        }
                    ]
                },
                {},
            )
            for sn in ("BAT-1", "BAT-2")
        },
    )

    control = CloudControl(0, FakeCloudControlPort(), discovery)

    assert [child["name"] for child in control.children] == [
        "SigenStor Battery BAT-1",
        "SigenStor Battery BAT-2",
    ]
    assert [child.unique_id for child in control.children] == [
        "sigen_0_cloud_station-123_battery_BAT-1",
        "sigen_0_cloud_station-123_battery_BAT-2",
    ]


def test_device_parameters_are_deduplicated_by_normalized_suffix() -> None:
    dynamic = {
        "realTimeInfo": [
            {"paramKey": "PV Power", "paramValueText": "1", "paramValueUnit": "kW"},
            {"paramKey": "pv-power", "paramValueText": "2", "paramValueUnit": "kW"},
        ]
    }
    discovery = CloudDiscovery(
        device_list=[{"deviceType": "Inverter", "serialNumber": "INV-1", "attrMap": {}}],
        device_info={"INV-1": (dynamic, {})},
    )

    control = CloudControl(0, FakeCloudControlPort(), discovery)

    assert len(control.children[0].sensors) == 1


@pytest.mark.asyncio
async def test_device_snapshot_retains_failure_until_next_refresh() -> None:
    port = FakeCloudControlPort()
    port.device_dynamic_info = AsyncMock(side_effect=CloudControlUnavailableError("offline"))
    snapshot = DeviceInfoSnapshot(3, "INV-1", False)

    with pytest.raises(CloudControlUnavailableError):
        await snapshot.read(port)
    with pytest.raises(CloudControlUnavailableError):
        await snapshot.read(port)

    port.device_dynamic_info.assert_awaited_once_with(3, "INV-1")


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf"])
@pytest.mark.asyncio
async def test_device_numeric_sensor_rejects_non_finite_values(value: str) -> None:
    port = FakeCloudControlPort()
    port.device_dynamic_info = AsyncMock(return_value={"realTimeInfo": [{"paramKey": "Active Power", "paramValueText": value}]})
    sensor = DeviceInfoSensor(
        0,
        port.station_id,
        "INV-1",
        "Active Power",
        "kW",
        DeviceInfoSnapshot(3, "INV-1", False),
        static=False,
    )

    assert await sensor._read_cloud_state(port) is None


@pytest.mark.asyncio
async def test_discovery_keeps_dynamic_info_when_static_info_fails() -> None:
    port = FakeCloudControlPort()
    port.gateway_info = AsyncMock(return_value={})
    port.device_list = AsyncMock(return_value=[{"deviceType": "Inverter", "serialNumber": "INV-1", "attrMap": {}}])
    dynamic = {"realTimeInfo": [{"paramKey": "PV Power"}]}
    port.device_dynamic_info = AsyncMock(return_value=dynamic)
    port.device_static_info = AsyncMock(side_effect=CloudControlUnavailableError("offline"))

    discovery = await discover_cloud(port)

    assert discovery is not None
    assert discovery.device_info == {"INV-1": (dynamic, {})}


def test_cloud_control_adds_gateway_child_with_dynamic_sensors() -> None:
    device = CloudControl(
        0,
        FakeCloudControlPort(),
        CloudDiscovery(device_list=[], gateway_info=GATEWAY_INFO),
    )

    assert len(device.children) == 1
    gateway = device.children[0]
    assert isinstance(gateway, Gateway)
    assert gateway["model_id"] == "Sigen Gateway SP AU"
    assert gateway["sn"] == "GW-SN"
    assert gateway["sw"] == "V100R001C00"
    assert gateway.via_device == device.unique_id
    assert [type(sensor) for sensor in gateway.sensors.values()] == [
        GatewayCommunicationStatus,
        GatewayFirmwareVersion,
        GatewayModel,
        GatewaySerialNumber,
        GatewayGridVoltage,
        GatewayGridCurrent,
        GatewayGridFrequency,
        GatewayGridPower,
        GatewayGridReactivePower,
        GatewayGridText,
    ]
    reactive = next(sensor for sensor in gateway.sensors.values() if isinstance(sensor, GatewayGridReactivePower))
    assert reactive[DiscoveryKeys.UNIT_OF_MEASUREMENT] == "kvar"


@pytest.mark.asyncio
async def test_gateway_sensors_share_one_endpoint_read_per_refresh() -> None:
    port = FakeCloudControlPort()
    port.gateway_info = AsyncMock(return_value=GATEWAY_INFO)
    gateway = Gateway(
        plant_index=0,
        station_id=port.station_id,
        model="model",
        sn="serial",
        sw="firmware",
        grid_side_info=GATEWAY_INFO["gridSideInfoList"],
    )
    sensors = list(gateway.sensors.values())
    coordinator = sensors[0]._polling_coordinator  # type: ignore[attr-defined]

    coordinator.begin_refresh()
    values = [await sensor._read_cloud_state(port) for sensor in sensors]  # type: ignore[attr-defined]

    assert values == [
        "Online",
        "V100R001C00",
        "Sigen Gateway SP AU",
        "GW-SN",
        233.29,
        10.76,
        49.99,
        2.444,
        -0.406,
        "Close",
    ]
    port.gateway_info.assert_awaited_once_with()


@pytest.mark.parametrize("param_value", ["233.29 kV", "NaN V", "inf V", "-inf V"])
@pytest.mark.asyncio
async def test_gateway_numeric_sensor_rejects_changed_units_and_non_finite_values(
    param_value: str,
) -> None:
    port = FakeCloudControlPort()
    payload = {
        **GATEWAY_INFO,
        "gridSideInfoList": [{"paramKey": "Phase A Voltage", "paramValue": param_value}],
    }
    port.gateway_info = AsyncMock(return_value=payload)
    gateway = Gateway(
        plant_index=0,
        station_id=port.station_id,
        model="model",
        sn="serial",
        sw="firmware",
        grid_side_info=[{"paramKey": "Phase A Voltage", "paramValue": "233.29 V"}],
    )
    sensor = next(sensor for sensor in gateway.sensors.values() if isinstance(sensor, GatewayGridVoltage))

    sensor._polling_coordinator.begin_refresh()  # type: ignore[attr-defined]
    assert await sensor._read_cloud_state(port) is None  # type: ignore[attr-defined]
