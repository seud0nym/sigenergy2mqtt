"""Home Assistant controls for temporary cloud battery overrides."""

from __future__ import annotations

import logging
import math
import time
from datetime import timedelta
from typing import Any, cast

from paho.mqtt.client import Client

from aiohttp import ClientError

from sigenergy2mqtt.cloud.exceptions import CloudControlError
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
    DiscoveryKeys,
    NumericSensorMixin,
    SelectSensorMixin,
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

    @staticmethod
    def _parse_modes(payload: dict[str, object]) -> tuple[list[str], list[tuple[int, int]]]:
        options: list[str] = []
        mode_values: list[tuple[int, int]] = []

        def add_option(label: str, value: tuple[int, int], qualifier: str) -> None:
            option = label
            if option in options:
                option = f"{label} ({qualifier})"
                suffix = 2
                while option in options:
                    option = f"{label} ({qualifier} {suffix})"
                    suffix += 1
            options.append(option)
            mode_values.append(value)

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
                add_option(label, (mode, -1), f"Mode {mode}")

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
                add_option(label, (9, profile_id), f"Profile {profile_id}")

        if not options:
            raise ValueError("OperationalMode: available_modes contains no valid modes")
        return options, mode_values

    def _update_modes(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("OperationalMode: available modes response is not an object")
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
        except (ClientError, CloudControlError, ValueError) as exc:
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


_OPTION_TO_MODE = {
    0: Mode.CHARGE,
    1: Mode.DISCHARGE,
    2: Mode.HOLD,
    3: Mode.SELF_CONSUMPTION,
}
_MODE_TO_OPTION = {mode: option for option, mode in _OPTION_TO_MODE.items()}


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


class InstantControlMode(SelectSensorMixin, CloudReadWriteSensor):
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


class InstantControlDuration(NumericSensorMixin, CloudReadWriteSensor):
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
        remaining = int(max(0.0, (status.ends_at - time.time()) / 60))
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

    async def _pre_publish(self, state: Any, mqtt_client: Client, transport: Any, republish: bool) -> None:
        if self._availability_topic is not None:
            mqtt_client.publish(
                self._availability_topic,
                "0" if self._mode.pending_value is None or self._duration.pending_value == 0 else "1",
                qos=self._qos,
                retain=False,
            )
        return await super()._pre_publish(state, mqtt_client, transport, republish)

    async def publish(self, mqtt_client: Client, transport: Any, republish: bool = False) -> bool:
        return await super().publish(mqtt_client, transport, republish)


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


def _parse_power_limit(sensor: CloudReadWriteSensor, value: object, key: str) -> float | str:
    """Convert a cloud power-limit value into a number entity state."""
    if value in (None, "") or is_unlimited_power(value):
        return "None"
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = math.nan
    if not math.isfinite(parsed) or parsed < 0:
        logger.warning(f"{sensor.log_identity} cloud response contains invalid {key}={value!r}")
        return "None"
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

    def _parse_limits(self, payload: object) -> dict[str, float | None] | None:
        if not isinstance(payload, dict):
            logger.warning(f"{self.log_identity} cloud response is not an object: {payload!r}")
            return None
        if any(key not in payload for key in (self._CHARGE_KEY, self._DISCHARGE_KEY)):
            logger.warning(f"{self.log_identity} cloud response contains incomplete battery limits: {payload!r}")
            return None
        limits: dict[str, float | None] = {}
        for key in (self._CHARGE_KEY, self._DISCHARGE_KEY):
            state = _parse_power_limit(self, payload.get(key), key)
            if state == "None" and payload.get(key) not in (None, "") and not is_unlimited_power(payload.get(key)):
                return None
            limits[key] = None if state == "None" else float(state)
        return limits

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str:
        limits = self._parse_limits(await self._snapshot.read(port))
        if limits is None:
            return "None"
        state = limits[self._key]
        return "None" if state is None else state

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        # The endpoint replaces both limits, so always refresh immediately
        # before writing, without invalidating an in-progress polling snapshot.
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

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str:
        payload = await port.solar_power_limit()
        if not isinstance(payload, dict):
            logger.warning(f"{self.log_identity} cloud response is not an object: {payload!r}")
            return "None"
        return _parse_power_limit(self, payload.get("powerLimit"), "powerLimit")

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        await port.set_solar_power_limit(float(value))
        return True
