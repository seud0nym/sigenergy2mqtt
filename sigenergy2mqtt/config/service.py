"""
MQTT service device that publishes sigenergy2mqtt settings to MQTT.

:class:`SettingsService` wires together the individual :mod:`sensors`
sensor entities and handles the service lifecycle.
"""

import logging

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClient

from .sensors import (
    ApplicationLogLevel,
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

logger = logging.getLogger(__name__)


class SettingsService(Device):
    """Virtual device that publishes sigenergy2mqtt settings to MQTT."""

    def __init__(self):
        unique_id = f"{active_config.home_assistant.unique_id_prefix}_config"
        super().__init__("Sigenergy2MQTT Runtime Configuration", -1, unique_id, "sigenergy2mqtt", "Transient Configuration Settings", ProtocolVersion.N_A)

        self._add_sensor(ApplicationLogLevel())
        self._add_sensor(ModbusLogLevel())
        self._add_sensor(MQTTLogLevel())
        self._add_sensor(PersistenceDebugging())

        self._add_sensor(RepeatedStatePublishInterval())
        self._add_sensor(SanityCheckFailuresIncrement())

        if active_config.diagnostics.enabled:
            self._add_sensor(DiagnosticsLogLevel())
        if active_config.influxdb.enabled:
            self._add_sensor(InfluxDBLogLevel())
        if active_config.pvoutput.enabled:
            self._add_sensor(PVOutputLogLevel())
            self._add_sensor(PVOutputUploadLogLevel())
            self._add_sensor(PVOutputCalcDebugLogging())
            self._add_sensor(PVOutputUpdateDebugLogging())

    def on_commencement(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """Mark the service online."""
        logger.info(f"{self.log_identity} Commenced")

    def on_completion(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """Mark the service offline on shutdown."""
        logger.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")
