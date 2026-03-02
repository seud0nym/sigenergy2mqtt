"""Core Sensor class and foundational mixins."""

from __future__ import annotations

import abc
import asyncio
import html
import json
import logging
import re
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import DeviceClass, Protocol, RegisterAccess, StateClass
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

from .constants import _DEFAULT_STATE_HISTORY_SIZE, DiscoveryKeys, SensorAttribute, SensorAttributeKeys, _sanitize_path_component
from .sanity_check import SanityCheck, SanityCheckException

if TYPE_CHECKING:
    from .derived import DerivedSensor

# =============================================================================


class SensorDebuggingMixin:
    """Mixin that adds debug logging capability to sensors."""

    def __init__(self, **kwargs):
        self.debug_logging: bool = cast(bool, kwargs.get("debug_logging", active_config.sensor_debug_logging))
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

    """

    # Class-level tracking of used IDs (intentional shared state)
    _used_object_ids: dict[str, str] = {}
    _used_unique_ids: dict[str, str] = {}

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
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = active_config.home_assistant.enabled_by_default

        self._gain: float | None = gain

        # Publishing state
        self._attributes_published: bool = False
        self._publish_raw: bool = False
        self._publishable: bool = True

        # Use sanitized unique_id for file paths
        safe_unique_id = _sanitize_path_component(unique_id)
        self._persistent_publish_state_file: Path = Path(active_config.persistent_state_path, f"{safe_unique_id}.publishable")

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
        self.derived_sensors: dict[str, DerivedSensor] = {}
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
            delta=None,
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

        if not unique_id.startswith(active_config.home_assistant.unique_id_prefix):
            raise AssertionError(f"{self.__class__.__name__} unique_id {unique_id} does not start with '{active_config.home_assistant.unique_id_prefix}'")

    def _validate_object_id(self, object_id: str) -> None:
        """Validate that object_id is not duplicated and has correct prefix.

        Args:
            object_id: The object identifier to validate

        Raises:
            ValueError: If validation fails
        """
        if object_id in self._used_object_ids and self._used_object_ids[object_id] != self.__class__.__name__:
            raise AssertionError(f"{self.__class__.__name__} object_id {object_id} has already been used for class {self._used_object_ids[object_id]}")

        if not object_id.startswith(active_config.home_assistant.entity_id_prefix):
            raise AssertionError(f"{self.__class__.__name__} object_id {object_id} does not start with '{active_config.home_assistant.entity_id_prefix}'")

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

        self.derived_sensors[sensor.__class__.__name__] = sensor

    def apply_sensor_overrides(self, registers: RegisterAccess | None):
        """Apply configuration overrides from config file.

        Args:
            registers: Register access configuration for this device
        """
        # Pre-compile regex patterns for efficiency
        identifier_patterns = {identifier: re.compile(identifier) for identifier in active_config.sensor_overrides.keys()}  # type: ignore[reportGeneralTypeIssues]

        for identifier, pattern in identifier_patterns.items():
            if self._matches_override_pattern(pattern):
                self._apply_override(identifier, active_config.sensor_overrides[identifier])

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
        # Lazy imports to avoid circular dependencies
        from .derived import DerivedSensor
        from .mixins import ReadableSensorMixin, WritableSensorMixin
        from .writable import WriteOnlySensor

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

        if active_config.home_assistant.enabled:
            self[DiscoveryKeys.AVAILABILITY_MODE] = "all"
            self[DiscoveryKeys.AVAILABILITY] = [{"topic": f"{active_config.home_assistant.discovery_prefix}/device/{device_id}/availability"}]

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
        if active_config.home_assistant.enabled and not active_config.home_assistant.use_simplified_topics:
            return f"{active_config.home_assistant.discovery_prefix}/{self[DiscoveryKeys.PLATFORM]}/{device_id}/{self[DiscoveryKeys.OBJECT_ID]}"
        else:
            return f"sigenergy2mqtt/{self[DiscoveryKeys.OBJECT_ID]}"

    def _log_configured_topics(self) -> None:
        """Log the configured MQTT topics for debugging."""
        logging.debug(f"{self.__class__.__name__} Configured MQTT topics (enabled={active_config.home_assistant.enabled} simplified={active_config.home_assistant.use_simplified_topics})")
        for key in (DiscoveryKeys.STATE_TOPIC, DiscoveryKeys.RAW_STATE_TOPIC, DiscoveryKeys.JSON_ATTRIBUTES_TOPIC, DiscoveryKeys.AVAILABILITY):
            if key in self:
                logging.debug(f"{self.__class__.__name__} >>> {key}={self[key]})")

    def get_attributes(self) -> dict[str, float | int | str]:
        """Get sensor attributes for MQTT publishing.

        Returns:
            Dictionary of sensor attributes
        """
        attributes: dict[str, float | int | str] = {}

        # Lazy imports to avoid circular dependencies
        from .mixins import ReadableSensorMixin, WritableSensorMixin

        if not active_config.home_assistant.enabled:
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
        if self.publishable and not active_config.clean:
            self._cleanup_persistent_state_file()
        else:
            components = self._handle_unpublishable_discovery(mqtt_client, components)

        return components

    def _cleanup_persistent_state_file(self) -> None:
        """Remove persistent state file if sensor is publishable and not in clean mode."""
        if self._persistent_publish_state_file.exists():
            try:
                self._persistent_publish_state_file.unlink(missing_ok=True)
                logging.debug(f"{self.__class__.__name__} Removed {self._persistent_publish_state_file} (publishable={self.publishable} clean={active_config.clean})")
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
        if self._persistent_publish_state_file.exists() or active_config.clean:
            components = {}
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery (persistent file exists={self._persistent_publish_state_file.exists()} clean={active_config.clean})")
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

        # Ensure integer type is returned when precision == 0 or None
        if not raw and not isinstance(result, str) and self.precision in (0, None) and isinstance(result, float) and result == int(result):
            return int(result)

        return result

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool = False) -> bool:
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

    async def _attempt_publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool) -> bool:
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

    async def _publish_derived_sensors(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, republish: bool) -> None:
        """Publish all derived sensors.

        Args:
            mqtt_client: MQTT client for publishing
            modbus_client: Modbus client for reading values
            republish: If True, republish last known state
        """
        for sensor in self.derived_sensors.values():
            await sensor.publish(mqtt_client, modbus_client, republish=republish)

    def _handle_publish_error(self, mqtt_client: mqtt.Client, modbus_client: ModbusClient | None, error: Exception) -> bool:
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

        if active_config.home_assistant.enabled:
            self.publish_attributes(mqtt_client, clean=False, failures=self._failures, exception=f"{repr(error)}")

        if self._failures >= self._max_failures:
            self._log_publish_disabled()

        return False

    def _update_failure_count(self, error: Exception) -> None:
        """Update failure count and next retry time.

        Args:
            error: The exception that occurred
        """
        if isinstance(error, SanityCheckException) and not active_config.sanity_check_failures_increment:
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
        affected = [s.__class__.__name__ for s in self.derived_sensors.values()]
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
        for sensor in self.derived_sensors.values():
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

    def set_latest_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> bool:
        """Update latest state and propagate to derived sensors.

        Args:
            state: The new state value

        Returns:
            True if state was updated and should be published, False if state was suppressed as a repeated
        """
        # Determine whether the incoming value is a repeat of the last recorded state.
        previous_raw = self._states[-1][1] if self._states else None
        state_is_repeated = previous_raw is not None and state == previous_raw

        if not state_is_repeated:
            # Value has changed – always record and publish.
            self.set_state(state)
            updated = True
        else:
            interval = active_config.repeated_state_publish_interval
            if interval == 0:
                # Always republish even when the value is unchanged.
                self.set_state(state)
                updated = True
            elif interval < 0:
                # Never republish an unchanged value.
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} Repeated state suppressed (repeated_state_publish_interval={interval}): {state=}")
                updated = False
            else:
                # Republish only when a full interval (or multiple thereof) has elapsed
                # since the state was first recorded at this value.
                elapsed = time.time() - self._states[-1][0]
                if elapsed >= interval:
                    if self.debug_logging:
                        logging.debug(f"{self.__class__.__name__} Repeated state republished after {elapsed:.1f}s (repeated_state_publish_interval={interval}): {state=}")
                    self.set_state(state)
                    updated = True
                else:
                    if self.debug_logging:
                        logging.debug(f"{self.__class__.__name__} Repeated state suppressed ({elapsed:.1f}s < repeated_state_publish_interval={interval}): {state=}")
                    updated = False

        # Always pass the current state to derived sensors regardless of suppression,
        # so they can make their own publishing decisions.
        for sensor in self.derived_sensors.values():
            sensor.set_source_values(self, self._states)

        return updated

    def _get_applicable_overrides(self, identifier: str) -> dict | None:
        """Get override configuration if identifier matches this sensor.

        Args:
            identifier: The override identifier pattern

        Returns:
            Override configuration dict or None
        """
        pattern = re.compile(identifier)
        if self._matches_override_pattern(pattern):
            return active_config.sensor_overrides[identifier]
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
                state = int(state)  # pyrefly: ignore (int and float are both valid)

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
            return ""  # in-range but undocumented: return empty string, not None

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# =============================================================================
# Derived Sensor Classes
