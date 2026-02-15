"""Base sensor classes for Sigenergy2MQTT integration.

This module provides the core sensor classes and mixins for reading/writing
Modbus registers and publishing to MQTT with Home Assistant discovery support.
"""

from __future__ import annotations

import abc
import asyncio
import datetime
import html
import json
import logging
import re
import sys
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, Final, Iterable, TypeAlias, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.common import HybridInverter, Protocol, PVInverter, RegisterAccess
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus.types import ModbusClientType, ModbusDataType

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

from .const import PERCENTAGE, DeviceClass, InputType, StateClass, UnitOfEnergy
from .sanity_check import SanityCheck, SanityCheckException

# =============================================================================
# Constants
# =============================================================================

# State history configuration
_DEFAULT_STATE_HISTORY_SIZE: Final = 2  # Keep current and previous state for delta calculations


# MQTT Configuration Keys
class DiscoveryKeys:
    """Constants for MQTT message keys."""

    PLATFORM = "platform"
    NAME = "name"
    OBJECT_ID = "object_id"
    UNIQUE_ID = "unique_id"
    DEVICE_CLASS = "device_class"
    ICON = "icon"
    STATE_CLASS = "state_class"
    UNIT_OF_MEASUREMENT = "unit_of_measurement"
    DISPLAY_PRECISION = "display_precision"
    ENABLED_BY_DEFAULT = "enabled_by_default"
    STATE_TOPIC = "state_topic"
    RAW_STATE_TOPIC = "raw_state_topic"
    JSON_ATTRIBUTES_TOPIC = "json_attributes_topic"
    AVAILABILITY_MODE = "availability_mode"
    AVAILABILITY = "availability"
    COMMAND_TOPIC = "command_topic"
    OPTIONS = "options"
    PAYLOAD_OFF = "payload_off"
    PAYLOAD_ON = "payload_on"
    STATE_OFF = "state_off"
    STATE_ON = "state_on"
    MIN = "min"
    MAX = "max"
    MODE = "mode"
    STEP = "step"
    ENTITY_CATEGORY = "entity_category"
    DEFAULT_ENTITY_ID = "default_entity_id"


# Sensor attribute keys
class SensorAttributeKeys:
    """Constants for sensor attribute keys."""

    NAME = "name"
    UNIT_OF_MEASUREMENT = "unit-of-measurement"
    SENSOR_CLASS = "sensor-class"
    SINCE_PROTOCOL = "since-protocol"
    GAIN = "gain"
    SCAN_INTERVAL = "scan-interval"
    UPDATE_TOPIC = "update-topic"
    SOURCE = "source"
    COMMENT = "comment"
    RESET_TOPIC = "reset_topic"
    RESET_UNIT = "reset_unit"


# Type aliases for better readability
SensorValue: TypeAlias = str | int | bool | float | list[str] | list[dict[str, str]] | tuple[float, ...]
SensorAttribute: TypeAlias = SensorValue | DeviceClass | StateClass | None
SensorDict: TypeAlias = dict[str, SensorAttribute]
StateHistory: TypeAlias = list[tuple[float, Any]]


# =============================================================================
# Module-level utilities with proper error handling
# =============================================================================


class _ModbusLockFactoryProxy:
    """Lazy proxy for ModbusLockFactory to avoid circular imports."""

    @staticmethod
    def get(modbus):
        from sigenergy2mqtt.modbus import ModbusLockFactory as _Real

        return _Real.get(modbus)

    @staticmethod
    def get_waiter_count() -> int:
        from sigenergy2mqtt.modbus import ModbusLockFactory as _Real

        return _Real.get_waiter_count()


ModbusLockFactory = _ModbusLockFactoryProxy


def _load_metrics_module() -> Any:
    """Load the metrics module with proper error handling.

    Returns:
        The Metrics class/module if available, None otherwise.
    """
    try:
        import importlib

        metrics_module = importlib.import_module("sigenergy2mqtt.metrics.metrics")
        return getattr(metrics_module, "Metrics", metrics_module)
    except ImportError:
        logging.info("Metrics module not available - metrics collection disabled")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading metrics module: {e}")
        return None


Metrics = _load_metrics_module()


def _sanitize_path_component(component: str) -> str:
    """Sanitize a string for safe use in file paths.

    Args:
        component: The path component to sanitize

    Returns:
        Sanitized string safe for use in filenames
    """
    # Replace path separators and other unsafe characters
    unsafe_chars = ["/", "\\", "..", "\0", "\n", "\r", "\t"]
    sanitized = component
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, "_")
    return sanitized


# =============================================================================
# Mixin Classes
# =============================================================================


class SensorDebuggingMixin:
    """Mixin that adds debug logging capability to sensors."""

    def __init__(self, **kwargs):
        self.debug_logging: bool = kwargs.get("debug_logging", Config.sensor_debug_logging)
        super().__init__(**kwargs)


class TypedSensorMixin:
    """Mixin that adds Modbus data type validation to sensors.

    Ensures sensors specify a valid ModbusDataType during initialization.
    This mixin should be used before other sensor base classes in the MRO.
    """

    def __init__(self, **kwargs):
        if "data_type" not in kwargs:
            raise AssertionError("Missing required parameter: data_type")

        if kwargs["data_type"] not in ModbusDataType:
            raise AssertionError(f"Invalid data type {kwargs['data_type']}")

        self.data_type = kwargs.pop("data_type")
        super().__init__(**kwargs)


# =============================================================================
# Base Sensor Class
# =============================================================================


class Sensor(SensorDebuggingMixin, dict[str, SensorAttribute], metaclass=abc.ABCMeta):
    """Base class for all sensors in the Sigenergy2MQTT system.

    This class provides core functionality for:
    - MQTT topic configuration and discovery
    - State management and history
    - Sensor value validation and transformation
    - Publishing state to MQTT brokers
    - Attribute management for Home Assistant integration

    Attributes:
        _requires_delta_check: Whether this sensor type requires delta validation.
                               Override in subclasses to disable (e.g., Available sensors).
    """

    # Class-level tracking of used IDs (intentional shared state)
    _used_object_ids: dict[str, str] = {}
    _used_unique_ids: dict[str, str] = {}

    # Class attribute to control delta checking behaviour
    _requires_delta_check: bool = True

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol = Protocol.V2_4,
        **kwargs,
    ):
        # Validate unique_id
        self._validate_unique_id(unique_id)

        # Validate object_id
        self._validate_object_id(object_id)

        # Validate icon format
        if icon is not None and not icon.startswith("mdi:"):
            raise AssertionError(f"{self.__class__.__name__} icon {icon} does not start with 'mdi:'")

        # Validate protocol version
        if not isinstance(protocol_version, Protocol):
            raise AssertionError(f"{self.__class__.__name__} protocol_version '{protocol_version}' is invalid")

        super().__init__(**kwargs)

        # Register IDs
        self._used_unique_ids[unique_id] = self.__class__.__name__
        self._used_object_ids[object_id] = self.__class__.__name__

        self._protocol_version = protocol_version

        # Initialize dict properties
        self[DiscoveryKeys.PLATFORM] = "sensor"
        self[DiscoveryKeys.NAME] = _t(f"{self.__class__.__name__}.name", name, self.debug_logging, **kwargs)
        self[DiscoveryKeys.OBJECT_ID] = object_id
        self[DiscoveryKeys.UNIQUE_ID] = unique_id
        self[DiscoveryKeys.DEVICE_CLASS] = device_class
        self[DiscoveryKeys.ICON] = icon
        self[DiscoveryKeys.STATE_CLASS] = state_class
        self[DiscoveryKeys.UNIT_OF_MEASUREMENT] = unit
        self[DiscoveryKeys.DISPLAY_PRECISION] = precision
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = Config.home_assistant.enabled_by_default

        self._gain: float | None = gain
        self._derived_sensors: dict[str, DerivedSensor] = {}

        # Publishing state
        self._attributes_published: bool = False
        self._publish_raw: bool = False
        self._publishable: bool = True

        # Use sanitized unique_id for file paths
        safe_unique_id = _sanitize_path_component(unique_id)
        self._persistent_publish_state_file: Path = Path(Config.persistent_state_path, f"{safe_unique_id}.publishable")

        # State history - use deque for efficient bounded collection
        self._states: Deque[tuple[float, Any]] = deque(maxlen=_DEFAULT_STATE_HISTORY_SIZE)

        # Failure tracking
        self._failures: int = 0
        self._max_failures: int = 10
        self._max_failures_retry_interval: int = 0
        self._next_retry: float | None = None

        # MQTT configuration
        self._qos: int = 0
        self._retain: bool = False

        # Public attributes
        self.force_publish: bool = False
        self.name: str = name
        self.object_id: str = object_id
        self.parent_device: Any = None
        self.precision: int | None = precision
        self.sleeper_task: asyncio.Task[None] | None = None
        self.state_class: StateClass | None = state_class
        self.unit: str | None = unit
        self.unique_id: str = unique_id

        # Sanity checking
        self.sanity_check: SanityCheck = SanityCheck(
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            gain=gain,
            precision=precision,
            data_type=getattr(self, "data_type", None),
            delta=not self._requires_delta_check if self._requires_delta_check is not None else None,
        )

    def _validate_unique_id(self, unique_id: str) -> None:
        """Validate that unique_id is not duplicated and has correct prefix.

        Args:
            unique_id: The unique identifier to validate

        Raises:
            ValueError: If validation fails
        """
        if unique_id in self._used_unique_ids and self._used_unique_ids[unique_id] != self.__class__.__name__:
            raise AssertionError(f"{self.__class__.__name__} unique_id {unique_id} has already been used for class {self._used_unique_ids[unique_id]}")

        if not unique_id.startswith(Config.home_assistant.unique_id_prefix):
            raise AssertionError(f"{self.__class__.__name__} unique_id {unique_id} does not start with '{Config.home_assistant.unique_id_prefix}'")

    def _validate_object_id(self, object_id: str) -> None:
        """Validate that object_id is not duplicated and has correct prefix.

        Args:
            object_id: The object identifier to validate

        Raises:
            ValueError: If validation fails
        """
        if object_id in self._used_object_ids and self._used_object_ids[object_id] != self.__class__.__name__:
            raise AssertionError(f"{self.__class__.__name__} object_id {object_id} has already been used for class {self._used_object_ids[object_id]}")

        if not object_id.startswith(Config.home_assistant.entity_id_prefix):
            raise AssertionError(f"{self.__class__.__name__} object_id {object_id} does not start with '{Config.home_assistant.entity_id_prefix}'")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def device_class(self) -> DeviceClass:
        """Get the device class of this sensor."""
        return cast(DeviceClass, self[DiscoveryKeys.DEVICE_CLASS])

    @property
    def gain(self) -> float:
        """Get the gain multiplier for this sensor (default 1.0)."""
        return 1.0 if self._gain is None else self._gain

    @gain.setter
    def gain(self, value: float | None):
        """Set the gain multiplier for this sensor."""
        self._gain = value

    @property
    def latest_interval(self) -> float | None:
        """Get time interval between last two states in seconds."""
        return None if len(self._states) < 2 else self._states[-1][0] - self._states[-2][0]

    @property
    def latest_raw_state(self) -> float | int | str | None:
        """Get the most recent raw state value."""
        return None if len(self._states) == 0 else self._states[-1][1]

    @latest_raw_state.setter
    def latest_raw_state(self, value: float | int | str):
        """Update the most recent raw state value."""
        if len(self._states) > 0:
            latest = self._states.pop()
            self._states.append((latest[0], value))

    @property
    def latest_time(self) -> float:
        """Get timestamp of most recent state."""
        return 0 if len(self._states) == 0 else self._states[-1][0]

    @property
    def protocol_version(self) -> Protocol:
        """Get the protocol version this sensor was introduced in."""
        return self._protocol_version if self._protocol_version else Protocol.N_A

    @protocol_version.setter
    def protocol_version(self, protocol_version: Protocol | float):
        """Set the protocol version this sensor was introduced in."""
        if isinstance(protocol_version, Protocol):
            self._protocol_version = protocol_version
        elif isinstance(protocol_version, float):
            if protocol_version not in [p.value for p in Protocol]:
                raise AssertionError(f"{self.__class__.__name__}: Invalid protocol_version '{protocol_version}'")
            protocol = {p.value: p for p in Protocol}.get(protocol_version)
            if protocol is None:
                raise AssertionError(f"{self.__class__.__name__}: Invalid protocol_version '{protocol_version}'")
            self._protocol_version = protocol
        else:
            raise AssertionError(f"{self.__class__.__name__}: protocol_version must be Protocol or float, got {type(protocol_version)}")

    @property
    def publishable(self) -> bool:
        """Check if this sensor should be published to MQTT."""
        return self._publishable

    @publishable.setter
    def publishable(self, value: bool):
        """Set whether this sensor should be published to MQTT."""
        if not isinstance(value, bool):
            raise ValueError(f"{self.__class__.__name__}.publishable must be a bool")

        if self._publishable == value:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__}.publishable unchanged ({value})")
        else:
            self._publishable = value
            logging.debug(f"{self.__class__.__name__}.publishable set to {value}")

    @property
    def publish_raw(self) -> bool:
        """Check if raw values should be published alongside processed values."""
        return self._publish_raw

    @publish_raw.setter
    def publish_raw(self, value: bool):
        """Set whether raw values should be published."""
        if not isinstance(value, bool):
            raise ValueError(f"{self.__class__.__name__}.publish_raw must be a bool")

        if self._publish_raw == value:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__}.publish_raw unchanged ({value})")
        else:
            self._publish_raw = value
            logging.debug(f"{self.__class__.__name__}.publish_raw set to {value}")

    @property
    def raw_state_topic(self) -> str:
        """Get the MQTT topic for publishing raw state values."""
        return cast(str, self[DiscoveryKeys.RAW_STATE_TOPIC])

    @property
    def state_topic(self) -> str:
        """Get the MQTT topic for publishing processed state values."""
        return cast(str, self[DiscoveryKeys.STATE_TOPIC])

    # =========================================================================
    # Abstract Methods
    # =========================================================================

    @abc.abstractmethod
    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Retrieve current state and update internal state history.

        Args:
            **kwargs: Implementation-specific arguments.

        Returns:
            True if state was updated, False otherwise, or Exception on error.
        """
        pass

    # =========================================================================
    # Public Methods
    # =========================================================================

    def add_derived_sensor(self, sensor: DerivedSensor) -> None:
        """Add a derived sensor that depends on this sensor's values.

        Args:
            sensor: The derived sensor to add
        """
        self._derived_sensors[sensor.__class__.__name__] = sensor

    def apply_sensor_overrides(self, registers: RegisterAccess | None):
        """Apply configuration overrides from config file.

        Args:
            registers: Register access configuration for this device
        """
        # Pre-compile regex patterns for efficiency
        identifier_patterns = {identifier: re.compile(identifier) for identifier in Config.sensor_overrides.keys()}

        for identifier, pattern in identifier_patterns.items():
            if self._matches_override_pattern(pattern):
                self._apply_override(identifier, Config.sensor_overrides[identifier])

        # Apply device-level overrides
        if self.publishable and registers:
            self._apply_device_overrides(registers)

    def _matches_override_pattern(self, pattern: re.Pattern) -> bool:
        """Check if this sensor matches an override pattern.

        Args:
            pattern: Compiled regex pattern to match against

        Returns:
            True if pattern matches class name, object_id, or unique_id
        """
        return bool(pattern.search(self.__class__.__name__) or pattern.search(self.object_id) or pattern.search(self.unique_id))

    def _apply_override(self, identifier: str, overrides: dict) -> None:
        """Apply a specific override configuration.

        Args:
            identifier: The override identifier
            overrides: Dictionary of override values
        """
        override_handlers = {
            "debug-logging": self._override_debug_logging,
            "gain": self._override_gain,
            "icon": self._override_icon,
            "max-failures": self._override_max_failures,
            "max-failures-retry-interval": self._override_max_failures_retry_interval,
            "precision": self._override_precision,
            "publishable": self._override_publishable,
            "publish-raw": self._override_publish_raw,
            "sanity-check-delta": self._override_sanity_check_delta,
            "sanity-check-max-value": self._override_sanity_check_max,
            "sanity-check-min-value": self._override_sanity_check_min,
            "unit-of-measurement": self._override_unit,
            "device-class": self._override_device_class,
            "state-class": self._override_state_class,
            "name": self._override_name,
        }

        for key, handler in override_handlers.items():
            if key in overrides:
                handler(identifier, overrides[key])

    def _override_debug_logging(self, identifier: str, value: bool) -> None:
        """Apply debug logging override."""
        if self.debug_logging != value:
            self.debug_logging = value
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'debug-logging' override ({value})")

    def _override_gain(self, identifier: str, value: float) -> None:
        """Apply gain override."""
        if self._gain != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'gain' override ({value})")
            self._gain = value

    def _override_icon(self, identifier: str, value: str) -> None:
        """Apply icon override."""
        if self[DiscoveryKeys.ICON] != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'icon' override ({value})")
            self[DiscoveryKeys.ICON] = value

    def _override_max_failures(self, identifier: str, value: int) -> None:
        """Apply max failures override."""
        if self._max_failures != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'max-failures' override ({value})")
            self._max_failures = value

    def _override_max_failures_retry_interval(self, identifier: str, value: int) -> None:
        """Apply max failures retry interval override."""
        if self._max_failures_retry_interval != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'max-failures-retry-interval' override ({value})")
            self._max_failures_retry_interval = value

    def _override_precision(self, identifier: str, value: int) -> None:
        """Apply precision override."""
        if self.precision != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'precision' override ({value})")
            self.precision = value
            self[DiscoveryKeys.DISPLAY_PRECISION] = self.precision

    def _override_publishable(self, identifier: str, value: bool) -> None:
        """Apply publishable override."""
        if self.publishable != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'publishable' override ({value})")
            self.publishable = value

    def _override_publish_raw(self, identifier: str, value: bool) -> None:
        """Apply publish-raw override."""
        if self.publish_raw != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'publish-raw' override ({value})")
            self.publish_raw = value

    def _override_sanity_check_delta(self, identifier: str, value: bool) -> None:
        """Apply sanity check delta override."""
        if self.sanity_check.delta != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-delta' override ({value})")
            self.sanity_check.delta = value

    def _override_sanity_check_max(self, identifier: str, value: float) -> None:
        """Apply sanity check max value override."""
        if self.sanity_check.max_raw != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-max-value' override ({value})")
            self.sanity_check.max_raw = value

    def _override_sanity_check_min(self, identifier: str, value: float) -> None:
        """Apply sanity check min value override."""
        if self.sanity_check.min_raw != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-min-value' override ({value})")
            self.sanity_check.min_raw = value

    def _override_unit(self, identifier: str, value: str) -> None:
        """Apply unit of measurement override."""
        if self[DiscoveryKeys.UNIT_OF_MEASUREMENT] != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'unit-of-measurement' override ({value})")
            self[DiscoveryKeys.UNIT_OF_MEASUREMENT] = value

    def _override_device_class(self, identifier: str, value: DeviceClass) -> None:
        """Apply device class override."""
        if self[DiscoveryKeys.DEVICE_CLASS] != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'device-class' override ({value})")
            self[DiscoveryKeys.DEVICE_CLASS] = value

    def _override_state_class(self, identifier: str, value: StateClass) -> None:
        """Apply state class override."""
        if self[DiscoveryKeys.STATE_CLASS] != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'state-class' override ({value})")
            self[DiscoveryKeys.STATE_CLASS] = value

    def _override_name(self, identifier: str, value: str) -> None:
        """Apply name override."""
        if self[DiscoveryKeys.NAME] != value:
            logging.debug(f"{self.__class__.__name__} Applying {identifier} 'name' override ({value})")
            self[DiscoveryKeys.NAME] = value

    def _apply_device_overrides(self, registers: RegisterAccess) -> None:
        """Apply device-level publishable overrides.

        Args:
            registers: Register access configuration for this device
        """
        # Check for remote EMS override
        if registers.no_remote_ems and (getattr(self, "_remote_ems", None) is not None or getattr(self, "address", None) == 40029):
            logging.debug(f"{self.__class__.__name__} Applying device 'no-remote-ems' override ({registers.no_remote_ems})")
            self.publishable = False
            return

        # Check read/write permissions
        if isinstance(self, WritableSensorMixin) and not isinstance(self, WriteOnlySensor):
            if not registers.read_write:
                logging.debug(f"{self.__class__.__name__} Applying device 'read-write' override ({registers.read_write})")
                self.publishable = registers.read_write
        elif isinstance(self, (ReadableSensorMixin, DerivedSensor)):
            if not registers.read_only:
                logging.debug(f"{self.__class__.__name__} Applying device 'read-only' override ({registers.read_only})")
                self.publishable = registers.read_only
        elif isinstance(self, WriteOnlySensor):
            if not registers.write_only:
                logging.debug(f"{self.__class__.__name__} Applying device 'write-only' override ({registers.write_only})")
                self.publishable = registers.write_only
        else:
            logging.warning(f"{self.__class__.__name__} Failed to determine superclass to apply device publishable overrides")

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure MQTT topics for this sensor.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        base = self._get_base_topic(device_id)

        self[DiscoveryKeys.STATE_TOPIC] = f"{base}/state"
        self[DiscoveryKeys.RAW_STATE_TOPIC] = f"{base}/raw"
        self[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC] = f"{base}/attributes"

        if Config.home_assistant.enabled:
            self[DiscoveryKeys.AVAILABILITY_MODE] = "all"
            self[DiscoveryKeys.AVAILABILITY] = [{"topic": f"{Config.home_assistant.discovery_prefix}/device/{device_id}/availability"}]

        if self.debug_logging:
            self._log_configured_topics()

        return base

    def _get_base_topic(self, device_id: str) -> str:
        """Get the base MQTT topic for this sensor.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        if Config.home_assistant.enabled and not Config.home_assistant.use_simplified_topics:
            return f"{Config.home_assistant.discovery_prefix}/{self[DiscoveryKeys.PLATFORM]}/{device_id}/{self[DiscoveryKeys.OBJECT_ID]}"
        else:
            return f"sigenergy2mqtt/{self[DiscoveryKeys.OBJECT_ID]}"

    def _log_configured_topics(self) -> None:
        """Log the configured MQTT topics for debugging."""
        logging.debug(f"{self.__class__.__name__} Configured MQTT topics (enabled={Config.home_assistant.enabled} simplified={Config.home_assistant.use_simplified_topics})")
        for key in (DiscoveryKeys.STATE_TOPIC, DiscoveryKeys.RAW_STATE_TOPIC, DiscoveryKeys.JSON_ATTRIBUTES_TOPIC, DiscoveryKeys.AVAILABILITY):
            if key in self:
                logging.debug(f"{self.__class__.__name__} >>> {key}={self[key]})")

    def get_attributes(self) -> dict[str, float | int | str]:
        """Get sensor attributes for MQTT publishing.

        Returns:
            Dictionary of sensor attributes
        """
        attributes: dict[str, float | int | str] = {}

        if not Config.home_assistant.enabled:
            attributes[SensorAttributeKeys.NAME] = self.name
            if self.unit:
                attributes[SensorAttributeKeys.UNIT_OF_MEASUREMENT] = self.unit

        attributes[SensorAttributeKeys.SENSOR_CLASS] = self.__class__.__name__

        if self.protocol_version and self.protocol_version != Protocol.N_A:
            attributes[SensorAttributeKeys.SINCE_PROTOCOL] = f"V{self.protocol_version.value}"

        if self._gain:
            attributes[SensorAttributeKeys.GAIN] = self._gain

        if isinstance(self, ReadableSensorMixin):
            attributes[SensorAttributeKeys.SCAN_INTERVAL] = self.scan_interval

        if isinstance(self, WritableSensorMixin):
            attributes[SensorAttributeKeys.UPDATE_TOPIC] = self.command_topic

        return attributes

    def get_discovery(self, mqtt_client: mqtt.Client) -> dict[str, dict[str, Any]]:
        """Get Home Assistant discovery configuration.

        Args:
            mqtt_client: MQTT client for publishing messages

        Returns:
            Dictionary of discovery configurations by unique_id
        """
        if DiscoveryKeys.STATE_TOPIC not in self:
            raise RuntimeError(f"{self.__class__.__name__} MQTT topics are not configured")

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Getting discovery")

        components = self.get_discovery_components()

        # Clean up discovery components
        for config in components.values():
            if DiscoveryKeys.OBJECT_ID in config:
                config[DiscoveryKeys.DEFAULT_ENTITY_ID] = f"{config[DiscoveryKeys.PLATFORM]}.{config[DiscoveryKeys.OBJECT_ID]}"
                del config[DiscoveryKeys.OBJECT_ID]
            if DiscoveryKeys.RAW_STATE_TOPIC in config:
                del config[DiscoveryKeys.RAW_STATE_TOPIC]

        # Handle unpublishable sensors
        if self.publishable and not Config.clean:
            self._cleanup_persistent_state_file()
        else:
            components = self._handle_unpublishable_discovery(mqtt_client, components)

        return components

    def _cleanup_persistent_state_file(self) -> None:
        """Remove persistent state file if sensor is publishable and not in clean mode."""
        if self._persistent_publish_state_file.exists():
            try:
                self._persistent_publish_state_file.unlink(missing_ok=True)
                logging.debug(f"{self.__class__.__name__} Removed {self._persistent_publish_state_file} (publishable={self.publishable} clean={Config.clean})")
            except OSError as e:
                logging.warning(f"Failed to remove persistent state file: {e}")

    def _handle_unpublishable_discovery(self, mqtt_client: mqtt.Client, components: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Handle discovery for unpublishable sensors.

        Args:
            mqtt_client: MQTT client for publishing messages
            components: Current discovery components

        Returns:
            Updated discovery components (may be empty or minimal)
        """
        # Clear retained attributes
        if DiscoveryKeys.JSON_ATTRIBUTES_TOPIC in self:
            mqtt_client.publish(cast(str, self[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]), None, qos=0, retain=False)
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} unpublished - removed any retained messages in topic {self[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]}")

        # Handle persistent state file
        if self._persistent_publish_state_file.exists() or Config.clean:
            components = {}
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery (persistent file exists={self._persistent_publish_state_file.exists()} clean={Config.clean})")
        else:
            # Create minimal discovery to remove entity
            for comp_id in components.keys():
                components[comp_id] = {"p": self[DiscoveryKeys.PLATFORM]}

            try:
                with self._persistent_publish_state_file.open("w") as f:
                    f.write("0")
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery except {components} (persistent file handling)")
            except OSError as e:
                logging.warning(f"Failed to create persistent state file: {e}")

        return components

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        """Get individual discovery components for this sensor.

        Returns:
            Dictionary mapping component ID to configuration
        """
        components = {k: v for k, v in self.items() if v is not None}

        if DiscoveryKeys.OPTIONS in self:
            components[DiscoveryKeys.OPTIONS] = [
                _t(f"{self.__class__.__name__}.options.{i}", x, self.debug_logging) for i, x in enumerate(cast(list[str], self[DiscoveryKeys.OPTIONS])) if x is not None and x != ""
            ]

        return {self.unique_id: dict(components)}

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get current sensor state.

        Args:
            raw: If True, return raw unprocessed value
            republish: If True, return last known state without updating
            **kwargs: Additional arguments passed to _update_internal_state

        Returns:
            Current state value or None
        """
        state: float | int | str | None = None

        if republish and len(self._states) > 0:
            state = self._states[-1][1]
            if self.debug_logging:
                timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self._states[-1][0]))
                logging.debug(f"{self.__class__.__name__} Republishing previous state (state={state} retrieved={timestamp})")
        else:
            result = await self._update_internal_state(**kwargs)
            if result:
                state = self._states[-1][1] if len(self._states) > 0 else None

        # Compute processed state
        result = state if raw or isinstance(state, str) else self._apply_gain_and_precision(state, raw)

        # Ensure integer type is returned when precision == 0
        if not raw and not isinstance(result, str) and getattr(self, "precision", None) == 0 and isinstance(result, float) and result == int(result):
            return int(result)

        return result

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool = False) -> bool:
        """Publish sensor state to MQTT.

        Args:
            mqtt_client: MQTT client for publishing
            modbus_client: Modbus client for reading values
            republish: If True, republish last known state

        Returns:
            True if successfully published
        """
        if not self._should_attempt_publish():
            return False

        try:
            published = await self._attempt_publish(mqtt_client, modbus_client, republish)
            await self._publish_derived_sensors(mqtt_client, modbus_client, republish)
            return published
        except Exception as e:
            return self._handle_publish_error(mqtt_client, modbus_client, e)
        finally:
            self.force_publish = False

    def _should_attempt_publish(self) -> bool:
        """Check if we should attempt to publish based on failure count.

        Returns:
            True if should attempt publish
        """
        now = time.time()
        should_publish = self._failures < self._max_failures or (self._next_retry is not None and self._next_retry <= now)

        if not should_publish and self.debug_logging:
            logging.debug(f"{self.__class__.__name__} failures={self._failures} max={self._max_failures} next_retry={self._next_retry} now={now}")

        return should_publish

    async def _attempt_publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool) -> bool:
        """Attempt to publish sensor state.

        Args:
            mqtt_client: MQTT client for publishing
            modbus_client: Modbus client for reading values
            republish: If True, republish last known state

        Returns:
            True if successfully published
        """
        if not self.publishable:
            return False

        state = await self.get_state(modbus_client=modbus_client, raw=False, republish=republish)

        if state is None and not self.force_publish:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Publishing SKIPPED: State is None")
            return False

        # Reset failure count on successful state acquisition
        if self._failures > 0:
            logging.info(f"{self.__class__.__name__} Resetting failure count from {self._failures} to 0 because valid state acquired (state={state})")
            self._failures = 0
            self._next_retry = None

        # Publish state
        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Publishing state={state} to topic {self[DiscoveryKeys.STATE_TOPIC]}")

        mqtt_client.publish(cast(str, self[DiscoveryKeys.STATE_TOPIC]), f"{state}", self._qos, self._retain)

        # Publish raw state if configured
        if self.publish_raw:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Publishing raw state={self.latest_raw_state} to topic {self[DiscoveryKeys.RAW_STATE_TOPIC]}")
            mqtt_client.publish(cast(str, self[DiscoveryKeys.RAW_STATE_TOPIC]), f"{self.latest_raw_state}", self._qos, self._retain)

        return True

    async def _publish_derived_sensors(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool) -> None:
        """Publish all derived sensors.

        Args:
            mqtt_client: MQTT client for publishing
            modbus_client: Modbus client for reading values
            republish: If True, republish last known state
        """
        for sensor in self._derived_sensors.values():
            await sensor.publish(mqtt_client, modbus_client, republish=republish)

    def _handle_publish_error(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, error: Exception) -> bool:
        """Handle errors during publish.

        Args:
            mqtt_client: MQTT client
            modbus_client: Modbus client
            error: The exception that occurred

        Returns:
            False (publish failed)
        """
        logging.warning(f"{self.__class__.__name__} Publishing SKIPPED: Failed to get state ({repr(error)})")

        if modbus_client and modbus_client.connected:
            self._update_failure_count(error)
        else:
            raise

        if Config.home_assistant.enabled:
            self.publish_attributes(mqtt_client, clean=False, failures=self._failures, exception=f"{repr(error)}")

        if self._failures >= self._max_failures:
            self._log_publish_disabled()

        return False

    def _update_failure_count(self, error: Exception) -> None:
        """Update failure count and next retry time.

        Args:
            error: The exception that occurred
        """
        if isinstance(error, SanityCheckException) and not Config.sanity_check_failures_increment:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} SanityCheck failure ignored for failure counting ({self._failures} failures)")
        else:
            self._failures += 1
            now = time.time()
            self._next_retry = (
                None if self._failures < self._max_failures or self._max_failures_retry_interval == 0 else (now + (self._max_failures_retry_interval * max(1, self._failures - self._max_failures)))
            )
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} failures={self._failures} max_failures={self._max_failures} next_retry={self._next_retry}")

    def _log_publish_disabled(self) -> None:
        """Log that publishing has been disabled due to too many failures."""
        next_str = "restart" if self._next_retry is None else time.strftime("%c", time.localtime(self._next_retry))
        affected = [s.__class__.__name__ for s in self._derived_sensors.values()]
        logging.warning(f"{self.__class__.__name__} Publishing DISABLED until {next_str} ({self._failures} failures >= {self._max_failures}) Affected derived sensors={','.join(affected)}")

    def publish_attributes(self, mqtt_client: mqtt.Client, clean: bool = False, **kwargs) -> None:
        """Publish sensor attributes to MQTT.

        Args:
            mqtt_client: MQTT client for publishing
            clean: If True, clear retained attributes
            **kwargs: Additional attributes to include
        """
        if not self._attributes_published or clean:
            if clean:
                self._clean_attributes(mqtt_client)
            elif self.publishable:
                self._publish_current_attributes(mqtt_client, **kwargs)

        # Publish derived sensor attributes
        for sensor in self._derived_sensors.values():
            sensor.publish_attributes(mqtt_client, clean=clean)

    def _clean_attributes(self, mqtt_client: mqtt.Client) -> None:
        """Clear retained attribute messages.

        Args:
            mqtt_client: MQTT client for publishing
        """
        if self.debug_logging:
            logging.debug(f"{self.name} cleaning attributes")

        mqtt_client.publish(cast(str, self[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]), None, qos=1, retain=True)

    def _publish_current_attributes(self, mqtt_client: mqtt.Client, **kwargs) -> None:
        """Publish current sensor attributes.

        Args:
            mqtt_client: MQTT client for publishing
            **kwargs: Additional attributes to include
        """
        attributes = {key: html.unescape(value) if isinstance(value, str) else value for key, value in self.get_attributes().items()}

        # Add any additional attributes from kwargs
        for k, v in kwargs.items():
            attributes[k] = v

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Publishing attributes={attributes}")

        mqtt_client.publish(cast(str, self[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]), json.dumps(attributes, indent=4), qos=2, retain=True)

        self._attributes_published = True
        self.force_publish = False

    def set_latest_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> None:
        """Update latest state and propagate to derived sensors.

        Args:
            state: The new state value
        """
        self.set_state(state)

        # Propagate to derived sensors
        for sensor in self._derived_sensors.values():
            sensor.set_source_values(self, self._states)

    def _get_applicable_overrides(self, identifier: str) -> dict | None:
        """Get override configuration if identifier matches this sensor.

        Args:
            identifier: The override identifier pattern

        Returns:
            Override configuration dict or None
        """
        pattern = re.compile(identifier)
        if self._matches_override_pattern(pattern):
            return Config.sensor_overrides[identifier]
        return None

    def set_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> None:
        """Update latest state without propagating to derived sensors.

        Args:
            state: The new state value
        """
        if isinstance(state, str) or (isinstance(state, (int, float)) and self.sanity_check.is_sane(state, list(self._states))):
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Acquired raw state={state}")

            self._states.append((time.time(), state))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _apply_gain_and_precision(self, state: float | int | None, raw: bool = False) -> float | int | None:
        """Apply gain and precision transformations to a state value.

        Args:
            state: The state value to transform
            raw: If True, skip transformations

        Returns:
            Transformed state value
        """
        if state is None:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Skipped applying gain={self.gain} and precision={self.precision} to state={state}")
            return None

        if not isinstance(state, (float, int)) or raw:
            return state

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Applying gain={self.gain} and precision={self.precision} to state={state}")

        if self.gain is not None:
            state /= self.gain

        if isinstance(state, float) and self.precision is not None:
            # Diagnostic: ensure we see the types during test runs
            # (temporary - will be removed once root cause is found)
            state = round(state, self.precision)
            if self.precision == 0:
                state = int(state)

        return state

    def _get_option(self, index: int) -> str | None:
        """Get option value by index with translation.

        Args:
            index: The option index

        Returns:
            Translated option string or None if not found
        """
        if DiscoveryKeys.OPTIONS not in self:
            return None

        options = cast(list[str], self[DiscoveryKeys.OPTIONS])
        if not (0 <= index < len(options)):
            return None

        option = options[index]
        if option is None or option == "":
            return None

        return _t(f"{self.__class__.__name__}.options.{index}", option, self.debug_logging)

    def _get_option_index(self, value: str | int | float) -> int:
        """Get option index by value or translated value.

        Args:
            value: The option value or index

        Returns:
            The option index

        Raises:
            ValueError: If value is not a valid option
        """
        # Try as direct index
        try:
            index = int(float(value))
            if DiscoveryKeys.OPTIONS in self:
                options = cast(list[str], self[DiscoveryKeys.OPTIONS])
                if 0 <= index < len(options):
                    return index
        except (ValueError, TypeError):
            pass

        # Try matching translated option
        if DiscoveryKeys.OPTIONS in self:
            options = cast(list[str], self[DiscoveryKeys.OPTIONS])

            # Try translated strings
            for i, option in enumerate(options):
                if option != "" and option is not None:
                    if _t(f"{self.__class__.__name__}.options.{i}", option, self.debug_logging) == str(value):
                        return i

            # Try raw English strings
            for i, option in enumerate(options):
                if option == str(value):
                    return i

        raise ValueError(f"'{value}' is not a valid option")

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        """Convert processed state back to raw value.

        Args:
            state: The processed state value

        Returns:
            Raw state value suitable for writing to device
        """
        if state is None:
            return None

        if isinstance(state, str):
            # Handle string data types
            if isinstance(self, TypedSensorMixin) and self.data_type == ModbusDataType.STRING:
                return state

            # Handle option strings
            if DiscoveryKeys.OPTIONS in self and state in cast(list[str], self[DiscoveryKeys.OPTIONS]):
                return cast(list[str], self[DiscoveryKeys.OPTIONS]).index(state)

            # Try parsing as number
            try:
                value = float(state) if "." in state else int(state)
            except ValueError:
                value = state
        else:
            value = state

        # Apply gain to numeric values
        if isinstance(value, (float, int)):
            if self.gain is not None and self.gain != 1:
                value *= self.gain

        return int(value)

    def __eq__(self, other: object) -> bool:
        """Check equality based on unique_id."""
        if isinstance(other, Sensor):
            return self[DiscoveryKeys.UNIQUE_ID] == other[DiscoveryKeys.UNIQUE_ID]
        return False

    def __hash__(self) -> int:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Hash based on unique_id."""
        return hash(self[DiscoveryKeys.UNIQUE_ID])


# =============================================================================
# Sensor subclasses with specific delta check requirements
# =============================================================================


class AvailabilityMixin(Sensor):
    """Mixin for sensors that control availability of other sensors."""

    # Override delta checking for availability sensors
    _requires_delta_check = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# =============================================================================
# Derived Sensor Classes
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


# =============================================================================
# Readable Sensor Mixin
# =============================================================================


class ReadableSensorMixin(Sensor):
    """Mixin for sensors that can be read periodically.

    Adds scan interval configuration for periodic polling.
    """

    def __init__(self, **kwargs):
        if "scan_interval" not in kwargs:
            raise ValueError(f"{self.__class__.__name__}: Missing required parameter 'scan_interval'")

        if not isinstance(kwargs["scan_interval"], int):
            raise ValueError(f"{self.__class__.__name__}: scan_interval must be an int")

        if kwargs["scan_interval"] < 1:
            raise ValueError(f"{self.__class__.__name__}: scan_interval cannot be less than 1 second")

        self.scan_interval = kwargs.pop("scan_interval")
        super().__init__(**kwargs)

        # Apply scan interval overrides
        self._apply_scan_interval_overrides()

    def _apply_scan_interval_overrides(self) -> None:
        """Apply scan interval overrides from configuration."""
        for identifier in Config.sensor_overrides.keys():
            overrides = self._get_applicable_overrides(identifier)
            if overrides and "scan-interval" in overrides:
                if self.scan_interval != overrides["scan-interval"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'scan-interval' override ({overrides['scan-interval']})")
                    self.scan_interval = overrides["scan-interval"]

    def _get_applicable_overrides(self, identifier: str) -> dict | None:
        """Get override configuration if identifier matches this sensor.

        Args:
            identifier: The override identifier pattern

        Returns:
            Override configuration dict or None
        """
        pattern = re.compile(identifier)
        if self._matches_override_pattern(pattern):
            return Config.sensor_overrides[identifier]
        return None


# =============================================================================
# Modbus Sensor Mixin
# =============================================================================


class ModbusSensorMixin(SensorDebuggingMixin):
    """Mixin for sensors that read/write Modbus registers.

    Provides Modbus-specific configuration and error handling.
    """

    # Modbus exception codes
    class ExceptionCode:
        ILLEGAL_FUNCTION = 1
        ILLEGAL_DATA_ADDRESS = 2
        ILLEGAL_DATA_VALUE = 3
        SLAVE_DEVICE_FAILURE = 4

    def __init__(self, input_type: InputType, plant_index: int, device_address: int, address: int, count: int, unique_id_override: str | None = None, **kwargs):
        # Validate parameters
        if not (1 <= device_address <= 247):
            raise AssertionError(f"{self.__class__.__name__}: Invalid device address {device_address}")

        if address < 30000:
            raise AssertionError(f"{self.__class__.__name__}: Invalid address {address}")

        if count <= 0:
            raise AssertionError(f"{self.__class__.__name__}: Invalid count {count}")

        # Set unique_id
        if unique_id_override is not None:
            kwargs[DiscoveryKeys.UNIQUE_ID] = unique_id_override
        else:
            kwargs[DiscoveryKeys.UNIQUE_ID] = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{address}"

        self.unique_id = kwargs[DiscoveryKeys.UNIQUE_ID]

        super().__init__(**kwargs)

        self.address = address
        self.count = count
        self.device_address = device_address
        self.input_type = input_type
        self.plant_index = plant_index

    def _check_register_response(self, rr: ModbusPDU | None, source: str) -> bool:
        """Check and handle Modbus register response.

        Args:
            rr: Modbus response object
            source: Description of operation (for logging)

        Returns:
            True if response is valid

        Raises:
            Exception: For various Modbus error conditions
        """
        if rr is None:
            logging.error(f"{self.__class__.__name__} Modbus {source} failed to read registers (None response)")
            return False

        if not (rr.isError() or isinstance(rr, ExceptionResponse)):
            return True

        # Handle specific exception codes
        exc_code = rr.exception_code

        if exc_code == self.ExceptionCode.ILLEGAL_FUNCTION:
            self._handle_illegal_function(source, rr)
        elif exc_code == self.ExceptionCode.ILLEGAL_DATA_ADDRESS:
            self._handle_illegal_data_address(source, rr)
        elif exc_code == self.ExceptionCode.ILLEGAL_DATA_VALUE:
            self._handle_illegal_data_value(source, rr)
        elif exc_code == self.ExceptionCode.SLAVE_DEVICE_FAILURE:
            self._handle_slave_device_failure(source, rr)
        else:
            self._handle_unknown_exception(source, rr)

        return False

    def _handle_illegal_function(self, source: str, rr: ModbusPDU) -> None:
        """Handle illegal function exception."""
        logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x01 ILLEGAL FUNCTION")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x01 ILLEGAL FUNCTION")

    def _handle_illegal_data_address(self, source: str, rr: ModbusPDU) -> None:
        """Handle illegal data address exception."""
        logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x02 ILLEGAL DATA ADDRESS")
        if self.debug_logging:
            logging.debug(rr)

        # Disable retries for invalid addresses on read operations
        if source != "write_registers":
            logging.warning(f"{self.__class__.__name__} Setting max allowed failures to 0 for '{self.unique_id}' because of ILLEGAL DATA ADDRESS exception")
            self._max_failures = 0
            self._max_failures_retry_interval = 0

        raise Exception("0x02 ILLEGAL DATA ADDRESS")

    def _handle_illegal_data_value(self, source: str, rr: ModbusPDU) -> None:
        """Handle illegal data value exception."""
        logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x03 ILLEGAL DATA VALUE")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x03 ILLEGAL DATA VALUE")

    def _handle_slave_device_failure(self, source: str, rr: ModbusPDU) -> None:
        """Handle slave device failure exception."""
        logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x04 SLAVE DEVICE FAILURE")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x04 SLAVE DEVICE FAILURE")

    def _handle_unknown_exception(self, source: str, rr: ModbusPDU) -> None:
        """Handle unknown exception."""
        logging.error(f"{self.__class__.__name__} Modbus {source} returned {rr}")
        raise Exception(rr)


# =============================================================================
# Read-Only Sensor
# =============================================================================


class ReadOnlySensor(TypedSensorMixin, ReadableSensorMixin, ModbusSensorMixin, Sensor):
    """Sensor that reads values from Modbus registers.

    This is the primary sensor type for monitoring device state.
    """

    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        unique_id_override: str | None = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            object_id=object_id,
            input_type=input_type,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=count,
            data_type=data_type,
            scan_interval=scan_interval,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
            protocol_version=protocol_version,
            unique_id_override=unique_id_override,
            **kwargs,
        )

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Read current value from Modbus registers.

        Args:
            **kwargs: Must contain 'modbus_client'

        Returns:
            True if successfully read, False otherwise

        Raises:
            Various exceptions for Modbus errors
        """
        if "modbus_client" not in kwargs:
            raise ValueError(f"{self.__class__.__name__}: Required argument 'modbus_client' not supplied")

        modbus_client: ModbusClientType = kwargs["modbus_client"]

        if self.debug_logging:
            self._log_read_attempt()

        try:
            return await self._perform_modbus_read(modbus_client)
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus read interrupted")
            return False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus read failed to acquire lock within {self.scan_interval}s")
            return False
        except Exception:
            # Record error in metrics if available
            if Metrics:
                await Metrics.modbus_read_error()
            raise

    def _log_read_attempt(self) -> None:
        """Log details of Modbus read attempt."""
        actual_interval = None if len(self._states) == 0 else f"{round(time.time() - self._states[-1][0], 2)}s"

        logging.debug(
            f"{self.__class__.__name__} read_{self.input_type}_registers("
            f"{self.address}, count={self.count}, device_id={self.device_address}) "
            f"plant_index={self.plant_index} interval={self.scan_interval}s "
            f"actual={actual_interval}"
        )

    async def _perform_modbus_read(self, modbus_client: ModbusClientType) -> bool:
        """Perform the actual Modbus read operation.

        Args:
            modbus_client: Modbus client for reading

        Returns:
            True if read was successful
        """
        start = time.monotonic()

        # Perform read based on input type
        if self.input_type == InputType.HOLDING:
            rr = await modbus_client.read_holding_registers(self.address, count=self.count, device_id=self.device_address, trace=self.debug_logging)
        elif self.input_type == InputType.INPUT:
            rr = await modbus_client.read_input_registers(self.address, count=self.count, device_id=self.device_address, trace=self.debug_logging)
        else:
            raise ValueError(f"{self.__class__.__name__}: Unknown input type '{self.input_type}'")

        elapsed = time.monotonic() - start

        # Record metrics if available
        if Metrics:
            await Metrics.modbus_read(self.count, elapsed)

        # Check response validity
        result = self._check_register_response(rr, f"read_{self.input_type}_registers")

        if result and rr:
            # Convert registers to value and update state
            value = modbus_client.convert_from_registers(rr.registers, self.data_type)  # pyright: ignore
            self.set_latest_state(value)

        if self.debug_logging:
            self._log_read_complete(elapsed, result)

        return result

    def _log_read_complete(self, elapsed: float, result: bool) -> None:
        """Log completion of Modbus read.

        Args:
            elapsed: Time taken in seconds
            result: Whether read was successful
        """
        actual_interval = None if len(self._states) == 0 else f"{round(time.time() - self._states[-1][0], 2)}s"

        logging.debug(
            f"{self.__class__.__name__} read_{self.input_type}_registers("
            f"{self.address}, count={self.count}, device_id={self.device_address}) "
            f"plant_index={self.plant_index} interval={self.scan_interval}s "
            f"actual={actual_interval} elapsed={(elapsed / 1000):.2f}ms result={result}"
        )

    def get_attributes(self) -> dict[str, float | int | str]:
        """Get sensor attributes including Modbus register info.

        Returns:
            Dictionary of sensor attributes
        """
        attributes = super().get_attributes()

        # Add register source information
        if self.count == 1:
            source_key = "ReadOnlySensor.attributes.source"
            source_default = f"Modbus Register {self.address}"
        else:
            source_key = "ReadOnlySensor.attributes.source_range"
            source_default = f"Modbus Registers {self.address}-{self.address + self.count - 1}"

        attributes[SensorAttributeKeys.SOURCE] = _t(source_key, source_default, self.debug_logging, address=self.address, start=self.address, end=self.address + self.count - 1)

        if "comment" in self:
            attributes[SensorAttributeKeys.COMMENT] = _t(f"{self.__class__.__name__}.comment", cast(str, self["comment"]), self.debug_logging)

        return attributes


# =============================================================================
# Reserved Sensor
# =============================================================================


class ReservedSensor(ReadOnlySensor):
    """Sensor for reserved Modbus registers.

    Reserved sensors are never published but can be used for internal logic.
    """

    # Override delta checking for reserved sensors
    _requires_delta_check = False

    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        unique_id_override: str | None = None,
        availability_control_sensor: AvailabilityMixin | None = None,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
            protocol_version,
            unique_id_override=unique_id_override,
            **kwargs,
        )

        # Validate class name
        if not self.__class__.__name__.startswith("Reserved"):
            raise ValueError(f"{self.__class__.__name__}: class name must start with 'Reserved'")

        # Reserved sensors are never published
        self._publishable = False

    @property
    def publishable(self) -> bool:
        """Reserved sensors are never publishable."""
        return False

    @publishable.setter
    def publishable(self, value: bool):
        """Prevent setting publishable=True for reserved sensors."""
        if value:
            raise ValueError("Cannot set publishable=True for ReservedSensor")

    def apply_sensor_overrides(self, registers):
        """Reserved sensors ignore overrides."""
        pass


# =============================================================================
# Timestamp Sensor
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

    def state2raw(self, state) -> float | int | str:
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


# =============================================================================
# Observable and Substitute Mixins
# =============================================================================


class ObservableMixin(abc.ABC):
    """Mixin for sensors that can be observed/controlled via MQTT."""

    @abc.abstractmethod
    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Handle notification of value change.

        Args:
            modbus_client: Modbus client for writing values
            mqtt_client: MQTT client
            value: New value
            source: Source topic of the value
            handler: MQTT handler

        Returns:
            True if notification was handled
        """
        pass

    def observable_topics(self) -> set[str]:
        """Get set of MQTT topics this sensor observes.

        Returns:
            Set of topic strings
        """
        return set()


class SubstituteMixin(abc.ABC):
    """Mixin for sensors that can substitute for failed sensors."""

    @abc.abstractmethod
    def fallback(self, source: str):
        """Handle fallback to this sensor from failed source.

        Args:
            source: Identifier of failed source sensor
        """
        pass

    @abc.abstractmethod
    def failover(self, smartport_sensor: Sensor) -> bool:
        """Handle failover from another sensor.

        Args:
            smartport_sensor: The sensor to fail over from

        Returns:
            True if failover was successful
        """
        pass


"""Continuation of base sensor classes (Part 3).

This file contains writable sensors, alarm sensors, and accumulation sensors.
Merge with base_refactored.py and base_refactored_part2.py for the complete module.
"""

# =============================================================================
# Writable Sensor Mixin
# =============================================================================


class WritableSensorMixin(TypedSensorMixin, ModbusSensorMixin, Sensor):
    """Mixin for sensors that can write values to Modbus registers.

    Provides command topic configuration and value writing capabilities.
    """

    @property
    def command_topic(self) -> str:
        """Get the MQTT topic for receiving commands.

        Returns:
            Command topic string

        Raises:
            RuntimeError: If command topic is not configured
        """
        topic = cast(str, self.get(DiscoveryKeys.COMMAND_TOPIC))
        if not topic or topic.isspace():
            raise RuntimeError(f"{self.__class__.__name__} command topic is not defined")
        return topic

    def _raw2state(self, raw_value: float | int | str) -> float | int | str:
        """Convert raw value to display state.

        Args:
            raw_value: Raw value from device

        Returns:
            Display-friendly state value
        """
        if isinstance(raw_value, str):
            return raw_value

        # Handle option-based sensors
        if DiscoveryKeys.OPTIONS in self and isinstance(raw_value, (int, float)):
            option = self._get_option(int(raw_value))
            if option:
                return option

        # Handle WriteOnlySensor states
        if isinstance(self, WriteOnlySensor) and isinstance(raw_value, str):
            if self._values["off"] == raw_value:
                return self._names["off"]
            elif self._values["on"] == raw_value:
                return self._names["on"]
            return raw_value

        # Handle SwitchSensor states
        if isinstance(self, SwitchSensor) and isinstance(raw_value, str):
            if self[DiscoveryKeys.PAYLOAD_OFF] == raw_value:
                return "Off"
            elif self[DiscoveryKeys.PAYLOAD_ON] == raw_value:
                return "On"
            return raw_value

        # Apply gain and precision
        if isinstance(raw_value, (float, int)):
            state = self._apply_gain_and_precision(raw_value)
            if state is not None:
                return state

        return raw_value

    async def _write_registers(self, modbus_client: ModbusClientType, raw_value: float | int | str, mqtt_client: mqtt.Client) -> bool:
        """Write value to Modbus registers.

        Args:
            modbus_client: Modbus client for writing
            raw_value: Raw value to write
            mqtt_client: MQTT client for status updates

        Returns:
            True if write was successful
        """
        max_wait = 2
        device_id = self.device_address
        no_response_expected = False

        logging.info(f"{self.__class__.__name__} _write_registers value={self._raw2state(raw_value)} (raw={raw_value} latest_raw_state={self.latest_raw_state} address={self.address} device_id={device_id})")

        # Convert value to registers
        registers = self._convert_value_to_registers(modbus_client, raw_value)
        method = "write_register" if len(registers) == 1 else "write_registers"

        self.force_publish = True

        try:
            return await self._perform_modbus_write(modbus_client, registers, device_id, no_response_expected, method)
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus write interrupted")
            return False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus write failed to acquire lock within {max_wait}s")
            return False
        except Exception as e:
            logging.error(f"{self.__class__.__name__} write_registers: {repr(e)}")
            if Metrics:
                await Metrics.modbus_write_error()
            raise

    def _convert_value_to_registers(self, modbus_client: ModbusClientType, raw_value: float | int | str) -> list[int]:
        """Convert a value to Modbus register format.

        Args:
            modbus_client: Modbus client with conversion utilities
            raw_value: Value to convert

        Returns:
            List of register values
        """
        # Unsigned 8-bit integers don't need encoding
        if self.data_type == ModbusDataType.UINT16 and isinstance(raw_value, int) and 0 <= raw_value <= 255:
            return [raw_value]

        # String values
        if self.data_type == ModbusDataType.STRING:
            return modbus_client.convert_to_registers(str(raw_value), self.data_type)

        # Numeric values
        return modbus_client.convert_to_registers(int(raw_value), self.data_type)

    async def _perform_modbus_write(self, modbus_client: ModbusClientType, registers: list[int], device_id: int, no_response_expected: bool, method: str) -> bool:
        """Perform the actual Modbus write operation.

        Args:
            modbus_client: Modbus client
            registers: Register values to write
            device_id: Target device ID
            no_response_expected: Whether to wait for response
            method: Method name for logging

        Returns:
            True if write was successful
        """
        start = time.monotonic()

        async with ModbusLockFactory.get(modbus_client).lock(2):  # max_wait=2
            if len(registers) == 1:
                rr = await modbus_client.write_register(self.address, registers[0], device_id=device_id, no_response_expected=no_response_expected)
            else:
                rr = await modbus_client.write_registers(self.address, registers, device_id=device_id, no_response_expected=no_response_expected)

        elapsed = time.monotonic() - start

        # Record metrics if available
        if Metrics:
            await Metrics.modbus_write(len(registers), elapsed)

        if self.debug_logging:
            logging.debug(
                f"{self.__class__.__name__} {method}({self.address}, value={registers}, device_id={device_id}, no_response_expected={no_response_expected}) [plant_index={self.plant_index}] took {elapsed:.3f}s"
            )

        return self._check_register_response(rr, method)

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure MQTT topics including command topic.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        base = super().configure_mqtt_topics(device_id)
        self[DiscoveryKeys.COMMAND_TOPIC] = f"{base}/set"
        return base

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Set sensor value from MQTT command.

        Args:
            modbus_client: Modbus client for writing (required)
            mqtt_client: MQTT client
            value: New value to set
            source: Source topic of the command
            handler: MQTT handler

        Returns:
            True if value was set successfully
        """
        if modbus_client is None:
            raise ValueError(f"{self.__class__.__name__}: ModbusClient cannot be None")

        try:
            if not await self.value_is_valid(modbus_client, value):
                return False
        except Exception as e:
            logging.error(f"{self.__class__.__name__} value_is_valid check of value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) FAILED: {repr(e)}")
            raise

        if source == self[DiscoveryKeys.COMMAND_TOPIC]:
            return await self._write_registers(modbus_client, value, mqtt_client)
        else:
            logging.error(f"{self.__class__.__name__} Attempt to set value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) from unknown topic {source}")
            return False

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        """Validate that a value is acceptable for this sensor.

        Args:
            modbus_client: Modbus client (may be used for validation)
            raw_value: Value to validate

        Returns:
            True if value is valid
        """
        return True


# =============================================================================
# Write-Only Sensor
# =============================================================================


class WriteOnlySensor(WritableSensorMixin, Sensor):
    """Sensor that can only write values (e.g., buttons, triggers).

    Write-only sensors appear as buttons in Home Assistant and don't
    have a readable state.
    """

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        payload_off: str = "off",
        payload_on: str = "on",
        name_off: str = "Power Off",
        name_on: str = "Power On",
        icon_off: str = "mdi:power-off",
        icon_on: str = "mdi:power-on",
        value_off: int = 0,
        value_on: int = 1,
        **kwargs,
    ):
        # Validate icons
        if not icon_on.startswith("mdi:"):
            raise ValueError(f"{self.__class__.__name__}: on icon '{icon_on}' does not start with 'mdi:'")
        if not icon_off.startswith("mdi:"):
            raise ValueError(f"{self.__class__.__name__}: off icon '{icon_off}' does not start with 'mdi:'")

        super().__init__(
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            unit=None,
            device_class=None,
            state_class=None,
            icon=None,
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.PLATFORM] = "button"
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

        self._payloads = {"off": payload_off, "on": payload_on}

        # Use shared translation for defaults, specific for overrides
        t_off = _t("WriteOnlySensor.name_off", name_off, self.debug_logging) if name_off == "Power Off" else _t(f"{self.__class__.__name__}.name_off", name_off, self.debug_logging)
        t_on = _t("WriteOnlySensor.name_on", name_on, self.debug_logging) if name_on == "Power On" else _t(f"{self.__class__.__name__}.name_on", name_on, self.debug_logging)

        self._names = {"off": t_off, "on": t_on}
        self._icons = {"off": icon_off, "on": icon_on}
        self._values = {"off": value_off, "on": value_on}

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Write-only sensors don't have internal state."""
        return False

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        """Get discovery components for both on and off buttons.

        Returns:
            Dictionary of component configurations
        """
        components: dict[str, Any] = {}

        # Remove legacy entities first
        for action in ["On", "Off"]:
            components[f"{self.unique_id}_{action}"] = {"p": "button"}

        # Create new button entities
        for action in ["on", "off"]:
            config: dict[str, Any] = {}

            for k, v in self.items():
                if v is None:
                    continue

                if k == DiscoveryKeys.NAME:
                    config[k] = self._names[action]
                elif k in (DiscoveryKeys.OBJECT_ID, DiscoveryKeys.UNIQUE_ID):
                    config[k] = f"{v}_{self._payloads[action]}"
                else:
                    config[k] = v

            config[DiscoveryKeys.ICON] = self._icons[action]
            config["payload_press"] = self._payloads[action]
            components[f"{self.unique_id}_{action}"] = config

        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Discovered components={components}")

        return components

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Set value, translating payload to actual value.

        Args:
            modbus_client: Modbus client for writing
            mqtt_client: MQTT client
            value: Payload value ("on" or "off")
            source: Source topic
            handler: MQTT handler

        Returns:
            True if successfully set
        """
        # Translate payload to actual value
        if self._payloads["off"] == value:
            actual_value = self._values["off"]
        elif self._payloads["on"] == value:
            actual_value = self._values["on"]
        else:
            actual_value = value

        return await super().set_value(modbus_client, mqtt_client, actual_value, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        """Validate that value is either on or off value.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if valid
        """
        if raw_value not in (self._values["off"], self._values["on"]):
            logging.error(f"{self.__class__.__name__} Invalid value '{raw_value}': Must be either '{self._payloads['on']}' or '{self._payloads['off']}'")
            return False
        return True


# =============================================================================
# Read-Write Sensor
# =============================================================================


class ReadWriteSensor(WritableSensorMixin, ReadOnlySensor):
    """Sensor that can both read and write values.

    This combines readable sensor capabilities with writable control.
    """

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        **kwargs,
    ):
        # Validate availability control sensor
        if availability_control_sensor is not None:
            if not isinstance(availability_control_sensor, AvailabilityMixin):
                raise ValueError(f"{self.__class__.__name__}: availability_control_sensor must be an instance of AvailabilityMixin")

        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
            protocol_version,
            **kwargs,
        )

        self._availability_control_sensor = availability_control_sensor
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure MQTT topics including availability from control sensor.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        base = super().configure_mqtt_topics(device_id)

        # Add availability from control sensor if configured
        if self._availability_control_sensor is not None and Config.home_assistant.enabled:
            control_topic = self._availability_control_sensor.state_topic

            if not control_topic or control_topic.isspace():
                raise RuntimeError("RemoteEMS state_topic has not been configured")

            availability_list = cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY])
            availability_list.append({"topic": control_topic, "payload_available": 1, "payload_not_available": 0})

        return base


# =============================================================================
# Numeric Sensor
# =============================================================================


class NumericSensor(ReadWriteSensor):
    """Sensor for numeric values with min/max constraints.

    Appears as a number input in Home Assistant with configurable range.
    """

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        minimum: float | tuple[float, float] | None = None,
        maximum: float | tuple[float, float] | None = None,
        **kwargs,
    ):
        # Validate min/max ranges
        self._validate_min_max_ranges(minimum, maximum)

        super().__init__(
            availability_control_sensor,
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
            protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.PLATFORM] = "number"

        # Set default min/max for percentage
        if minimum is None and maximum is None and unit == PERCENTAGE:
            self[DiscoveryKeys.MIN] = 0.0
            self[DiscoveryKeys.MAX] = 100.0

        # Set minimum
        if minimum is not None:
            self[DiscoveryKeys.MIN] = self._format_range_value(minimum)
        elif minimum is None and maximum is not None:
            self[DiscoveryKeys.MIN] = 0.0 if isinstance(maximum, float) else 0

        # Set maximum
        if maximum is not None:
            self[DiscoveryKeys.MAX] = self._format_range_value(maximum)

        # Set input mode and step
        self[DiscoveryKeys.MODE] = "slider" if (unit == PERCENTAGE and not Config.home_assistant.edit_percentage_with_box) else "box"
        self[DiscoveryKeys.STEP] = 1 if precision is None else 10**-precision

        # Update sanity check ranges
        self._update_sanity_check_ranges(gain)

    def _validate_min_max_ranges(self, minimum: float | tuple[float, float] | None, maximum: float | tuple[float, float] | None) -> None:
        """Validate minimum and maximum range values.

        Args:
            minimum: Minimum value or range
            maximum: Maximum value or range

        Raises:
            ValueError: If ranges are invalid
        """
        if minimum is None or maximum is None:
            return

        # Both are simple numbers
        if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
            if minimum >= maximum:
                raise AssertionError(f"{self.__class__.__name__}: Invalid min/max values: {minimum}/{maximum} (min must be < max)")
            return

        # Both are tuples
        if isinstance(minimum, tuple) and isinstance(maximum, tuple):
            if len(minimum) != len(maximum):
                raise AssertionError(f"{self.__class__.__name__}: Invalid min/max tuples: different lengths {len(minimum)}/{len(maximum)}")

            for mn, mx in zip(minimum, maximum):
                if not (isinstance(mn, (int, float)) and isinstance(mx, (int, float))):
                    raise ValueError(f"{self.__class__.__name__}: Invalid tuple values: {mn}/{mx} (must be numeric)")
                if mn >= mx:
                    raise ValueError(f"{self.__class__.__name__}: Invalid tuple values: {mn}/{mx} (min must be < max)")
            return

        raise ValueError(f"{self.__class__.__name__}: Invalid min/max types: {type(minimum)}/{type(maximum)}")

    def _format_range_value(self, value: float | tuple[float, float]) -> float | tuple[float, ...]:
        """Format a range value for MQTT.

        Args:
            value: Single value or tuple of values

        Returns:
            Formatted value
        """
        if isinstance(value, (int, float)):
            return float(value)
        return cast(tuple, value)

    def _update_sanity_check_ranges(self, gain: float | None) -> None:
        """Update sanity check min/max based on configured ranges.

        Args:
            gain: Gain multiplier to apply
        """
        # Update minimum
        if DiscoveryKeys.MIN in self:
            if isinstance(self[DiscoveryKeys.MIN], (int, float)):
                min_val = cast(float, self[DiscoveryKeys.MIN])
                self.sanity_check.min_raw = int(min_val * gain) if gain else int(min_val)
            elif isinstance(self[DiscoveryKeys.MIN], tuple):
                min_val = min(cast(tuple[float, ...], self[DiscoveryKeys.MIN]))
                self.sanity_check.min_raw = int(min_val * gain) if gain else int(min_val)

        # Update maximum
        if DiscoveryKeys.MAX in self:
            if isinstance(self[DiscoveryKeys.MAX], (int, float)):
                max_val = cast(float, self[DiscoveryKeys.MAX])
                self.sanity_check.max_raw = int(max_val * gain) if gain else int(max_val)
            elif isinstance(self[DiscoveryKeys.MAX], tuple):
                max_val = max(cast(tuple[float, ...], self[DiscoveryKeys.MAX]))
                self.sanity_check.max_raw = int(max_val * gain) if gain else int(max_val)

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        """Get discovery components with flattened min/max.

        Returns:
            Dictionary of component configurations
        """
        components = super().get_discovery_components()

        # Flatten tuple ranges to single min/max values
        if DiscoveryKeys.MIN in self and isinstance(components[self.unique_id][DiscoveryKeys.MIN], (tuple, list)):
            components[self.unique_id][DiscoveryKeys.MIN] = min(cast(Iterable[float], self[DiscoveryKeys.MIN]))

        if DiscoveryKeys.MAX in self and isinstance(components[self.unique_id][DiscoveryKeys.MAX], (tuple, list)):
            components[self.unique_id][DiscoveryKeys.MAX] = max(cast(Iterable[float], self[DiscoveryKeys.MAX]))

        return components

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get state, constraining to min/max range.

        Args:
            raw: If True, return raw value
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            State value constrained to valid range
        """
        state = await super().get_state(raw=raw, republish=republish, **kwargs)

        if not isinstance(state, (float, int)):
            return state

        # Apply gain/precision first (unless raw requested)
        processed = state if raw else self._apply_gain_and_precision(state)
        original_value = processed

        # Preserve integer when precision == 0
        if getattr(self, "precision", None) == 0:
            if isinstance(processed, int):
                value = processed
            elif isinstance(processed, float) and processed == int(processed):
                value = int(processed)
            else:
                value = float(processed)  # type: ignore
        else:
            value = float(processed)  # type: ignore

        # Constrain to simple min/max
        if DiscoveryKeys.MIN in self and isinstance(self[DiscoveryKeys.MIN], float):
            min_val = cast(float, self[DiscoveryKeys.MIN])
            if value < min_val:
                value = min_val if not raw else min_val * self.gain

        if DiscoveryKeys.MAX in self and isinstance(self[DiscoveryKeys.MAX], float):
            max_val = cast(float, self[DiscoveryKeys.MAX])
            if value > max_val:
                value = max_val if not raw else max_val * self.gain

        # Constrain to negative range (tuple)
        if DiscoveryKeys.MIN in self and isinstance(self[DiscoveryKeys.MIN], tuple) and value < 0:
            min_range = cast(tuple[float, ...], self[DiscoveryKeys.MIN])
            if not (min(min_range) <= value <= max(min_range)):
                value = min(min_range) if not raw else min(min_range) * self.gain

        # Constrain to positive range (tuple)
        if DiscoveryKeys.MAX in self and isinstance(self[DiscoveryKeys.MAX], tuple) and value > 0:
            max_range = cast(tuple[float, ...], self[DiscoveryKeys.MAX])
            if not (min(max_range) <= value <= max(max_range)):
                value = max(max_range) if not raw else max(max_range) * self.gain

        if value != original_value and self.debug_logging:
            logging.debug(f"{self.__class__.__name__} value={original_value} adjusted to {value}")

        return value

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Set numeric value with validation.

        Args:
            modbus_client: Modbus client for writing
            mqtt_client: MQTT client
            value: New value
            source: Source topic
            handler: MQTT handler

        Returns:
            True if successfully set
        """
        if value is None:
            logging.warning(f"{self.__class__.__name__} Ignored attempt to set value to *None*")
            return False

        try:
            state = float(value)
            if self.gain != 1:
                state = state * self.gain  # Convert to raw value
        except Exception as e:
            logging.warning(f"{self.__class__.__name__} Attempt to set value to '{value}' FAILED: {repr(e)}")
            return False

        return await super().set_value(modbus_client, mqtt_client, state, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        """Validate numeric value is within range.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if valid
        """
        try:
            value = cast(float, self._apply_gain_and_precision(float(raw_value)))

            # Check simple minimum
            if isinstance(self.get(DiscoveryKeys.MIN), float):
                min_val = cast(float, self[DiscoveryKeys.MIN])
                if value < min_val:
                    logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Less than minimum of {min_val}")
                    return False

            # Check simple maximum
            if isinstance(self.get(DiscoveryKeys.MAX), float):
                max_val = cast(float, self[DiscoveryKeys.MAX])
                if value > max_val:
                    logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Greater than maximum of {max_val}")
                    return False

            # Check negative range
            if isinstance(self.get(DiscoveryKeys.MIN), tuple) and value < 0:
                min_range = cast(tuple[float, ...], self[DiscoveryKeys.MIN])
                if not (min(min_range) <= value <= max(min_range)):
                    logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Not in range {min_range}")
                    return False

            # Check positive range
            if isinstance(self.get(DiscoveryKeys.MAX), tuple) and value > 0:
                max_range = cast(tuple[float, ...], self[DiscoveryKeys.MAX])
                if not (min(max_range) <= value <= max(max_range)):
                    logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Not in range {max_range}")
                    return False

            return True
        except ValueError:
            logging.error(f"{self.name} invalid value '{raw_value}': Not a number")
            return False


# =============================================================================
# Select Sensor
# =============================================================================


class SelectSensor(ReadWriteSensor):
    """Sensor for selecting from a list of options.

    Appears as a dropdown selector in Home Assistant.
    """

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        scan_interval: int,
        options: list[str],
        protocol_version: Protocol,
        **kwargs,
    ):
        # Validate options
        if not options or not isinstance(options, list):
            raise ValueError(f"{self.__class__.__name__}: options must be a non-empty list")

        if not all(isinstance(o, str) for o in options):
            raise ValueError(f"{self.__class__.__name__}: all options must be strings")

        super().__init__(
            availability_control_sensor=availability_control_sensor,
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=scan_interval,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:list-status",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.PLATFORM] = "select"
        self[DiscoveryKeys.OPTIONS] = options

        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get state as option string.

        Args:
            raw: If True, return raw index value
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            Option string or "Unknown Mode: X" if invalid
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)

        if raw:
            return value

        if isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            return f"Unknown Mode: {value}"

        return f"Unknown Mode: {value}"

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Set selected option by name or index.

        Args:
            modbus_client: Modbus client for writing
            mqtt_client: MQTT client
            value: Option name or index
            source: Source topic
            handler: MQTT handler

        Returns:
            True if successfully set
        """
        try:
            index = self._get_option_index(value)
        except ValueError:
            logging.error(f"{self.name} invalid value '{value}': Not a valid option or index")
            return False

        return await super().set_value(modbus_client, mqtt_client, index, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        """Validate that value is a valid option.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if valid option
        """
        try:
            self._get_option_index(raw_value)
            return True
        except ValueError:
            logging.error(f"{self.name} invalid value '{raw_value}': Not a valid option or index")
            return False


# =============================================================================
# Switch Sensor
# =============================================================================


class SwitchSensor(ReadWriteSensor):
    """Binary switch sensor (on/off).

    Appears as a switch in Home Assistant.
    """

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        scan_interval: int,
        protocol_version: Protocol,
        **kwargs,
    ):
        super().__init__(
            availability_control_sensor=availability_control_sensor,
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=0,
            protocol_version=protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.PLATFORM] = "switch"
        self[DiscoveryKeys.PAYLOAD_OFF] = 0
        self[DiscoveryKeys.PAYLOAD_ON] = 1
        self[DiscoveryKeys.STATE_OFF] = 0
        self[DiscoveryKeys.STATE_ON] = 1

        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = 1

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Set switch value.

        Args:
            modbus_client: Modbus client for writing
            mqtt_client: MQTT client
            value: 0 or 1
            source: Source topic
            handler: MQTT handler

        Returns:
            True if successfully set
        """
        try:
            return await super().set_value(modbus_client, mqtt_client, int(value), source, handler)
        except ValueError as e:
            logging.error(f"{self.__class__.__name__} value_is_valid check of value '{value}' FAILED: {repr(e)}")
            raise

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        """Validate switch value is 0 or 1.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if 0 or 1
        """
        if raw_value not in (self[DiscoveryKeys.PAYLOAD_OFF], self[DiscoveryKeys.PAYLOAD_ON]):
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Must be either '{self[DiscoveryKeys.PAYLOAD_OFF]}' or '{self[DiscoveryKeys.PAYLOAD_ON]}'")
            return False
        return True


"""Continuation of base sensor classes (Part 4 - Final).

This file contains alarm sensors, accumulation sensors, and utility sensors.
Merge with previous parts for the complete module.
"""

# =============================================================================
# Alarm Sensor Base Class
# =============================================================================


class AlarmSensor(ReadOnlySensor, metaclass=abc.ABCMeta):
    """Base class for alarm/fault sensors.

    Alarm sensors decode bit-field values into human-readable alarm descriptions.
    """

    NO_ALARM: Final = "No Alarm"

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        alarm_type: str,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=(Config.modbus[plant_index].scan_interval.realtime if plant_index < len(Config.modbus) else 5),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )
        self.alarm_type = alarm_type

    @abc.abstractmethod
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode an alarm bit position to description.

        Args:
            bit_position: The bit position (0-15) in the alarm register

        Returns:
            Alarm description or None if bit is not used
        """
        pass

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get alarm state as human-readable string.

        Args:
            raw: If True, return raw alarm code
            republish: If True, return last known state
            **kwargs: May contain 'max_length' for truncation

        Returns:
            Alarm description or NO_ALARM
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)

        if raw:
            return value

        # Treat None as no alarm
        if value is None:
            return _t("AlarmSensor.no_alarm", self.NO_ALARM, self.debug_logging)

        # Check for no alarm conditions
        if self._is_no_alarm(value):
            return _t("AlarmSensor.no_alarm", self.NO_ALARM, self.debug_logging)

        # Decode alarm bits
        alarm_code = self._normalize_alarm_code(value)
        active_alarms = self._decode_alarm_bits(alarm_code, value)

        if not active_alarms:
            return f"Unknown Alarm {value}"

        # Join alarms and truncate if needed
        alarms = ", ".join(active_alarms)
        return self._truncate_alarms(alarms, kwargs.get("max_length"))

    def _is_no_alarm(self, value: float | int | str | list | None) -> bool:
        """Check if value represents no alarm condition.

        Args:
            value: Alarm value to check

        Returns:
            True if no alarm
        """
        if value is None or value == 0 or value == 65535:
            return True

        if isinstance(value, list):
            return sum(cast(list[int], value)) == 0

        return False

    def _normalize_alarm_code(self, value: float | int | str) -> int:
        """Normalize alarm value to integer code.

        Args:
            value: Raw alarm value

        Returns:
            Normalized alarm code
        """
        if isinstance(value, list) and len(value) == 2 and value[0] == 0 and value[1] != 0:
            logging.warning(f"{self.__class__.__name__} Converting '{value}' to {value[1]} for {self.alarm_type} alarm bit decoding")
            return int(value[1])

        return int(value)

    def _decode_alarm_bits(self, alarm_code: int, original_value: Any) -> list[str]:
        """Decode individual alarm bits to descriptions.

        Args:
            alarm_code: Normalized alarm code
            original_value: Original value for error reporting

        Returns:
            List of active alarm descriptions
        """
        active_alarms = []

        try:
            for bit_position in range(16):
                if alarm_code & (1 << bit_position):
                    description = self.decode_alarm_bit(bit_position)

                    if description:
                        translated = _t(f"{self.__class__.__name__}.alarm.{bit_position}", description, self.debug_logging)
                        active_alarms.append(translated)
                    else:
                        unknown = _t("AlarmSensor.unknown_alarm", "Unknown (bit{bit}∈{value})", self.debug_logging).format(bit=bit_position, value=original_value)
                        active_alarms.append(unknown)
                        logging.warning(f"{self.__class__.__name__} Unknown {self.alarm_type} alarm bit {bit_position} set in value {original_value}")
        except TypeError as e:
            logging.warning(f"{self.__class__.__name__} Failed to decode {self.alarm_type} alarm bits from '{original_value}': {e}")

        return active_alarms

    def _truncate_alarms(self, alarms: str, max_length: int | None) -> str:
        """Truncate alarm string if needed for Home Assistant.

        Args:
            alarms: Joined alarm descriptions
            max_length: Maximum length (default 255)

        Returns:
            Possibly truncated alarm string
        """
        if not Config.home_assistant.enabled:
            return alarms

        max_len = 255 if not max_length or max_length <= 0 else max_length

        if len(alarms) <= max_len:
            return alarms

        # Remove numbers, colons, underscores and collapse whitespace
        compressed = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", alarms)).strip()

        if len(compressed) <= max_len:
            return compressed

        return compressed[: (max_len - 3)] + "..."

    def state2raw(self, state):
        """Convert alarm description back to code.

        Args:
            state: Alarm description string

        Returns:
            Alarm code (0 for NO_ALARM)
        """
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


# =============================================================================
# Specific Alarm Sensor Implementations
# =============================================================================


class Alarm1Sensor(AlarmSensor):
    """PCS (Power Conversion System) alarms - Register 1."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode PCS alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance",
            2: "Over-temperature",
            3: "Equipment fault",
            4: "System grounding fault",
            5: "PV string over-voltage",
            6: "PV string reversely connected",
            7: "PV string back-filling",
            8: "AFCI fault",
            9: "Grid power outage",
            10: "Grid over-voltage",
            11: "Grid under-voltage",
            12: "Grid over-frequency",
            13: "Grid under-frequency",
            14: "Grid voltage imbalance",
            15: "DC component of output current out of limit",
        }
        return alarm_descriptions.get(bit_position)


class Alarm2Sensor(AlarmSensor):
    """PCS (Power Conversion System) alarms - Register 2."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode PCS alarm bits - second register."""
        alarm_descriptions = {
            0: "Leak current out of limit",
            1: "Communication abnormal",
            2: "System internal protection",
            3: "AFCI self-checking circuit fault",
            4: "Off-grid protection",
            5: "Manual operation protection",
            7: "Abnormal phase sequence",
            8: "Short circuit to PE",
            9: "Soft start failure",
        }
        return alarm_descriptions.get(bit_position)


class Alarm3Sensor(AlarmSensor):
    """ESS (Energy Storage System) alarms."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "ESS")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode ESS alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance to ground",
            2: "Temperature too high",
            3: "Equipment fault",
            4: "Under-temperature",
            5: "Internal protection",
            6: "Thermal runaway",
        }
        return alarm_descriptions.get(bit_position)


class Alarm4Sensor(AlarmSensor):
    """Gateway alarms."""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
    ):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "GW")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode Gateway alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Temperature too high",
            2: "Equipment fault",
            3: "Excessive leakage current in off-grid output",
            4: "N line grounding fault",
            5: "Abnormal phase sequence of grid wiring",
            6: "Abnormal phase sequence of inverter wiring",
            7: "Grid phase loss",
        }
        return alarm_descriptions.get(bit_position)


class Alarm5Sensor(AlarmSensor):
    """EV DC Charger alarms."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "EVDC")
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decode DC Charger alarm bits."""
        alarm_descriptions = {
            0: "Software version mismatch",
            1: "Low insulation resistance to ground",
            2: "Over-temperature",
            3: "Equipment fault",
            4: "Charging fault",
            5: "Equipment protection",
        }
        return alarm_descriptions.get(bit_position)


# =============================================================================
# Combined Alarm Sensor
# =============================================================================


class AlarmCombinedSensor(ReadOnlySensor, HybridInverter, PVInverter):
    """Combines multiple alarm sensors into a single view.

    Reads all alarm registers and combines active alarms into one string.
    """

    def __init__(self, name: str, unique_id: str, object_id: str, *alarms: AlarmSensor, **kwargs):
        # Validate alarm sensors
        if not alarms:
            raise ValueError(f"{self.__class__.__name__}: At least one alarm sensor required")

        device_addresses = set(a.device_address for a in alarms)
        if len(device_addresses) != 1:
            raise ValueError(f"{self.__class__.__name__}: All alarms must have same device address (found {device_addresses})")

        # Calculate address range
        first_address = min(a.address for a in alarms)
        last_address = max(a.address + a.count - 1 for a in alarms)
        count = sum(a.count for a in alarms)

        if (last_address - first_address + 1) != count:
            raise ValueError(f"{self.__class__.__name__}: Alarms must have contiguous address ranges (addresses: {[a.address for a in alarms]})")

        self.alarms = list(alarms)
        plant_index: int = kwargs.pop("plant_index", self.alarms[0].plant_index)

        # Remove conflicting kwargs
        kwargs.pop("input_type", None)
        kwargs.pop("device_address", None)
        kwargs.pop("address", None)
        kwargs.pop("count", None)
        kwargs.pop("unique_id_override", None)

        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            scan_interval=min(a.scan_interval for a in alarms),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=Protocol.N_A,
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=list(device_addresses)[0],
            data_type=ModbusDataType.STRING,
            address=first_address,
            count=count,
            unique_id_override=unique_id,
            **kwargs,
        )
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True

    @property
    def protocol_version(self) -> Protocol:
        """Get the highest protocol version from all alarms."""
        protocol = super().protocol_version
        for alarm in self.alarms:
            if alarm.protocol_version > protocol:
                protocol = alarm.protocol_version
        return protocol

    @protocol_version.setter
    def protocol_version(self, protocol_version: Protocol | float):
        """Protocol version is read-only for combined sensors."""
        raise NotImplementedError("protocol_version is read-only for AlarmCombinedSensor")

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Combined sensor doesn't update - it reads from sub-sensors."""
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure topics for combined sensor and all alarm sensors.

        Args:
            device_id: The device identifier

        Returns:
            Base topic path
        """
        base = super().configure_mqtt_topics(device_id)

        # Configure topics for all alarm sensors
        for alarm in self.alarms:
            alarm.configure_mqtt_topics(device_id)

        return base

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get combined alarm state from all alarm sensors.

        Args:
            raw: If True, return raw value
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            Combined alarm string
        """
        if republish and len(self._states) > 0:
            state = self._states[-1][1]
            return self._apply_gain_and_precision(state, raw) if isinstance(state, (float, int)) else state

        no_alarm = _t("AlarmSensor.no_alarm", AlarmSensor.NO_ALARM, self.debug_logging)
        result: str = no_alarm

        # Collect alarms from all publishable sensors
        for alarm in (a for a in self.alarms if a.publishable):
            state = cast(str, await alarm.get_state(raw=False, republish=False, max_length=sys.maxsize, **kwargs))

            if state != no_alarm:
                result = state if result == no_alarm else f"{result}, {state}"

                # Truncate if needed for Home Assistant
                if len(result) > 255 and Config.home_assistant.enabled:
                    result = self._compress_alarm_string(result)

        self.set_state(result)
        return result

    def _compress_alarm_string(self, alarms: str) -> str:
        """Compress alarm string to fit Home Assistant limit.

        Args:
            alarms: Combined alarm string

        Returns:
            Compressed string under 255 characters
        """
        compressed = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", alarms)).strip()

        if len(compressed) > 255:
            compressed = compressed[:252] + "..."

        return compressed

    def state2raw(self, state):
        """Convert alarm state back to code.

        Args:
            state: Alarm description

        Returns:
            0 for NO_ALARM, otherwise pass through
        """
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


# =============================================================================
# Running State Sensor
# =============================================================================


class RunningStateSensor(ReadOnlySensor):
    """Sensor for device running state/status."""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        **kwargs,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=(Config.modbus[plant_index].scan_interval.high if plant_index < len(Config.modbus) else 10),
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:power-settings",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )

        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True
        self[DiscoveryKeys.OPTIONS] = [
            "Standby",  # 0
            "Normal",  # 1
            "Fault",  # 2
            "Power-Off",  # 3
            "",  # 4
            "",  # 5
            "",  # 6
            "Environmental Abnormality",  # 7
        ]

        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self[DiscoveryKeys.OPTIONS])) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Get running state as string.

        Args:
            raw: If True, return raw state code
            republish: If True, return last known state
            **kwargs: Additional arguments

        Returns:
            State description or "Unknown State code: X"
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)

        if raw or value is None:
            return value

        if isinstance(value, (float, int)):
            option = self._get_option(int(value))
            if option:
                return option
            return f"Unknown State code: {value}"

        return f"Unknown State code: {value}"


# =============================================================================
# Resettable Accumulation Sensor
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
        self._persistent_state_file = Path(Config.persistent_state_path, f"{safe_uid}.state")

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

    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
            # Schedule persistence asynchronously. If no running loop, fallback
            # to getting the event loop and use run_coroutine_threadsafe.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(self._persist_current_total(new_total), loop)
                except Exception:
                    # Best effort; ignore scheduling failures
                    pass
            else:
                loop.create_task(self._persist_current_total(new_total))

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
        self._persistent_state_file = Path(Config.persistent_state_path, f"{safe_uid}.atmidnight")

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

    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool = False) -> bool:
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
                # Schedule persistence asynchronously. If no running loop, fallback
                # to getting the event loop and use run_coroutine_threadsafe.
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    try:
                        loop = asyncio.get_event_loop()
                        asyncio.run_coroutine_threadsafe(self._update_state_at_midnight(now_state), loop)
                    except Exception:
                        # Best effort; ignore scheduling failures
                        pass
                else:
                    loop.create_task(self._update_state_at_midnight(now_state))

                asyncio.create_task(self._update_state_at_midnight(now_state))
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
# =============================================================================


class PVPowerSensor(ObservableMixin):
    """Mixin for PV power sensors that can be observed."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        """Handle notification (currently no-op).

        Args:
            modbus_client: Modbus client
            mqtt_client: MQTT client
            value: Notification value
            source: Source topic
            handler: MQTT handler

        Returns:
            Always True
        """
        return True
