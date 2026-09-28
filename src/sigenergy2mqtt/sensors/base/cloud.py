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


class CloudSensor(ReadableSensorMixin, AvailabilityMixin):
    """Readable sensor whose transport implements :class:`CloudControlPort`."""

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
        try:
            value = await self._read_cloud_state(port)
        except (ClientError, CloudControlError) as exc:
            logger.warning(f"{self.log_identity} cloud read failed: {exc!r}")
            return False
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
        if availability_control_sensor is not None and not isinstance(availability_control_sensor, AvailabilityMixin):
            raise ValueError("availability_control_sensor must be an AvailabilityMixin instance")
        self._availability_control_sensor = availability_control_sensor
        self._payload_available = 1
        self._payload_not_available = 0
        super().__init__(**kwargs)

    def set_availability_control_sensor(self, sensor: AvailabilityMixin | None) -> None:
        """Set the availability gate before MQTT topics are configured."""
        if sensor is not None and not isinstance(sensor, AvailabilityMixin):
            raise ValueError("sensor must be an AvailabilityMixin instance")
        self._availability_control_sensor = sensor

    def configure_mqtt_topics(self, device_id: str) -> str:
        """Configure MQTT topics and, when Home Assistant is enabled, append the
        availability gate sensor's topic to the discovery availability list.

        Args:
            device_id: The unique device identifier used to build MQTT topic paths.

        Returns:
            The base MQTT topic string returned by the parent implementation.

        Raises:
            RuntimeError: If the availability gate sensor has not yet had its state
                topic configured.
        """
        base = super().configure_mqtt_topics(device_id)
        gate = self._availability_control_sensor
        if gate is not None and active_config.home_assistant.enabled:
            gate_topic = gate.get(DiscoveryKeys.STATE_TOPIC)
            if not gate_topic:
                raise RuntimeError(f"{self.log_identity} availability sensor topic is not configured")
            availability = cast(list[dict[str, Any]], self[DiscoveryKeys.AVAILABILITY])
            availability.append({
                "topic": gate_topic,
                "payload_available": self._payload_available,
                "payload_not_available": self._payload_not_available,
            })
        return base

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
            return await self._write_cloud_value(port, value)
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
        super().__init__(minimum=0.0, maximum=0.0, **kwargs)

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
        else:
            self.apply_min_max(0.0, maximum)
        if previous != self.get(DiscoveryKeys.MAX) and self.parent_device is not None:
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
        from sigenergy2mqtt.devices.base.ha_publisher import HaPublisherMixin

        if self.parent_device.rediscover and isinstance(self.parent_device, HaPublisherMixin) and active_config.home_assistant.enabled:
            info = self.parent_device.publish_discovery(mqtt_client, clean=False)
            if info is not None and info.is_published():
                self.parent_device.rediscover = False  # pyright: ignore[reportAttributeAccessIssue]

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str:
        """Read the current grid-limit state from the cloud backend.

        Calls the configured *read_method* on *port* and interprets the response
        payload to derive the current owner-set limit.  Updates the entity's
        installer-configured maximum and ``_updates_allowed`` flag as a side effect.

        Returns the numeric current limit when the limit is enabled and all response
        fields are valid, or the string ``"None"`` when the limit is disabled,
        missing, or the response is malformed.

        Args:
            port: The :class:`CloudControlPort` used to communicate with the cloud
                backend.

        Returns:
            The current grid-limit as a ``float``, or ``"None"`` when the value is
            unavailable or the limit is disabled.
        """
        payload = await getattr(port, self._read_method)()
        if not isinstance(payload, dict):
            logger.warning(f"{self.log_identity} cloud response is not an object: {payload!r}")
            self._updates_allowed = False
            self._update_installer_maximum(None)
            return "None"
        enabled_value = payload.get("enable")
        enabled_valid = isinstance(enabled_value, bool)
        if not enabled_valid:
            logger.warning(f"{self.log_identity} cloud response contains invalid enable={enabled_value!r}")
        enabled = enabled_value is True
        current, current_valid = self._parse_number(payload, self._current_key)
        installer_maximum, installer_valid = self._parse_number(payload, self._installer_key)
        # A write enables the limit in the same request, so a currently disabled
        # limit remains writable whenever its installer maximum is usable.
        self._updates_allowed = enabled_valid and current_valid and installer_valid and installer_maximum is not None
        self._update_installer_maximum(installer_maximum)
        if not enabled_valid or not current_valid or not installer_valid or not enabled or current is None:
            return "None"
        return current

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
            logger.warning(f"{self.log_identity} cannot write: grid limit is disabled or has no installer limit")
            return False
        await getattr(port, self._write_method)(float(value), enabled=True)
        return True
