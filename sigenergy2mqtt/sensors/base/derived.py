"""DerivedSensor base class for computed sensors."""

from __future__ import annotations

import abc
from typing import Any, Deque

from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import Protocol

from .constants import DiscoveryKeys
from .sensor import Sensor, TypedSensorMixin

# =============================================================================


class DerivedSensor(TypedSensorMixin, Sensor):
    """Base class for sensors that derive their values from other sensors.

    Derived sensors compute their state based on values from one or more
    source sensors rather than reading directly from Modbus.
    """

    def __init__(self, **kwargs):
        if "protocol_version" not in kwargs:
            kwargs["protocol_version"] = Protocol.N_A

        super().__init__(**kwargs)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Derived sensors don't update from Modbus."""
        return False

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get derived sensor state.

        Args:
            raw: If True, return raw unprocessed value
            republish: If True, return last known state
            **kwargs: Additional arguments (ignored)

        Returns:
            Current state value or 0 if no state available
        """
        if len(self._states) == 0:
            return 0

        state = self._states[-1][1]
        return state if isinstance(state, str) else self._apply_gain_and_precision(state, raw)

    @abc.abstractmethod
    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        """Apply values from source sensor to this derived sensor.

        Args:
            sensor: The source sensor providing values
            values: List of current values to update this sensor

        Returns:
            True if values were applied successfully
        """
        pass
