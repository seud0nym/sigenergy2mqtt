from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import Constants, ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, InputType, StateClass

from .constants import DiscoveryKeys
from .mixins import ModbusWriteableSensorMixin, WriteableSensorMixin
from .readable import ReadOnlySensor
from .sensor import AvailabilityMixin, Sensor

logger = logging.getLogger(__name__)
# =============================================================================


class WriteOnlySensor(ModbusWriteableSensorMixin, Sensor):
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
        protocol_version: ProtocolVersion,
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

            if self._names[action] == "" or self._names[action].isspace():
                continue

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
            logger.debug(f"{self.log_identity} Discovered components={components}")

        return components

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | str, source: str, handler: MqttHandler) -> bool:
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

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | str) -> bool:
        """Validate that value is either on or off value.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if valid
        """
        if raw_value not in (self._values["off"], self._values["on"]):
            logger.error(f"{self.log_identity} Invalid value '{raw_value}': Must be either '{self._payloads['on']}' or '{self._payloads['off']}'")
            return False
        return True


# =============================================================================
# Read-Write Sensor
# =============================================================================


class ReadWriteSensor(ModbusWriteableSensorMixin, ReadOnlySensor):
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
        protocol_version: ProtocolVersion,
        **kwargs,
    ):
        # Validate availability control sensor
        if availability_control_sensor is not None and not isinstance(availability_control_sensor, AvailabilityMixin):
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
        self[DiscoveryKeys.ENABLED_BY_DEFAULT] = True
        self._availability_control_sensor = availability_control_sensor
        self._payload_available = 1
        self._payload_not_available = 0
        self._use_raw_for_availability = False

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
            control_topic = (
                self._availability_control_sensor.raw_state_topic if self._use_raw_for_availability and self._availability_control_sensor.publish_raw else self._availability_control_sensor.state_topic
            )

            if not control_topic or control_topic.isspace():
                raise RuntimeError(
                    f"{self.log_identity} - {self._availability_control_sensor.__class__.__name__} {'raw_state_topic' if self._use_raw_for_availability and self._availability_control_sensor.publish_raw else 'state_topic'} has not been configured"
                )

            availability_list = cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY])
            availability_list.append({"topic": control_topic, "payload_available": self._payload_available, "payload_not_available": self._payload_not_available})

        return base


# =============================================================================
# Transport-independent writable entity mixins
# =============================================================================


class NumericSensorMixin(WriteableSensorMixin):
    """Add Home Assistant number configuration and range validation.

    This inherits :class:`WriteableSensorMixin`; provide ``_write_value`` in a
    subclass when the value is not backed by Modbus.
    """

    def __init__(self, minimum: float | tuple[float, float] | None = None, maximum: float | tuple[float, float] | None = None, **kwargs):
        self._validate_min_max_ranges(minimum, maximum)
        super().__init__(**kwargs)
        self[DiscoveryKeys.PLATFORM] = "number"
        self[DiscoveryKeys.MODE] = "slider" if (self.unit == PERCENTAGE and not active_config.home_assistant.edit_percentage_with_box) else "box"
        self[DiscoveryKeys.STEP] = 1 if self.precision is None else 10**-self.precision
        if minimum is None and maximum is None and self.unit == PERCENTAGE:
            minimum, maximum = 0.0, 100.0
        if minimum is not None:
            self[DiscoveryKeys.MIN] = self._format_range_value(minimum)
        if maximum is not None:
            self[DiscoveryKeys.MAX] = self._format_range_value(maximum)

        self._update_sanity_check_ranges(self.gain)

    def _validate_min_max_ranges(self, minimum, maximum) -> None:
        if minimum is None or maximum is None:
            return
        if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)):
            if minimum >= maximum:
                raise AssertionError(f"{self.__class__.__name__}: Invalid min/max values: {minimum}/{maximum} (min must be < max)")
            return
        if isinstance(minimum, tuple) and isinstance(maximum, tuple):
            if len(minimum) != len(maximum):
                raise AssertionError(f"{self.__class__.__name__}: Invalid min/max tuples: different lengths {len(minimum)}/{len(maximum)}")
            for mn, mx in zip(minimum, maximum):
                if not (isinstance(mn, (int, float)) and isinstance(mx, (int, float))):
                    raise TypeError(f"{self.__class__.__name__}: Invalid tuple values: {mn}/{mx} (must be numeric)")
                if mn >= mx:
                    raise ValueError(f"{self.__class__.__name__}: Invalid tuple values: {mn}/{mx} (min must be < max)")
            return
        raise ValueError(f"{self.__class__.__name__}: Invalid min/max types: {type(minimum)}/{type(maximum)}")

    def _format_range_value(self, value):
        return float(value) if isinstance(value, (int, float)) else cast(tuple, value)

    def _update_sanity_check_ranges(self, gain: float | None) -> None:
        if DiscoveryKeys.MIN in self:
            minimum = cast(float | tuple[float, ...], self[DiscoveryKeys.MIN])
            minimum = min(minimum) if isinstance(minimum, tuple) else minimum
            self.sanity_check.min_raw = int(minimum * gain) if gain else int(minimum)
        if DiscoveryKeys.MAX in self:
            maximum = cast(float | tuple[float, ...], self[DiscoveryKeys.MAX])
            maximum = max(maximum) if isinstance(maximum, tuple) else maximum
            self.sanity_check.max_raw = int(maximum * gain) if gain else int(maximum)

    def apply_min_max(self, minimum, maximum) -> None:
        if minimum is None and maximum is None and self.unit == PERCENTAGE:
            self[DiscoveryKeys.MIN], self[DiscoveryKeys.MAX] = 0.0, 100.0
        if minimum is not None:
            self[DiscoveryKeys.MIN] = self._format_range_value(minimum)
        elif maximum is not None:
            self[DiscoveryKeys.MIN] = 0.0 if isinstance(maximum, float) else 0
        if maximum is not None:
            self[DiscoveryKeys.MAX] = self._format_range_value(maximum)
        self._update_sanity_check_ranges(self.gain)

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components = super().get_discovery_components()
        if DiscoveryKeys.MIN in self and isinstance(components[self.unique_id][DiscoveryKeys.MIN], (tuple, list)):
            components[self.unique_id][DiscoveryKeys.MIN] = min(cast(Iterable[float], self[DiscoveryKeys.MIN]))
        if DiscoveryKeys.MAX in self and isinstance(components[self.unique_id][DiscoveryKeys.MAX], (tuple, list)):
            components[self.unique_id][DiscoveryKeys.MAX] = max(cast(Iterable[float], self[DiscoveryKeys.MAX]))
        return components

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        state = await super().get_state(raw=raw, republish=republish, **kwargs)
        if not isinstance(state, (float, int)):
            return state
        processed = cast(float | int, self._apply_gain_and_precision(state) if raw else state)
        if getattr(self, "precision", None) == 0:
            if isinstance(processed, int):
                value = processed
            elif processed == int(processed):
                value = int(processed)
            else:
                value = float(processed)
        else:
            value = float(processed)
        minimum = self.get(DiscoveryKeys.MIN)
        maximum = self.get(DiscoveryKeys.MAX)
        if isinstance(minimum, float):
            value = max(value, minimum)
        if isinstance(maximum, float):
            value = min(value, maximum)
        if isinstance(minimum, tuple) and value < 0 and not (min(minimum) <= value <= max(minimum)):
            value = min(minimum)
        if isinstance(maximum, tuple) and value > 0 and not (min(maximum) <= value <= max(maximum)):
            value = max(maximum)
        if raw and self.gain and self.gain != 1:
            return value * self.gain
        return value

    async def set_value(self, modbus_client, mqtt_client, value, source, handler) -> bool:
        if value is None:
            logger.warning(f"{self.log_identity} Ignored attempt to set value to *None*")
            return False
        try:
            state = float(value)
            if self.gain != 1:
                state *= self.gain
        except (ValueError, TypeError, RuntimeError) as exc:
            logger.warning(f"{self.log_identity} Attempt to set value to '{value}' FAILED: {exc!r}")
            return False
        return await super().set_value(modbus_client, mqtt_client, state, source, handler)

    async def value_is_valid(self, modbus_client, raw_value) -> bool:
        try:
            value = cast(float, self._apply_gain_and_precision(float(raw_value)))
            minimum, maximum = self.get(DiscoveryKeys.MIN), self.get(DiscoveryKeys.MAX)
            if isinstance(minimum, float) and value < minimum:
                return False
            if isinstance(maximum, float) and value > maximum:
                return False
            if isinstance(minimum, tuple) and value < 0 and not (min(minimum) <= value <= max(minimum)):
                return False
            if isinstance(maximum, tuple) and value > 0:
                return min(maximum) <= value <= max(maximum)
            return True
        except (TypeError, ValueError):
            return False


class SelectSensorMixin(WriteableSensorMixin):
    """Add Home Assistant select configuration and option validation."""

    def __init__(self, options: list[str], **kwargs):
        # Validate options
        if not options or not isinstance(options, list):
            raise ValueError(f"{self.__class__.__name__}: options must be a non-empty list")

        if not all(isinstance(o, str) for o in options):
            raise ValueError(f"{self.__class__.__name__}: all options must be strings")

        super().__init__(**kwargs)

        self[DiscoveryKeys.PLATFORM] = "select"
        self[DiscoveryKeys.OPTIONS] = options
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw or value is None:
            return value
        if isinstance(value, (float, int)):
            option = self._get_option(int(value))
            return option if option else f"Unknown Mode: {value}"
        return f"Unknown Mode: {value}"

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | str, source: str, handler: MqttHandler) -> bool:
        try:
            value = self._get_option_index(value)
        except ValueError:
            self.force_publish = True
            logger.error(f"{self.log_identity} invalid value '{value}': Not a valid option or index")
            return False
        return await super().set_value(modbus_client, mqtt_client, value, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | str) -> bool:
        try:
            self._get_option_index(raw_value)
        except ValueError:
            logger.error(f"{self.log_identity} invalid value '{raw_value}': Not a valid option or index")
            return False
        return True


class SwitchSensorMixin(WriteableSensorMixin):
    """Add Home Assistant switch configuration and binary value validation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self[DiscoveryKeys.PLATFORM] = "switch"
        self[DiscoveryKeys.PAYLOAD_OFF] = 0
        self[DiscoveryKeys.PAYLOAD_ON] = 1
        self[DiscoveryKeys.STATE_OFF] = 0
        self[DiscoveryKeys.STATE_ON] = 1
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = 1

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | str, source: str, handler: MqttHandler) -> bool:
        return await super().set_value(modbus_client, mqtt_client, int(value), source, handler)

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | str) -> bool:
        return raw_value in (self[DiscoveryKeys.PAYLOAD_OFF], self[DiscoveryKeys.PAYLOAD_ON])


# =============================================================================
# Numeric Sensor
# =============================================================================


class NumericSensor(NumericSensorMixin, ReadWriteSensor):
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
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: ProtocolVersion,
        minimum: float | tuple[float, float] | None = None,
        maximum: float | tuple[float, float] | None = None,
        **kwargs,
    ):
        kwargs.pop("state_class", None)
        super().__init__(
            availability_control_sensor=availability_control_sensor,
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
            state_class=None,
            icon=icon,
            gain=gain,
            precision=precision,
            protocol_version=protocol_version,
            minimum=minimum,
            maximum=maximum,
            **kwargs,
        )
        self.sanity_check.delta = False


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


class SelectSensor(SelectSensorMixin, ReadWriteSensor):
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
        protocol_version: ProtocolVersion,
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
            options=options,
            **kwargs,
        )


# =============================================================================
# Switch Sensor
# =============================================================================


class SwitchSensor(SwitchSensorMixin, ReadWriteSensor):
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
        protocol_version: ProtocolVersion,
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

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | str, source: str, handler: MqttHandler) -> bool:
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
            logger.error(f"{self.log_identity} value_is_valid check of value '{value}' FAILED: {e!r}")
            raise

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | str) -> bool:
        """Validate switch value is 0 or 1.

        Args:
            modbus_client: Modbus client (unused)
            raw_value: Value to validate

        Returns:
            True if 0 or 1
        """
        if raw_value not in (self[DiscoveryKeys.PAYLOAD_OFF], self[DiscoveryKeys.PAYLOAD_ON]):
            logger.error(f"{self.log_identity} Failed to write value '{raw_value}': Must be either '{self[DiscoveryKeys.PAYLOAD_OFF]}' or '{self[DiscoveryKeys.PAYLOAD_ON]}'")
            return False
        return True
