import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.test_utils import make_mocked_request

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.config.service import SettingsService
from sigenergy2mqtt.diagnostics.collectors import DiagnosticsCollectors
from sigenergy2mqtt.diagnostics.server import DiagnosticsServer
from sigenergy2mqtt.main import device_thread
from sigenergy2mqtt.main.service_setup import setup_services
from sigenergy2mqtt.main.thread_config import thread_config_registry


@pytest.fixture
def services(monkeypatch):
    active_config.runtime_config_enabled = False
    active_config.metrics_enabled = False
    active_config.pvoutput.enabled = False
    active_config.influxdb.enabled = False
    active_config.home_assistant.enabled = False
    monkeypatch.setattr("sigenergy2mqtt.main.service_setup.is_docker", lambda: False)
    thread_config_registry.clear()
    yield
    thread_config_registry.clear()


@pytest.mark.asyncio
async def test_diagnostics_controls_and_http_updates_without_mqtt_publishing(services):
    active_config.diagnostics.enabled = True
    configs = setup_services([], ProtocolVersion.N_A)
    service = next(device for config in configs for device in config.devices if isinstance(device, SettingsService))

    payload = await DiagnosticsCollectors._diagnostics_collect_runtime_config()
    controls = payload["controls"]
    assert controls["log_level"]["type"] == "select"
    assert controls["diagnostics_log_level"]["type"] == "select"
    assert controls["repeated_state_publish_interval"]["type"] == "number"
    assert controls["persistence_debug"]["type"] == "switch"
    assert all(not sensor.publishable for sensor in service.sensors.values())

    mqtt_client = MagicMock()
    server = DiagnosticsServer()
    server._mqtt_client = mqtt_client
    request = make_mocked_request("POST", "/diagnostics/config/repeated_state_publish_interval", match_info={"endpoint": "repeated_state_publish_interval"})
    request.json = AsyncMock(return_value={"value": 60})
    response = await server._handle_config_update(request)

    assert response.status == 200
    assert json.loads(response.text)["ok"] is True
    assert active_config.repeated_state_publish_interval == 60
    updated = await DiagnosticsCollectors._diagnostics_collect_runtime_config()
    assert updated["controls"]["repeated_state_publish_interval"]["value"] == 60
    mqtt_client.publish.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("clean, publishing", [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize("ha_enabled", [False, True])
async def test_settings_discovery_removed_via_device_thread(services, clean, publishing, ha_enabled):
    active_config.diagnostics.enabled = False
    active_config.runtime_config_enabled = publishing
    active_config.home_assistant.enabled = ha_enabled
    active_config.home_assistant.unique_id_prefix = "sig"
    active_config.home_assistant.discovery_prefix = "custom-ha"
    active_config.home_assistant.republish_discovery_interval = 1
    active_config.clean = clean
    configs = setup_services([], ProtocolVersion.N_A)
    config = next(config for config in configs if config.name == "Services")
    service = next(device for device in config.devices if isinstance(device, SettingsService))

    mqtt_client = MagicMock()
    mqtt_handler = MagicMock()

    async def wait_for(seconds, name, method, *args, **kwargs):
        return method(*args, **kwargs)

    mqtt_handler.wait_for = AsyncMock(side_effect=wait_for)
    with (
        patch.object(device_thread, "mqtt_setup", AsyncMock(return_value=(mqtt_client, mqtt_handler))),
        patch.object(device_thread, "mqtt_teardown", AsyncMock()) as teardown,
    ):
        await device_thread.read_and_publish_device_sensors(config, asyncio.get_running_loop())
        teardown.assert_awaited_once_with(mqtt_client, mqtt_handler)

    assert service in config.devices
    mqtt_client.publish.assert_any_call("custom-ha/device/sig_config/config", b"", qos=0, retain=True)
    mqtt_client.publish.assert_any_call("custom-ha/device/sig_config/availability", b"", 0, True)
    assert len(mqtt_client.publish.call_args_list) == 2
    mqtt_handler.register.assert_not_called()
    assert service.schedule(None, mqtt_client) == []


def test_enabled_settings_still_publish_and_subscribe(services):
    active_config.runtime_config_enabled = True
    active_config.home_assistant.enabled = True
    active_config.home_assistant.republish_discovery_interval = 1
    active_config.diagnostics.enabled = False
    active_config.clean = False
    configs = setup_services([], ProtocolVersion.N_A)
    service = next(device for config in configs for device in config.devices if isinstance(device, SettingsService))
    mqtt_client = MagicMock()
    mqtt_handler = MagicMock()

    service.publish_discovery(mqtt_client)
    discovery_call = next(call for call in mqtt_client.publish.call_args_list if call.args[0].endswith("/config"))
    payload = json.loads(discovery_call.args[1])
    assert "sigenergy2mqtt_config_log_level" in payload["cmps"]
    assert discovery_call.kwargs["retain"] is True
    assert all(sensor.publishable for sensor in service.sensors.values())

    service.subscribe(mqtt_client, mqtt_handler)
    assert any(call.args[1] == "sigenergy2mqtt/config/log_level/set" for call in mqtt_handler.register.call_args_list)
    tasks = service.schedule(None, mqtt_client)
    try:
        assert tasks
    finally:
        for task in tasks:
            task.close()
