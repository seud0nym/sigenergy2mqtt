"""ReadOnlySensor and ReservedSensor classes."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, cast

from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol, StateClass
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.metrics import Metrics
from sigenergy2mqtt.modbus import ModbusClient, ModbusDataType

from .constants import SensorAttributeKeys
from .mixins import ModbusSensorMixin, ReadableSensorMixin
from .sensor import AvailabilityMixin, Sensor, TypedSensorMixin

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
            raise ValueError(f"{self.log_identity}: Required argument 'modbus_client' not supplied")

        modbus_client: ModbusClient = kwargs["modbus_client"]

        if self.debug_logging:
            self._log_read_attempt()

        try:
            return await self._perform_modbus_read(modbus_client)
        except asyncio.CancelledError:
            logging.warning(f"{self.log_identity} Modbus read interrupted")
            return False
        except asyncio.TimeoutError:
            logging.warning(f"{self.log_identity} Modbus read failed to acquire lock within {self.scan_interval}s")
            return False
        except Exception:
            # Record error in metrics
            await Metrics.modbus_read_error()
            raise

    def _log_read_attempt(self) -> None:
        """Log details of Modbus read attempt."""
        actual_interval = None if len(self._states) == 0 else f"{round(time.time() - self._states[-1][0], 2)}s"

        logging.debug(
            f"{self.log_identity} read_{self.input_type}_registers("
            f"{self.address}, count={self.count}, device_id={self.device_address}) "
            f"plant_index={self.plant_index} interval={self.scan_interval}s "
            f"actual={actual_interval}"
        )

    async def _perform_modbus_read(self, modbus_client: ModbusClient) -> bool:
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
            raise ValueError(f"{self.log_identity}: Unknown input type '{self.input_type}'")

        elapsed = time.monotonic() - start

        # Record metrics
        await Metrics.modbus_read(self.count, elapsed)

        # Check response validity
        result = self._check_register_response(rr, f"read_{self.input_type}_registers")

        if result and rr:
            # Convert registers to value and update state
            value = modbus_client.convert_from_registers(rr.registers, cast(Any, self.data_type))
            if self.debug_logging:
                logging.debug(f"{self.log_identity} Converted registers {rr.registers} to {self.data_type.name} raw state value: {value}")
            # set_latest_state returns True only when self._states was updated
            # (i.e. the value changed, or the repeat-publish interval has elapsed).
            # Returning False here causes get_state() to return None, which
            # suppresses MQTT publication for unchanged repeated values while
            # still allowing derived sensors to evaluate their own state.
            result = self.set_latest_state(value)

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
            f"{self.log_identity} read_{self.input_type}_registers("
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


class UnpublishResetSensorMixin(Sensor):
    """Mixin that unpublishes the reset sensor created by a
    ResettableAccumulationSensor that is no longer required
    because the sensor has been redefined as a ModbusSensor
    sub-class when Sigenergy provide access to the register
    via Modbus, and therefore no longer needs to be
    calculated (and optionally reset).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components: dict[str, dict[str, Any]] = super().get_discovery_components()
        components[f"{self.unique_id}_reset"] = {"platform": "number"}
        return components


# =============================================================================
# Reserved Sensor
# =============================================================================


class ReservedSensor(ReadOnlySensor):
    """Sensor for Modbus registers marked as Reserved in the Protocol document.

    Reserved sensors are never published but can be used for internal logic.
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
        self.sanity_check.min_raw = None
        self.sanity_check.max_raw = None

        # Validate class name
        if not self.__class__.__name__.startswith("Reserved"):
            raise ValueError(f"{self.log_identity}: class name must start with 'Reserved'")

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
