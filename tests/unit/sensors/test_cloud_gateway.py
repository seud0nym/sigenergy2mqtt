"""Tests for dynamically discovered cloud gateway sensors."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.cloud.exceptions import (
    CloudControlRateLimitedError,
    CloudControlRejectedError,
    CloudControlUnavailableError,
)
from sigenergy2mqtt.common import DeviceClass, ScanIntervalDefault
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices.cloud import (
    CloudControl,
    CloudDiscovery,
    Gateway,
    discover_cloud,
)
from sigenergy2mqtt.devices.cloud.sigen_device import CloudBattery, CloudInverter
from sigenergy2mqtt.sensors.base import (
    CloudWritableSensor,
    CloudWriteOnlySensor,
    DiscoveryKeys,
    WriteOnlySensorMixin,
)
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
    GatewaySensor,
    GatewaySerialNumber,
)
from sigenergy2mqtt.sensors.cloud.read_write import (
    BatteryExportLimitation,
    GatewayGridConnectionControl,
    GatewayGridConnectionStatus,
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


def test_rated_battery_capacity_uses_energy_class_without_state_class() -> None:
    sensor = DeviceInfoSensor(
        0,
        FakeCloudControlPort.station_id,
        "BAT-1",
        "Rated Battery Capacity",
        "kWh",
        DeviceInfoSnapshot(4, "BAT-1", True),
        static=True,
    )

    assert sensor[DiscoveryKeys.DEVICE_CLASS] == DeviceClass.ENERGY
    assert sensor[DiscoveryKeys.STATE_CLASS] is None


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
    assert control.children[0]["model"] == "SigenStor EC 10.0 TP"
    assert "sn=INV-1" in control.children[0].log_identity
    assert control.children[1]["name"] == "SigenStor EC 10.0 TP 2"
    assert control.children[1]["model"] == "SigenStor EC 10.0 TP"
    assert "batPosition=2" in control.children[1].log_identity
    assert control.children[1].unique_id == "sigen_0_station-123_battery_BAT-1"
    static_sensor = list(control.children[0].sensors.values())[1]
    assert static_sensor[DiscoveryKeys.ENTITY_CATEGORY] == "diagnostic"
    assert static_sensor.scan_interval == ScanIntervalDefault.LOW  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_battery_pack_merge_sensors_belong_to_the_matching_battery() -> None:
    packs = {
        "BAT-1": {"paramInfoVOList": [
            {"paramKey": "Total Discharge Amount", "paramValueText": "2.96", "paramValueUnit": "MWh"},
            {"paramKey": "Average Cell Voltage", "paramValueText": "3.338", "paramValueUnit": "V"},
            {"paramKey": "Average Cell Temperature", "paramValueText": "25.3", "paramValueUnit": "℃"},
        ]}
    }
    discovery = CloudDiscovery(
        device_list=[{"deviceType": "Battery", "serialNumber": "BAT-1", "attrMap": {}}],
        device_info={"BAT-1": ({}, {})},
        battery_pack_info=packs,
    )
    battery = CloudControl(0, FakeCloudControlPort(), discovery).children[0]
    sensors = {sensor.name: sensor for sensor in battery.sensors.values()}
    assert set(sensors) == {"Total Discharge Amount", "Average Cell Voltage", "Average Cell Temperature"}
    assert all(sensor[DiscoveryKeys.UNIQUE_ID].startswith("sigen_0_station-123_4_BAT-1_") for sensor in sensors.values())
    assert sensors["Total Discharge Amount"][DiscoveryKeys.DEVICE_CLASS] == DeviceClass.ENERGY
    assert sensors["Total Discharge Amount"][DiscoveryKeys.STATE_CLASS] == "total_increasing"
    assert sensors["Average Cell Voltage"][DiscoveryKeys.STATE_CLASS] == "measurement"
    assert sensors["Average Cell Temperature"][DiscoveryKeys.STATE_CLASS] == "measurement"
    port = FakeCloudControlPort()
    port.battery_pack_merge_info = AsyncMock(return_value=packs["BAT-1"])
    assert await sensors["Average Cell Temperature"]._read_cloud_state(port) == 25.3
    port.battery_pack_merge_info.assert_awaited_once_with("BAT-1")


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
    assert [child["model"] for child in control.children] == ["Inverter", "Battery"]


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
        "sigen_0_station-123_battery_BAT-1",
        "sigen_0_station-123_battery_BAT-2",
    ]
    assert [child.log_identity for child in control.children] == [
        "CloudBattery[plant=0,sn=BAT-1]",
        "CloudBattery[plant=0,sn=BAT-2]",
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
        GatewayGridConnectionStatus,
        GatewayGridConnectionControl,
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
    sensors = [sensor for sensor in gateway.read_sensors.values() if isinstance(sensor, GatewaySensor)]
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


def _gateway_status(on_off_grid: int = 0, manual: int = 0, show_button: object = True) -> dict[str, object]:
    return {
        "onOffGridStatus": on_off_grid,
        "manualOffGridStatus": manual,
        "isSupportSignal": True,
        "doorStatus": None,
        "onOffGridControlMode": 0,
        "showButton": show_button,
    }


def _grid_control(plant_grid_status: int | None = None) -> GatewayGridConnectionControl:
    status_sensor = GatewayGridConnectionStatus(0, FakeCloudControlPort.station_id)
    status_sensor.configure_mqtt_topics("device")
    sensor = GatewayGridConnectionControl(0, FakeCloudControlPort.station_id, status_sensor)
    sensor.configure_mqtt_topics("device")
    if plant_grid_status is not None:
        sensor.set_plant_grid_status(MagicMock(latest_raw_state=plant_grid_status))
    return sensor


def _published_availability(sensor: GatewayGridConnectionControl, mqtt_client: MagicMock) -> dict[str, str]:
    """Return the last availability payload published for each button."""
    published = {call.args[0]: call.args[1] for call in mqtt_client.publish.call_args_list}
    return {payload: published[topic] for payload, topic in (("go_off_grid", sensor._available_topics["off"]), ("go_on_grid", sensor._available_topics["on"]))}


@pytest.fixture
def home_assistant_enabled():
    previous = active_config.home_assistant.enabled
    active_config.home_assistant.enabled = True
    yield
    active_config.home_assistant.enabled = previous


async def _press(sensor: GatewayGridConnectionControl, port: FakeCloudControlPort, payload: str) -> bool:
    return await sensor.set_value(port, MagicMock(), payload, sensor.command_topic, MagicMock())


def test_gateway_grid_control_is_a_cloud_write_only_sensor_on_the_gateway() -> None:
    gateway = Gateway.from_discovery(0, FakeCloudControlPort.station_id, CloudDiscovery(device_list=[], gateway_info=GATEWAY_INFO))

    assert gateway is not None
    sensor = next(s for s in gateway.sensors.values() if isinstance(s, GatewayGridConnectionControl))
    assert isinstance(sensor, CloudWriteOnlySensor)
    assert isinstance(sensor, CloudWritableSensor)
    assert isinstance(sensor, WriteOnlySensorMixin)
    assert sensor.unique_id in gateway.write_sensors
    assert sensor.unique_id not in gateway.read_sensors


def test_gateway_grid_control_discovers_a_pair_of_labelled_buttons() -> None:
    sensor = _grid_control()

    components = sensor.get_discovery_components()
    off_grid = components[f"{sensor.unique_id}_off"]
    on_grid = components[f"{sensor.unique_id}_on"]

    assert off_grid["name"] == "Go Off-Grid"
    assert off_grid["payload_press"] == "go_off_grid"
    assert off_grid["icon"] == "mdi:transmission-tower-off"
    assert off_grid[DiscoveryKeys.UNIQUE_ID] == f"{sensor.unique_id}_go_off_grid"
    assert on_grid["name"] == "Go On-Grid"
    assert on_grid["payload_press"] == "go_on_grid"
    assert on_grid["icon"] == "mdi:transmission-tower"
    assert on_grid[DiscoveryKeys.UNIQUE_ID] == f"{sensor.unique_id}_go_on_grid"
    assert off_grid[DiscoveryKeys.COMMAND_TOPIC] == on_grid[DiscoveryKeys.COMMAND_TOPIC] == sensor.command_topic


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "status", "expected_off_grid"),
    [
        ("go_off_grid", _gateway_status(0, 0), True),
        ("go_off_grid", _gateway_status(0, 2), True),  # a previous round trip leaves manualOffGridStatus at 2
        ("go_on_grid", _gateway_status(2, 2), False),
    ],
)
async def test_gateway_grid_control_sends_command_when_transition_is_available(payload: str, status: dict[str, object], expected_off_grid: bool) -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.return_value = status

    assert await _press(sensor, port, payload) is True

    port.gateway_status.assert_awaited_once_with(wait_for_rate_limit=False)
    port.set_gateway_off_grid.assert_awaited_once_with(expected_off_grid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "status"),
    [
        pytest.param("go_off_grid", _gateway_status(2, 2), id="already-off-grid"),
        pytest.param("go_on_grid", _gateway_status(0, 0), id="already-on-grid"),
        pytest.param("go_on_grid", _gateway_status(0, 2), id="already-back-on-grid"),
        pytest.param("go_on_grid", _gateway_status(2, 0), id="off-grid-without-manual-request"),
        pytest.param("go_off_grid", _gateway_status(0, 1), id="off-while-going-off-grid"),
        pytest.param("go_on_grid", _gateway_status(0, 1), id="on-while-going-off-grid"),
        pytest.param("go_off_grid", _gateway_status(1, 2), id="off-while-returning"),
        pytest.param("go_on_grid", _gateway_status(1, 2), id="on-while-returning"),
        pytest.param("go_off_grid", _gateway_status(0, 0, show_button=False), id="off-button-hidden"),
        pytest.param("go_on_grid", _gateway_status(2, 2, show_button=False), id="on-button-hidden"),
        pytest.param("go_off_grid", _gateway_status(0, 0, show_button=None), id="show-button-missing"),
        pytest.param("go_off_grid", {**_gateway_status(), "onOffGridStatus": 9}, id="unknown-status"),
        pytest.param("go_off_grid", {"showButton": True}, id="incomplete-status"),
        pytest.param("go_off_grid", None, id="not-an-object"),
        pytest.param("go_off_grid", [], id="list"),
    ],
)
async def test_gateway_grid_control_sends_nothing_unless_transition_is_available(payload: str, status: object) -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.return_value = status

    assert await _press(sensor, port, payload) is False

    port.set_gateway_off_grid.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_grid_control_sends_nothing_when_status_read_fails() -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.side_effect = CloudControlUnavailableError("offline")

    assert await _press(sensor, port, "go_off_grid") is False

    port.set_gateway_off_grid.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_grid_control_reports_rejected_command_as_failed_write() -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status()
    port.set_gateway_off_grid.side_effect = CloudControlRejectedError("refused")

    assert await _press(sensor, port, "go_off_grid") is False


@pytest.mark.asyncio
async def test_gateway_grid_control_cannot_write_without_a_cloud_backend() -> None:
    sensor = _grid_control()

    assert await sensor.set_value(None, MagicMock(), "go_off_grid", sensor.command_topic, MagicMock()) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["0", "1", "off", "on", "press", ""])
async def test_gateway_grid_control_ignores_payloads_other_than_its_buttons(payload: str) -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()

    assert await _press(sensor, port, payload) is False

    port.gateway_status.assert_not_awaited()
    port.set_gateway_off_grid.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_grid_control_ignores_commands_from_other_topics() -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()

    assert await sensor.set_value(port, MagicMock(), "go_off_grid", "some/other/topic", MagicMock()) is False

    port.gateway_status.assert_not_awaited()
    port.set_gateway_off_grid.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_grid_control_has_no_state_to_poll() -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()

    assert await sensor._update_internal_state(modbus_client=port) is False

    port.gateway_status.assert_not_awaited()


def test_read_write_sensors_share_the_cloud_write_path() -> None:
    assert issubclass(BatteryExportLimitation, CloudWritableSensor)
    assert not issubclass(BatteryExportLimitation, CloudWriteOnlySensor)


def test_gateway_grid_control_documents_its_payloads() -> None:
    comment = str(_grid_control().get_attributes()["comment"])

    assert "go_off_grid" in comment
    assert "go_on_grid" in comment


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("on_off_grid", "manual", "expected"),
    [
        (0, 0, "On Grid"),
        (0, 2, "On Grid"),
        (0, 1, "Going Off Grid"),
        (2, 2, "Off Grid"),
        (1, 2, "Returning to Grid"),
    ],
)
async def test_grid_connection_status_reports_each_recorded_state(on_off_grid: int, manual: int, expected: str) -> None:
    sensor = GatewayGridConnectionStatus(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status(on_off_grid, manual)

    assert await sensor.get_state(modbus_client=port) == expected

    port.gateway_status.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_grid_connection_status_keeps_no_status_after_unknown_value() -> None:
    sensor = GatewayGridConnectionStatus(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status()
    assert await sensor._read_cloud_state(port) == 0

    port.gateway_status.return_value = {**_gateway_status(), "onOffGridStatus": 9}

    assert await sensor._read_cloud_state(port) is None
    assert sensor.gateway_status is None


@pytest.mark.asyncio
async def test_grid_connection_status_rejects_a_response_that_is_not_an_object() -> None:
    sensor = GatewayGridConnectionStatus(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.gateway_status.return_value = []

    with pytest.raises(CloudControlUnavailableError):
        await sensor._read_cloud_state(port)
    assert sensor.gateway_status is None


@pytest.mark.parametrize(
    ("status", "plant_grid_status", "expected_off", "expected_on"),
    [
        pytest.param(_gateway_status(0, 0), None, "1", "0", id="on-grid-cloud-only"),
        pytest.param(_gateway_status(2, 2), None, "0", "1", id="manual-off-grid-cloud-only"),
        pytest.param(_gateway_status(0, 0), 0, "1", "0", id="both-on-grid"),
        pytest.param(_gateway_status(2, 2), 2, "0", "1", id="both-manual-off-grid"),
        pytest.param(_gateway_status(2, 2), 1, "0", "0", id="outage-blocks-go-on-grid"),
        pytest.param(_gateway_status(0, 0), 1, "0", "0", id="outage-blocks-go-off-grid"),
        pytest.param(_gateway_status(2, 2), 0, "0", "0", id="plant-disagrees-on-grid"),
        pytest.param(_gateway_status(0, 0), 2, "0", "0", id="plant-disagrees-off-grid"),
        pytest.param(_gateway_status(0, 1), 0, "0", "0", id="going-off-grid"),
        pytest.param(_gateway_status(1, 2), 2, "0", "0", id="returning-to-grid"),
        pytest.param(_gateway_status(0, 0, show_button=False), 0, "0", "0", id="button-hidden"),
        pytest.param(None, 0, "0", "0", id="no-cloud-status"),
    ],
)
def test_button_availability_combines_cloud_status_and_plant_grid_status(home_assistant_enabled, status, plant_grid_status, expected_off: str, expected_on: str) -> None:
    sensor = _grid_control(plant_grid_status)
    sensor._status_sensor.gateway_status = status
    mqtt_client = MagicMock()

    sensor.publish_button_availability(mqtt_client)

    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": expected_off, "go_on_grid": expected_on}


@pytest.mark.parametrize(
    ("status", "plant_grid_status", "expected_off", "expected_on"),
    [
        pytest.param(_gateway_status(0, 0), 0, "1", "0", id="on-grid"),
        pytest.param(_gateway_status(0, 1), 0, "0", "0", id="going-off-grid"),
        pytest.param(_gateway_status(2, 2), 2, "0", "1", id="off-grid-manual"),
        pytest.param(_gateway_status(1, 2), 1, "0", "0", id="returning-reports-off-grid-auto"),
        pytest.param(_gateway_status(0, 2), 0, "1", "0", id="back-on-grid"),
    ],
)
def test_button_availability_through_recorded_round_trip(home_assistant_enabled, status, plant_grid_status: int, expected_off: str, expected_on: str) -> None:
    sensor = _grid_control(plant_grid_status)
    sensor._status_sensor.gateway_status = status
    mqtt_client = MagicMock()

    sensor.publish_button_availability(mqtt_client)

    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": expected_off, "go_on_grid": expected_on}


def test_button_availability_is_unavailable_until_plant_grid_status_is_read(home_assistant_enabled) -> None:
    sensor = _grid_control()
    sensor.set_plant_grid_status(MagicMock(latest_raw_state=None))
    sensor._status_sensor.gateway_status = _gateway_status(0, 0)
    mqtt_client = MagicMock()

    sensor.publish_button_availability(mqtt_client)

    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": "0", "go_on_grid": "0"}


def test_button_availability_publishes_nothing_without_home_assistant() -> None:
    previous = active_config.home_assistant.enabled
    active_config.home_assistant.enabled = False
    try:
        sensor = _grid_control(0)
        sensor._status_sensor.gateway_status = _gateway_status()
        mqtt_client = MagicMock()

        sensor.publish_button_availability(mqtt_client)

        mqtt_client.publish.assert_not_called()
    finally:
        active_config.home_assistant.enabled = previous


def test_each_button_discovers_its_own_availability_topic(home_assistant_enabled) -> None:
    sensor = _grid_control()

    components = sensor.get_discovery_components()
    off_availability = components[f"{sensor.unique_id}_off"][DiscoveryKeys.AVAILABILITY]
    on_availability = components[f"{sensor.unique_id}_on"][DiscoveryKeys.AVAILABILITY]

    assert off_availability[-1] == {"topic": sensor._available_topics["off"], "payload_available": "1", "payload_not_available": "0"}
    assert on_availability[-1] == {"topic": sensor._available_topics["on"], "payload_available": "1", "payload_not_available": "0"}
    assert sensor._available_topics["off"] != sensor._available_topics["on"]
    assert off_availability[:-1] == on_availability[:-1] == sensor[DiscoveryKeys.AVAILABILITY]
    assert components[f"{sensor.unique_id}_off"]["availability_mode"] == "all"


@pytest.mark.asyncio
async def test_status_poll_publishes_state_and_button_availability(home_assistant_enabled) -> None:
    sensor = _grid_control(0)
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status(0, 0)
    mqtt_client = MagicMock()

    await sensor._status_sensor.publish(mqtt_client, port)

    published = {call.args[0]: call.args[1] for call in mqtt_client.publish.call_args_list}
    assert published[sensor._status_sensor.state_topic] == "On Grid"
    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": "1", "go_on_grid": "0"}


@pytest.mark.asyncio
async def test_failed_status_poll_makes_both_buttons_unavailable(home_assistant_enabled) -> None:
    sensor = _grid_control(0)
    sensor._status_sensor.gateway_status = _gateway_status(0, 0)
    port = FakeCloudControlPort()
    port.gateway_status.side_effect = CloudControlUnavailableError("offline")
    mqtt_client = MagicMock()

    with pytest.raises(CloudControlUnavailableError):
        await sensor._status_sensor.publish(mqtt_client, port)

    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": "0", "go_on_grid": "0"}


@pytest.mark.asyncio
async def test_accepted_press_disables_buttons_and_requests_immediate_poll(home_assistant_enabled) -> None:
    sensor = _grid_control(0)
    sensor._status_sensor.gateway_status = _gateway_status(0, 0)
    sensor._status_sensor.force_publish = False
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status(0, 0)
    mqtt_client = MagicMock()

    assert await sensor.set_value(port, mqtt_client, "go_off_grid", sensor.command_topic, MagicMock()) is True

    assert _published_availability(sensor, mqtt_client) == {"go_off_grid": "0", "go_on_grid": "0"}
    assert sensor._status_sensor.force_publish is True


@pytest.mark.asyncio
async def test_refused_press_leaves_buttons_and_polling_unchanged(home_assistant_enabled) -> None:
    sensor = _grid_control(0)
    status = _gateway_status(2, 2)
    sensor._status_sensor.gateway_status = status
    sensor._status_sensor.force_publish = False
    port = FakeCloudControlPort()
    port.gateway_status.return_value = status
    mqtt_client = MagicMock()

    assert await sensor.set_value(port, mqtt_client, "go_off_grid", sensor.command_topic, MagicMock()) is False

    assert sensor._status_sensor.gateway_status is status
    assert sensor._status_sensor.force_publish is False
    mqtt_client.publish.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "status", "plant_grid_status"),
    [
        pytest.param("go_on_grid", _gateway_status(2, 2), 1, id="outage-blocks-go-on-grid"),
        pytest.param("go_off_grid", _gateway_status(0, 0), 1, id="outage-blocks-go-off-grid"),
        pytest.param("go_off_grid", _gateway_status(0, 0), None, id="plant-disagrees"),
    ],
)
async def test_press_is_refused_when_plant_grid_status_disagrees(payload: str, status: dict[str, object], plant_grid_status: int | None) -> None:
    sensor = _grid_control()
    sensor.set_plant_grid_status(MagicMock(latest_raw_state=plant_grid_status))
    port = FakeCloudControlPort()
    port.gateway_status.return_value = status

    assert await _press(sensor, port, payload) is False

    port.set_gateway_off_grid.assert_not_awaited()


@pytest.mark.asyncio
async def test_press_during_cooldown_is_dropped_with_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.side_effect = CloudControlRateLimitedError("rate limited for another 90 seconds", retry_after=90.0)

    with caplog.at_level("WARNING"):
        assert await _press(sensor, port, "go_off_grid") is False

    port.set_gateway_off_grid.assert_not_awaited()
    assert any(record.levelname == "WARNING" and "dropping go_off_grid" in record.getMessage() and "90 seconds" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_cooldown_starting_after_status_read_drops_command_with_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    sensor = _grid_control()
    port = FakeCloudControlPort()
    port.gateway_status.return_value = _gateway_status()
    port.set_gateway_off_grid.side_effect = CloudControlRateLimitedError("rate limited", retry_after=30.0)

    with caplog.at_level("WARNING"):
        assert await _press(sensor, port, "go_off_grid") is False

    assert any(record.levelname == "WARNING" and "dropping go_off_grid" in record.getMessage() for record in caplog.records)
