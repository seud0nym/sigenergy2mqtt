"""Sensor bases backed by a cloud battery-control transport."""

from __future__ import annotations

import abc
import logging
import math
from typing import Any, cast

import paho.mqtt.client as mqtt
from aiohttp import ClientError

from sigenergy2mqtt.cloud.exceptions import CloudControlError
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttHandler

from .constants import DiscoveryKeys
from .mixins import ReadableSensorMixin, WriteableSensorMixin
from .sensor import AvailabilityMixin
from .writeable import NumericSensorMixin

logger = logging.getLogger(__name__)

# Track which cloud ports are currently experiencing an outage to suppress
# per-sensor log noise. Key: port id() -> dict of sensor id() -> exc_repr
_port_outage: dict[int, dict[int, str]] = {}
# Track the latest error message for the port to deduplicate "error changed" warnings
_port_latest_error: dict[int, str] = {}


class CloudSensor(ReadableSensorMixin, AvailabilityMixin):
    """Readable sensor whose transport implements :class:`CloudControlPort`."""

    @property
    def payload_available(self) -> bool | int | float | str | None:
        return 1

    @property
    def payload_not_available(self) -> bool | int | float | str | None:
        return 0

    async def _update_internal_state(self, **kwargs) -> bool:
        """Read the current value from the cloud backend and update internal state.

        Expects ``modbus_client`` (a :class:`CloudControlPort` instance or ``None``) in
        *kwargs*.  Returns ``False`` if the port is unavailable, the read fails, or the
        returned value is ``None``; otherwise delegates to :meth:`set_latest_state` and
        returns its result.

        Args:
            **kwargs: Must include ``modbus_client``, the :class:`CloudControlPort`
                used to communicate with the cloud backend.

        Returns:
            ``True`` if the internal state was successfully updated, ``False`` otherwise.

        Raises:
            ValueError: If ``modbus_client`` is not present in *kwargs*.
        """
        if "modbus_client" not in kwargs:
            raise ValueError(f"{self.log_identity}: Required argument 'modbus_client' not supplied")
        port = cast(CloudControlPort | None, kwargs.pop("modbus_client"))
        if port is None:
            return False
        port_id = id(port)
        sensor_id = id(self)
        try:
            value = await self._read_cloud_state(port)
        except (ClientError, CloudControlError) as exc:
            exc_repr = repr(exc)
            port_outages = _port_outage.setdefault(port_id, {})
            
            if not port_outages:
                # First failure for this port - log at WARNING level
                logger.warning(f"{self.log_identity} cloud read failed: {exc_repr}")
                port_outages[sensor_id] = exc_repr
                _port_latest_error[port_id] = exc_repr
            elif sensor_id not in port_outages:
                # Port already in outage, new sensor failing - check if error is new
                port_outages[sensor_id] = exc_repr
                if exc_repr != _port_latest_error.get(port_id):
                    logger.warning(f"{self.log_identity} cloud read failed (error changed): {exc_repr}")
                    _port_latest_error[port_id] = exc_repr
                else:
                    logger.debug(f"{self.log_identity} cloud read failed (outage ongoing): {exc_repr}")
            elif port_outages[sensor_id] != exc_repr:
                # Error changed for this specific sensor - check if it's new for the port
                port_outages[sensor_id] = exc_repr
                if exc_repr != _port_latest_error.get(port_id):
                    logger.warning(f"{self.log_identity} cloud read failed (error changed): {exc_repr}")
                    _port_latest_error[port_id] = exc_repr
                else:
                    logger.debug(f"{self.log_identity} cloud read failed (outage ongoing): {exc_repr}")
            else:
                # Same outage already reported for this sensor - suppress to debug
                logger.debug(f"{self.log_identity} cloud read failed (outage ongoing): {exc_repr}")
            return False
            
        # Successful read: clear outage state for this sensor
        if port_id in _port_outage:
            port_outages = _port_outage[port_id]
            if sensor_id in port_outages:
                was_exc = port_outages.pop(sensor_id)
                if not port_outages:
                    # Last failing sensor recovered
                    logger.info(f"{self.log_identity} cloud read recovered for all sensors (was: {was_exc})")
                    del _port_outage[port_id]
                    _port_latest_error.pop(port_id, None)
                else:
                    logger.debug(f"{self.log_identity} cloud read recovered, but other sensors are still failing")
                    
        if value is None:
            return False
        return self.set_latest_state(cast(Any, value))

    @abc.abstractmethod
    async def _read_cloud_state(self, port: CloudControlPort) -> Any:
        """Retrieve the current sensor value from the cloud backend.

        Subclasses must implement this method to issue the appropriate API call via
        *port* and return the raw value to be stored as the sensor's latest state.

        Args:
            port: The :class:`CloudControlPort` used to communicate with the cloud
                backend.

        Returns:
            The current sensor value, or ``None`` if no value is available.
        """
        ...


class CloudReadWriteSensor(WriteableSensorMixin, CloudSensor):
    """Cloud read/write behaviour mixed with a writable entity mixin."""

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        **kwargs,
    ) -> None:
        """Initialise the cloud read/write sensor.

        Args:
            availability_control_sensor: Optional sensor whose state is used as an
                additional availability gate in the Home Assistant discovery payload.
                Must be an :class:`AvailabilityMixin` instance when provided.
            **kwargs: Forwarded to parent initialisers.

        Raises:
            ValueError: If *availability_control_sensor* is provided but is not an
                :class:`AvailabilityMixin` instance.
        """
        super().__init__(availability_control_sensor=availability_control_sensor, **kwargs)

    async def _write_value(
        self,
        transport: Any,
        mqtt_client: mqtt.Client,
        value: float | str,
        source: str,
        handler: MqttHandler,
    ) -> bool:
        """Write *value* to the cloud backend via the given transport.

        Casts *transport* to a :class:`CloudControlPort` and delegates to
        :meth:`_write_cloud_value`.  Logs an error and returns ``False`` when the
        transport is unavailable or the write raises a network/API exception.

        Args:
            transport: The cloud transport object, expected to be a
                :class:`CloudControlPort` instance (or ``None`` when unavailable).
            mqtt_client: The active MQTT client (unused at this level but required by
                the base-class interface).
            value: The new value to write to the device.
            source: Human-readable description of what triggered the write, used in
                log messages (unused at this level but required by the base-class
                interface).
            handler: The :class:`MqttHandler` coordinating this write (unused at this
                level but required by the base-class interface).

        Returns:
            ``True`` if the write succeeded, ``False`` otherwise.
        """
        port = cast(CloudControlPort | None, transport)
        if port is None:
            logger.error(f"{self.log_identity} cannot write: cloud backend unavailable")
            return False
        try:
            result = await self._write_cloud_value(port, value)
            if result:
                logger.info(f"{self.log_identity} _write_cloud_value value={self._raw2state(value)} (raw={value} latest_raw_state={self.latest_raw_state})")
            return result
        except (ClientError, CloudControlError) as exc:
            logger.error(f"{self.log_identity} cloud write failed: {exc!r}")
            return False

    @abc.abstractmethod
    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        """Send *value* to the cloud backend.

        Subclasses must implement this method to issue the appropriate API call via
        *port* and return whether the write was accepted.

        Args:
            port: The :class:`CloudControlPort` used to communicate with the cloud
                backend.
            value: The new numeric or string value to write.

        Returns:
            ``True`` if the cloud backend accepted the value, ``False`` otherwise.
        """
        ...


class CloudGridLimitSensor(NumericSensorMixin, CloudReadWriteSensor):
    """Number entity for owner grid limits constrained by installer settings."""

    def __init__(
        self,
        *,
        read_method: str,
        write_method: str,
        current_key: str,
        installer_key: str,
        **kwargs,
    ) -> None:
        """Initialise the cloud grid-limit number entity.

        Args:
            read_method: Name of the :class:`CloudControlPort` method to call when
                reading the current grid-limit state from the cloud backend.
            write_method: Name of the :class:`CloudControlPort` method to call when
                writing a new grid-limit value to the cloud backend.
            current_key: Key used to extract the current owner-set limit from the
                cloud API response payload.
            installer_key: Key used to extract the installer-configured maximum from
                the cloud API response payload.
            **kwargs: Forwarded to parent initialisers.
        """
        self._read_method = read_method
        self._write_method = write_method
        self._current_key = current_key
        self._installer_key = installer_key
        self._updates_allowed = False
        self._writable_topic: str | None = None
        super().__init__(minimum=0.0, maximum=0.0, **kwargs)
        self.state_topic_dict_key = current_key

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if active_config.home_assistant.enabled:
            availability = cast(list[dict[str, float | int | str]], self[DiscoveryKeys.AVAILABILITY])
            self._writable_topic = f"{base}/writable"
            availability.append({"topic": self._writable_topic, "payload_available": "1", "payload_not_available": "0"})
        return base

    async def publish(self, mqtt_client: mqtt.Client, transport: Any, republish: bool = False) -> bool:
        published = await super().publish(mqtt_client, transport, republish)
        if self._writable_topic is not None:
            mqtt_client.publish(self._writable_topic, int(self._updates_allowed), qos=self._qos)
        return published

    def _update_installer_maximum(self, maximum: float | None) -> None:
        """Update the entity's maximum to reflect the installer-configured grid limit.

        When *maximum* is ``None`` the upper bound is removed and writes are implicitly
        disallowed (``sanity_check.max_raw`` is reset to ``0.0``).  If the maximum
        changes and a parent device is attached, the device is flagged for
        re-discovery so Home Assistant picks up the updated range.

        Args:
            maximum: The installer-configured upper bound in the same unit as the
                entity, or ``None`` to clear any existing maximum.
        """
        previous = self.get(DiscoveryKeys.MAX)
        if maximum is None:
            self.pop(DiscoveryKeys.MAX, None)
            self.sanity_check.max_raw = 0.0  # If no installer maximum is set, the user cannot apply an override
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Installer maximum is None - {self.sanity_check}")
        else:
            self.apply_min_max(0.0, maximum)
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Installer maximum is {maximum} - {self.sanity_check}")
        if previous != self.get(DiscoveryKeys.MAX) and self.parent_device is not None:
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Requesting rediscover on {self.parent_device.name}")
            self.parent_device.rediscover = True

    def _parse_number(self, payload: dict[str, Any], key: str) -> tuple[float | None, bool]:
        """Extract and validate a numeric value from a cloud API response payload.

        Args:
            payload: The raw dictionary returned by the cloud API call.
            key: The key whose value should be parsed as a number.

        Returns:
            A ``(value, valid)`` tuple where *value* is the parsed ``float`` (or
            ``None`` if the key is absent, empty, non-numeric, or non-finite) and
            *valid* is ``True`` unless the key was present with an unparseable or
            non-finite value.
        """
        value = payload.get(key)
        if value in (None, ""):
            return None, True
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            logger.warning(f"{self.log_identity} cloud response contains invalid {key}={value!r}")
            return None, False
        if not math.isfinite(parsed):
            logger.warning(f"{self.log_identity} cloud response contains invalid {key}={value!r}")
            return None, False
        return parsed, True

    async def _pre_publish(self, state: float | str | None, mqtt_client: mqtt.Client, transport: Any, republish: bool) -> None:
        """Publish discovery if required before publishing state so altered maximum is in effect."""
        from sigenergy2mqtt.devices.base.device import Device

        if isinstance(self.parent_device, Device) and self.parent_device.rediscover and active_config.home_assistant.enabled:
            if self.debug_logging:
                logger.debug(f"{self.log_identity} Publishing discovery on {self.parent_device.name} to reset max/min values")
            info = self.parent_device.publish_discovery(mqtt_client, clean=False)
            if info is not None and info.is_published():
                self.parent_device.rediscover = False

    async def _read_cloud_state(self, port: CloudControlPort) -> dict[str, Any] | None:
        """Read the current grid-limit state from the cloud backend.

        Calls the configured *read_method* on *port* and interprets the response
        payload to derive the current owner-set limit.  Updates the entity's
        installer-configured maximum and ``_updates_allowed`` flag as a side effect.

        Returns the current limit configuration or ``None`` if the cloud response is
        malformed.

        Args:
            port: The :class:`CloudControlPort` used to communicate with the cloud
                backend.

        Returns:
            The current grid-limit configuration as a ``dict``, or ``None`` when
            the API returned an invalid configuration.
        """
        state = await getattr(port, self._read_method)()
        if not isinstance(state, dict):
            logger.warning(f"{self.log_identity} cloud response is not an object: {state!r}")
            self._updates_allowed = False
            self._update_installer_maximum(None)
            return None
        if self.debug_logging:
            logger.debug(f"{self.log_identity} Read cloud state {state}")
        enabled_value = state.get("enable")
        enabled_valid = isinstance(enabled_value, bool)
        if not enabled_valid:
            logger.warning(f"{self.log_identity} cloud response contains invalid enable={enabled_value!r}")
        _, current_valid = self._parse_number(state, self._current_key)
        installer_maximum, installer_valid = self._parse_number(state, self._installer_key)
        # A write enables the limit in the same request, so a currently disabled
        # limit remains writable whenever its installer maximum is usable.
        self._updates_allowed = enabled_valid and current_valid and installer_valid and installer_maximum is not None
        if self.debug_logging:
            logger.debug(f"{self.log_identity} {self._updates_allowed=}")
        self._update_installer_maximum(installer_maximum)
        return state

    async def _write_cloud_value(self, port: CloudControlPort, value: float | str) -> bool:
        """Write a new grid-limit value to the cloud backend.

        The write is refused (with a warning log) when ``_updates_allowed`` is
        ``False``, which occurs whenever the installer has not configured a maximum
        or the most recent cloud read returned invalid data.  A successful write
        also enables the grid limit in the same request.

        Args:
            port: The :class:`CloudControlPort` used to communicate with the cloud
                backend.
            value: The new grid-limit value to apply (converted to ``float`` before
                being sent).

        Returns:
            ``True`` if the value was written successfully, ``False`` if the write
            was refused due to ``_updates_allowed`` being ``False``.
        """
        if not self._updates_allowed:
            logger.warning(f"{self.log_identity} cannot write: grid limit has invalid data or no installer limit")
            return False
        await getattr(port, self._write_method)(float(value), enabled=True)
        return True

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["comment"] = "Only available when the installer has configured a maximum limit."
        return attributes
