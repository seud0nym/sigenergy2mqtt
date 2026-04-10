"""Sensor mixins for readable, writable, observable, and substitute behaviors."""

from __future__ import annotations

import abc
import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING, Any, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.common import Constants, DeviceClass, InputType
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.metrics import Metrics
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

from .constants import (
    DiscoveryKeys,
    ModbusLockFactory,
)
from .sensor import Sensor, SensorDebuggingMixin, TypedSensorMixin

try:
    from ._sigenergy_local_modbus_registers import SIGENERGY_LOCAL_MODBUS_REGISTERS
except ImportError:
    SIGENERGY_LOCAL_MODBUS_REGISTERS = {}

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

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
        for identifier in active_config.sensor_overrides.keys():  # type: ignore[reportGeneralTypeIssues]
            overrides = self._get_applicable_overrides(identifier)
            if overrides and "scan-interval" in overrides:
                if self.scan_interval != overrides["scan-interval"]:
                    logging.debug(f"{self.log_identity} Applying {identifier} 'scan-interval' override ({overrides['scan-interval']})")
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
            return active_config.sensor_overrides[identifier]
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

    if TYPE_CHECKING:

        @property
        def log_identity(self) -> str: ...

        def refresh_log_identity(self) -> None: ...

    def __init__(self, input_type: InputType, plant_index: int, device_address: int, address: int, count: int, unique_id_override: str | None = None, **kwargs):
        # Validate parameters
        if not (1 <= device_address <= Constants.PLANT_DEVICE_ADDRESS):
            raise AssertionError(f"{self.__class__.__name__}: Invalid device address {device_address}")

        if address < 30000:
            raise AssertionError(f"{self.__class__.__name__}: Invalid address {address}")

        if count <= 0:
            raise AssertionError(f"{self.__class__.__name__}: Invalid count {count}")

        use_slm_naming = (  # Exclude combined alarm sensors from SLM naming otherwise will cause duplicate entity_id error
            not getattr(self, "alarms", None) and active_config.home_assistant.enabled and active_config.home_assistant.sigenergy_local_modbus_naming
        )
        slm_map = SIGENERGY_LOCAL_MODBUS_REGISTERS.get(address) if use_slm_naming else None

        if slm_map:
            kwargs[DiscoveryKeys.OBJECT_ID] = str(slm_map["object_id"])
            kwargs.pop(DiscoveryKeys.UNIT_OF_MEASUREMENT, None)
            uom = cast(str | None, slm_map.get("unit"))
            if uom == "s" and kwargs[DiscoveryKeys.DEVICE_CLASS] == DeviceClass.TIMESTAMP:
                pass  # Sigenergy-Local-Modbus register definitions incorrectly apply numeric UoM "s" to non-numeric device class "timestamp"
            elif uom is not None:
                kwargs["unit"] = uom
            kwargs["gain"] = cast(float | None, slm_map.get("gain"))

        # Set unique_id
        if unique_id_override is not None:
            kwargs[DiscoveryKeys.UNIQUE_ID] = unique_id_override
        else:
            kwargs[DiscoveryKeys.UNIQUE_ID] = f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{address}"

        self.unique_id = kwargs[DiscoveryKeys.UNIQUE_ID]

        super().__init__(**kwargs)

        self.address = address
        self.count = count
        self.device_address = device_address
        self.input_type = input_type
        self.plant_index = plant_index
        self.refresh_log_identity()

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
            logging.error(f"{self.log_identity} Modbus {source} failed to read registers (None response)")
            return False

        if self.debug_logging:
            logging.debug(f"{self.log_identity} Modbus {source} response: {rr}")

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
        logging.error(f"{self.log_identity} Modbus {source} returned 0x01 ILLEGAL FUNCTION")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x01 ILLEGAL FUNCTION")

    def _handle_illegal_data_address(self, source: str, rr: ModbusPDU) -> None:
        """Handle illegal data address exception."""
        logging.error(f"{self.log_identity} Modbus {source} returned 0x02 ILLEGAL DATA ADDRESS")
        if self.debug_logging:
            logging.debug(rr)

        # Disable retries for invalid addresses on read operations
        if source != "write_registers":
            logging.warning(f"{self.log_identity} Setting max allowed failures to 0 for '{self.unique_id}' because of ILLEGAL DATA ADDRESS exception")
            self._max_failures = 0
            self._max_failures_retry_interval = 0

        raise Exception("0x02 ILLEGAL DATA ADDRESS")

    def _handle_illegal_data_value(self, source: str, rr: ModbusPDU) -> None:
        """Handle illegal data value exception."""
        logging.error(f"{self.log_identity} Modbus {source} returned 0x03 ILLEGAL DATA VALUE")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x03 ILLEGAL DATA VALUE")

    def _handle_slave_device_failure(self, source: str, rr: ModbusPDU) -> None:
        """Handle slave device failure exception."""
        logging.error(f"{self.log_identity} Modbus {source} returned 0x04 SLAVE DEVICE FAILURE")
        if self.debug_logging:
            logging.debug(rr)
        raise Exception("0x04 SLAVE DEVICE FAILURE")

    def _handle_unknown_exception(self, source: str, rr: ModbusPDU) -> None:
        """Handle unknown exception."""
        logging.error(f"{self.log_identity} Modbus {source} returned {rr}")
        raise Exception(rr)


# =============================================================================
# Read-Only Sensor


# =============================================================================


class ObservableMixin(abc.ABC):
    """Mixin for sensors that can be observed/controlled via MQTT."""

    @abc.abstractmethod
    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
            raise RuntimeError(f"{self.log_identity} command topic is not defined")
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

        # Lazy import to avoid circular dependencies
        from .writable import SwitchSensor, WriteOnlySensor

        # Handle Option-based sensors
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

    async def _write_registers(self, modbus_client: ModbusClient, raw_value: float | int | str, mqtt_client: mqtt.Client) -> bool:
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

        logging.info(f"{self.log_identity} _write_registers value={self._raw2state(raw_value)} (raw={raw_value} latest_raw_state={self.latest_raw_state} address={self.address} device_id={device_id})")

        # Convert value to registers
        registers = self._convert_value_to_registers(modbus_client, raw_value)
        method = "write_register" if len(registers) == 1 else "write_registers"

        self.force_publish = True

        try:
            return await self._perform_modbus_write(modbus_client, registers, device_id, no_response_expected, method)
        except asyncio.CancelledError:
            logging.warning(f"{self.log_identity} Modbus write interrupted")
            return False
        except asyncio.TimeoutError:
            logging.warning(f"{self.log_identity} Modbus write failed to acquire lock within {max_wait}s")
            return False
        except Exception as e:
            logging.error(f"{self.log_identity} write_registers: {repr(e)}")
            await Metrics.modbus_write_error()
            raise

    def _convert_value_to_registers(self, modbus_client: ModbusClient, raw_value: float | int | str) -> list[int]:
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
            return modbus_client.convert_to_registers(str(raw_value), cast(Any, self.data_type))

        # Numeric values
        return modbus_client.convert_to_registers(int(raw_value), cast(Any, self.data_type))

    async def _perform_modbus_write(self, modbus_client: ModbusClient, registers: list[int], device_id: int, no_response_expected: bool, method: str) -> bool:
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

        # Record metrics
        await Metrics.modbus_write(len(registers), elapsed)

        if self.debug_logging:
            logging.debug(
                f"{self.log_identity} {method}({self.address}, value={registers}, device_id={device_id}, no_response_expected={no_response_expected}) [plant_index={self.plant_index}] took {elapsed:.3f}s"
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

    async def set_value(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
        self.force_publish = True

        if modbus_client is None:
            raise ValueError(f"{self.log_identity}: ModbusClient cannot be None")

        try:
            if not await self.value_is_valid(modbus_client, value):
                return False
        except Exception as e:
            logging.error(f"{self.log_identity} value_is_valid check of value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) FAILED: {repr(e)}")
            raise

        if source == self[DiscoveryKeys.COMMAND_TOPIC]:
            return await self._write_registers(modbus_client, value, mqtt_client)
        else:
            logging.error(f"{self.log_identity} Attempt to set value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) from unknown topic {source}")
            return False

    async def value_is_valid(self, modbus_client: ModbusClient | None, raw_value: float | int | str) -> bool:
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


class PVPowerSensor(ObservableMixin):
    """Mixin for PV power sensors that can be observed."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def notify(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
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
