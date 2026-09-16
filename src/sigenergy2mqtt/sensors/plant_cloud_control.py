"""Home Assistant controls for temporary cloud battery overrides."""

from __future__ import annotations

import logging
from datetime import timedelta

from sigenergy2mqtt.cloud.models import InstantControlMode as Mode
from sigenergy2mqtt.cloud.models import InstantOverrideCommand
from sigenergy2mqtt.cloud.port import BatteryControlPort
from sigenergy2mqtt.common import ProtocolVersion, UnitOfTime
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.sensors.base import (
    CloudReadWriteSensor,
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


def _identity(plant_index: int, suffix: str) -> tuple[str, str]:
    entity_prefix = active_config.home_assistant.entity_id_prefix
    unique_prefix = active_config.home_assistant.unique_id_prefix
    return (
        f"{entity_prefix}_{plant_index}_{suffix}",
        f"{unique_prefix}_{plant_index}_cloud_{suffix}",
    )


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
            protocol_version=ProtocolVersion.V2_4,
        )
        self._payload_available, self._payload_not_available = 0, 1
        self.set_latest_state(0)

    async def _read_cloud_state(self, port: BatteryControlPort) -> int | None:
        state = self.latest_raw_state
        return int(state) if state is not None else None

    async def _write_cloud_value(
        self, port: BatteryControlPort, value: float | str
    ) -> bool:
        return self.set_latest_state(value)


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
            protocol_version=ProtocolVersion.V2_4,
        )
        self._payload_available, self._payload_not_available = 0, 1
        self.set_latest_state(30)

    async def _read_cloud_state(self, port: BatteryControlPort) -> float | None:
        state = self.latest_raw_state
        return float(state) if state is not None else None

    async def _write_cloud_value(
        self, port: BatteryControlPort, value: float | str
    ) -> bool:
        return self.set_latest_state(value)


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
            protocol_version=ProtocolVersion.V2_4,
        )

    async def _read_cloud_state(self, port: BatteryControlPort) -> int:
        return int((await port.instant_control_status()).enabled)

    async def _write_cloud_value(
        self, port: BatteryControlPort, value: float | str
    ) -> bool:
        if int(value) == 0:
            await port.clear_instant_override()
            return True

        option = self._mode.latest_raw_state
        if option is None or int(option) not in _OPTION_TO_MODE:
            logger.error(f"{self.log_identity} no valid mode selected")
            return False
        duration = self._duration.latest_raw_state
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
