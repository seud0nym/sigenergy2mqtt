"""Home Assistant controls for temporary cloud battery overrides."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from sigenergy2mqtt.cloud.models import InstantControlMode as Mode
from sigenergy2mqtt.cloud.models import InstantControlStatus, InstantOverrideCommand
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.common import (
    DeviceClass,
    ProtocolVersion,
    UnitOfElectricCurrent,
    UnitOfPower,
    UnitOfTime,
)
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import (
    CloudReadWriteSensor,
    CloudGridLimitSensor,
    NumericSensorMixin,
    SelectSensorMixin,
    SwitchSensorMixin,
)

logger = logging.getLogger(__name__)

INSTANT_CONTROL_OPTIONS = [
    "Charging",
    "Discharging",
    "Hold Battery",
    "Self-Consumption",
]
_OPTION_TO_MODE = {
    0: Mode.CHARGE,
    1: Mode.DISCHARGE,
    2: Mode.HOLD,
    3: Mode.SELF_CONSUMPTION,
}
_MODE_TO_OPTION = {mode: option for option, mode in _OPTION_TO_MODE.items()}


def _identity(plant_index: int, suffix: str) -> tuple[str, str]:
    entity_prefix = active_config.home_assistant.entity_id_prefix
    unique_prefix = active_config.home_assistant.unique_id_prefix
    return (
        f"{entity_prefix}_{plant_index}_{suffix}",
        f"{unique_prefix}_{plant_index}_cloud_{suffix}",
    )


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


class InstantControlMode(SelectSensorMixin, CloudReadWriteSensor):
    """Mode to use the next time Instant Manual Control is enabled."""

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "instant_control_mode")
        self.plant_index = plant_index
        super().__init__(
            availability_control_sensor=None,
            name="Instant Manual Control Mode",
            object_id=object_id,
            unique_id=unique_id,
            scan_interval=active_config.cloud.scan_interval,
            options=INSTANT_CONTROL_OPTIONS,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:battery-charging-medium",
            gain=None,
            precision=None,
            protocol_version=ProtocolVersion.N_A,
        )
        self._payload_available, self._payload_not_available = 0, 1
        self._pending_value: int | None = None
        self._status_snapshot = _InstantControlStatusSnapshot()
        self._polling_coordinator = self._status_snapshot

    async def _read_cloud_state(self, port: CloudControlPort) -> int | None:
        status = await self._status_snapshot.read(port)
        if not status.enabled or status.mode is None:
            return None
        return _MODE_TO_OPTION.get(status.mode)

    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool:
        changed = self.set_latest_state(value)
        self._pending_value = int(value)
        return changed


class InstantControlDuration(NumericSensorMixin, CloudReadWriteSensor):
    """Duration in minutes for the next Instant Manual Control request."""

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "instant_control_duration")
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
            minimum=1.0,
            maximum=1440.0,
            protocol_version=ProtocolVersion.N_A,
        )
        self._payload_available, self._payload_not_available = 0, 1
        self._pending_value: float | None = None
        self._status_snapshot = _InstantControlStatusSnapshot()
        self._polling_coordinator = self._status_snapshot

    async def _read_cloud_state(self, port: CloudControlPort) -> float | None:
        status = await self._status_snapshot.read(port)
        if not status.enabled or status.ends_at is None:
            return None
        remaining = max(0.0, (status.ends_at - time.time()) / 60)
        return round(remaining, self.precision or 0)

    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool:
        changed = self.set_latest_state(value)
        self._pending_value = float(value)
        return changed


class InstantControlSwitch(SwitchSensorMixin, CloudReadWriteSensor):
    """Authoritative enabled state and command switch for an instant override."""

    def __init__(
        self,
        plant_index: int,
        mode: InstantControlMode,
        duration: InstantControlDuration,
    ) -> None:
        object_id, unique_id = _identity(plant_index, "instant_control")
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

    async def _read_cloud_state(self, port: CloudControlPort) -> int:
        status = await self._status_snapshot.read(port)
        return int(status.enabled)

    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool:
        if int(value) == 0:
            await port.clear_instant_override()
            return True

        option = self._mode._pending_value
        if option is None or int(option) not in _OPTION_TO_MODE:
            logger.error(f"{self.log_identity} no valid mode selected")
            return False
        duration = self._duration._pending_value
        if duration is None:
            logger.error(f"{self.log_identity} no valid duration selected")
            return False
        await port.set_instant_override(
            InstantOverrideCommand(
                mode=_OPTION_TO_MODE[int(option)],
                duration=timedelta(minutes=float(duration)),
            )
        )
        return True


class GridExportLimit(CloudGridLimitSensor):
    """Maximum power that the owner permits the plant to export."""

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "grid_export_limit")
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

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "grid_import_limit")
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

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "grid_connection_limit")
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


class BatteryExportLimitation(SwitchSensorMixin, CloudReadWriteSensor):
    """Control whether the battery is permitted to export to the grid."""

    def __init__(self, plant_index: int) -> None:
        object_id, unique_id = _identity(plant_index, "battery_export_limitation")
        super().__init__(
            availability_control_sensor=None,
            name="Battery Export Limitation",
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

    async def _read_cloud_state(self, port: CloudControlPort) -> int | str:
        payload = await port.battery_export_limitation()
        if not isinstance(payload, dict) or not isinstance(
            payload.get("currentEnable"), bool
        ):
            logger.warning(
                f"{self.log_identity} cloud response contains invalid currentEnable: {payload!r}"
            )
            return "None"
        return int(payload["currentEnable"])

    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool:
        await port.set_battery_export_limitation(bool(int(value)))
        return True
