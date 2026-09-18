"""Sensor bases backed by a cloud battery-control transport."""

from __future__ import annotations

import abc
import logging
from typing import Any, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.cloud.exceptions import BatteryControlError
from sigenergy2mqtt.cloud.port import BatteryControlPort
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttHandler

from .constants import DiscoveryKeys
from .mixins import ReadableSensorMixin, WriteableSensorMixin
from .sensor import AvailabilityMixin

logger = logging.getLogger(__name__)


class CloudSensor(ReadableSensorMixin, AvailabilityMixin):
    """Readable sensor whose transport implements :class:`BatteryControlPort`."""

    async def _update_internal_state(self, **kwargs) -> bool:
        if "modbus_client" not in kwargs:
            raise ValueError(
                f"{self.log_identity}: Required argument 'modbus_client' not supplied"
            )
        port = cast(BatteryControlPort | None, kwargs.pop("modbus_client"))
        if port is None:
            return False
        try:
            value = await self._read_cloud_state(port)
        except BatteryControlError as exc:
            logger.warning(f"{self.log_identity} cloud read failed: {exc!r}")
            return False
        if value is None:
            return False
        return self.set_latest_state(value)

    @abc.abstractmethod
    async def _read_cloud_state(
        self, port: BatteryControlPort
    ) -> float | int | str | None: ...


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
        port = cast(BatteryControlPort | None, transport)
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
        self, port: BatteryControlPort, value: float | str
    ) -> bool: ...
