"""Constants and utilities for the sensors module."""

from __future__ import annotations

from typing import Any, Final

from sigenergy2mqtt.common import DeviceClass, StateClass

# =============================================================================
# Constants
# =============================================================================

# State history configuration
_DEFAULT_STATE_HISTORY_SIZE: Final = 2  # Keep current and previous state for delta calculations


# Home Assistant Discovery Configuration Keys
class DiscoveryKeys:
    """Constants for Home Assistant Discovery Configuration message keys."""

    AVAILABILITY = "availability"
    AVAILABILITY_MODE = "availability_mode"
    AVAILABILITY_TOPIC = "availability_topic"
    COMMAND_TOPIC = "command_topic"
    DEFAULT_ENTITY_ID = "default_entity_id"
    DEVICE_CLASS = "device_class"
    DISPLAY_PRECISION = "display_precision"
    ENABLED_BY_DEFAULT = "enabled_by_default"
    ENTITY_CATEGORY = "entity_category"
    ICON = "icon"
    JSON_ATTRIBUTES_TOPIC = "json_attributes_topic"
    MAX = "max"
    MIN = "min"
    MODE = "mode"
    NAME = "name"
    OBJECT_ID = "object_id"
    OPTIONS = "options"
    PAYLOAD_AVAILABLE = "payload_available"
    PAYLOAD_NOT_AVAILABLE = "payload_not_available"
    PAYLOAD_OFF = "payload_off"
    PAYLOAD_ON = "payload_on"
    PLATFORM = "platform"
    RAW_STATE_TOPIC = "raw_state_topic"
    STATE_CLASS = "state_class"
    STATE_OFF = "state_off"
    STATE_ON = "state_on"
    STATE_TOPIC = "state_topic"
    STEP = "step"
    UNIQUE_ID = "unique_id"
    TOPIC = "topic"
    UNIT_OF_MEASUREMENT = "unit_of_measurement"


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
type SensorValue = str | int | bool | float | list[str] | list[dict[str, str]] | tuple[float, ...]
type SensorAttribute = SensorValue | DeviceClass | StateClass | None
type SensorDict = dict[str, SensorAttribute]
type StateHistory = list[tuple[float, Any]]


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
