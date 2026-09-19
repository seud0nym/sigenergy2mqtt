"""Sensor bases backed by a cloud battery-control transport."""

from __future__ import annotations

import abc
import logging
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

    async def _read_cloud_state(self, port: CloudControlPort) -> bytes | float:
        payload = await getattr(port, self._read_method)()
        enabled = bool(payload.get("enable"))
        current = payload.get(self._current_key)
        installer_maximum = payload.get(self._installer_key)
        self._updates_allowed = enabled and installer_maximum not in (None, "")
        if self._updates_allowed:
            self.apply_min_max(0.0, float(cast(float | str, installer_maximum)))
        if not enabled or current in (None, ""):
            return b""
        return float(current)

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
