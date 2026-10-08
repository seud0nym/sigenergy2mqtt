"""Regression coverage for concurrent cloud controls and startup recovery."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.auth import OAuthSession, TokenBundle
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.cloud.sigen_device import CloudBattery
from sigenergy2mqtt.sensors.cloud.read_write import BatteryChargePowerLimit, BatteryDischargePowerLimit, SolarPowerLimit
from tests.unit.sensors.test_cloud_sensors import FakeCloudControlPort, _controls
from sigenergy2mqtt.cloud.models import InstantControlStatus


async def test_concurrent_battery_writes_preserve_both_changes():
    charge = BatteryChargePowerLimit(0, "station")
    discharge = BatteryDischargePowerLimit(0, "station", charge._snapshot)
    state = {"batteryMaxChargingPower": 4.0, "batteryMaxDischargingPower": 6.0}
    port = FakeCloudControlPort()

    async def read():
        result = dict(state)
        await asyncio.sleep(0)
        return result

    async def write(*, max_charge_kw, max_discharge_kw):
        await asyncio.sleep(0)
        state.update(batteryMaxChargingPower=max_charge_kw, batteryMaxDischargingPower=max_discharge_kw)

    port.battery_power_limit.side_effect = read
    port.set_battery_power_limit.side_effect = write
    assert await asyncio.gather(charge._write_cloud_value(port, 2), discharge._write_cloud_value(port, 3)) == [True, True]
    assert state == {"batteryMaxChargingPower": 2.0, "batteryMaxDischargingPower": 3.0}


async def test_expired_token_is_refreshed_once_for_concurrent_requests():
    auth = OAuthSession("eu")
    auth._tokens = TokenBundle("old", "refresh", 0)

    async def refresh(*args):
        await asyncio.sleep(0)
        return TokenBundle("new", "rotated", time.time() + 3600)

    auth._request_token = AsyncMock(side_effect=refresh)
    await asyncio.gather(auth.ensure_token(None, "url"), auth.ensure_token(None, "url"))
    auth._request_token.assert_awaited_once()


async def test_switch_availability_updates_with_unchanged_state(monkeypatch):
    mode, duration, switch = _controls()
    switch._availability_topic = "available"
    switch.set_latest_state(0)
    mqtt = MagicMock()
    monkeypatch.setattr("sigenergy2mqtt.sensors.base.cloud.CloudReadWriteSensor.publish", AsyncMock(return_value=False))
    await switch.publish(mqtt, None)
    assert mqtt.publish.call_args.args == ("available", "0")
    await mode._write_cloud_value(None, 1)
    await duration._write_cloud_value(None, 1)
    await switch.publish(mqtt, None)
    assert mqtt.publish.call_args.args == ("available", "1")
    mode._pending_value = None
    duration._pending_value = 0
    switch.set_latest_state(1)
    await switch.publish(mqtt, None)
    assert mqtt.publish.call_args.args == ("available", "1")


async def test_final_minute_duration_rounds_up():
    _, duration, _ = _controls()
    port = FakeCloudControlPort()
    port.instant_control_status = AsyncMock(return_value=InstantControlStatus(True, None, time.time() + 20))
    assert await duration._read_cloud_state(port) == 1


async def test_unlimited_solar_replaces_finite_reading():
    solar = SolarPowerLimit(0, "station")
    port = FakeCloudControlPort()
    port.solar_power_limit.return_value = {"powerLimit": 2}
    await solar._update_internal_state(modbus_client=port)
    assert solar.latest_raw_state == 2
    port.solar_power_limit.return_value = {"powerLimit": "4294967.295"}
    await solar._update_internal_state(modbus_client=port)
    assert solar.latest_raw_state == 4294967.295


async def test_failed_startup_device_info_recovers_and_starts_polling(monkeypatch):
    config = Config()
    with _swap_active_config(config):
        child = CloudBattery(0, "station", {"serialNumber": "battery"}, {}, {"paramInfoVOList": []})
        child.online = asyncio.get_running_loop().create_future()
        port = FakeCloudControlPort()
        port.device_dynamic_info.return_value = {"realTimeInfo": [{"paramKey": "SOC", "paramValueUnit": "%", "paramValueText": "50"}]}
        poll = AsyncMock()
        monkeypatch.setattr("sigenergy2mqtt.devices.cloud.sigen_device.SensorGroupPoller.run", poll)
        mqtt = MagicMock()
        await child.recover_info(port, mqtt)
        assert not child._pending_info
        assert len(child.sensors) == 1
        poll.assert_awaited_once()
        assert mqtt.publish.called
        child.online = False


async def test_setting_commands_publish_switch_availability_immediately():
    mode, duration, switch = _controls()
    switch._availability_topic = "available"
    switch.set_latest_state(0)
    mqtt = MagicMock()
    await mode._write_value(FakeCloudControlPort(), mqtt, 1, "test", MagicMock())
    assert mqtt.publish.call_args.args == ("available", "0")
    await duration._write_value(FakeCloudControlPort(), mqtt, 1, "test", MagicMock())
    assert mqtt.publish.call_args.args == ("available", "1")


def test_empty_cloud_child_is_kept_for_recovery():
    from sigenergy2mqtt.devices.cloud import CloudControl, CloudDiscovery

    control = CloudControl(0, FakeCloudControlPort(), CloudDiscovery(
        device_list=[{"deviceType": "Battery", "serialNumber": "battery"}],
        device_info={"battery": ({}, {})},
    ))
    assert len(control.children) == 1
    assert control.children[0]._pending_info == {False, True}
    scheduled = control.schedule(FakeCloudControlPort(), MagicMock())
    assert any(task.cr_code.co_name == "recover_info" for task in scheduled)
    for task in scheduled:
        task.close()


@pytest.mark.parametrize("home_assistant", [False, True])
async def test_recovered_sensor_debug_subscription_works(monkeypatch, home_assistant):
    config = Config()
    config.home_assistant.enabled = home_assistant
    with _swap_active_config(config):
        child = CloudBattery(0, "station", {"serialNumber": "battery"}, {}, {"paramInfoVOList": []})
        child.online = asyncio.get_running_loop().create_future()
        mqtt, handler = MagicMock(), MagicMock()
        child.subscribe(mqtt, handler)
        handler.register.reset_mock()
        port = FakeCloudControlPort()
        port.device_dynamic_info.return_value = {"realTimeInfo": [{"paramKey": "SOC", "paramValueUnit": "%", "paramValueText": "50"}]}
        monkeypatch.setattr("sigenergy2mqtt.devices.cloud.sigen_device.SensorGroupPoller.run", AsyncMock())
        await child.recover_info(port, mqtt)
        sensor = next(iter(child.sensors.values()))
        topic = f"{sensor._get_base_topic(child.unique_id)}/debug"
        handler.register.assert_called_once_with(mqtt, topic, sensor.set_debug_logging)
        callback = handler.register.call_args.args[2]
        await callback(port, mqtt, "true", topic, handler)
        assert sensor.debug_logging
        child.online = False
