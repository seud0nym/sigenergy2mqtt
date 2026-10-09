"""Cloud sensor behavior and Instant Manual Control device wiring."""

from datetime import timedelta
import logging
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientPayloadError, ServerDisconnectedError

from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.cloud.models import (
    Capabilities,
    InstantControlStatus,
)
from sigenergy2mqtt.cloud.models import InstantControlMode as DomainMode
from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices.base.poller import SensorGroupPoller
from sigenergy2mqtt.devices.cloud import CloudControl, CloudDiscovery
from sigenergy2mqtt.mqtt.client import MqttClient
from sigenergy2mqtt.mqtt.handler import MqttHandler
from sigenergy2mqtt.sensors.base import CloudReadWriteSensor, DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.functions import _identity
from sigenergy2mqtt.sensors.cloud.read_write import (
    BatteryChargePowerLimit,
    BatteryDischargePowerLimit,
    GridConnectionLimit,
    GridExportLimit,
    GridImportLimit,
    InstantControlDuration,
    InstantControlMode,
    InstantControlSwitch,
    OperationalMode,
    SolarPowerLimit,
)


class FakeCloudControlPort:
    model = "Test Cloud"
    station_id = "station-123"
    capabilities = Capabilities(
        features=frozenset(),
        min_duration=timedelta(minutes=1),
        max_duration=timedelta(minutes=1440),
    )
    gateway_info = AsyncMock()

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.command = None
        self.clear_instant_override = AsyncMock(side_effect=self._clear)
        self.device_list = AsyncMock()
        self.device_dynamic_info = AsyncMock()
        self.device_static_info = AsyncMock()
        self.available_operational_modes = AsyncMock()
        self.get_operational_mode = AsyncMock()
        self.set_operational_mode = AsyncMock()
        self.grid_export_limit = AsyncMock()
        self.set_grid_export_limit = AsyncMock()
        self.grid_import_limit = AsyncMock()
        self.set_grid_import_limit = AsyncMock()
        self.grid_connection_limit = AsyncMock()
        self.set_grid_connection_limit = AsyncMock()
        self.battery_power_limit = AsyncMock()
        self.set_battery_power_limit = AsyncMock()
        self.solar_power_limit = AsyncMock()
        self.set_solar_power_limit = AsyncMock()
        self.battery_export_limitation = AsyncMock()
        self.set_battery_export_limitation = AsyncMock()

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def set_instant_override(self, command) -> None:
        self.command = command
        self.enabled = True

    async def _clear(self) -> None:
        self.enabled = False

    async def instant_control_status(self) -> InstantControlStatus:
        return InstantControlStatus(self.enabled, None, None)


OPERATIONAL_MODES = {
    "defaultWorkingModes": [
        {"label": "Maximum Self-Powered", "value": "0"},
        {"label": "Sigen AI Mode", "value": "1"},
    ],
    "energyProfileItems": [{"name": "Weekend profile", "profileId": 42}],
}


def _controls() -> tuple[InstantControlMode, InstantControlDuration, InstantControlSwitch]:
    mode = InstantControlMode(0, FakeCloudControlPort.station_id)
    duration = InstantControlDuration(0, FakeCloudControlPort.station_id)
    switch = InstantControlSwitch(0, FakeCloudControlPort.station_id, mode, duration)
    return mode, duration, switch


def test_cloud_identity_uses_cloud_object_id_and_station_unique_id() -> None:
    config = Config()
    config.home_assistant.entity_id_prefix = "entity"
    config.home_assistant.unique_id_prefix = "unique"

    with _swap_active_config(config):
        assert _identity(2, "station-123", "solar_power") == (
            "entity_2_cloud_solar_power",
            "unique_2_station-123_solar_power",
        )


def test_cloud_control_device_registers_normal_mqtt_entities() -> None:
    device = CloudControl(
        0,
        FakeCloudControlPort(),
        CloudDiscovery(
            device_list=[{"deviceType": "Battery"}],
            operational_modes=OPERATIONAL_MODES,
        ),
    )
    sensors = list(device.sensors.values())

    assert [type(sensor) for sensor in sensors] == [  # must be in the same order as the device constructor adds them
        InstantControlSwitch,
        InstantControlMode,
        InstantControlDuration,
        OperationalMode,
        GridExportLimit,
        GridImportLimit,
        GridConnectionLimit,
        SolarPowerLimit,
        BatteryChargePowerLimit,
        BatteryDischargePowerLimit,
    ]
    assert sensors[0][DiscoveryKeys.PLATFORM] == "switch"
    assert sensors[1][DiscoveryKeys.PLATFORM] == "select"
    assert sensors[2][DiscoveryKeys.PLATFORM] == "number"
    assert sensors[3][DiscoveryKeys.PLATFORM] == "select"
    assert all(sensor[DiscoveryKeys.PLATFORM] == "number" for sensor in sensors[4:10])
    assert device.protocol_version is ProtocolVersion.N_A
    assert device.name == "Sigenergy Cloud"
    assert device["model"] == "Test Cloud"
    assert all(sensor.protocol_version is ProtocolVersion.N_A for sensor in sensors)


@pytest.mark.asyncio
async def test_operational_mode_discovers_reads_and_writes_station_modes() -> None:
    device = CloudControl(
        0,
        FakeCloudControlPort(),
        CloudDiscovery(device_list=[], operational_modes=OPERATIONAL_MODES),
    )
    sensor = next(item for item in device.sensors.values() if isinstance(item, OperationalMode))
    port = FakeCloudControlPort()
    port.available_operational_modes.return_value = OPERATIONAL_MODES
    port.get_operational_mode.return_value = (9, 42)

    assert sensor[DiscoveryKeys.OPTIONS] == [
        "Maximum Self-Powered",
        "Sigen AI Mode",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Weekend profile",
    ]
    assert await sensor._read_cloud_state(port) == 9
    assert sensor.sanity_check.max_raw == 9
    port.available_operational_modes.assert_awaited_once_with()
    assert await sensor._write_cloud_value(port, 1) is True
    assert await sensor._write_cloud_value(port, 9) is True
    assert [item.args for item in port.set_operational_mode.await_args_list] == [
        (1, -1),
        (9, 42),
    ]


@pytest.mark.asyncio
async def test_operational_mode_rejects_unknown_cloud_and_command_modes() -> None:
    sensor = OperationalMode(
        0,
        FakeCloudControlPort.station_id,
        {
            "defaultWorkingModes": [{"label": "Self Consumption", "value": "2"}],
            "energyProfileItems": [],
        },
    )
    port = FakeCloudControlPort()
    port.available_operational_modes.return_value = {
        "defaultWorkingModes": [{"label": "Self Consumption", "value": "2"}],
        "energyProfileItems": [],
    }
    port.get_operational_mode.return_value = (99, -1)

    assert await sensor._read_cloud_state(port) is None
    assert await sensor._write_cloud_value(port, 4) is False
    port.set_operational_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_operational_mode_refreshes_options_and_disambiguates_duplicate_labels() -> None:
    device = CloudControl(
        0,
        FakeCloudControlPort(),
        CloudDiscovery(device_list=[], operational_modes=OPERATIONAL_MODES),
    )
    sensor = next(item for item in device.sensors.values() if isinstance(item, OperationalMode))
    port = FakeCloudControlPort()
    port.available_operational_modes.return_value = {
        "defaultWorkingModes": [{"label": "Shared", "value": "2"}],
        "energyProfileItems": [{"name": "Shared", "profileId": 7}],
    }
    port.get_operational_mode.return_value = (9, 7)
    device.rediscover = False

    assert await sensor._read_cloud_state(port) == 9
    assert sensor[DiscoveryKeys.OPTIONS] == ["", "", "Shared", "", "", "", "", "", "", "Shared (Profile 7)"]
    assert device.rediscover is True
    assert await sensor.set_value(port, MagicMock(spec=MqttClient), "Shared", sensor.command_topic, MagicMock(spec=MqttHandler)) is True
    port.set_operational_mode.assert_awaited_once_with(2, -1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options_response",
    [
        ["not", "an", "object"],
        CloudControlUnavailableError("options endpoint unavailable"),
    ],
)
async def test_operational_mode_reads_current_mode_when_option_refresh_fails(
    options_response,
) -> None:
    sensor = OperationalMode(0, FakeCloudControlPort.station_id, OPERATIONAL_MODES)
    port = FakeCloudControlPort()
    if isinstance(options_response, Exception):
        port.available_operational_modes.side_effect = options_response
    else:
        port.available_operational_modes.return_value = options_response
    port.get_operational_mode.return_value = (1, -1)

    assert await sensor._read_cloud_state(port) == 1
    port.get_operational_mode.assert_awaited_once_with()
    assert sensor[DiscoveryKeys.OPTIONS] == [
        "Maximum Self-Powered",
        "Sigen AI Mode",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Weekend profile",
    ]


@pytest.mark.asyncio
async def test_cloud_sensor_suppresses_repeated_outage_warnings(caplog: pytest.LogCaptureFixture) -> None:
    from sigenergy2mqtt.sensors.base.cloud import _port_outage, CloudSensor

    class TestSensor(CloudSensor):
        def __init__(self, uid_suffix="t1"):
            super().__init__(name="Test", unique_id=f"sigen_{uid_suffix}", object_id=f"sigen_{uid_suffix}", unit=None, device_class=None, state_class=None, icon=None, protocol_version=ProtocolVersion.N_A, scan_interval=60, gain=1.0, precision=2)

        async def _read_cloud_state(self, port):
            return await port.get_operational_mode()

    port = FakeCloudControlPort()
    sensor1 = TestSensor("t1")
    sensor2 = TestSensor("t2")
    
    # Ensure port outage state is clear before test
    _port_outage.clear()
    
    # 1. First failure for port -> logs WARNING
    port.get_operational_mode.side_effect = CloudControlUnavailableError("HTTP 503")
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        assert await sensor1._update_internal_state(modbus_client=port) is False
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 1
        assert len([r for r in caplog.records if r.levelname == "DEBUG"]) == 0

    # 2. Second failure for port (another sensor) -> logs DEBUG
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        assert await sensor2._update_internal_state(modbus_client=port) is False
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 0
        assert len([r for r in caplog.records if r.levelname == "DEBUG"]) == 1

    # 3. Third failure for port, but different error -> logs WARNING
    port.get_operational_mode.side_effect = CloudControlUnavailableError("HTTP 401")
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        assert await sensor1._update_internal_state(modbus_client=port) is False
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 1

    # 4. Success -> logs INFO for recovery
    port.get_operational_mode.side_effect = None
    port.get_operational_mode.return_value = 1
    with caplog.at_level(logging.INFO), patch.object(sensor1, "set_latest_state", return_value=True):
        caplog.clear()
        assert await sensor1._update_internal_state(modbus_client=port) is True
        assert len([r for r in caplog.records if r.levelname == "INFO" and "recovered" in r.message]) == 1

    # Ensure port outage state is clear after test
    _port_outage.clear()


def test_cloud_power_limit_sensors_expose_vendor_maximum() -> None:
    device = CloudControl(0, FakeCloudControlPort(), CloudDiscovery(device_list=[{"deviceType": "Battery"}]))
    power_limits = [
        sensor
        for sensor in device.sensors.values()
        if isinstance(
            sensor,
            (BatteryChargePowerLimit, BatteryDischargePowerLimit, SolarPowerLimit),
        )
    ]

    assert len(power_limits) == 3
    assert all(sensor[DiscoveryKeys.MAX] == 4_294_967.295 for sensor in power_limits)


def test_mode_and_duration_are_available_only_while_switch_is_off() -> None:
    config = Config()
    config.home_assistant.enabled = True
    with _swap_active_config(config):
        device = CloudControl(0, FakeCloudControlPort(), CloudDiscovery(device_list=[{"deviceType": "Battery"}]))
        sensors = list(device.sensors.values())
        switch = next(s for s in sensors if isinstance(s, InstantControlSwitch))
        mode = next(s for s in sensors if isinstance(s, InstantControlMode))
        duration = next(s for s in sensors if isinstance(s, InstantControlDuration))

        # Mode and duration no longer gate on the switch state - they're always visible
        assert DiscoveryKeys.AVAILABILITY not in mode or all(item.get("topic") != switch._availability_topic for item in cast(list, mode.get(DiscoveryKeys.AVAILABILITY, [])) if isinstance(item, dict))
        assert DiscoveryKeys.AVAILABILITY not in duration or all(item.get("topic") != switch._availability_topic for item in cast(list, duration.get(DiscoveryKeys.AVAILABILITY, [])) if isinstance(item, dict))
        # The switch itself has its own availability topic (to indicate mode/duration are ready)
        assert switch._availability_topic is not None
        availability = switch[DiscoveryKeys.AVAILABILITY]
        assert isinstance(availability, list)
        gate = next((item for item in availability if isinstance(item, dict) and item.get("topic") == switch._availability_topic), None)
        assert gate is not None
        assert gate[DiscoveryKeys.PAYLOAD_AVAILABLE] == 1
        assert gate[DiscoveryKeys.PAYLOAD_NOT_AVAILABLE] == 0


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
    await mode._write_cloud_value(port, 4)  # Self-Consumption"
    await duration._write_cloud_value(port, 90)

    assert await switch._write_cloud_value(port, 1) is True
    assert port.command is not None
    assert port.command.mode is DomainMode.SELF_CONSUMPTION
    assert port.command.duration == timedelta(minutes=90)


@pytest.mark.asyncio
async def test_switch_off_clears_override() -> None:
    _, _, switch = _controls()
    port = FakeCloudControlPort(enabled=True)

    assert await switch._write_cloud_value(port, 0) is True
    port.clear_instant_override.assert_awaited_once()


@pytest.mark.asyncio
async def test_selection_sensors_read_authoritative_cloud_values(monkeypatch) -> None:
    mode, duration, switch = _controls()
    port = FakeCloudControlPort()
    port.enabled = True
    port.instant_control_status = AsyncMock(return_value=InstantControlStatus(True, DomainMode.HOLD, 1_800_000_599))
    monkeypatch.setattr(
        "sigenergy2mqtt.sensors.cloud.read_write.time.time",
        lambda: 1_800_000_000,
    )

    SensorGroupPoller._begin_coordinated_refresh([switch, mode, duration])
    assert await switch._read_cloud_state(port) == 1
    assert await mode._read_cloud_state(port) == 3
    assert await duration._read_cloud_state(port) == 10
    port.instant_control_status.assert_awaited_once()

    SensorGroupPoller._begin_coordinated_refresh([switch, mode, duration])
    assert await switch._read_cloud_state(port) == 1
    assert port.instant_control_status.await_count == 2


@pytest.mark.asyncio
async def test_forced_selector_refresh_cannot_leak_into_next_group_poll() -> None:
    mode, duration, switch = _controls()
    port = FakeCloudControlPort(enabled=True)
    port.instant_control_status = AsyncMock(
        side_effect=[
            InstantControlStatus(True, DomainMode.CHARGE, 1_800_000_600),
            InstantControlStatus(True, DomainMode.DISCHARGE, 1_800_000_600),
        ]
    )

    # A forced selector-only polling batch gets its own snapshot.
    SensorGroupPoller._begin_coordinated_refresh([mode])
    assert await mode._read_cloud_state(port) == 1

    # The next regular batch is explicitly invalidated before any sensor reads.
    SensorGroupPoller._begin_coordinated_refresh([switch, mode, duration])
    assert await switch._read_cloud_state(port) == 1
    assert await mode._read_cloud_state(port) == 2
    assert port.instant_control_status.await_count == 2


@pytest.mark.asyncio
async def test_selection_sensors_keep_pending_values_separate_from_cloud_state() -> None:
    mode, duration, switch = _controls()
    port = FakeCloudControlPort(enabled=True)

    await mode._write_cloud_value(port, 1)
    await duration._write_cloud_value(port, 45)
    port.instant_control_status = AsyncMock(return_value=InstantControlStatus(True, DomainMode.HOLD, None))

    assert await mode._read_cloud_state(port) == 1
    assert await duration._read_cloud_state(port) == 45
    assert await switch._write_cloud_value(port, 1) is True
    assert port.command is not None
    assert port.command.mode is DomainMode.CHARGE
    assert port.command.duration == timedelta(minutes=45)


@pytest.mark.asyncio
async def test_selection_sensors_have_no_arbitrary_initial_values() -> None:
    mode, duration, switch = _controls()
    port = FakeCloudControlPort()

    assert mode.latest_raw_state is None
    assert duration.latest_raw_state is None
    assert await mode._read_cloud_state(port) == 0
    assert await duration._read_cloud_state(port) == 0
    assert await switch._write_cloud_value(port, 1) is False


@pytest.mark.asyncio
async def test_cloud_sensor_requires_transport_keyword_and_ignores_missing_port() -> None:
    mode, _, _ = _controls()

    with pytest.raises(ValueError, match="modbus_client"):
        await mode._update_internal_state()
    assert await mode._update_internal_state(modbus_client=None) is False


@pytest.mark.asyncio
async def test_cloud_sensor_handles_failed_and_unknown_reads(caplog) -> None:
    _, _, switch = _controls()
    port = FakeCloudControlPort()
    switch._read_cloud_state = AsyncMock(  # type: ignore[method-assign]
        side_effect=CloudControlUnavailableError("offline")
    )

    assert await switch._update_internal_state(modbus_client=port) is False
    assert "cloud read failed" in caplog.text

    switch._read_cloud_state = AsyncMock(  # type: ignore[method-assign]
        side_effect=ClientPayloadError("truncated response")
    )
    assert await switch._update_internal_state(modbus_client=port) is False

    switch._read_cloud_state = AsyncMock(return_value=None)  # type: ignore[method-assign]
    assert await switch._update_internal_state(modbus_client=port) is False


def test_cloud_sensor_validates_availability_gate() -> None:
    mode, _, switch = _controls()

    with pytest.raises(TypeError, match="AvailabilityMixin"):
        mode.set_availability_control_sensor(object())  # type: ignore[arg-type]

    config = Config()
    config.home_assistant.enabled = True
    with _swap_active_config(config):
        mode.set_availability_control_sensor(switch)
        with pytest.raises(RuntimeError, match="topic is not configured"):
            mode.configure_mqtt_topics("cloud-device")


def test_cloud_sensor_constructor_rejects_invalid_availability_gate() -> None:
    uninitialized_mode = InstantControlMode.__new__(InstantControlMode)
    with pytest.raises(TypeError, match="AvailabilityMixin"):
        CloudReadWriteSensor.__init__(
            uninitialized_mode,
            availability_control_sensor=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_cloud_write_handles_missing_transport_and_domain_error(caplog) -> None:
    mode, _, _ = _controls()

    assert await mode._write_value(None, AsyncMock(), 1, "source", AsyncMock()) is False
    mode._write_cloud_value = AsyncMock(  # type: ignore[method-assign]
        side_effect=CloudControlUnavailableError("offline")
    )
    assert await mode._write_value(FakeCloudControlPort(), AsyncMock(), 1, "source", AsyncMock()) is False
    assert "cloud write failed" in caplog.text

    mode._write_cloud_value = AsyncMock(  # type: ignore[method-assign]
        side_effect=ServerDisconnectedError()
    )
    assert await mode._write_value(FakeCloudControlPort(), AsyncMock(), 1, "source", AsyncMock()) is False


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
async def test_grid_limit_reads_installer_maximum_and_writes_owner_value(sensor_type, read_method, write_method, payload, maximum) -> None:
    sensor = sensor_type(0, FakeCloudControlPort.station_id)
    port = AsyncMock()
    getattr(port, read_method).return_value = payload

    assert await sensor._read_cloud_state(port) == payload
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
    sensor = GridExportLimit(0, FakeCloudControlPort.station_id)
    port = AsyncMock()
    port.grid_export_limit.return_value = payload

    state = await sensor._read_cloud_state(port)
    if payload["enable"] and payload["maxLimitation"]:
        assert state == payload
    else:
        assert state == payload
    is_writable = bool(payload.get("maxLimitationInstaller"))
    assert await sensor._write_cloud_value(port, 4.0) is is_writable
    if is_writable:
        port.set_grid_export_limit.assert_awaited_once_with(4.0, enabled=True)
    else:
        port.set_grid_export_limit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("enable", [None, "false", 0, 1])
async def test_grid_limit_invalid_enable_status_disallows_updates(enable) -> None:
    sensor = GridExportLimit(0, FakeCloudControlPort.station_id)
    port = AsyncMock()
    port.grid_export_limit.return_value = {
        "enable": enable,
        "maxLimitation": "5.000",
        "maxLimitationInstaller": "10.000",
    }

    assert await sensor._read_cloud_state(port) == port.grid_export_limit.return_value
    assert await sensor._write_cloud_value(port, 4.0) is False
    port.set_grid_export_limit.assert_not_awaited()


@pytest.mark.asyncio
async def test_battery_power_limits_share_read_and_preserve_other_limit_on_write() -> None:
    device = CloudControl(0, FakeCloudControlPort(), CloudDiscovery(device_list=[{"deviceType": "Battery"}]))
    charge = next(sensor for sensor in device.sensors.values() if isinstance(sensor, BatteryChargePowerLimit))
    discharge = next(sensor for sensor in device.sensors.values() if isinstance(sensor, BatteryDischargePowerLimit))
    port = FakeCloudControlPort()
    port.battery_power_limit.side_effect = [
        {
            "batteryMaxChargingPower": "4.500",
            "batteryMaxDischargingPower": "6.250",
        },
        {
            "batteryMaxChargingPower": "4.500",
            "batteryMaxDischargingPower": "7.750",
        },
    ]

    SensorGroupPoller._begin_coordinated_refresh([charge, discharge])
    assert await charge._read_cloud_state(port) == 4.5
    port.battery_power_limit.assert_awaited_once()

    # A command between the two sensor reads fetches the current limits for its
    # replacement write, but must not invalidate the polling batch's snapshot.
    assert await charge._write_cloud_value(port, 3) is True
    assert await discharge._read_cloud_state(port) == 6.25
    assert port.battery_power_limit.await_count == 2
    port.set_battery_power_limit.assert_awaited_once_with(
        max_charge_kw=3.0,
        max_discharge_kw=7.75,
    )


@pytest.mark.asyncio
async def test_battery_power_limit_preserves_unlimited_sentinel_as_none() -> None:
    charge = BatteryChargePowerLimit(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.battery_power_limit.return_value = {
        "batteryMaxChargingPower": "4294967.295",
        "batteryMaxDischargingPower": "6.000",
    }

    assert await charge._read_cloud_state(port) == 4294967.295
    assert await charge._write_cloud_value(port, 2) is True
    port.set_battery_power_limit.assert_awaited_once_with(
        max_charge_kw=2.0,
        max_discharge_kw=6.0,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sensor", "read_payload", "expected_call"),
    [
        (
            BatteryChargePowerLimit(0, FakeCloudControlPort.station_id),
            {
                "batteryMaxChargingPower": "4.000",
                "batteryMaxDischargingPower": "6.000",
            },
            ("battery", {"max_charge_kw": 3.5, "max_discharge_kw": 6.0}),
        ),
        (
            SolarPowerLimit(0, FakeCloudControlPort.station_id),
            None,
            ("solar", 3.5),
        ),
    ],
)
async def test_power_limit_mqtt_command_reaches_cloud(sensor, read_payload, expected_call) -> None:
    port = FakeCloudControlPort()
    if read_payload is not None:
        port.battery_power_limit.return_value = read_payload
    sensor.configure_mqtt_topics("cloud-device")

    assert (
        await sensor.set_value(
            port,
            AsyncMock(),
            "3.5",
            sensor.command_topic,
            AsyncMock(),
        )
        is True
    )
    assert sensor.gain == 1
    if expected_call[0] == "battery":
        port.set_battery_power_limit.assert_awaited_once_with(**expected_call[1])
    else:
        port.set_solar_power_limit.assert_awaited_once_with(expected_call[1])


@pytest.mark.asyncio
async def test_solar_power_limit_reads_and_writes() -> None:
    sensor = SolarPowerLimit(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.solar_power_limit.return_value = {"powerLimit": "8.125"}

    assert await sensor._read_cloud_state(port) == 8.125
    assert await sensor._write_cloud_value(port, 7.5) is True
    port.set_solar_power_limit.assert_awaited_once_with(7.5)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, [], {"powerLimit": "invalid"}])
async def test_solar_power_limit_malformed_payload_is_unavailable(payload) -> None:
    sensor = SolarPowerLimit(0, FakeCloudControlPort.station_id)
    port = FakeCloudControlPort()
    port.solar_power_limit.return_value = payload

    assert await sensor._read_cloud_state(port) is None


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
    sensor = GridExportLimit(0, FakeCloudControlPort.station_id)
    port = AsyncMock()
    port.grid_export_limit.return_value = payload

    if isinstance(payload, dict):
        assert await sensor._update_internal_state(modbus_client=port) is True
        assert sensor.latest_raw_state == payload
    else:
        assert await sensor._update_internal_state(modbus_client=port) is False
        assert sensor.latest_raw_state is None
    assert await sensor._write_cloud_value(port, 1) is False


@pytest.mark.asyncio
async def test_grid_limit_maximum_changes_request_discovery_republish() -> None:
    device = CloudControl(0, FakeCloudControlPort(), CloudDiscovery(device_list=[]))
    sensor = next(item for item in device.sensors.values() if isinstance(item, GridExportLimit))
    port = AsyncMock()
    port.grid_export_limit.return_value = {
        "enable": True,
        "maxLimitation": "5",
        "maxLimitationInstaller": "10",
    }

    state = await sensor._read_cloud_state(port)
    assert state is not None and state.get("maxLimitation") == "5"
    assert sensor[DiscoveryKeys.MAX] == 10.0
    assert sensor.sanity_check.min_raw == 0.0
    assert device.rediscover is True

    device.rediscover = False
    port.grid_export_limit.return_value["maxLimitationInstaller"] = ""
    state = await sensor._read_cloud_state(port)
    assert state is not None and state.get("maxLimitation") == "5"
    assert DiscoveryKeys.MAX not in sensor
    assert sensor.sanity_check.min_raw == 0.0
    assert sensor.sanity_check.max_raw == 0.0
    assert device.rediscover is True
