"""DerivedSensor base class for computed sensors."""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any, Coroutine

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

    def __init__(self, *args, source_sensors: tuple["Sensor", ...] = (), **kwargs):
        """Initialise the derived sensor.

        Args:
            source_sensors: The sensors whose values drive this sensor's state.
                            Subclasses should always supply this so that source
                            wiring is configured at construction time.
            **kwargs: Forwarded to the Sensor base class.
        """
        if "protocol_version" not in kwargs:
            kwargs["protocol_version"] = Protocol.N_A

        super().__init__(*args, **kwargs)
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True
        self.bound_source_sensors: list[Sensor] = []

        # Initialise source_sensors from the constructor argument.  Subclasses
        # that use deferred / cross-device binding start with an empty list and
        # populate it later via _declare_source_sensors() / finalise_binding().
        self.source_sensors: list["Sensor"] = []
        if source_sensors:
            self._declare_source_sensors(*source_sensors)

    def _declare_source_sensors(self, *sensors: "Sensor") -> None:
        """Internal helper – update source_sensors after construction.

        Ordinary subclasses must NOT call this directly; pass ``source_sensors``
        to ``__init__`` instead.  This method exists only for subclasses that
        perform deferred or cross-device binding (e.g.
        ``CrossDeviceDerivedSensor.finalise_binding``).
        """
        self.source_sensors = [s for s in sensors if s is not None]
        if not self.source_sensors:
            log_id = getattr(self, "_log_identity", self.__class__.__name__)
            logging.error(f"{log_id} - no declared source sensors")
        if not hasattr(self, "bound_source_sensors"):
            self.bound_source_sensors = []

    def bind_source_sensor(self, sensor: Sensor) -> None:
        if not hasattr(self, "bound_source_sensors"):
            self.bound_source_sensors = []
        if sensor not in self.bound_source_sensors:
            self.bound_source_sensors.append(sensor)

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
    def set_source_values(self, sensor: Sensor) -> bool:
        """Apply values from source sensor to this derived sensor.

        Args:
            sensor: The source sensor providing values

        Returns:
            True if values were applied successfully
        """
        pass


# =============================================================================


class CrossDeviceDerivedSensor(DerivedSensor):
    """DerivedSensor whose sources may live on any Device in the same plant.

    Subclasses call declare_cross_device_sources() in __init__ to record
    their pending source sensors. Actual binding is deferred until
    finalise_binding() is called by the framework (via bind_cross_device_sensors)
    after all devices for the plant are fully constructed.

    Unlike ordinary DerivedSensors, these sensors are registered in all_sensors
    by _add_sensor without source validation — the validation occurs during
    finalise_binding() which searches all devices in the DeviceRegistry.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Sources declared via declare_cross_device_sources(); kept separate
        # from source_sensors until finalise_binding() runs.
        self._pending_sources: list[Sensor] = []

    def declare_cross_device_sources(self, *sensors: Sensor) -> None:
        """Record sources that may live on any device in the plant.

        Must be called from __init__ instead of _declare_source_sensors().
        Actual binding is completed by finalise_binding() once all devices exist.
        """
        self._pending_sources = [s for s in sensors if s is not None]
        if not self._pending_sources:
            log_id = getattr(self, "_log_identity", self.__class__.__name__)
            logging.error(f"{log_id} - no declared cross-device sources")

    def finalise_binding(self, plant_index: int) -> bool:
        """Wire up sources from the full device graph after all devices are constructed.

        Searches every device registered under plant_index for each pending
        source sensor. Applies protocol filtering and calls add_derived_sensor /
        bind_source_sensor exactly as _add_sensor does for ordinary DerivedSensors.

        Must only be called after this sensor has been added to a device
        (i.e. parent_device is set) and after all sibling/peer devices for the
        plant have been constructed and registered in the DeviceRegistry.

        Args:
            plant_index: The plant index to search for sources.

        Returns:
            True if at least one source was bound successfully.
        """
        import logging

        from sigenergy2mqtt.devices.base.registry import DeviceRegistry

        owner_device = self.parent_device
        if owner_device is None:
            raise RuntimeError(
                f"{self.log_identity} finalise_binding called before sensor was added to a device"
            )

        added = False
        for pending in self._pending_sources:
            # Skip sources that violate the owner device's protocol version
            if (
                owner_device.protocol_version > Protocol.N_A
                and pending.protocol_version > owner_device.protocol_version
            ):
                logging.debug(
                    f"{self.log_identity} skipped cross-device binding of "
                    f"{pending.__class__.__name__} - source protocol {pending.protocol_version} "
                    f"> device protocol {owner_device.protocol_version}"
                )
                continue

            # Search all devices registered for this plant
            found: Sensor | None = None
            for device in DeviceRegistry.get(plant_index):
                found = device.get_sensor(pending.unique_id, search_children=True)
                if found:
                    break

            if not found:
                logging.warning(
                    f"{self.log_identity} cannot bind cross-device source "
                    f"{pending.__class__.__name__} ({pending.unique_id}) - "
                    f"not found in plant {plant_index}"
                )
                continue

            if found not in self.bound_source_sensors:
                found.add_derived_sensor(self)
                self.bind_source_sensor(found)
                added = True
                if self.debug_logging:
                    logging.debug(
                        f"{self.log_identity} bound cross-device source "
                        f"{found.__class__.__name__} from "
                        f"{getattr(found.parent_device, 'log_identity', 'unknown')}"
                    )

        # Populate source_sensors from what was actually bound so that the
        # rest of the framework (protocol checks, etc.) can inspect it.
        self.source_sensors = list(self.bound_source_sensors)
        self._pending_sources = []
        return added
