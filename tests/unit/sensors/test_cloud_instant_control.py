"""Cloud sensor behavior and Instant Manual Control device wiring."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.exceptions import BatteryControlUnavailableError
from sigenergy2mqtt.cloud.models import (
    Capabilities,
    InstantControlStatus,
)
from sigenergy2mqtt.cloud.models import InstantControlMode as DomainMode
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.plant.cloud_control import SigenergyCloudControl
from sigenergy2mqtt.sensors.base import CloudReadWriteSensor, DiscoveryKeys
from sigenergy2mqtt.sensors.plant_cloud_control import (
    BatteryExportLimitation,
    GridConnectionLimit,
    GridExportLimit,
    GridImportLimit,
    INSTANT_CONTROL_OPTIONS,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
)


class FakeCloudControlPort:
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


def _controls() -> tuple[
    InstantControlMode, InstantControlDuration, InstantControlSwitch
]:
    mode = InstantControlMode(0)
    duration = InstantControlDuration(0)
    switch = InstantControlSwitch(0, mode, duration)
    return mode, duration, switch


def test_cloud_control_device_registers_normal_mqtt_entities() -> None:
    device = SigenergyCloudControl(0)
    sensors = list(device.sensors.values())

    assert [type(sensor) for sensor in sensors] == [
        InstantControlSwitch,
        InstantControlMode,
        InstantControlDuration,
        GridExportLimit,
        GridImportLimit,
        GridConnectionLimit,
        BatteryExportLimitation,
    ]
    assert sensors[0][DiscoveryKeys.PLATFORM] == "switch"
    assert sensors[1][DiscoveryKeys.PLATFORM] == "select"
    assert sensors[2][DiscoveryKeys.PLATFORM] == "number"
    assert all(sensor[DiscoveryKeys.PLATFORM] == "number" for sensor in sensors[3:6])
    assert sensors[6][DiscoveryKeys.PLATFORM] == "switch"
    assert device.protocol_version is ProtocolVersion.N_A
    assert all(sensor.protocol_version is ProtocolVersion.N_A for sensor in sensors)


def test_mode_and_duration_are_available_only_while_switch_is_off() -> None:
    config = Config()
    config.home_assistant.enabled = True
    with _swap_active_config(config):
        device = SigenergyCloudControl(0)
        switch, mode, duration = list(device.sensors.values())[:3]

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
    port = FakeCloudControlPort(enabled=True)

    changed = await switch._update_internal_state(modbus_client=port)

    assert changed is True
    assert switch.latest_raw_state == 1


@pytest.mark.asyncio
async def test_switch_submits_current_mode_and_duration() -> None:
    mode, duration, switch = _controls()
    port = FakeCloudControlPort()
    mode.set_latest_state(INSTANT_CONTROL_OPTIONS.index("Self-Consumption"))
    duration.set_latest_state(90)

    assert await switch._write_cloud_value(port, 1) is True
    assert port.command.mode is DomainMode.SELF_CONSUMPTION
    assert port.command.duration == timedelta(minutes=90)


@pytest.mark.asyncio
async def test_switch_off_clears_override() -> None:
    _, _, switch = _controls()
    port = FakeCloudControlPort(enabled=True)

    assert await switch._write_cloud_value(port, 0) is True
    port.clear_instant_override.assert_awaited_once()


@pytest.mark.asyncio
async def test_selection_sensors_retain_next_values_without_cloud_reads() -> None:
    mode, duration, _ = _controls()
    port = FakeCloudControlPort()
    mode.set_latest_state(2)
    duration.set_latest_state(1440)

    assert await mode._read_cloud_state(port) == 2
    assert await duration._read_cloud_state(port) == 1440


@pytest.mark.asyncio
async def test_cloud_sensor_requires_transport_keyword_and_ignores_missing_port() -> (
    None
):
    mode, _, _ = _controls()

    with pytest.raises(ValueError, match="modbus_client"):
        await mode._update_internal_state()
    assert await mode._update_internal_state(modbus_client=None) is False


@pytest.mark.asyncio
async def test_cloud_sensor_handles_failed_and_unknown_reads(caplog) -> None:
    _, _, switch = _controls()
    port = FakeCloudControlPort()
    switch._read_cloud_state = AsyncMock(  # type: ignore[method-assign]
        side_effect=BatteryControlUnavailableError("offline")
    )

    assert await switch._update_internal_state(modbus_client=port) is False
    assert "cloud read failed" in caplog.text

    switch._read_cloud_state = AsyncMock(return_value=None)  # type: ignore[method-assign]
    assert await switch._update_internal_state(modbus_client=port) is False


def test_cloud_sensor_validates_availability_gate() -> None:
    mode, _, switch = _controls()

    with pytest.raises(ValueError, match="AvailabilityMixin"):
        mode.set_availability_control_sensor(object())  # type: ignore[arg-type]

    config = Config()
    config.home_assistant.enabled = True
    with _swap_active_config(config):
        mode.set_availability_control_sensor(switch)
        with pytest.raises(RuntimeError, match="topic is not configured"):
            mode.configure_mqtt_topics("cloud-device")


def test_cloud_sensor_constructor_rejects_invalid_availability_gate() -> None:
    uninitialized_mode = InstantControlMode.__new__(InstantControlMode)
    with pytest.raises(ValueError, match="AvailabilityMixin"):
        CloudReadWriteSensor.__init__(
            uninitialized_mode,
            availability_control_sensor=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_cloud_write_handles_missing_transport_and_domain_error(caplog) -> None:
    mode, _, _ = _controls()

    assert await mode._write_value(None, AsyncMock(), 1, "source", AsyncMock()) is False
    mode._write_cloud_value = AsyncMock(  # type: ignore[method-assign]
        side_effect=BatteryControlUnavailableError("offline")
    )
    assert (
        await mode._write_value(
            FakeCloudControlPort(), AsyncMock(), 1, "source", AsyncMock()
        )
        is False
    )
    assert "cloud write failed" in caplog.text


@pytest.mark.asyncio
async def test_cloud_write_delegates_successfully() -> None:
    mode, _, _ = _controls()
    mode._write_cloud_value = AsyncMock(return_value=True)  # type: ignore[method-assign]
    port = FakeCloudControlPort()

    assert await mode._write_value(port, AsyncMock(), 2, "source", AsyncMock()) is True
    mode._write_cloud_value.assert_awaited_once_with(port, 2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor_type", "read_method", "write_method", "payload", "maximum"),
    [
        (
            GridExportLimit,
            "grid_export_limit",
            "set_grid_export_limit",
            {
                "enable": True,
                "maxLimitation": "7.500",
                "maxLimitationOwner": "7.500",
                "maxLimitationInstaller": "10.000",
            },
            10.0,
        ),
        (
            GridImportLimit,
            "grid_import_limit",
            "set_grid_import_limit",
            {
                "enable": True,
                "maxLimitation": "8.500",
                "maxLimitationOwner": "8.500",
                "maxLimitationInstaller": "12.000",
            },
            12.0,
        ),
        (
            GridConnectionLimit,
            "grid_connection_limit",
            "set_grid_connection_limit",
            {
                "enable": True,
                "currentLimitation": "32.0",
                "ownerSetLimitation": "32.0",
                "installerSetLimitation": "63.0",
            },
            63.0,
        ),
    ],
)
async def test_grid_limit_reads_installer_maximum_and_writes_owner_value(
    sensor_type, read_method, write_method, payload, maximum
) -> None:
    sensor = sensor_type(0)
    port = AsyncMock()
    getattr(port, read_method).return_value = payload

    assert await sensor._read_cloud_state(port) == float(
        payload.get("maxLimitation", payload.get("currentLimitation"))
    )
    assert sensor[DiscoveryKeys.MIN] == 0.0
    assert sensor[DiscoveryKeys.MAX] == maximum
    assert await sensor._write_cloud_value(port, maximum / 2) is True
    getattr(port, write_method).assert_awaited_once_with(maximum / 2, enabled=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {
            "enable": False,
            "maxLimitation": "5.000",
            "maxLimitationInstaller": "10.000",
        },
        {
            "enable": True,
            "maxLimitation": "",
            "maxLimitationInstaller": "10.000",
        },
        {
            "enable": True,
            "maxLimitation": "5.000",
            "maxLimitationInstaller": "",
        },
    ],
)
async def test_grid_limit_empty_states_and_disallowed_updates(payload) -> None:
    sensor = GridExportLimit(0)
    port = AsyncMock()
    port.grid_export_limit.return_value = payload

    state = await sensor._read_cloud_state(port)
    if payload["enable"] and payload["maxLimitation"]:
        assert state == 5.0
    else:
        assert state == "None"
    assert await sensor._write_cloud_value(port, 4.0) is (
        payload["enable"] and bool(payload["maxLimitationInstaller"])
    )


@pytest.mark.asyncio
async def test_battery_export_limitation_reads_current_state_and_writes_owner_state() -> (
    None
):
    sensor = BatteryExportLimitation(0)
    port = AsyncMock()
    port.battery_export_limitation.return_value = {
        "currentEnable": False,
        "ownerSetEnable": None,
        "installerSetEnable": None,
        "nearModify": None,
    }

    assert await sensor._read_cloud_state(port) == 0
    assert await sensor._write_cloud_value(port, 1) is True
    port.set_battery_export_limitation.assert_awaited_once_with(True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"enable": True, "maxLimitation": "invalid", "maxLimitationInstaller": "10"},
        {"enable": True, "maxLimitation": "5", "maxLimitationInstaller": object()},
        {"enable": True, "maxLimitation": "nan", "maxLimitationInstaller": "10"},
        [],
    ],
)
async def test_grid_limit_malformed_payload_publishes_unavailable_without_raising(
    payload,
) -> None:
    sensor = GridExportLimit(0)
    port = AsyncMock()
    port.grid_export_limit.return_value = payload

    assert await sensor._update_internal_state(modbus_client=port) is True
    assert sensor.latest_raw_state == "None"
    assert await sensor._write_cloud_value(port, 1) is False


@pytest.mark.asyncio
async def test_grid_limit_maximum_changes_request_discovery_republish() -> None:
    device = SigenergyCloudControl(0)
    sensor = next(
        item for item in device.sensors.values() if isinstance(item, GridExportLimit)
    )
    port = AsyncMock()
    port.grid_export_limit.return_value = {
        "enable": True,
        "maxLimitation": "5",
        "maxLimitationInstaller": "10",
    }

    assert await sensor._read_cloud_state(port) == 5.0
    assert sensor[DiscoveryKeys.MAX] == 10.0
    assert device.rediscover is True

    device.rediscover = False
    port.grid_export_limit.return_value["maxLimitationInstaller"] = ""
    assert await sensor._read_cloud_state(port) == 5.0
    assert DiscoveryKeys.MAX not in sensor
    assert sensor.sanity_check.max_raw is None
    assert device.rediscover is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{}, {"currentEnable": None}, {"currentEnable": "false"}, []],
)
async def test_battery_export_malformed_payload_publishes_unavailable(payload) -> None:
    sensor = BatteryExportLimitation(0)
    port = AsyncMock()
    port.battery_export_limitation.return_value = payload

    assert await sensor._update_internal_state(modbus_client=port) is True
    assert sensor.latest_raw_state == "None"
