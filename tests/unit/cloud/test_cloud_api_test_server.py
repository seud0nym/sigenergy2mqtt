"""Tests for the stateful cloud API facsimile used by integration tests."""

import asyncio
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer
from pymodbus.client.mixin import ModbusClientMixin

from sigenergy2mqtt.sensors.inverter.read_only import (
    InverterModel,
    InverterSerialNumber,
    RatedActivePower,
)
from tests.utils import modbus_test_server as server_module
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


async def test_cloud_api_test_server_dashboard_edits_live_response_values() -> None:
    api = CloudApiTestServer(None, None)
    api.internet_available = False

    async with TestClient(TestServer(api.app())) as client:
        dashboard = await client.get("/cloud-api-test")
        assert dashboard.status == 200
        dashboard_html = await dashboard.text()
        assert "Cloud API Test Server" in dashboard_html
        assert "Preserved ${preserved} unapplied edit" in dashboard_html

        script = await client.get("/cloud-api-test/cloud_api.mjs")
        assert script.status == 200
        assert "reconcileEditors" in await script.text()

        state = await client.get("/cloud-api-test/state")
        assert state.status == 200
        assert (await state.json())["grid_export_limit"]["maxLimitation"] == "10.000"

        update = await client.put(
            "/cloud-api-test/state/grid_export_limit",
            json={
                "value": {
                    "enable": False,
                    "maxLimitation": "2.500",
                    "maxLimitationOwner": "2.500",
                    "maxLimitationInstaller": "20.000",
                    "isUltra": False,
                }
            },
        )
        assert update.status == 200
        assert api.grid_export_limit["maxLimitation"] == "2.500"

        restore = await client.put(
            "/cloud-api-test/state/internet_available", json={"value": True}
        )
        assert restore.status == 200
        api.access_token = "test-token"
        response = await client.get(
            "/device/energy-profile/grid/limitation/export/1",
            headers={"Authorization": "Bearer test-token"},
        )
        assert (await response.json())["data"]["maxLimitation"] == "2.500"


@pytest.mark.parametrize(
    ("name", "value", "status"),
    [
        ("not_a_setting", True, 404),
        ("internet_available", 1, 400),
        ("internet_outage_status", 404, 400),
        ("gateway_info", [], 400),
    ],
)
async def test_cloud_api_test_server_dashboard_rejects_invalid_updates(
    name: str, value: object, status: int
) -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        response = await client.put(
            f"/cloud-api-test/state/{name}", json={"value": value}
        )
        assert response.status == status


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_cloud_api_dashboard_reload_preserves_unapplied_edits() -> None:
    """Execute the same reconciliation module used by the Reload button."""
    module_uri = (Path(server_module.__file__).parent / "static/cloud_api.mjs").as_uri()
    javascript = f"""
        import assert from 'node:assert/strict';
        import {{bindReload, reconcileEditors}} from {module_uri!r};

        const dirty = {{value: 'unapplied operator edit', dataset: {{dirty: 'true'}}}};
        const clean = {{value: 'old value', dataset: {{dirty: 'false'}}}};
        const article = (name, textarea) => ({{
          dataset: {{name}}, querySelector: () => textarea
        }});
        const values = {{
          children: [article('dirty_setting', dirty), article('clean_setting', clean)],
          append: () => assert.fail('Reload unexpectedly created an editor')
        }};
        const setEditorValue = (textarea, value) => {{
          textarea.value = value;
          textarea.dataset.dirty = 'false';
        }};
        let preserved;
        const reload = {{
          listener: null,
          addEventListener: (event, listener) => {{
            assert.equal(event, 'click');
            reload.listener = listener;
          }},
          click: () => reload.listener()
        }};
        bindReload(reload, () => {{
          preserved = reconcileEditors(
            values,
            {{dirty_setting: 'server replacement', clean_setting: 'fresh server value'}},
            () => assert.fail('Reload unexpectedly created a card'),
            setEditorValue
          );
        }});

        // Match an operator editing one textarea and then clicking Reload.
        reload.click();

        assert.equal(preserved, 1);
        assert.equal(dirty.value, 'unapplied operator edit');
        assert.equal(dirty.dataset.dirty, 'true');
        assert.equal(clean.value, 'fresh server value');
    """
    subprocess.run(
        ["node", "--input-type=module", "--eval", javascript],
        check=True,
        capture_output=True,
        text=True,
    )


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


async def test_simulate_internet_outage_restores_service_when_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = CloudApiTestServer(None, None)
    outage_started = asyncio.Event()
    hold_outage = asyncio.Event()
    sleep_count = 0

    async def controlled_sleep(_seconds: int) -> None:
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 2:
            outage_started.set()
            await hold_outage.wait()

    monkeypatch.setattr(asyncio, "sleep", controlled_sleep)
    task = asyncio.create_task(
        simulate_internet_outage(
            api,
            wait_for_seconds=10,
            duration_seconds=20,
            repeated=True,
        )
    )

    await outage_started.wait()
    assert api.internet_available is False

    task.cancel()
    await task

    assert api.internet_available is True


async def test_simulate_internet_outage_rejects_non_server_error() -> None:
    with pytest.raises(ValueError, match="between 500 and 599"):
        await simulate_internet_outage(
            CloudApiTestServer(None, None),
            wait_for_seconds=0,
            duration_seconds=0,
            repeated=False,
            status_code=404,
        )


async def test_run_async_server_schedules_configured_internet_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the startup branch controlled by TestConfig's outage flag."""
    simulated_outage = AsyncMock()
    monkeypatch.setattr(server_module, "simulate_internet_outage", simulated_outage)
    monkeypatch.setattr(server_module, "get_sensor_instances", AsyncMock(return_value={}))
    monkeypatch.setattr(
        server_module.ModbusTcpServer,
        "serve_forever",
        AsyncMock(),
    )
    monkeypatch.setattr(server_module.TestConfig, "simulate_internet_outage", True)
    monkeypatch.setattr(
        server_module.TestConfig, "internet_outage_initial_delay_seconds", 11
    )
    monkeypatch.setattr(
        server_module.TestConfig, "internet_outage_duration_seconds", 22
    )
    monkeypatch.setattr(server_module.TestConfig, "internet_outage_repeated", False)
    monkeypatch.setattr(server_module.TestConfig, "internet_outage_status_code", 502)

    await server_module.run_async_server(
        mqtt_client=None,
        modbus_client=None,
        use_simplified_topics=True,
        host="127.0.0.1",
        port=0,
        cloud_port=0,
    )

    simulated_outage.assert_awaited_once()
    assert simulated_outage.await_args is not None
    _, kwargs = simulated_outage.await_args
    assert kwargs == {
        "wait_for_seconds": 11,
        "duration_seconds": 22,
        "repeated": False,
        "status_code": 502,
    }


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
            "/device/device/pack/queryPackMergeInfo",
            params={"stationId": str(api.device_topology["stationId"]), "snCode": "BAT-1"},
            headers=headers,
        )
        assert (await response.json())["data"] == api.battery_pack_merge_info

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
                "snCode": HYBRID_INVERTER_SERIAL[3:],
                "deviceName": "",
                "deviceType": 3,
                "deviceModel": "",
                "deviceCode": "1104002600",
                "deviceTypeDesc": "Inverter",
                "deviceStatus": 1,
                "communicateStatus": 2,
                "batPosition": 0,
                "nodeList": [],
                "deviceOrder": 1,
                "ratedActivePower": HYBRID_INVERTER_RATED_ACTIVE_POWER,
                "hasDcCharger": None,
                "dcRunStatus": None,
            },
            {
                "stationId": api.device_topology["stationId"],
                "snCode": PV_INVERTER_SERIAL[3:],
                "deviceType": 3,
                "deviceStatus": 1,
                "communicateStatus": 2,
                "deviceCode": PV_INVERTER_MODEL,
                "modelVersionStr": FIRMWARE_VERSION,
                "ratedActivePower": PV_INVERTER_RATED_ACTIVE_POWER,
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
            HYBRID_INVERTER_SERIAL[3:],
            HYBRID_INVERTER_RATED_ACTIVE_POWER,
        ),
        (
            3,
            PV_INVERTER_MODEL,
            PV_INVERTER_SERIAL[3:],
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
        assert modbus_values["snCode"] == f"CMU{cloud_node['snCode']}"
        if address == 1:
            assert cloud_node["deviceCode"] == "1104002600"
            assert modbus_values["deviceCode"] == HYBRID_INVERTER_MODEL
        else:
            assert cloud_node["deviceCode"] == modbus_values["deviceCode"]
        assert cloud_node["ratedActivePower"] == modbus_values["ratedActivePower"]


class _GatewayClient:
    """Authenticated requests against a test server with a controllable clock."""

    def __init__(self, api: CloudApiTestServer, client: TestClient) -> None:
        self.api = api
        self.client = client
        self.now = 0.0
        api._clock = lambda: self.now
        api.access_token = "token"
        self.headers = {"Authorization": "Bearer token"}
        self.station_id = api.station_home_data["stationId"]

    async def status(self) -> tuple[int, int]:
        response = await self.client.get(
            "/device/gateway/gateway-status",
            headers=self.headers,
            params={"stationId": str(self.station_id)},
        )
        assert response.status == 200
        data = (await response.json())["data"]
        return data["onOffGridStatus"], data["manualOffGridStatus"]

    async def press(self, on_grid_state: int) -> None:
        response = await self.client.post(
            "/device/gateway/ongrid-state/update",
            headers=self.headers,
            json={"onGridState": on_grid_state, "stationId": int(self.station_id)},
        )
        assert response.status == 200
        payload = await response.json()
        assert payload["code"] == 0
        assert payload["data"] == 0

    async def timeline(self, samples: int) -> list[tuple[int, int]]:
        """Sample the status every 2 seconds, as the recorded app responses were."""
        statuses = []
        for _ in range(samples):
            statuses.append(await self.status())
            self.now += 2.0
        return statuses


async def test_gateway_status_reports_full_payload_before_any_press() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        response = await client.get(
            "/device/gateway/gateway-status",
            headers=gateway.headers,
            params={"stationId": str(gateway.station_id)},
        )
        assert (await response.json())["data"] == {
            "onOffGridStatus": 0,
            "manualOffGridStatus": 0,
            "isSupportSignal": True,
            "doorStatus": None,
            "onOffGridControlMode": 0,
            "showButton": True,
        }


async def test_gateway_status_route_does_not_shadow_gateway_info() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        response = await client.get(f"/device/gateway/{gateway.station_id}", headers=gateway.headers)
        assert (await response.json())["data"] == api.gateway_info


async def test_gateway_go_off_grid_matches_recorded_timeline() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        assert await gateway.status() == (0, 0)

        await gateway.press(1)

        assert await gateway.timeline(5) == [(0, 1), (0, 1), (0, 1), (2, 2), (2, 2)]


async def test_gateway_go_on_grid_matches_recorded_timeline() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        await gateway.press(1)
        gateway.now += api.gateway_off_grid_seconds
        assert await gateway.status() == (2, 2)

        await gateway.press(0)

        assert await gateway.timeline(11) == [(1, 2)] * 9 + [(0, 2)] * 2


async def test_gateway_can_go_off_grid_again_after_a_round_trip() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        await gateway.press(1)
        gateway.now += api.gateway_off_grid_seconds
        await gateway.status()
        await gateway.press(0)
        gateway.now += api.gateway_on_grid_seconds
        assert await gateway.status() == (0, 2)

        await gateway.press(1)

        assert await gateway.status() == (0, 1)


async def test_gateway_press_matching_current_state_changes_nothing() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)

        await gateway.press(0)
        assert await gateway.status() == (0, 0)
        assert api._gateway_transition is None

        await gateway.press(1)
        gateway.now += api.gateway_off_grid_seconds
        await gateway.press(1)
        assert await gateway.status() == (2, 2)
        assert api._gateway_transition is None


async def test_gateway_press_during_transition_changes_nothing() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        await gateway.press(1)
        gateway.now += 2.0

        await gateway.press(0)

        assert await gateway.status() == (0, 1)
        gateway.now += api.gateway_off_grid_seconds
        assert await gateway.status() == (2, 2)


async def test_gateway_endpoints_require_authorization() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        station_id = api.station_home_data["stationId"]
        response = await client.get("/device/gateway/gateway-status", params={"stationId": str(station_id)})
        assert response.status == 401
        response = await client.post("/device/gateway/ongrid-state/update", json={"onGridState": 1, "stationId": int(station_id)})
        assert response.status == 401
        assert api.gateway_status["manualOffGridStatus"] == 0


@pytest.mark.parametrize("on_grid_state", [2, -1, "1", True, None])
async def test_gateway_update_rejects_invalid_on_grid_state(on_grid_state: object) -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        response = await client.post(
            "/device/gateway/ongrid-state/update",
            headers=gateway.headers,
            json={"onGridState": on_grid_state, "stationId": int(gateway.station_id)},
        )
        assert response.status == 400
        assert api._gateway_transition is None
        assert await gateway.status() == (0, 0)


async def test_gateway_endpoints_reject_unknown_station() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        response = await client.get("/device/gateway/gateway-status", headers=gateway.headers)
        assert response.status == 400
        response = await client.post(
            "/device/gateway/ongrid-state/update",
            headers=gateway.headers,
            json={"onGridState": 1, "stationId": 1},
        )
        assert response.status == 400
        assert api._gateway_transition is None


async def test_gateway_status_is_editable_and_edit_replaces_transition() -> None:
    api = CloudApiTestServer(None, None)
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)
        await gateway.press(1)

        response = await client.get("/cloud-api-test/state")
        assert (await response.json())["gateway_status"]["manualOffGridStatus"] == 1
        gateway.now += api.gateway_off_grid_seconds
        response = await client.get("/cloud-api-test/state")
        assert (await response.json())["gateway_status"]["onOffGridStatus"] == 2

        await gateway.press(0)
        edited = {**api.gateway_status, "onOffGridStatus": 2, "showButton": False}
        response = await client.put("/cloud-api-test/state/gateway_status", json={"value": edited})
        assert response.status == 200
        gateway.now += api.gateway_on_grid_seconds

        assert await gateway.status() == (2, 2)
        assert api.gateway_status["showButton"] is False


async def test_gateway_round_trip_drives_plant_grid_status_as_recorded() -> None:
    api = CloudApiTestServer(None, None)
    api.plant_grid_status_writer = AsyncMock()
    written = api.plant_grid_status_writer
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)

        await gateway.press(1)
        assert await gateway.status() == (0, 1)
        written.assert_not_awaited()

        gateway.now += api.gateway_off_grid_seconds
        assert await gateway.status() == (2, 2)
        assert [call.args[0] for call in written.await_args_list] == [2]  # Off Grid (manual)

        await gateway.press(0)
        assert [call.args[0] for call in written.await_args_list] == [2, 1]  # Off Grid (auto) during the return

        gateway.now += api.gateway_on_grid_seconds
        assert await gateway.status() == (0, 2)
        assert [call.args[0] for call in written.await_args_list] == [2, 1, 0]  # On Grid


async def test_gateway_press_matching_current_state_does_not_write_plant_grid_status() -> None:
    api = CloudApiTestServer(None, None)
    api.plant_grid_status_writer = AsyncMock()
    async with TestClient(TestServer(api.app())) as client:
        gateway = _GatewayClient(api, client)

        await gateway.press(0)

        api.plant_grid_status_writer.assert_not_awaited()


async def test_gateway_transition_completes_without_another_cloud_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CloudApiTestServer, "gateway_off_grid_seconds", 0.05)
    monkeypatch.setattr(CloudApiTestServer, "gateway_on_grid_seconds", 0.05)
    api = CloudApiTestServer(None, None)
    api.plant_grid_status_writer = AsyncMock()
    written = api.plant_grid_status_writer
    async with TestClient(TestServer(api.app())) as client:
        api.access_token = "token"
        headers = {"Authorization": "Bearer token"}
        station_id = api.station_home_data["stationId"]

        async def press(on_grid_state: int) -> None:
            response = await client.post("/device/gateway/ongrid-state/update", json={"onGridState": on_grid_state, "stationId": int(station_id)}, headers=headers)
            assert response.status == 200

        await press(1)
        async with asyncio.timeout(1):
            while api._gateway_transition is not None:
                await asyncio.sleep(0.01)
        assert api.gateway_status["onOffGridStatus"] == 2
        assert [call.args[0] for call in written.await_args_list] == [2]

        await press(0)
        async with asyncio.timeout(1):
            while api._gateway_transition is not None:
                await asyncio.sleep(0.01)
        assert api.gateway_status["onOffGridStatus"] == 0
        assert [call.args[0] for call in written.await_args_list] == [2, 1, 0]
