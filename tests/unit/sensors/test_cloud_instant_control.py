"""Cloud sensor behavior and Instant Manual Control device wiring."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.models import (
    Capabilities,
    InstantControlStatus,
)
from sigenergy2mqtt.cloud.models import InstantControlMode as DomainMode
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.plant.cloud_control import SigenergyCloudControl
from sigenergy2mqtt.sensors.base import DiscoveryKeys
from sigenergy2mqtt.sensors.plant_cloud_control import (
    INSTANT_CONTROL_OPTIONS,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
)


class FakeBatteryControlPort:
    capabilities = Capabilities(
        features=frozenset(),
        min_duration=timedelta(minutes=1),
        max_duration=timedelta(minutes=1440),
    )

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.command = None
        self.clear_instant_override = AsyncMock(side_effect=self._clear)

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def set_instant_override(self, command) -> None:
        self.command = command
        self.enabled = True

    async def _clear(self) -> None:
        self.enabled = False

    async def instant_control_status(self) -> InstantControlStatus:
        return InstantControlStatus(self.enabled, None, None)

    async def current_strategy_label(self) -> str | None:
        return "TOU"


def _controls() -> tuple[
    InstantControlMode, InstantControlDuration, InstantControlSwitch
]:
    mode = InstantControlMode(0)
    duration = InstantControlDuration(0)
    switch = InstantControlSwitch(0, mode, duration)
    return mode, duration, switch


def test_cloud_control_device_registers_three_normal_mqtt_entities() -> None:
    device = SigenergyCloudControl(0)
    sensors = list(device.sensors.values())

    assert [type(sensor) for sensor in sensors] == [
        InstantControlSwitch,
        InstantControlMode,
        InstantControlDuration,
    ]
    assert sensors[0][DiscoveryKeys.PLATFORM] == "switch"
    assert sensors[1][DiscoveryKeys.PLATFORM] == "select"
    assert sensors[2][DiscoveryKeys.PLATFORM] == "number"


def test_mode_and_duration_are_available_only_while_switch_is_off() -> None:
    config = Config()
    config.home_assistant.enabled = True
    with _swap_active_config(config):
        device = SigenergyCloudControl(0)
        switch, mode, duration = list(device.sensors.values())

        for selector in (mode, duration):
            availability = selector[DiscoveryKeys.AVAILABILITY]
            gate = next(
                item for item in availability if item["topic"] == switch.state_topic
            )
            assert gate["payload_available"] == 0
            assert gate["payload_not_available"] == 1


@pytest.mark.asyncio
async def test_switch_reads_authoritative_cloud_state() -> None:
    _, _, switch = _controls()
    port = FakeBatteryControlPort(enabled=True)

    changed = await switch._update_internal_state(modbus_client=port)

    assert changed is True
    assert switch.latest_raw_state == 1


@pytest.mark.asyncio
async def test_switch_submits_current_mode_and_duration() -> None:
    mode, duration, switch = _controls()
    port = FakeBatteryControlPort()
    mode.set_latest_state(INSTANT_CONTROL_OPTIONS.index("Self-Consumption"))
    duration.set_latest_state(90)

    assert await switch._write_cloud_value(port, 1) is True
    assert port.command.mode is DomainMode.SELF_CONSUMPTION
    assert port.command.duration == timedelta(minutes=90)


@pytest.mark.asyncio
async def test_switch_off_clears_override() -> None:
    _, _, switch = _controls()
    port = FakeBatteryControlPort(enabled=True)

    assert await switch._write_cloud_value(port, 0) is True
    port.clear_instant_override.assert_awaited_once()


@pytest.mark.asyncio
async def test_selection_sensors_retain_next_values_without_cloud_reads() -> None:
    mode, duration, _ = _controls()
    port = FakeBatteryControlPort()
    mode.set_latest_state(2)
    duration.set_latest_state(1440)

    assert await mode._read_cloud_state(port) == 2
    assert await duration._read_cloud_state(port) == 1440
