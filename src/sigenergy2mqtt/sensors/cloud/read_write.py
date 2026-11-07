"""Home Assistant controls for temporary cloud battery overrides."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import timedelta
from typing import Any, cast

from aiohttp import ClientError
from paho.mqtt.client import Client

from sigenergy2mqtt.cloud.exceptions import CloudControlError, CloudControlRateLimitedError, CloudControlUnavailableError
from sigenergy2mqtt.cloud.models import InstantControlMode as Mode
from sigenergy2mqtt.cloud.models import InstantControlStatus, InstantOverrideCommand
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import (
    UNLIMITED_POWER_KW,
    is_unlimited_power,
)
from sigenergy2mqtt.common import (
    DeviceClass,
    ProtocolVersion,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfTime,
)
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import (
    AvailabilityMixin,
    CloudGridLimitSensor,
    CloudReadWriteSensor,
    CloudSensor,
    CloudWriteOnlySensor,
    DiscoveryKeys,
    NumericSensorMixin,
    SelectSensorMixin,
    Sensor,
    SwitchSensorMixin,
)
from sigenergy2mqtt.sensors.cloud.functions import _identity

logger = logging.getLogger(__name__)

INSTANT_CONTROL_OPTIONS = [
    "Charging",
    "Discharging",
    "Hold Battery",
    "Self-Consumption",
]


class OperationalMode(SelectSensorMixin, CloudReadWriteSensor):
    """Select the station's persistent cloud operating mode or energy profile."""

    def __init__(self, plant_index: int, station_id: str, available_modes: dict[str, object]) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "operational_mode")
        options, self._mode_values = self._parse_modes(available_modes)
        super().__init__(
            availability_control_sensor=None,
            name="Operational Mode",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            options=options,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:home-lightning-bolt-outline",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @staticmethod
    def _parse_modes(payload: dict[str, object]) -> tuple[list[str], list[tuple[int, int]]]:
        options: list[str] = []
        mode_values: list[tuple[int, int]] = []
        no_mode = (-1, -1)  # placeholder for empty slots
        profile_min_index = 9

        def place(
            index: int | None,
            label: str,
            value: tuple[int, int],
            qualifier: str,
            min_index: int = 0,
        ) -> None:
            option = label
            if option in options:
                option = f"{label} ({qualifier})"
                suffix = 2
                while option in options:
                    option = f"{label} ({qualifier} {suffix})"
                    suffix += 1

            # No fixed index, or the requested slot is unusable/taken: append,
            # padding first so the entry lands at or beyond min_index
            if index is None or index < 0 or (index < len(options) and options[index]):
                while len(options) < min_index:
                    options.append("")
                    mode_values.append(no_mode)
                options.append(option)
                mode_values.append(value)
                return

            # Pad with empty slots up to the index, then fill it
            while len(options) <= index:
                options.append("")
                mode_values.append(no_mode)
            options[index] = option
            mode_values[index] = value

        default_modes = payload.get("defaultWorkingModes")
        for item in default_modes if isinstance(default_modes, list) else ():
            if not isinstance(item, dict):
                continue
            try:
                label = str(item["label"])
                mode = int(item["value"])
            except (KeyError, TypeError, ValueError):
                continue
            if label:
                place(mode, label, (mode, -1), f"Mode {mode}")

        energy_profiles = payload.get("energyProfileItems")
        for item in energy_profiles if isinstance(energy_profiles, list) else ():
            if not isinstance(item, dict):
                continue
            try:
                label = str(item["name"])
                profile_id = int(item["profileId"])
            except (KeyError, TypeError, ValueError):
                continue
            if label:
                place(None, label, (9, profile_id), f"Profile {profile_id}", profile_min_index)

        if not any(options):
            raise ValueError("OperationalMode: available_modes contains no valid modes")
        return options, mode_values

    def _update_modes(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise TypeError("OperationalMode: available modes response is not an object")
        options, mode_values = self._parse_modes(payload)
        if options != self[DiscoveryKeys.OPTIONS]:
            self[DiscoveryKeys.OPTIONS] = options
            self.sanity_check.max_raw = len(options) - 1
            if self.parent_device is not None:
                self.parent_device.rediscover = True
        self._mode_values = mode_values

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        try:
            payload = await port.available_operational_modes()
            self._update_modes(payload)
        except (ClientError, CloudControlError, TypeError, ValueError) as exc:
            logger.warning(f"{self.log_identity} could not refresh operational modes; using existing options: {exc!r}")
        current = await port.get_operational_mode()
        try:
            return self._mode_values.index((int(current[0]), int(current[1])))
        except (IndexError, TypeError, ValueError):
            logger.warning(f"{self.log_identity} cloud response contains unknown operational mode: {current!r}")
            return None

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        index = int(value)
        if not 0 <= index < len(self._mode_values):
            logger.warning(f"{self.log_identity} cannot write unknown operational mode index {index}")
            return False
        mode, profile_id = self._mode_values[index]
        await port.set_operational_mode(mode, profile_id)
        return True


class _InstantControlStatusSnapshot:
    """Share one cloud status response across a complete control refresh."""

    def __init__(self) -> None:
        self._status: InstantControlStatus | None = None
        self._error: Exception | None = None

    def begin_refresh(self) -> None:
        """Invalidate the previous polling batch's snapshot."""
        self._status = None
        self._error = None

    async def read(self, port: CloudControlPort) -> InstantControlStatus:
        if self._error is not None:
            raise self._error
        if self._status is None:
            try:
                self._status = await port.instant_control_status()
            except Exception as exc:
                # All sensors in this batch must observe the same outcome rather
                # than issuing retries that could mix refresh snapshots.
                self._error = exc
                raise
        return self._status


class _BatteryPowerLimitSnapshot:
    """Share one battery power-limit response across both limit sensors."""

    def __init__(self) -> None:
        self.write_lock = asyncio.Lock()
        self._payload: dict[str, object] | None = None
        self._error: Exception | None = None

    def begin_refresh(self) -> None:
        """Invalidate the previous polling batch's snapshot."""
        self._payload = None
        self._error = None

    async def read(self, port: CloudControlPort) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        if self._payload is None:
            try:
                payload = await port.battery_power_limit()
                self._payload = payload if isinstance(payload, dict) else {}
            except Exception as exc:
                self._error = exc
                raise
        return self._payload


class _InstantControlSetting(CloudReadWriteSensor):
    _control_switch: InstantControlSwitch | None = None

    async def _write_value(self, transport: Any, mqtt_client: Client, value: float | str, source: str, handler: Any) -> bool:
        result = await super()._write_value(transport, mqtt_client, value, source, handler)
        switch = self._control_switch
        if switch is not None:
            switch._publish_control_availability(mqtt_client)
        return result


class InstantControlMode(SelectSensorMixin, _InstantControlSetting):
    """Mode to use the next time Instant Manual Control is enabled."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "instant_control_mode")
        self.plant_index = plant_index
        super().__init__(
            availability_control_sensor=None,
            name="Instant Manual Control Mode",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            options=[
                "Not Set",  # 0
                "Charging",  # 1
                "Discharging",  # 2
                "Hold Battery",  # 3
                "Self-Consumption",  # 4
            ],
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:battery-charging-medium",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self.monitorable = False  # only need to monitor InstantControlSwitch
        self._pending_value: Mode | None = None
        self._status_snapshot = _InstantControlStatusSnapshot()
        self._polling_coordinator = self._status_snapshot
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @property
    def pending_value(self) -> Mode | None:
        if self._pending_value is not None:
            return self._pending_value
        match self.latest_raw_state:
            case 1:
                return Mode.CHARGE
            case 2:
                return Mode.DISCHARGE
            case 3:
                return Mode.HOLD
            case 4:
                return Mode.SELF_CONSUMPTION
            case _:
                return None

    async def _read_cloud_state(self, port: CloudControlPort) -> int:
        status = await self._status_snapshot.read(port)
        if status.mode is None and self._pending_value is None:
            return 0
        if self._pending_value is not None:
            mode = self._pending_value
        else:
            mode = status.mode
        match mode:
            case Mode.CHARGE:
                return 1
            case Mode.DISCHARGE:
                return 2
            case Mode.HOLD:
                return 3
            case Mode.SELF_CONSUMPTION:
                return 4
            case _:
                self._pending_value = None
                raise ValueError(f"Unknown Instant Control Mode '{status.mode}'")

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        state = int(value)
        match state:
            case 0:
                self._pending_value = None
            case 1:
                self._pending_value = Mode.CHARGE
            case 2:
                self._pending_value = Mode.DISCHARGE
            case 3:
                self._pending_value = Mode.HOLD
            case 4:
                self._pending_value = Mode.SELF_CONSUMPTION
            case _:
                self._pending_value = None
                raise ValueError(f"Invalid Instant Control Mode '{state}'")
        changed = self.set_latest_state(state)
        return changed


class InstantControlDuration(NumericSensorMixin, _InstantControlSetting):
    """Duration in minutes for the next Instant Manual Control request."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "instant_control_duration")
        self.plant_index = plant_index
        super().__init__(
            availability_control_sensor=None,
            name="Instant Manual Control Duration",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfTime.MINUTES,
            device_class=None,
            state_class=None,
            icon="mdi:timer-outline",
            gain=None,
            precision=0,
            minimum=0,
            maximum=1440,
            protocol_version=ProtocolVersion.N_A,
        )
        self.monitorable = False  # only need to monitor InstantControlSwitch
        self._pending_value: int | None = None
        self._status_snapshot = _InstantControlStatusSnapshot()
        self._polling_coordinator = self._status_snapshot
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @property
    def pending_value(self) -> int:
        if self._pending_value is not None:
            return self._pending_value
        elif self.latest_raw_state is None or self.latest_raw_state == 0:
            return 0
        else:
            return self.latest_raw_state

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        if self._pending_value is not None:
            return self._pending_value
        status = await self._status_snapshot.read(port)
        if status.ends_at is None:
            return 0
        remaining = math.ceil(max(0.0, (status.ends_at - time.time()) / 60))
        return remaining

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        self._pending_value = int(value)
        changed = self.set_latest_state(self._pending_value)
        return changed


class InstantControlSwitch(SwitchSensorMixin, CloudReadWriteSensor, AvailabilityMixin):
    """Authoritative enabled state and command switch for an instant override."""

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        mode: InstantControlMode,
        duration: InstantControlDuration,
    ) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "instant_control")
        self.plant_index = plant_index
        self._mode = mode
        self._duration = duration
        mode._control_switch = self
        duration._control_switch = self
        self._status_snapshot = mode._status_snapshot
        duration._status_snapshot = self._status_snapshot
        self._polling_coordinator = self._status_snapshot
        mode._polling_coordinator = self._status_snapshot
        duration._polling_coordinator = self._status_snapshot
        super().__init__(
            availability_control_sensor=None,
            name="Instant Manual Control",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:battery-sync",
            gain=None,
            precision=0,
            protocol_version=ProtocolVersion.N_A,
        )
        self._availability_topic: str | None = None
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @property
    def payload_available(self) -> bool | int | float | str | None:
        return 0

    @property
    def payload_not_available(self) -> bool | int | float | str | None:
        return 1

    async def _read_cloud_state(self, port: CloudControlPort) -> int:
        status = await self._status_snapshot.read(port)
        return int(status.enabled)

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        if int(value) == 0:
            await port.clear_instant_override()
            self._mode._pending_value = None
            self._duration._pending_value = None
            return True

        option = self._mode.pending_value
        if option is None:
            logger.error(f"{self.log_identity} no valid mode selected")
            return False
        duration = self._duration.pending_value
        if duration == 0:
            logger.error(f"{self.log_identity} no valid duration selected")
            return False

        await port.set_instant_override(
            InstantOverrideCommand(
                mode=option,
                duration=timedelta(minutes=float(duration)),
            )
        )
        self._mode._pending_value = None
        self._duration._pending_value = None
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            self._availability_topic = f"{base}/enabled"
            availability = cast(list[dict[str, Any]], self[DiscoveryKeys.AVAILABILITY])
            availability.append({
                DiscoveryKeys.TOPIC: self._availability_topic,
                DiscoveryKeys.PAYLOAD_AVAILABLE: 1,
                DiscoveryKeys.PAYLOAD_NOT_AVAILABLE: 0,
            })
        return base

    def _publish_control_availability(self, mqtt_client: Client) -> None:
        if self._availability_topic is not None:
            mqtt_client.publish(
                self._availability_topic,
                "1" if self.latest_raw_state == 1 or (self._mode.pending_value is not None and self._duration.pending_value > 0) else "0",
                qos=self._qos,
                retain=False,
            )

    async def publish(self, mqtt_client: Client, transport: Any, republish: bool = False) -> bool:
        published = await super().publish(mqtt_client, transport, republish)
        self._publish_control_availability(mqtt_client)
        return published


class GridExportLimit(CloudGridLimitSensor):
    """Maximum power that the owner permits the plant to export."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "grid_export_limit")
        super().__init__(
            availability_control_sensor=None,
            read_method="grid_export_limit",
            write_method="set_grid_export_limit",
            current_key="maxLimitation",
            installer_key="maxLimitationInstaller",
            name="Grid Export Limit",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-export",
            gain=None,
            precision=3,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True


class GridImportLimit(CloudGridLimitSensor):
    """Maximum power that the owner permits the plant to import."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "grid_import_limit")
        super().__init__(
            availability_control_sensor=None,
            read_method="grid_import_limit",
            write_method="set_grid_import_limit",
            current_key="maxLimitation",
            installer_key="maxLimitationInstaller",
            name="Grid Import Limit",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:transmission-tower-import",
            gain=None,
            precision=3,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True


class GridConnectionLimit(CloudGridLimitSensor):
    """Maximum phase current allowed at the grid connection point."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "grid_connection_limit")
        super().__init__(
            availability_control_sensor=None,
            read_method="grid_connection_limit",
            write_method="set_grid_connection_limit",
            current_key="currentLimitation",
            installer_key="installerSetLimitation",
            name="Grid Connection Current Limit",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-ac",
            gain=None,
            precision=1,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True


def _parse_power_limit(sensor: CloudReadWriteSensor, value: object, key: str) -> float | str | None:
    """Convert a cloud power-limit value into a number entity state."""
    if value in (None, ""):
        return None
    if is_unlimited_power(value):
        return UNLIMITED_POWER_KW
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = math.nan
    if not math.isfinite(parsed) or parsed < 0:
        raise CloudControlUnavailableError(f"invalid {key} in cloud response: {value!r}")
    return parsed


class _BatteryPowerLimit(NumericSensorMixin, CloudReadWriteSensor):
    """Common behaviour for one half of the battery power-limit setting."""

    _CHARGE_KEY = "batteryMaxChargingPower"
    _DISCHARGE_KEY = "batteryMaxDischargingPower"

    def __init__(
        self,
        plant_index: int,
        station_id: str,
        *,
        key: str,
        name: str,
        suffix: str,
        icon: str,
        snapshot: _BatteryPowerLimitSnapshot | None = None,
    ) -> None:
        self._key = key
        self._snapshot = snapshot or _BatteryPowerLimitSnapshot()
        self._polling_coordinator = self._snapshot
        object_id, unique_id = _identity(plant_index, station_id, suffix)
        super().__init__(
            availability_control_sensor=None,
            name=name,
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon=icon,
            gain=1,
            precision=3,
            minimum=0.0,
            maximum=UNLIMITED_POWER_KW,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def _update_sanity_check_ranges(self, gain: float | None) -> None:
        super()._update_sanity_check_ranges(gain)
        # Cloud values are decimal kW, including the unlimited sentinel.
        self.sanity_check.max_raw = float(cast(float | str, self[DiscoveryKeys.MAX]))

    def _parse_limits(self, payload: object) -> dict[str, float | None] | None:
        if not isinstance(payload, dict):
            raise CloudControlUnavailableError("cloud response is not an object")
        if any(key not in payload for key in (self._CHARGE_KEY, self._DISCHARGE_KEY)):
            raise CloudControlUnavailableError("cloud response contains incomplete battery limits")
        limits: dict[str, float | None] = {}
        for key in (self._CHARGE_KEY, self._DISCHARGE_KEY):
            state = _parse_power_limit(self, payload.get(key), key)
            if state is None and payload.get(key) not in (None, "") and not is_unlimited_power(payload.get(key)):
                return None
            limits[key] = None if state is None else float(state)
        return limits

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        limits = self._parse_limits(await self._snapshot.read(port))
        if limits is None:
            return None
        state = limits[self._key]
        return state

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        # The endpoint replaces both limits, so always refresh immediately
        # before writing, without invalidating an in-progress polling snapshot.
        async with self._snapshot.write_lock:
            limits = self._parse_limits(await port.battery_power_limit())
            if limits is None:
                logger.warning(f"{self.log_identity} cannot write without both current battery power limits")
                return False
            limits[self._key] = float(value)
            await port.set_battery_power_limit(
                max_charge_kw=limits[self._CHARGE_KEY],
                max_discharge_kw=limits[self._DISCHARGE_KEY],
            )
            return True


class BatteryChargePowerLimit(_BatteryPowerLimit):
    """Maximum battery charging power requested by the owner."""

    def __init__(self, plant_index: int, station_id: str, snapshot: _BatteryPowerLimitSnapshot | None = None) -> None:
        super().__init__(
            plant_index,
            station_id,
            key=self._CHARGE_KEY,
            name="Battery Charge Power Limit",
            suffix="battery_charge_power_limit",
            icon="mdi:battery-arrow-down-outline",
            snapshot=snapshot,
        )


class BatteryDischargePowerLimit(_BatteryPowerLimit):
    """Maximum battery discharging power requested by the owner."""

    def __init__(self, plant_index: int, station_id: str, snapshot: _BatteryPowerLimitSnapshot | None = None) -> None:
        super().__init__(
            plant_index,
            station_id,
            key=self._DISCHARGE_KEY,
            name="Battery Discharge Power Limit",
            suffix="battery_discharge_power_limit",
            icon="mdi:battery-arrow-up-outline",
            snapshot=snapshot,
        )


class SolarPowerLimit(NumericSensorMixin, CloudReadWriteSensor):
    """Maximum solar generation power requested by the owner."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "solar_power_limit")
        super().__init__(
            availability_control_sensor=None,
            name="Solar Power Limit",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=UnitOfPower.KILO_WATT,
            device_class=DeviceClass.POWER,
            state_class=None,
            icon="mdi:solar-power",
            gain=1,
            precision=3,
            minimum=0.0,
            maximum=UNLIMITED_POWER_KW,
            protocol_version=ProtocolVersion.N_A,
        )

    def _update_sanity_check_ranges(self, gain: float | None) -> None:
        super()._update_sanity_check_ranges(gain)
        # Cloud values are decimal kW, including the unlimited sentinel.
        self.sanity_check.max_raw = float(cast(float | str, self[DiscoveryKeys.MAX]))

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str | None:
        payload = await port.solar_power_limit()
        if not isinstance(payload, dict):
            raise CloudControlUnavailableError("cloud response is not an object")
        if "powerLimit" not in payload:
            raise CloudControlUnavailableError("cloud response is missing powerLimit")
        return _parse_power_limit(self, payload.get("powerLimit"), "powerLimit")

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        await port.set_solar_power_limit(float(value))
        return True


class BatteryExportLimitation(SwitchSensorMixin, CloudReadWriteSensor):
    """Control whether the battery is permitted to export to the grid."""

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "battery_export_limitation")
        super().__init__(
            availability_control_sensor=None,
            name="Block Battery Export to Grid",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:battery-arrow-up-outline",
            gain=None,
            precision=0,
            protocol_version=ProtocolVersion.N_A,
        )
        self._updates_allowed = False
        self._writable_topic: str | None = None

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            availability = cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY])
            self._writable_topic = f"{base}/writable"
            availability.append({"topic": self._writable_topic, "payload_available": "1", "payload_not_available": "0"})
        return base

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Not available when disabled by installer."
        return attributes

    async def publish(self, mqtt_client: Client, transport: Any, republish: bool = False) -> bool:
        try:
            return await super().publish(mqtt_client, transport, republish)
        finally:
            if self._writable_topic is not None:
                mqtt_client.publish(self._writable_topic, int(self._updates_allowed), qos=self._qos)

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        payload = await port.battery_export_limitation()
        if not isinstance(payload, dict) or not isinstance(payload.get("currentEnable"), (bool, int)):
            self._updates_allowed = False
            raise CloudControlUnavailableError("cloud response contains invalid currentEnable")
        installerSetEnable = payload.get("installerSetEnable", None)
        self._updates_allowed = True if installerSetEnable is None else bool(installerSetEnable)
        return int(bool(payload.get("currentEnable", False)))

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        if not self._updates_allowed:
            logger.warning(f"{self.log_identity} cloud response indicates battery export limitation cannot be changed by the owner")
            return False
        await port.set_battery_export_limitation(bool(int(value)))
        return True


class GatewayGridConnectionStatus(CloudSensor):
    """Grid connection state reported by the gateway.

    Each poll also refreshes the availability of the Go Off-Grid and Go On-Grid
    buttons, which have no polling cycle of their own.
    """

    _ON_GRID = 0
    _GOING_OFF_GRID = 1
    _OFF_GRID = 2
    _RETURNING_TO_GRID = 3

    def __init__(self, plant_index: int, station_id: str) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "gateway_grid_connection_status")
        super().__init__(
            name="Grid Connection Status",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:transmission-tower",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True
        self[DiscoveryKeys.OPTIONS] = [
            "On Grid",  # 0
            "Going Off Grid",  # 1
            "Off Grid",  # 2
            "Returning to Grid",  # 3
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1
        self.gateway_status: dict[str, Any] | None = None  # None when the last read did not succeed
        self._control: GatewayGridConnectionControl | None = None

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        self.gateway_status = None
        payload = await port.gateway_status()
        if not isinstance(payload, dict):
            raise CloudControlUnavailableError("cloud response is not an object")
        match payload.get("onOffGridStatus"):
            case 0:
                state = self._GOING_OFF_GRID if payload.get("manualOffGridStatus") == 1 else self._ON_GRID
            case 1:
                state = self._RETURNING_TO_GRID
            case 2:
                state = self._OFF_GRID
            case unknown:
                logger.warning(f"{self.log_identity} cloud response contains unknown onOffGridStatus: {unknown!r}")
                return None
        self.gateway_status = payload
        return state

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> Any:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw or value is None:
            return value
        return self._get_option(int(value)) or f"Unknown Status: {value}"

    async def publish(self, mqtt_client: Client, transport: Any, republish: bool = False) -> bool:
        try:
            return await super().publish(mqtt_client, transport, republish)
        finally:
            if self._control is not None:
                self._control.publish_button_availability(mqtt_client)


class GatewayGridConnectionControl(CloudWriteOnlySensor):
    """"Go Off-Grid" and "Go On-Grid" buttons for the gateway.

    Pressing a button physically changes the site's grid connection. Availability
    in Home Assistant follows the polled gateway status and the plant's Modbus
    GridStatus (when it is available, which also requires its latest read to
    have succeeded recently). Because availability can lag and is not
    enforced for direct MQTT commands, every press applies the same rule to a
    fresh gateway status, and sends nothing if that read fails or the cloud is
    in a rate-limit cooldown.
    """

    _PLANT_ON_GRID = 0  # GridStatus "On Grid"
    _PLANT_OFF_GRID_MANUAL = 2  # GridStatus "Off Grid (manual)"; "Off Grid (auto)" means an outage or a return to the grid in progress
    _PLANT_MIN_MAX_AGE = 60.0  # seconds; GridStatus older than the larger of this and 3 scan intervals cannot permit a change

    def __init__(self, plant_index: int, station_id: str, status_sensor: GatewayGridConnectionStatus) -> None:
        object_id, unique_id = _identity(plant_index, station_id, "gateway_grid_connection")
        super().__init__(
            name="Grid Connection",
            object_id=object_id,
            unique_id=unique_id,
            unit=None,
            device_class=None,
            state_class=None,
            icon=None,
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
            name_off="Go Off-Grid",
            name_on="Go On-Grid",
            icon_off="mdi:transmission-tower-off",
            icon_on="mdi:transmission-tower",
            payload_off="go_off_grid",
            payload_on="go_on_grid",
            value_off=1,  # the values match the API's onGridState
            value_on=0,
        )
        self._status_sensor = status_sensor
        status_sensor._control = self
        self._plant_grid_status: Sensor | None = None
        self._available_topics: dict[str, str] = {}

    def set_plant_grid_status(self, sensor: Sensor | None) -> None:
        """Also require the plant's Modbus GridStatus sensor to permit each button."""
        self._plant_grid_status = sensor

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            self._available_topics = {action: f"{base}/{self._payloads[action]}/available" for action in ("off", "on")}
        return base

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components = super().get_discovery_components()
        for action, topic in self._available_topics.items():
            component = components[f"{self.unique_id}_{action}"]
            component[DiscoveryKeys.AVAILABILITY] = [
                *cast(list[dict[str, Any]], component[DiscoveryKeys.AVAILABILITY]),
                {DiscoveryKeys.TOPIC: topic, DiscoveryKeys.PAYLOAD_AVAILABLE: "1", DiscoveryKeys.PAYLOAD_NOT_AVAILABLE: "0"},
            ]
        return components

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Valid values: go_off_grid, go_on_grid. Ignored unless the gateway allows the change."
        return attributes

    def _permits(self, off_grid: bool, status: dict[str, Any] | None) -> bool:
        """Return whether a gateway status and the plant's GridStatus allow a button."""
        if not isinstance(status, dict) or status.get("showButton") is not True:
            return False
        grid_status, manual = status.get("onOffGridStatus"), status.get("manualOffGridStatus")
        if not (grid_status == 0 and manual != 1 if off_grid else grid_status == 2 and manual == 2):
            return False
        if self._plant_grid_status is None:
            return True
        if not self._plant_grid_status.is_read_current(self._plant_max_age()):
            return False
        return self._plant_grid_status.latest_raw_state == (self._PLANT_ON_GRID if off_grid else self._PLANT_OFF_GRID_MANUAL)

    def _plant_max_age(self) -> float:
        """Return how old the plant's GridStatus may be and still permit a button."""
        scan_interval = getattr(self._plant_grid_status, "scan_interval", None)
        if not isinstance(scan_interval, (int, float)) or scan_interval <= 0:
            return self._PLANT_MIN_MAX_AGE
        return max(self._PLANT_MIN_MAX_AGE, 3.0 * scan_interval)

    def publish_button_availability(self, mqtt_client: Client) -> None:
        """Publish whether each button can currently be pressed."""
        status = self._status_sensor.gateway_status
        for action, topic in self._available_topics.items():
            mqtt_client.publish(topic, "1" if self._permits(action == "off", status) else "0", qos=self._qos, retain=False)

    async def _write_value(self, transport: Any, mqtt_client: Client, value: float | str, source: str, handler: Any) -> bool:
        written = await super()._write_value(transport, mqtt_client, value, source, handler)
        if written:
            # Both buttons stay unavailable until the immediate re-poll reports the new state.
            self._status_sensor.gateway_status = None
            self._status_sensor.force_publish = True
            self.publish_button_availability(mqtt_client)
        return written

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        off_grid = int(value) == self._values["off"]
        payload = self._payloads["off" if off_grid else "on"]
        try:
            status = await port.gateway_status(wait_for_rate_limit=False)
            if not self._permits(off_grid, status):
                plant = self._plant_grid_status
                plant_grid_status = None if plant is None else plant.latest_raw_state
                plant_current = None if plant is None else plant.is_read_current(self._plant_max_age())
                logger.warning(f"{self.log_identity} ignoring {payload}: gateway status is {status!r} and plant GridStatus is {plant_grid_status!r} (current={plant_current})")
                return False
            await port.set_gateway_off_grid(off_grid)
        except CloudControlRateLimitedError as exc:
            logger.warning(f"{self.log_identity} dropping {payload}: {exc}")
            return False
        return True
