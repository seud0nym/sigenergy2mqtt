"""Writable sensor classes: WriteOnlySensor, ReadWriteSensor, NumericSensor, SelectSensor, SwitchSensor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Iterable, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import Constants, Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, InputType, StateClass

from .constants import DiscoveryKeys
from .mixins import WritableSensorMixin
from .readable import ReadOnlySensor
from .sensor import AvailabilityMixin, Sensor

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
            logging.debug(f"{self.log_identity} Discovered components={components}")

        return components

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        """Validate that value is either on or off value.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if valid
        """
        if raw_value not in (self._values["off"], self._values["on"]):
            logging.error(f"{self.log_identity} Invalid value '{raw_value}': Must be either '{self._payloads['on']}' or '{self._payloads['off']}'")
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
        if self._availability_control_sensor is not None and active_config.home_assistant.enabled:
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
        self.sanity_check.delta = False

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
        self[DiscoveryKeys.MODE] = "slider" if (unit == PERCENTAGE and not active_config.home_assistant.edit_percentage_with_box) else "box"
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

        # Apply gain/precision first if raw requested, because min/max are defined in terms of having gain applied
        processed = self._apply_gain_and_precision(state) if raw else state

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
                value = min_val if not raw else min_val

        if DiscoveryKeys.MAX in self and isinstance(self[DiscoveryKeys.MAX], float):
            max_val = cast(float, self[DiscoveryKeys.MAX])
            if value > max_val:
                value = max_val if not raw else max_val

        # Constrain to negative range (tuple)
        if DiscoveryKeys.MIN in self and isinstance(self[DiscoveryKeys.MIN], tuple) and value < 0:
            min_range = cast(tuple[float, ...], self[DiscoveryKeys.MIN])
            if not (min(min_range) <= value <= max(min_range)):
                value = min(min_range) if not raw else min(min_range)

        # Constrain to positive range (tuple)
        if DiscoveryKeys.MAX in self and isinstance(self[DiscoveryKeys.MAX], tuple) and value > 0:
            max_range = cast(tuple[float, ...], self[DiscoveryKeys.MAX])
            if not (min(max_range) <= value <= max(max_range)):
                value = max(max_range) if not raw else max(max_range)

        if value != processed and self.debug_logging:
            logging.debug(f"{self.log_identity} value={state} adjusted to {value}")

        # Re-apply gain to revert to back to raw value if necessary
        if raw and self.gain and self.gain != 1:
            return value * self.gain

        return value

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
            logging.warning(f"{self.log_identity} Ignored attempt to set value to *None*")
            return False

        try:
            state = float(value)
            if self.gain != 1:
                state = state * self.gain  # Convert to raw value
        except Exception as e:
            logging.warning(f"{self.log_identity} Attempt to set value to '{value}' FAILED: {repr(e)}")
            return False

        return await super().set_value(modbus_client, mqtt_client, state, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
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
                    logging.error(f"{self.log_identity} invalid value '{value}' (raw={raw_value}): Less than minimum of {min_val}")
                    return False

            # Check simple maximum
            if isinstance(self.get(DiscoveryKeys.MAX), float):
                max_val = cast(float, self[DiscoveryKeys.MAX])
                if value > max_val:
                    logging.error(f"{self.log_identity} invalid value '{value}' (raw={raw_value}): Greater than maximum of {max_val}")
                    return False

            # Check negative range
            if isinstance(self.get(DiscoveryKeys.MIN), tuple) and value < 0:
                min_range = cast(tuple[float, ...], self[DiscoveryKeys.MIN])
                if not (min(min_range) <= value <= max(min_range)):
                    logging.error(f"{self.log_identity} invalid value '{value}' (raw={raw_value}): Not in range {min_range}")
                    return False

            # Check positive range
            if isinstance(self.get(DiscoveryKeys.MAX), tuple) and value > 0:
                max_range = cast(tuple[float, ...], self[DiscoveryKeys.MAX])
                if not (min(max_range) <= value <= max(max_range)):
                    logging.error(f"{self.log_identity} invalid value '{value}' (raw={raw_value}): Not in range {max_range}")
                    return False

            return True
        except ValueError:
            logging.error(f"{self.log_identity} invalid value '{raw_value}': Not a number")
            return False


class ThreePhaseAdjustmentTargetValue(NumericSensor):
    """NumericSensor Mixin for setting adjustment target values on
    three-phase systems.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "output_type" not in kwargs:
            raise ValueError(f"{self.log_identity}: output_type parameter is required")
        if kwargs["output_type"] != Constants.THREE_PHASE_OUTPUT_TYPE:  # L1/L2/L3/N
            self.publishable = False


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

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
            self.force_publish = True
            logging.error(f"{self.log_identity} invalid value '{value}': Not a valid option or index")
            return False

        return await super().set_value(modbus_client, mqtt_client, index, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
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
            logging.error(f"{self.log_identity} invalid value '{raw_value}': Not a valid option or index")
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

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
            logging.error(f"{self.log_identity} value_is_valid check of value '{value}' FAILED: {repr(e)}")
            raise

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
        """Validate switch value is 0 or 1.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if 0 or 1
        """
        if raw_value not in (self[DiscoveryKeys.PAYLOAD_OFF], self[DiscoveryKeys.PAYLOAD_ON]):
            logging.error(f"{self.log_identity} Failed to write value '{raw_value}': Must be either '{self[DiscoveryKeys.PAYLOAD_OFF]}' or '{self[DiscoveryKeys.PAYLOAD_ON]}'")
            return False
        return True


"""Continuation of base sensor classes (Part 4 - Final).

This file contains alarm sensors, accumulation sensors, and utility sensors.
Merge with previous parts for the complete module.
"""

# =============================================================================
# Alarm Sensor Base Class
