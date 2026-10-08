"""
Runtime settings shared by diagnostics and optional MQTT publishing.

:class:`SettingsService` wires together the individual :mod:`sensors`
sensor entities and handles the service lifecycle.
"""

import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.sensors.settings import (
    ApplicationLogLevel,
    CloudLogLevel,
    DiagnosticsLogLevel,
    InfluxDBLogLevel,
    ModbusLogLevel,
    MQTTLogLevel,
    PersistenceDebugging,
    PVOutputCalcDebugLogging,
    PVOutputLogLevel,
    PVOutputUpdateDebugLogging,
    PVOutputUploadLogLevel,
    RepeatedStatePublishInterval,
    SanityCheckFailuresIncrement,
)

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

logger = logging.getLogger(__name__)


class SettingsService(Device):
    """Expose runtime settings to diagnostics, with optional MQTT publishing."""

    def __init__(self):
        unique_id = f"{active_config.home_assistant.unique_id_prefix}_config"
        super().__init__("Sigenergy2MQTT Runtime Configuration", -1, unique_id, "sigenergy2mqtt", "Transient Configuration Settings", ProtocolVersion.N_A)

        self._add_sensor(ApplicationLogLevel())
        self._add_sensor(ModbusLogLevel())
        self._add_sensor(MQTTLogLevel())
        self._add_sensor(PersistenceDebugging())

        self._add_sensor(RepeatedStatePublishInterval())
        self._add_sensor(SanityCheckFailuresIncrement())

        if active_config.cloud.enabled:
            self._add_sensor(CloudLogLevel())
        if active_config.diagnostics.enabled:
            self._add_sensor(DiagnosticsLogLevel())
        if active_config.influxdb.enabled:
            self._add_sensor(InfluxDBLogLevel())
        if active_config.pvoutput.enabled:
            self._add_sensor(PVOutputLogLevel())
            self._add_sensor(PVOutputUploadLogLevel())
            self._add_sensor(PVOutputCalcDebugLogging())
            self._add_sensor(PVOutputUpdateDebugLogging())

        if not active_config.runtime_config_enabled:
            for sensor in self.sensors.values():
                sensor.publishable = False

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """Remove retained settings discovery whenever MQTT publishing is disabled."""
        return super().publish_discovery(mqtt_client, clean=clean or not active_config.runtime_config_enabled)

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: bytes | str, qos: int = 2) -> None:
        """Allow retained availability removal without advertising disabled settings."""
        if active_config.runtime_config_enabled or ha_state == b"":
            super().publish_availability(mqtt_client, ha_state, qos)

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: "MqttHandler") -> None:
        """Subscribe to MQTT settings commands only when publishing is enabled."""
        if active_config.runtime_config_enabled and not active_config.clean:
            super().subscribe(mqtt_client, mqtt_handler)

    def schedule(self, transport: Any, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Keep diagnostics controls available without polling or republishing to MQTT."""
        if not active_config.runtime_config_enabled or active_config.clean:
            return []
        return super().schedule(transport, mqtt_client)

    def on_commencement(self, transport: Any, mqtt_client: mqtt.Client) -> None:
        """Mark the service online."""
        logger.info(f"{self.log_identity} Commenced")

    def on_completion(self, transport: Any, mqtt_client: mqtt.Client) -> None:
        """Mark the service offline on shutdown."""
        logger.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")
