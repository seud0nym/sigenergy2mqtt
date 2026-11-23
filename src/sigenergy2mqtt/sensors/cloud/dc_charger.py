"""DC charger settings and values exposed by the mySigen cloud API.

The endpoints were identified from mySigen web app captures supplied for
https://github.com/seud0nym/sigenergy2mqtt/issues/355.
"""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable
from typing import Any, cast

from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import SigenergyCloudClient
from sigenergy2mqtt.common import (
    PERCENTAGE,
    DeviceClass,
    ProtocolVersion,
    ScanIntervalDefault,
    StateClass,
    UnitOfEnergy,
    UnitOfPower,
)
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import (
    CloudReadWriteSensor,
    CloudSensor,
    DiscoveryKeys,
    NumericSensorMixin,
    SelectSensorMixin,
    SwitchSensorMixin,
)

logger = logging.getLogger(__name__)

#: ``chargeMode`` labels shown by the mySigen app's Charging Mode list.
CHARGE_MODE_LABELS: dict[int, str] = {
    0: "Fast Charging",
    1: "PV Surplus Charging",
    3: "Sigen AI Mode",
}

#: ``sgDeviceType`` values in the energy profile's ``pvPriority`` list.
SURPLUS_PV_DEVICE_LABELS: dict[int, str] = {
    4: "Battery",
    5: "DC Charger",
}


def charge_mode_label(mode: int) -> str:
    return CHARGE_MODE_LABELS.get(mode, f"Mode {mode}")


def surplus_pv_option(device_type: int) -> str:
    return f"{SURPLUS_PV_DEVICE_LABELS.get(device_type, f'Device Type {device_type}')} First"


def dc_charger_identity(plant_index: int, station_id: str, sn: str, index: int, suffix: str) -> tuple[str, str]:
    """Return object and unique IDs for a DC charger cloud sensor.

    The object ID numbers additional chargers (``dc_charger_2_...``) so entity IDs
    stay readable, while the unique ID uses the serial number so it is stable.
    """
    entity_prefix = active_config.home_assistant.entity_id_prefix
    unique_prefix = active_config.home_assistant.unique_id_prefix
    charger = "dc_charger" if index == 0 else f"dc_charger_{index + 1}"
    return (
        f"{entity_prefix}_{plant_index}_cloud_{charger}_{suffix}",
        f"{unique_prefix}_{plant_index}_{station_id}_dc_charger_{sn}_{suffix}",
    )


class CloudResponseSnapshot:
    """Share one cloud response across every sensor that reads it in a polling refresh."""

    def __init__(self, reader: Callable[[CloudControlPort], Awaitable[Any]]) -> None:
        self._reader = reader
        self.write_lock = asyncio.Lock()
        self._payload: Any = None
        self._loaded = False
        self._error: Exception | None = None

    def begin_refresh(self) -> None:
        """Invalidate the previous polling batch's snapshot."""
        self._payload = None
        self._loaded = False
        self._error = None

    async def read(self, port: CloudControlPort) -> Any:
        if self._error is not None:
            raise self._error
        if not self._loaded:
            try:
                self._payload = await self._reader(port)
                self._loaded = True
            except Exception as exc:
                # All sensors in this batch must observe the same outcome.
                self._error = exc
                raise
        return self._payload

    async def read_object(self, port: CloudControlPort) -> dict[str, Any]:
        payload = await self.read(port)
        if not isinstance(payload, dict):
            raise CloudControlUnavailableError("cloud response is not an object")
        return payload


def _number(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


#: The Modbus DCChargerRunningState labels (register 31513). The cloud charger status
#: and SECC run state appear to use the same codes, so the sensors using these labels
#: share that class's translations (see ``options_translation_class``).
DC_CHARGER_RUNNING_STATES: tuple[str, ...] = (
    "Idle",  # 0
    "Occupied (Charging Gun plugged in but not detected)",  # 1
    "Preparing (Establishing communication)",  # 2
    "Charging",  # 3
    "Fault",  # 4
    "Scheduled",  # 5
    "Ended",  # 6
    "Unavailable (Under maintenance)",  # 7
    "Discharging",  # 8
    "Alarm",  # 9
    "Preparing (Insulation detection in progress)",  # 10
)


def _int_code(value: Any) -> int | None:
    """Return an integer status code, or None for anything else (including booleans)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if math.isfinite(number) and number.is_integer() else None


class _EnumStateMixin:
    """Publish a raw status code as its (translated) option label.

    Codes without a label are published as ``Unknown State code: N``, as the
    Modbus DC charger Running State does.
    """

    def _accept_unknown_codes(self) -> None:
        # Unknown codes are published as such rather than rejected
        self.sanity_check.min_raw = 0  # type: ignore[attr-defined]
        self.sanity_check.max_raw = None  # type: ignore[attr-defined]

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> Any:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)  # type: ignore[misc]
        if raw or value is None:
            return value
        if isinstance(value, (float, int)) and (option := self._get_option(int(value))):  # type: ignore[attr-defined]
            return option
        return f"Unknown State code: {value}"


class _DcChargerSensorMixin:
    """Identity and polling-snapshot wiring shared by all DC charger sensors."""

    def _allow_counter_resets(self) -> None:
        """Accept any decrease of a counter that resets (per session, week or month).

        TOTAL_INCREASING normally rejects a decrease other than to exactly 0, and a
        rejected value is not remembered, so a reset that polling misses (an outage,
        or charging across the reset) would freeze the sensor until the new count
        passed the old one. Home Assistant treats a decrease as a reset itself.
        """
        self.sanity_check.min_raw = None  # type: ignore[attr-defined]

    def _dc_init(self, sn: str, snapshot: CloudResponseSnapshot) -> None:
        self._sn = sn
        self._snapshot = snapshot
        self._polling_coordinator = snapshot


# --- Charging mode (device/charge/mode/dc) -----------------------------------------


class _DcChargeModeSetting(_DcChargerSensorMixin, CloudReadWriteSensor):
    """A field of the charging-mode setting, which is always written as a whole."""

    async def _current_mode(self, port: CloudControlPort) -> tuple[int, bool, float]:
        """Return (chargeMode, enableFromPack, cutoffSocFromPack) from a fresh read."""
        payload = await port.dc_charge_mode(self._sn)
        if not isinstance(payload, dict):
            raise CloudControlUnavailableError("cloud response is not an object")
        mode, enabled, cutoff = payload.get("chargeMode"), payload.get("enableFromPack"), _number(payload, "cutoffSocFromPack")
        if isinstance(mode, bool) or not isinstance(mode, int) or not isinstance(enabled, bool) or cutoff is None:
            raise CloudControlUnavailableError(f"cloud response contains an incomplete charging mode: {payload!r}")
        return mode, enabled, cutoff

    async def _write_mode(self, port: CloudControlPort, *, mode: int | None = None, enabled: bool | None = None, cutoff: float | None = None) -> bool:
        # The app always sends all three fields, so fill the unchanged ones from
        # a read made immediately before the write.
        async with self._snapshot.write_lock:
            current_mode, current_enabled, current_cutoff = await self._current_mode(port)
            cutoff_value = current_cutoff if cutoff is None else cutoff
            await port.set_dc_charge_mode(
                current_mode if mode is None else mode,
                dc_sn=self._sn,
                enable_from_pack=current_enabled if enabled is None else enabled,
                cutoff_soc_from_pack=int(cutoff_value) if float(cutoff_value).is_integer() else cutoff_value,
            )
            return True


class DcChargerChargingMode(SelectSensorMixin, _DcChargeModeSetting):
    """The DC charger's Charging Mode."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, charge_modes: tuple[int, ...], snapshot: CloudResponseSnapshot) -> None:
        if not charge_modes:
            raise ValueError("DcChargerChargingMode: no supported charging modes")
        self._modes = list(charge_modes)
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "charging_mode")
        super().__init__(
            availability_control_sensor=None,
            name="Charging Mode",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            options=[charge_mode_label(mode) for mode in self._modes],
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:ev-station",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        mode = (await self._snapshot.read_object(port)).get("chargeMode")
        if isinstance(mode, int) and not isinstance(mode, bool) and mode in self._modes:
            return self._modes.index(mode)
        logger.warning(f"{self.log_identity} cloud response contains unknown charging mode: {mode!r}")
        return None

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        index = int(value)
        if not 0 <= index < len(self._modes):
            logger.warning(f"{self.log_identity} cannot write unknown charging mode index {index}")
            return False
        return await self._write_mode(port, mode=self._modes[index])


class DcChargerBatteryBoost(SwitchSensorMixin, _DcChargeModeSetting):
    """Battery Boost: also charge the vehicle from the home battery."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "battery_boost")
        super().__init__(
            availability_control_sensor=None,
            name="Battery Boost",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:battery-arrow-up",
            gain=None,
            precision=0,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Allows the home battery to charge the vehicle, down to the Battery Boost Cut-off SOC."
        return attributes

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        enabled = (await self._snapshot.read_object(port)).get("enableFromPack")
        if not isinstance(enabled, bool):
            raise CloudControlUnavailableError(f"cloud response contains invalid enableFromPack={enabled!r}")
        return int(enabled)

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        return await self._write_mode(port, enabled=bool(int(value)))


class DcChargerBatteryBoostCutoffSoc(NumericSensorMixin, _DcChargeModeSetting):
    """The home battery SOC below which Battery Boost stops."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, soc_range: tuple[float, float], snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "battery_boost_cutoff_soc")
        super().__init__(
            availability_control_sensor=None,
            name="Battery Boost Cut-off SOC",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=None,
            icon="mdi:battery-lock",
            gain=1,
            precision=0,
            minimum=soc_range[0],
            maximum=soc_range[1],
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        cutoff = _number(await self._snapshot.read_object(port), "cutoffSocFromPack")
        if cutoff is None:
            raise CloudControlUnavailableError("cloud response contains invalid cutoffSocFromPack")
        return cutoff

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        return await self._write_mode(port, cutoff=float(value))


class _DcChargeModeValue(_DcChargerSensorMixin, CloudSensor):
    """A read-only field of the charging-mode response."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot, *, key: str, suffix: str, name: str, unit: str, device_class: DeviceClass, icon: str) -> None:
        self._key = key
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, suffix)
        super().__init__(
            name=name,
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=unit,
            device_class=device_class,
            state_class=None,
            icon=icon,
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        return _number(await self._snapshot.read_object(port), self._key)


class DcChargerV2xDischargePowerLimit(_DcChargeModeValue):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        super().__init__(
            plant_index,
            station_id,
            sn,
            index,
            snapshot,
            key="allowsDischargePower",
            suffix="v2x_discharge_power_limit",
            name="V2X Discharge Power Limit",
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            icon="mdi:car-electric",
        )


class DcChargerV2xDischargeCutoffSoc(_DcChargeModeValue):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        super().__init__(
            plant_index,
            station_id,
            sn,
            index,
            snapshot,
            key="vehicleDischargeCutoffSoc",
            suffix="v2x_discharge_cutoff_soc",
            name="V2X Discharge Cut-off SOC",
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            icon="mdi:car-battery",
        )


# --- Surplus PV priority (device/energy-profile/setting) ---------------------------


class DcChargerSurplusPvPriority(SelectSensorMixin, _DcChargerSensorMixin, CloudReadWriteSensor):
    """Which device is served first from surplus PV generation."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, device_types: tuple[int, ...]) -> None:
        if len(set(device_types)) < 2:
            raise ValueError("DcChargerSurplusPvPriority: fewer than two devices share surplus PV")
        # A fixed order, so the options do not move when the priority changes between restarts
        self._device_types = sorted(set(device_types), reverse=True)
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "surplus_pv_priority")
        super().__init__(
            availability_control_sensor=None,
            name="Surplus PV Priority",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            options=[surplus_pv_option(device_type) for device_type in self._device_types],
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:solar-power-variant",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, CloudResponseSnapshot(lambda port: port.energy_profile_setting()))
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        order = SigenergyCloudClient.surplus_pv_priority_order(await self._snapshot.read_object(port))
        if order and order[0] in self._device_types:
            return self._device_types.index(order[0])
        logger.warning(f"{self.log_identity} cloud response contains unknown Surplus PV priority: {order!r}")
        return None

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        index = int(value)
        if not 0 <= index < len(self._device_types):
            logger.warning(f"{self.log_identity} cannot write unknown Surplus PV priority index {index}")
            return False
        await port.set_surplus_pv_priority(self._device_types[index])
        return True


# --- Read-only charger values -------------------------------------------------------


class DcChargerStatusCode(_EnumStateMixin, _DcChargerSensorMixin, CloudSensor):
    """device/dcevse/status, labelled with the Modbus DC charger Running State codes.

    0 (Idle) was captured from an idle charger. solidfox/homeassistant-sigenergy-cloud
    treats 1 as plugged in and ready, 2 as preparing and 3 as charging, which agree
    with the Modbus codes; the other codes are assumed to match.
    """

    options_translation_class = "DCChargerRunningState"

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "status_code")
        super().__init__(
            name="Status",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:ev-plug-ccs2",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, CloudResponseSnapshot(lambda port: port.dc_status(sn)))
        self[DiscoveryKeys.OPTIONS] = list(DC_CHARGER_RUNNING_STATES)
        self._accept_unknown_codes()
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Assumed to use the same codes as the Modbus DC charger Running State; only 0-3 have been corroborated."
        return attributes

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        return _int_code(await self._snapshot.read(port))


class _DcChargerEnergy(_DcChargerSensorMixin, CloudSensor):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot, *, key: str, suffix: str, name: str, resets: bool) -> None:
        self._key = key
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, suffix)
        super().__init__(
            name=name,
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.MEDIUM,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:ev-station",
            gain=None,
            precision=2,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        if resets:
            self._allow_counter_resets()
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        return _number(await self._snapshot.read_object(port), self._key)


class DcChargerWeeklyChargedEnergy(_DcChargerEnergy):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        super().__init__(plant_index, station_id, sn, index, snapshot, key="weeklyEnergy", suffix="weekly_charged_energy", name="Weekly Charged Energy", resets=True)


class DcChargerMonthlyChargedEnergy(_DcChargerEnergy):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        super().__init__(plant_index, station_id, sn, index, snapshot, key="monthlyEnergy", suffix="monthly_charged_energy", name="Monthly Charged Energy", resets=True)


class DcChargerLifetimeChargedEnergy(_DcChargerEnergy):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        super().__init__(plant_index, station_id, sn, index, snapshot, key="lifetimeEnergy", suffix="lifetime_charged_energy", name="Lifetime Charged Energy", resets=False)


class DcChargerOcppLinkStatus(_EnumStateMixin, _DcChargerSensorMixin, CloudSensor):
    """The OCPP link status (labels as used by solidfox/homeassistant-sigenergy-cloud)."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "ocpp_link_status")
        super().__init__(
            name="OCPP Link Status",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.MEDIUM,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:lan-connect",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        # Labels as used by solidfox/homeassistant-sigenergy-cloud
        self[DiscoveryKeys.OPTIONS] = ["Disconnected", "Connected", "Connecting"]
        self._accept_unknown_codes()
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        return _int_code((await self._snapshot.read_object(port)).get("ocppLinkStatus"))


class DcChargerOcppServerUrl(_DcChargerSensorMixin, CloudSensor):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "ocpp_server_url")
        super().__init__(
            name="OCPP Server URL",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.MEDIUM,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:web",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> str | None:
        url = (await self._snapshot.read_object(port)).get("url")
        return url if isinstance(url, str) else None


class DcChargerV2xDischargeEnabled(_DcChargerSensorMixin, CloudSensor):
    """Whether V2X discharge is enabled (read-only: the write has not been captured)."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "v2x_discharge_enabled")
        super().__init__(
            name="V2X Discharge Enabled",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.MEDIUM,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:car-electric-outline",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, CloudResponseSnapshot(lambda port: port.v2x_discharge_settings(sn)))

    async def _read_cloud_state(self, port: CloudControlPort) -> str | None:
        enabled = (await self._snapshot.read_object(port)).get("dischargeEnable")
        if isinstance(enabled, bool) or not isinstance(enabled, int):
            return None
        return "On" if enabled else "Off"


class _DcChargerVehicle(_DcChargerSensorMixin, CloudSensor):
    """A value of the primary vehicle registered in the app."""

    @staticmethod
    def primary_vehicle(vehicles: Any) -> dict[str, Any] | None:
        candidates = [vehicle for vehicle in vehicles if isinstance(vehicle, dict)] if isinstance(vehicles, list) else []
        return next((vehicle for vehicle in candidates if vehicle.get("primaryCar") == 1), candidates[0] if candidates else None)


class DcChargerPrimaryVehicle(_DcChargerVehicle):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "primary_vehicle")
        super().__init__(
            name="Primary Vehicle",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.LOW,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:car",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)

    async def _read_cloud_state(self, port: CloudControlPort) -> str | None:
        vehicle = self.primary_vehicle(await self._snapshot.read(port))
        if vehicle is None:
            return "None"
        parts = [str(vehicle.get(key)) for key in ("brand", "model") if vehicle.get(key)]
        if vehicle.get("years"):
            parts.append(f"({vehicle['years']})")
        return " ".join(parts) or "Unknown"


class DcChargerPrimaryVehicleBatteryCapacity(_DcChargerVehicle):
    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "primary_vehicle_battery_capacity")
        super().__init__(
            name="Primary Vehicle Battery Capacity",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=ScanIntervalDefault.LOW,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=None,
            state_class=None,
            icon="mdi:car-battery",
            gain=None,
            precision=1,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        vehicle = self.primary_vehicle(await self._snapshot.read(port))
        return None if vehicle is None else _number(cast(dict[str, Any], vehicle), "batteryCapacity")


# --- Live charging values (device/dcevse/charge/realtime) ---------------------------
# Field meanings follow solidfox/homeassistant-sigenergy-cloud. No capture of this
# endpoint during a charging session has been seen yet, so they are unverified.


class DcChargerSeccRunState(_EnumStateMixin, _DcChargerSensorMixin, CloudSensor):
    """``seccRunState``: the charging controller state, apparently in Running State codes."""

    options_translation_class = "DCChargerRunningState"

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "secc_run_state")
        super().__init__(
            name="SECC Run State",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:chip",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.OPTIONS] = list(DC_CHARGER_RUNNING_STATES)
        self._accept_unknown_codes()
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        return _int_code((await self._snapshot.read_object(port)).get("seccRunState"))


class DcChargerChargingPower(_DcChargerSensorMixin, CloudSensor):
    """``pileOutputPower``: positive while charging the vehicle, negative while discharging it (V2X)."""

    _DISCHARGING = 8

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "charging_power")
        super().__init__(
            name="Charging Power",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:ev-station",
            gain=None,
            precision=3,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        payload = await self._snapshot.read_object(port)
        power = _number(payload, "pileOutputPower")
        if power is None:
            return None
        # The cloud may report discharge power unsigned; the run state says which way it flows.
        if power < 0 or _int_code(payload.get("seccRunState")) == self._DISCHARGING:
            return -abs(power)
        return abs(power)


class DcChargerVehicleSoc(_DcChargerSensorMixin, CloudSensor):
    """``vehicleSoc``: the connected vehicle's state of charge."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "vehicle_soc")
        super().__init__(
            name="Vehicle SOC",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=PERCENTAGE,
            device_class=DeviceClass.BATTERY,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:car-electric",
            gain=None,
            precision=0,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Only meaningful while a vehicle is connected."
        return attributes

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        return _number(await self._snapshot.read_object(port), "vehicleSoc")


class DcChargerSessionChargedEnergy(_DcChargerSensorMixin, CloudSensor):
    """``singleChargePower``: energy delivered in the current session (despite its name, in kWh)."""

    def __init__(self, plant_index: int, station_id: str, sn: str, index: int, snapshot: CloudResponseSnapshot) -> None:
        object_id, unique_id = dc_charger_identity(plant_index, station_id, sn, index, "session_charged_energy")
        super().__init__(
            name="Session Charged Energy",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:battery-charging-high",
            gain=None,
            precision=2,
            protocol_version=ProtocolVersion.N_A,
        )
        self._dc_init(sn, snapshot)
        self._allow_counter_resets()
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        return _number(await self._snapshot.read_object(port), "singleChargePower")
