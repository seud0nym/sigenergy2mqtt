"""DerivedSensor base class for computed sensors."""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any, Coroutine, Deque

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
            Current state value or None if no state available
        """
        if len(self._states) == 0:
            return None

        state = self._states[-1][1]
        return state if isinstance(state, str) else self._apply_gain_and_precision(state, raw)

    def run_persistence_coroutine(self, coro: Coroutine[Any, Any, None]) -> None:
        """Run a coroutine in the background to persist state.

        Args:
            coro: The coroutine to run
        """
        # This is a fire and forget operation - we don't want to wait for the state to be persisted
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, loop)
                else:
                    coro.close()
            except Exception as e:
                logging.warning(f"{self.log_identity} Failed to persist state: {e}")
                coro.close()
        except Exception as e:
            logging.warning(f"{self.log_identity} Failed to persist state: {e}")
            coro.close()

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
