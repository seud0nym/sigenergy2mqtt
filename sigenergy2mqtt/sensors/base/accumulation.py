"""Accumulation sensors: ResettableAccumulationSensor, EnergyLifetimeAccumulationSensor, EnergyDailyAccumulationSensor."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import DeviceClass, StateClass, UnitOfEnergy
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

from .constants import DiscoveryKeys, SensorAttributeKeys, _sanitize_path_component
from .derived import DerivedSensor
from .mixins import ObservableMixin
from .readable import ReadOnlySensor
from .sensor import Sensor

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

# =============================================================================


class ResettableAccumulationSensor(ObservableMixin, DerivedSensor):
    """Sensor that accumulates values with manual reset capability.

    Integrates power readings over time to calculate energy, with ability
    to reset the accumulated value via MQTT.
    """

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        data_type: ModbusDataType,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            data_type=data_type,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
            **kwargs,
        )

        self._source = source
        self._reset_topic = f"sigenergy2mqtt/{self[DiscoveryKeys.OBJECT_ID]}/reset"
        self._current_total_lock = asyncio.Lock()
        self._current_total: float = 0.0

        # Use sanitized unique_id for file paths
        uid = str(self.unique_id)
        if uid.startswith("<MagicMock"):  # For testing
            uid = "mock_uid"

        safe_uid = _sanitize_path_component(uid)
        self._persistent_state_file = Path(active_config.persistent_state_path, f"{safe_uid}.state")

        # Load persisted state
        self._load_persisted_state()
        self.set_latest_state(self._current_total)

    def _load_persisted_state(self) -> None:
        """Load accumulated value from persistent storage."""
        if not self._persistent_state_file.is_file():
            return

        try:
            with self._persistent_state_file.open("r") as f:
                content = f.read().strip()
                if content and content != "None":
                    self._current_total = float(content)
                    logging.debug(f"{self.__class__.__name__} Loaded current state from {self._persistent_state_file} ({self._current_total})")
        except (OSError, ValueError, PermissionError) as e:
            logging.warning(f"{self.__class__.__name__} Failed to read {self._persistent_state_file}: {e}")
        except Exception as e:
            logging.error(f"{self.__class__.__name__} Unexpected error reading {self._persistent_state_file}: {e}")

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        """Get discovery components including reset control.

        Returns:
            Dictionary of component configurations
        """
        # Create reset number input
        updater: dict[str, Any] = {
            DiscoveryKeys.PLATFORM: "number",
            DiscoveryKeys.NAME: _t(f"{self.__class__.__name__}.name_reset", f"Set {self.name}", self.debug_logging),
            DiscoveryKeys.OBJECT_ID: f"{self[DiscoveryKeys.OBJECT_ID]}_reset",
            DiscoveryKeys.UNIQUE_ID: f"{self.unique_id}_reset",
            DiscoveryKeys.ICON: "mdi:numeric",
            DiscoveryKeys.UNIT_OF_MEASUREMENT: self.unit,
            DiscoveryKeys.DISPLAY_PRECISION: self.precision,
            DiscoveryKeys.COMMAND_TOPIC: self._reset_topic,
            DiscoveryKeys.MIN: 0,
            DiscoveryKeys.MAX: sys.float_info.max,
            DiscoveryKeys.MODE: "box",
            DiscoveryKeys.STEP: 10 ** -(self.precision if self.precision else 0),
            DiscoveryKeys.ENABLED_BY_DEFAULT: self.publishable,
        }

        components: dict[str, dict[str, Any]] = super().get_discovery_components()
        components[updater[DiscoveryKeys.UNIQUE_ID]] = updater

        return components

    def observable_topics(self) -> set[str]:
        """Get observable MQTT topics including reset topic.

        Returns:
            Set of topic strings
        """
        topics = super().observable_topics()
        topics.add(self._reset_topic)
        return topics

    def get_attributes(self) -> dict[str, float | int | str]:
        """Get sensor attributes including reset topic.

        Returns:
            Dictionary of attributes
        """
        attributes = super().get_attributes()
        attributes[SensorAttributeKeys.RESET_TOPIC] = self._reset_topic
        if self.unit:
            attributes[SensorAttributeKeys.RESET_UNIT] = self.unit
        return attributes

    async def _persist_current_total(self, new_total: float) -> None:
        """Persist accumulated value to file.

        Args:
            new_total: New total value to persist
        """
        async with self._current_total_lock:
            try:
                with self._persistent_state_file.open("w") as f:
                    f.write(str(new_total))
            except (OSError, PermissionError) as e:
                logging.error(f"Failed to persist state: {e}")
            except Exception as e:
                logging.error(f"Unexpected error persisting state: {e}")

    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Handle reset command from MQTT.

        Args:
            modbus_client: Modbus client (unused)
            mqtt_client: MQTT client
            value: New total value
            source: Source topic
            handler: MQTT handler

        Returns:
            True if reset was handled
        """
        if source not in self.observable_topics():
            return False

        new_total = (value if isinstance(value, float) else float(value)) * self.gain

        logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} (raw={new_total})")

        if new_total != self._current_total:
            await self._persist_current_total(new_total)

        self._current_total = new_total
        self.set_latest_state(self._current_total)
        self.force_publish = True

        return True

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        """Update accumulated value from source sensor.

        Args:
            sensor: Source sensor providing power readings
            values: List of (timestamp, value) tuples

        Returns:
            True if accumulation was updated
        """
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False

        if len(values) < 2:
            return False  # Need at least two points

        # Calculate time difference in hours
        interval_hours = sensor.latest_interval / 3600 if sensor.latest_interval else 0

        if interval_hours < 0:
            logging.warning(f"{self.__class__.__name__} negative interval IGNORED (interval={sensor.latest_interval})")
            return False

        # Convert negative power to zero
        previous = max(0.0, values[-2][1])
        current = max(0.0, values[-1][1])

        # Calculate energy using trapezoidal rule: E = 0.5 * (P1 + P2) * Δt
        increase = 0.5 * (previous + current) * interval_hours
        new_total = self._current_total + increase

        # Check for decreasing total
        if new_total < self._current_total and self.state_class == StateClass.TOTAL_INCREASING:
            logging.debug(
                f"{self.__class__.__name__} negative increase IGNORED (current={self._current_total} prev={previous} curr={current} increase={increase} new={new_total} interval={sensor.latest_interval:.2f}s)"
            )
            return False

        # Update total
        if new_total != self._current_total:
            coro = self._persist_current_total(new_total)
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
                except Exception:
                    coro.close()
            except Exception:
                coro.close()

        self._current_total = new_total
        self.set_latest_state(self._current_total)

        return True


# =============================================================================
# Energy Accumulation Sensors
# =============================================================================


class EnergyLifetimeAccumulationSensor(ResettableAccumulationSensor):
    """Lifetime energy accumulation sensor.

    Tracks total energy over the lifetime of the device.
    """

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        data_type=None,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=DeviceClass.ENERGY,
        state_class=StateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt",
        gain=1000,
        precision=2,
        **kwargs,
    ):
        if data_type is None:
            data_type = ModbusDataType.UINT32

        super().__init__(
            name,
            unique_id,
            object_id,
            source,
            data_type=data_type,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
            **kwargs,
        )


class EnergyDailyAccumulationSensor(ResettableAccumulationSensor):
    """Daily energy accumulation sensor.

    Tracks energy for the current day, automatically resetting at midnight.
    """

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: ReadOnlySensor | DerivedSensor,
        **kwargs,
    ):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            source=source,
            data_type=source.data_type,
            unit=source.unit,
            device_class=source.device_class,
            state_class=source.state_class,
            icon=cast(str, source[DiscoveryKeys.ICON]),
            gain=source.gain,
            precision=source.precision,
            **kwargs,
        )

        self._state_at_midnight_lock = asyncio.Lock()
        self._state_at_midnight: float | None = None

        # Use sanitized unique_id for file path
        uid = str(source.unique_id)
        if uid.startswith("<MagicMock"):
            uid = "mock_uid_atmidnight"

        safe_uid = _sanitize_path_component(uid)
        self._persistent_state_file = Path(active_config.persistent_state_path, f"{safe_uid}.atmidnight")

        # Load midnight state if it's from today
        self._load_midnight_state()

    def _load_midnight_state(self) -> None:
        """Load state at midnight if file is from today."""
        if not self._persistent_state_file.is_file():
            return

        try:
            file_time = time.localtime(self._persistent_state_file.stat().st_mtime)
            now = time.localtime()

            # Check if file is from today
            if not (file_time.tm_year == now.tm_year and file_time.tm_mon == now.tm_mon and file_time.tm_mday == now.tm_mday):
                logging.debug(f"{self.__class__.__name__} Ignored stale midnight state file {self._persistent_state_file} (from {file_time})")
                self._persistent_state_file.unlink(missing_ok=True)
                return

            with self._persistent_state_file.open("r") as f:
                content = f.read().strip()
                if content and content != "None":
                    value = float(content)
                    if value <= 0.0:
                        logging.debug(f"{self.__class__.__name__} Ignored negative midnight state from {self._persistent_state_file} ({value})")
                        self._persistent_state_file.unlink()
                    else:
                        self._state_at_midnight = value
                        logging.debug(f"{self.__class__.__name__} Loaded midnight state from {self._persistent_state_file} ({self._state_at_midnight})")
        except (OSError, ValueError, PermissionError) as e:
            logging.warning(f"{self.__class__.__name__} Failed to read {self._persistent_state_file}: {e}")
            self._persistent_state_file.unlink(missing_ok=True)
        except Exception as e:
            logging.error(f"{self.__class__.__name__} Unexpected error reading {self._persistent_state_file}: {e}")

    async def _update_state_at_midnight(self, midnight_state: float | None) -> None:
        """Persist state at midnight.

        Args:
            midnight_state: State value at midnight
        """
        if midnight_state is None:
            return

        async with self._state_at_midnight_lock:
            try:
                with self._persistent_state_file.open("w") as f:
                    f.write(str(midnight_state))
                self._state_at_midnight = midnight_state
            except (OSError, PermissionError) as e:
                logging.error(f"Failed to update midnight state: {e}")
            except Exception as e:
                logging.error(f"Unexpected error updating midnight state: {e}")

    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Handle reset command.

        Args:
            modbus_client: Modbus client (unused)
            mqtt_client: MQTT client
            value: New value
            source: Source topic
            handler: MQTT handler

        Returns:
            True if handled
        """
        if source not in self.observable_topics():
            return False

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} notified of updated state {value} {self.unit}")

        self._state_now = (value if isinstance(value, float) else float(value)) * self.gain

        # Calculate new midnight state
        updated_midnight_state = self._source.latest_raw_state - self._state_now if isinstance(self._source.latest_raw_state, (float, int)) and self._source.latest_raw_state else self._state_now

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} source_raw={self._source.latest_raw_state} (from {self._source.unique_id}) state_now={self._state_now} midnight_state={updated_midnight_state}")

        await self._update_state_at_midnight(updated_midnight_state)
        self.set_latest_state(self._state_now)

        logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} (raw={self._state_now})")

        self.force_publish = True
        return True

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
        """Publish state, ensuring midnight state is persisted.

        Args:
            mqtt_client: MQTT client
            modbus_client: Modbus client
            republish: If True, republish last state

        Returns:
            True if published
        """
        if not self._persistent_state_file.is_file():
            await self._update_state_at_midnight(self._state_at_midnight)

        return await super().publish(mqtt_client, modbus_client, republish)

    def set_source_values(self, sensor: Sensor, values: Deque[tuple[float, Any]]) -> bool:
        """Update daily accumulation from source values.

        Args:
            sensor: Source sensor
            values: List of (timestamp, value) tuples

        Returns:
            True if updated
        """
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False

        now_state = values[-1][1]

        # Check for day change
        if len(values) > 1:
            was_time = time.localtime(values[-2][0])
            now_time = time.localtime(values[-1][0])

            if was_time.tm_year != now_time.tm_year or was_time.tm_mon != now_time.tm_mon or was_time.tm_mday != now_time.tm_mday:
                # Day changed - reset midnight state
                coro = self._update_state_at_midnight(now_state)
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
                    except Exception:
                        coro.close()
                except Exception:
                    coro.close()
                self._states.clear()
                self._state_at_midnight = now_state

        # Initialize midnight state if needed
        if not self._state_at_midnight:
            self._state_at_midnight = now_state

        # Calculate today's accumulation
        self._state_now = now_state - self._state_at_midnight
        self.set_latest_state(self._state_now)

        return True


# =============================================================================
# PV Power Sensor
