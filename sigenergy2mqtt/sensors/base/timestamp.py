"""TimestampSensor for Unix timestamp values."""

from __future__ import annotations

import datetime
from typing import cast

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol
from sigenergy2mqtt.modbus.types import ModbusDataType

from .constants import DiscoveryKeys
from .readable import ReadOnlySensor

# =============================================================================


class TimestampSensor(ReadOnlySensor):
    """Sensor for Unix timestamp values.

    Automatically converts timestamps to ISO 8601 format for display.
    """

    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        scan_interval: int,
        protocol_version: Protocol,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count=2,  # Unix timestamp is 32-bit
            data_type=ModbusDataType.UINT32,
            scan_interval=scan_interval,
            unit=None,
            device_class=DeviceClass.TIMESTAMP,
            state_class=None,
            icon="mdi:calendar-clock",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )
        self[DiscoveryKeys.ENTITY_CATEGORY] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get timestamp state in ISO 8601 format.

        Args:
            raw: If True, return raw Unix timestamp
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            ISO 8601 formatted timestamp or raw value
        """
        value = cast(float, await super().get_state(raw=raw, republish=republish, **kwargs))

        if raw or value is None:
            return value

        if value == 0:
            return "--"

        # Convert to ISO 8601 format
        dt_object = datetime.datetime.fromtimestamp(value, datetime.timezone.utc)
        return dt_object.isoformat()

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        """Convert ISO 8601 timestamp back to Unix timestamp.

        Args:
            state: ISO 8601 timestamp string or Unix timestamp

        Returns:
            Unix timestamp as integer
        """
        if isinstance(state, (float, int)):
            return int(state)

        if state == "--":
            return 0

        return int(datetime.datetime.fromisoformat(state).timestamp())
