"""Sensor bases backed by a cloud battery-control transport."""

from __future__ import annotations

import abc
import logging
import math
from typing import Any, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.cloud.exceptions import BatteryControlError
from sigenergy2mqtt.cloud.port import CloudControlPort
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttHandler

from .constants import DiscoveryKeys
from .mixins import ReadableSensorMixin, WriteableSensorMixin
from .writeable import NumericSensorMixin
from .sensor import AvailabilityMixin

logger = logging.getLogger(__name__)


class CloudSensor(ReadableSensorMixin, AvailabilityMixin):
    """Readable sensor whose transport implements :class:`CloudControlPort`."""

    async def _update_internal_state(self, **kwargs) -> bool:
        if "modbus_client" not in kwargs:
            raise ValueError(
                f"{self.log_identity}: Required argument 'modbus_client' not supplied"
            )
        port = cast(CloudControlPort | None, kwargs.pop("modbus_client"))
        if port is None:
            return False
        try:
            value = await self._read_cloud_state(port)
        except BatteryControlError as exc:
            logger.warning(f"{self.log_identity} cloud read failed: {exc!r}")
            return False
        if value is None:
            return False
        return self.set_latest_state(cast(Any, value))

    @abc.abstractmethod
    async def _read_cloud_state(
        self, port: CloudControlPort
    ) -> bytes | float | int | str | None: ...


class CloudReadWriteSensor(WriteableSensorMixin, CloudSensor):
    """Cloud read/write behavior mixed with a writable entity mixin."""

    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        **kwargs,
    ) -> None:
        if availability_control_sensor is not None and not isinstance(
            availability_control_sensor, AvailabilityMixin
        ):
            raise ValueError(
                "availability_control_sensor must be an AvailabilityMixin instance"
            )
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
        base = super().configure_mqtt_topics(device_id)
        gate = self._availability_control_sensor
        if gate is not None and active_config.home_assistant.enabled:
            gate_topic = gate.get(DiscoveryKeys.STATE_TOPIC)
            if not gate_topic:
                raise RuntimeError(
                    f"{self.log_identity} availability sensor topic is not configured"
                )
            availability = cast(list[dict[str, Any]], self[DiscoveryKeys.AVAILABILITY])
            availability.append(
                {
                    "topic": gate_topic,
                    "payload_available": self._payload_available,
                    "payload_not_available": self._payload_not_available,
                }
            )
        return base

    async def _write_value(
        self,
        transport: Any,
        mqtt_client: mqtt.Client,
        value: float | str,
        source: str,
        handler: MqttHandler,
    ) -> bool:
        port = cast(CloudControlPort | None, transport)
        if port is None:
            logger.error(f"{self.log_identity} cannot write: cloud backend unavailable")
            return False
        try:
            return await self._write_cloud_value(port, value)
        except BatteryControlError as exc:
            logger.error(f"{self.log_identity} cloud write failed: {exc!r}")
            return False

    @abc.abstractmethod
    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool: ...


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
        self._read_method = read_method
        self._write_method = write_method
        self._current_key = current_key
        self._installer_key = installer_key
        self._updates_allowed = False
        super().__init__(minimum=0.0, maximum=None, **kwargs)

    def _update_installer_maximum(self, maximum: float | None) -> None:
        previous = self.get(DiscoveryKeys.MAX)
        if maximum is None:
            self.pop(DiscoveryKeys.MAX, None)
            self.sanity_check.max_raw = None
        else:
            self.apply_min_max(0.0, maximum)
        if previous != self.get(DiscoveryKeys.MAX) and self.parent_device is not None:
            self.parent_device.rediscover = True

    def _parse_number(
        self, payload: dict[str, Any], key: str
    ) -> tuple[float | None, bool]:
        value = payload.get(key)
        if value in (None, ""):
            return None, True
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            logger.warning(
                f"{self.log_identity} cloud response contains invalid {key}={value!r}"
            )
            return None, False
        if not math.isfinite(parsed):
            logger.warning(
                f"{self.log_identity} cloud response contains invalid {key}={value!r}"
            )
            return None, False
        return parsed, True

    async def _read_cloud_state(self, port: CloudControlPort) -> float | str:
        payload = await getattr(port, self._read_method)()
        if not isinstance(payload, dict):
            logger.warning(
                f"{self.log_identity} cloud response is not an object: {payload!r}"
            )
            self._updates_allowed = False
            self._update_installer_maximum(None)
            return "None"
        enabled_value = payload.get("enable")
        enabled_valid = isinstance(enabled_value, bool)
        if not enabled_valid:
            logger.warning(
                f"{self.log_identity} cloud response contains invalid enable={enabled_value!r}"
            )
        enabled = enabled_value is True
        current, current_valid = self._parse_number(payload, self._current_key)
        installer_maximum, installer_valid = self._parse_number(
            payload, self._installer_key
        )
        self._updates_allowed = (
            enabled
            and current_valid
            and installer_valid
            and installer_maximum is not None
        )
        self._update_installer_maximum(installer_maximum)
        if (
            not enabled_valid
            or not current_valid
            or not installer_valid
            or not enabled
            or current is None
        ):
            return "None"
        return current

    async def _write_cloud_value(
        self, port: CloudControlPort, value: float | str
    ) -> bool:
        if not self._updates_allowed:
            logger.warning(
                f"{self.log_identity} cannot write: grid limit is disabled or has no installer limit"
            )
            return False
        await getattr(port, self._write_method)(float(value), enabled=True)
        return True
