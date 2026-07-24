"""TimestampSensor for Unix timestamp values."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import cast

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol
from sigenergy2mqtt.modbus import ModbusDataType

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
        tz: timezone,
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
        self._tz = tz
        self._tz_offset_seconds = tz.utcoffset(None).total_seconds()

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get timestamp state in ISO 8601 format.

        Args:
            raw: If True, return raw Unix timestamp
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            ISO 8601 formatted timestamp or "unavailable" or raw value
        """
        value = cast(float, await super().get_state(raw=raw, republish=republish, **kwargs))

        if raw or value is None:
            return value

        if value == 0:
            return None

        # 1. Correct the epoch by subtracting the offset (in seconds)
        correct_epoch = value - self._tz_offset_seconds

        # 2. Generate the correct datetime object in ISO 8601 format
        dt_object = datetime.fromtimestamp(correct_epoch, self._tz)

        # 3. Convert to ISO 8601
        iso8601 = dt_object.isoformat()

        if self.debug_logging:
            logging.debug(f"{self.log_identity} get_state: raw={value} tz_offset={self._tz_offset_seconds} corrected_epoch={correct_epoch} {iso8601=}")

        return iso8601

    def state2raw(self, state: float | str) -> float | int | str | None:
        """Convert ISO 8601 timestamp back to Unix timestamp.

        Args:
            state: ISO 8601 timestamp string or Unix timestamp

        Returns:
            Unix timestamp as integer
        """
        if isinstance(state, (float, int)):
            return int(state)

        if state == "--":  # Home Assistant uses "--" to represent unavailable timestamps??
            return 0

        try:
            # 1. Convert the ISO 8601 value to the epoch
            epoch = int(datetime.fromisoformat(state).timestamp())

            # 2. Correct the epoch by adding the offset (in seconds)
            raw = epoch + self._tz_offset_seconds

            if self.debug_logging:
                logging.debug(f"{self.log_identity} state2raw: {state=} {epoch=} tz_offset={self._tz_offset_seconds} corrected_epoch={raw}")

            return int(raw)
        except ValueError:
            logging.error(f"{self.log_identity} Invalid timestamp: {state}")
            return 0
