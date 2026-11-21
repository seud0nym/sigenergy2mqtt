"""Cloud DC charger sensors, device wiring and discovery."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.devices.cloud import (
    CloudControl,
    CloudDcCharger,
    CloudDiscovery,
    DcChargerDiscovery,
    discover_dc_chargers,
)
from sigenergy2mqtt.sensors.base import DiscoveryKeys
from sigenergy2mqtt.sensors.cloud.dc_charger import (
    CloudResponseSnapshot,
    DcChargerBatteryBoost,
    DcChargerBatteryBoostCutoffSoc,
    DcChargerChargingMode,
    DcChargerLifetimeChargedEnergy,
    DcChargerMonthlyChargedEnergy,
    DcChargerOcppLinkStatus,
    DcChargerOcppServerUrl,
    DcChargerPrimaryVehicle,
    DcChargerPrimaryVehicleBatteryCapacity,
    DcChargerStatusCode,
    DcChargerSurplusPvPriority,
    DcChargerV2xDischargeCutoffSoc,
    DcChargerV2xDischargeEnabled,
    DcChargerV2xDischargePowerLimit,
    DcChargerWeeklyChargedEnergy,
    charge_mode_label,
)
from tests.unit.sensors.test_cloud_sensors import FakeCloudControlPort

STATION = FakeCloudControlPort.station_id
SN = "DC-1"
CHARGE_MODE = {
    "chargeMode": 1,
    "enableFromPack": False,
    "cutoffSocFromPack": 5.0,
    "allowsDischargePower": 12.5,
    "vehicleDischargeCutoffSoc": 20,
    "minimumDischargeCutoffSoc": 20,
    "maximumDischargeCutoffSoc": 99,
}


def _profile(dc_priority: int, battery_priority: int) -> dict:
    return {
        "pvPriority": [
            {"loadsType": 4, "sgDeviceType": None, "priority": 5},
            {"loadsType": 1, "sgDeviceType": 5, "priority": dc_priority},
            {"loadsType": 1, "sgDeviceType": 4, "priority": battery_priority},
        ]
    }


def _port() -> SimpleNamespace:
    return SimpleNamespace(
        dc_charge_mode=AsyncMock(return_value=dict(CHARGE_MODE)),
        set_dc_charge_mode=AsyncMock(return_value={"code": 0}),
        energy_profile_setting=AsyncMock(return_value=_profile(2, 1)),
        set_surplus_pv_priority=AsyncMock(return_value={"code": 0}),
        dc_status=AsyncMock(return_value=0),
        dc_energy_totals=AsyncMock(return_value={"monthlyEnergy": 128.24, "weeklyEnergy": 41.63, "lifetimeEnergy": 781.68}),
        dc_ocpp_status=AsyncMock(return_value={"ocppLinkStatus": 0, "url": ""}),
        v2x_discharge_settings=AsyncMock(return_value={"dischargeEnable": 1}),
        dc_vehicles=AsyncMock(
            return_value=[
                {"brand": "zeekr", "model": "7x", "years": 2026, "batteryCapacity": 70.0, "primaryCar": 0},
                {"brand": "MG", "model": "MG4", "years": 2026, "batteryCapacity": 64.0, "primaryCar": 1},
            ]
        ),
        dc_charge_mode_supported=AsyncMock(return_value=True),
        dc_supported_charge_modes=AsyncMock(return_value=[0, 1, 3]),
        dc_charge_mode_soc_range=AsyncMock(return_value={"socUpperLimit": 100.0, "socLowerLimit": 0.0}),
    )


def _mode_sensors() -> tuple[CloudResponseSnapshot, DcChargerChargingMode, DcChargerBatteryBoost, DcChargerBatteryBoostCutoffSoc]:
    snapshot = CloudResponseSnapshot(lambda port: port.dc_charge_mode(SN))
    return (
        snapshot,
        DcChargerChargingMode(0, STATION, SN, 0, (0, 1, 3), snapshot),
        DcChargerBatteryBoost(0, STATION, SN, 0, snapshot),
        DcChargerBatteryBoostCutoffSoc(0, STATION, SN, 0, (0.0, 100.0), snapshot),
    )


def test_charge_mode_labels_match_app_and_fall_back_for_unknown_codes() -> None:
    assert [charge_mode_label(mode) for mode in (0, 1, 3, 7)] == ["Fast Charging", "PV Surplus Charging", "Sigen AI Mode", "Mode 7"]


async def test_mode_sensors_share_one_read_per_refresh() -> None:
    port = _port()
    snapshot, mode, boost, cutoff = _mode_sensors()

    assert mode[DiscoveryKeys.OPTIONS] == ["Fast Charging", "PV Surplus Charging", "Sigen AI Mode"]
    assert await mode._read_cloud_state(port) == 1
    assert await boost._read_cloud_state(port) == 0
    assert await cutoff._read_cloud_state(port) == 5.0
    port.dc_charge_mode.assert_awaited_once_with(SN)

    snapshot.begin_refresh()
    port.dc_charge_mode.return_value = dict(CHARGE_MODE, chargeMode=3, enableFromPack=True)
    assert await mode._read_cloud_state(port) == 2
    assert await boost._read_cloud_state(port) == 1
    assert port.dc_charge_mode.await_count == 2


async def test_mode_sensors_share_a_failed_read() -> None:
    port = _port()
    _, mode, boost, _ = _mode_sensors()
    port.dc_charge_mode.side_effect = CloudControlUnavailableError("down")
    with pytest.raises(CloudControlUnavailableError):
        await mode._read_cloud_state(port)
    with pytest.raises(CloudControlUnavailableError):
        await boost._read_cloud_state(port)
    port.dc_charge_mode.assert_awaited_once()


@pytest.mark.parametrize(
    ("sensor_index", "value", "expected"),
    [
        (1, 0, (0, True, 30)),  # Charging Mode: index 0 is Fast Charging
        (2, 0, (1, False, 30)),  # Battery Boost off
        (3, 12, (1, True, 12)),  # Cut-off SOC
    ],
)
async def test_mode_writes_send_all_fields_from_a_fresh_read(sensor_index, value, expected) -> None:
    port = _port()
    sensors = _mode_sensors()
    # The polling snapshot is stale; the write must use a fresh read.
    port.dc_charge_mode.return_value = dict(CHARGE_MODE, enableFromPack=True, cutoffSocFromPack=30.0)

    assert await sensors[sensor_index]._write_cloud_value(port, value) is True

    mode, enabled, cutoff = expected
    port.set_dc_charge_mode.assert_awaited_once_with(mode, dc_sn=SN, enable_from_pack=enabled, cutoff_soc_from_pack=cutoff)


async def test_cutoff_write_keeps_fractional_values() -> None:
    port = _port()
    _, _, _, cutoff = _mode_sensors()
    await cutoff._write_cloud_value(port, 12.5)
    assert port.set_dc_charge_mode.await_args.kwargs["cutoff_soc_from_pack"] == 12.5


@pytest.mark.parametrize("payload", [None, [], {"chargeMode": 1}, dict(CHARGE_MODE, enableFromPack="yes"), dict(CHARGE_MODE, chargeMode=True)])
async def test_mode_write_refuses_incomplete_current_settings(payload) -> None:
    port = _port()
    _, _, boost, _ = _mode_sensors()
    port.dc_charge_mode.return_value = payload
    with pytest.raises(CloudControlUnavailableError):
        await boost._write_cloud_value(port, 1)
    port.set_dc_charge_mode.assert_not_awaited()


async def test_mode_sensors_handle_invalid_reads() -> None:
    port = _port()
    _, mode, boost, cutoff = _mode_sensors()
    port.dc_charge_mode.return_value = dict(CHARGE_MODE, chargeMode=2, enableFromPack=None, cutoffSocFromPack="n/a")
    assert await mode._read_cloud_state(port) is None
    with pytest.raises(CloudControlUnavailableError):
        await boost._read_cloud_state(port)
    with pytest.raises(CloudControlUnavailableError):
        await cutoff._read_cloud_state(port)
    assert await mode._write_cloud_value(port, 5) is False


async def test_mode_snapshot_rejects_non_object() -> None:
    port = _port()
    _, mode, _, _ = _mode_sensors()
    port.dc_charge_mode.return_value = "oops"
    with pytest.raises(CloudControlUnavailableError):
        await mode._read_cloud_state(port)


def test_charging_mode_requires_modes_and_cutoff_uses_soc_range() -> None:
    snapshot = CloudResponseSnapshot(lambda port: port.dc_charge_mode(SN))
    with pytest.raises(ValueError):
        DcChargerChargingMode(0, STATION, "DC-X", 0, (), snapshot)
    cutoff = DcChargerBatteryBoostCutoffSoc(0, STATION, "DC-Y", 0, (10.0, 90.0), snapshot)
    assert (cutoff[DiscoveryKeys.MIN], cutoff[DiscoveryKeys.MAX]) == (10.0, 90.0)


async def test_surplus_pv_priority_reads_and_writes() -> None:
    port = _port()
    sensor = DcChargerSurplusPvPriority(0, STATION, SN, 0, (4, 5))
    # Options have a fixed order, regardless of the current priority
    assert sensor[DiscoveryKeys.OPTIONS] == ["DC Charger First", "Battery First"]
    assert await sensor._read_cloud_state(port) == 0

    sensor._snapshot.begin_refresh()
    port.energy_profile_setting.return_value = _profile(1, 2)
    assert await sensor._read_cloud_state(port) == 1

    assert await sensor._write_cloud_value(port, 0) is True
    port.set_surplus_pv_priority.assert_awaited_once_with(5)
    assert await sensor._write_cloud_value(port, 4) is False

    sensor._snapshot.begin_refresh()
    port.energy_profile_setting.return_value = {"pvPriority": []}
    assert await sensor._read_cloud_state(port) is None


def test_surplus_pv_priority_needs_two_devices() -> None:
    with pytest.raises(ValueError):
        DcChargerSurplusPvPriority(0, STATION, "DC-Z", 0, (5, 5))


async def test_read_only_values() -> None:
    port = _port()
    mode_snapshot = CloudResponseSnapshot(lambda p: p.dc_charge_mode(SN))
    energy = CloudResponseSnapshot(lambda p: p.dc_energy_totals(SN))
    ocpp = CloudResponseSnapshot(lambda p: p.dc_ocpp_status(SN))
    vehicles = CloudResponseSnapshot(lambda p: p.dc_vehicles(SN))

    assert await DcChargerV2xDischargePowerLimit(0, STATION, SN, 0, mode_snapshot)._read_cloud_state(port) == 12.5
    assert await DcChargerV2xDischargeCutoffSoc(0, STATION, SN, 0, mode_snapshot)._read_cloud_state(port) == 20.0
    assert await DcChargerStatusCode(0, STATION, SN, 0)._read_cloud_state(port) == 0
    assert await DcChargerWeeklyChargedEnergy(0, STATION, SN, 0, energy)._read_cloud_state(port) == 41.63
    assert await DcChargerMonthlyChargedEnergy(0, STATION, SN, 0, energy)._read_cloud_state(port) == 128.24
    assert await DcChargerLifetimeChargedEnergy(0, STATION, SN, 0, energy)._read_cloud_state(port) == 781.68
    port.dc_energy_totals.assert_awaited_once_with(SN)
    assert await DcChargerOcppLinkStatus(0, STATION, SN, 0, ocpp)._read_cloud_state(port) == 0
    assert await DcChargerOcppServerUrl(0, STATION, SN, 0, ocpp)._read_cloud_state(port) == ""
    assert await DcChargerV2xDischargeEnabled(0, STATION, SN, 0)._read_cloud_state(port) == "On"
    assert await DcChargerPrimaryVehicle(0, STATION, SN, 0, vehicles)._read_cloud_state(port) == "MG MG4 (2026)"
    assert await DcChargerPrimaryVehicleBatteryCapacity(0, STATION, SN, 0, vehicles)._read_cloud_state(port) == 64.0


async def test_read_only_values_tolerate_missing_data() -> None:
    port = _port()
    port.dc_status.return_value = {"unexpected": True}
    port.dc_energy_totals.return_value = {"weeklyEnergy": None}
    port.v2x_discharge_settings.return_value = {"dischargeEnable": None}
    port.dc_ocpp_status.return_value = {"ocppLinkStatus": True}
    port.dc_vehicles.return_value = []
    vehicles = CloudResponseSnapshot(lambda p: p.dc_vehicles(SN))

    assert await DcChargerStatusCode(0, STATION, SN, 0)._read_cloud_state(port) is None
    assert await DcChargerWeeklyChargedEnergy(0, STATION, SN, 0, CloudResponseSnapshot(lambda p: p.dc_energy_totals(SN)))._read_cloud_state(port) is None
    assert await DcChargerV2xDischargeEnabled(0, STATION, SN, 0)._read_cloud_state(port) is None
    assert await DcChargerOcppLinkStatus(0, STATION, SN, 0, CloudResponseSnapshot(lambda p: p.dc_ocpp_status(SN)))._read_cloud_state(port) is None
    assert await DcChargerPrimaryVehicle(0, STATION, SN, 0, vehicles)._read_cloud_state(port) == "None"
    assert await DcChargerPrimaryVehicleBatteryCapacity(0, STATION, SN, 0, vehicles)._read_cloud_state(port) is None


def test_device_sensors_depend_on_discovered_capabilities() -> None:
    full = CloudDcCharger(0, STATION, DcChargerDiscovery("DC-A", (0, 1, 3), (0.0, 100.0), (5, 4)))
    assert full.get_sensor(DcChargerChargingMode) is not None
    assert full.get_sensor(DcChargerSurplusPvPriority) is not None
    assert full.unique_id.endswith("_dc_charger_DC-A")

    # No charging-mode support and no DC charger in the Surplus PV list
    minimal = CloudDcCharger(0, STATION, DcChargerDiscovery("DC-B", (), (0.0, 100.0), (4, 6)))
    assert minimal.get_sensor(DcChargerChargingMode) is None
    assert minimal.get_sensor(DcChargerBatteryBoost) is None
    assert minimal.get_sensor(DcChargerSurplusPvPriority) is None
    assert minimal.get_sensor(DcChargerStatusCode) is not None


def test_multiple_chargers_get_numbered_names_and_one_surplus_pv_sensor() -> None:
    discovery = CloudDiscovery(
        device_list=[],
        dc_chargers=(
            DcChargerDiscovery("DC-C", (1,), (0.0, 100.0), (5, 4)),
            DcChargerDiscovery("DC-D", (1,), (0.0, 100.0), (5, 4)),
        ),
    )
    first, second = CloudDcCharger.from_discovery(0, STATION, discovery)
    assert (first.name, second.name) == ("Sigenergy Cloud DC Charger 1", "Sigenergy Cloud DC Charger 2")
    assert first.get_sensor(DcChargerSurplusPvPriority) is not None
    assert second.get_sensor(DcChargerSurplusPvPriority) is None
    second_mode = second.get_sensor(DcChargerChargingMode)
    assert second_mode is not None
    assert second_mode["object_id"].endswith("_cloud_dc_charger_2_charging_mode")


def test_cloud_control_adds_dc_charger_children() -> None:
    discovery = CloudDiscovery(device_list=[], dc_chargers=(DcChargerDiscovery("DC-E", (0, 1), (0.0, 100.0), (5, 4)),))
    device = CloudControl(0, FakeCloudControlPort(), discovery)
    assert any(isinstance(child, CloudDcCharger) for child in device.children)
    assert not any(isinstance(child, CloudDcCharger) for child in CloudControl(1, FakeCloudControlPort(), CloudDiscovery(device_list=[])).children)


async def test_discovery_reads_capabilities_for_each_charger() -> None:
    port = _port()
    discovery = CloudDiscovery(device_list=[{"deviceType": "DcCharger", "serialNumber": "DC-1"}, {"deviceType": "Battery", "serialNumber": "B"}])
    result = await discover_dc_chargers(port, discovery)
    assert result.dc_chargers == (DcChargerDiscovery("DC-1", (0, 1, 3), (0.0, 100.0), (5, 4)),)
    port.dc_supported_charge_modes.assert_awaited_once_with("DC-1")


async def test_discovery_without_dc_chargers_makes_no_requests() -> None:
    port = _port()
    discovery = CloudDiscovery(device_list=[{"deviceType": "Battery", "serialNumber": "B"}])
    assert await discover_dc_chargers(port, discovery) is discovery
    port.energy_profile_setting.assert_not_awaited()


async def test_discovery_degrades_when_capability_reads_fail() -> None:
    port = _port()
    port.energy_profile_setting.side_effect = CloudControlUnavailableError("down")
    port.dc_charge_mode_soc_range.return_value = {"socUpperLimit": 0, "socLowerLimit": 50}
    port.dc_charge_mode_supported.side_effect = [False, CloudControlUnavailableError("down")]
    discovery = CloudDiscovery(device_list=[{"deviceType": "DcCharger", "serialNumber": "DC-1"}, {"deviceType": "DcCharger", "serialNumber": "DC-2"}])

    result = await discover_dc_chargers(port, discovery)

    assert result.dc_chargers == (DcChargerDiscovery("DC-1"), DcChargerDiscovery("DC-2"))
    port.dc_supported_charge_modes.assert_not_awaited()
