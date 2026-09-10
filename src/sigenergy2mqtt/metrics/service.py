"""
MQTT service device that publishes sigenergy2mqtt runtime metrics to MQTT.

:class:`MetricsService` wires together the individual :mod:`sensors`
sensor entities and handles the service lifecycle: marking the broker status
topic online/offline and initialising the :class:`~sigenergy2mqtt.metrics.Metrics`
timestamps at actual commencement time.
"""

import logging
from typing import Any

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import ProtocolVersion
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.sensors import metrics

logger = logging.getLogger(__name__)


class MetricsService(Device):
    """
    Virtual device that publishes sigenergy2mqtt runtime metrics to MQTT.

    All sensor entities are registered in ``__init__``.

    The service publishes ``sigenergy2mqtt/status online`` on commencement and
    ``offline`` on completion so that all metrics sensors reflect availability
    correctly via their shared availability topic.
    """

    def __init__(self, protocol_version: ProtocolVersion):
        unique_id = f"{active_config.home_assistant.unique_id_prefix}_metrics"
        super().__init__("Sigenergy2MQTT Metrics", -1, unique_id, "sigenergy2mqtt", "Performance Metrics", ProtocolVersion.N_A)

        self._add_sensor(metrics.InfluxDBWrites())
        self._add_sensor(metrics.InfluxDBWriteErrors())
        self._add_sensor(metrics.InfluxDBWriteMax())
        self._add_sensor(metrics.InfluxDBWriteMean())
        self._add_sensor(metrics.InfluxDBWriteMin())
        self._add_sensor(metrics.InfluxDBQueries())
        self._add_sensor(metrics.InfluxDBQueryErrors())
        self._add_sensor(metrics.InfluxDBRateLimitWaits())
        self._add_sensor(metrics.InfluxDBRetries())
        self._add_sensor(metrics.InfluxDBThroughput())

        self._add_sensor(metrics.ModbusActiveLocks())
        self._add_sensor(metrics.ModbusCacheHits())
        self._add_sensor(metrics.ModbusPhysicalReads())
        self._add_sensor(metrics.ModbusReadsPerSecond())
        self._add_sensor(metrics.ModbusReadErrors())
        self._add_sensor(metrics.ModbusReadMax())
        self._add_sensor(metrics.ModbusReadMean())
        self._add_sensor(metrics.ModbusReadMin())
        self._add_sensor(metrics.ModbusSkippedErrors())
        self._add_sensor(metrics.ModbusWriteErrors())
        self._add_sensor(metrics.ModbusWriteMax())
        self._add_sensor(metrics.ModbusWriteMean())
        self._add_sensor(metrics.ModbusWriteMin())

        self._add_sensor(metrics.MQTTPublishFailures())
        self._add_sensor(metrics.MQTTPhysicalPublishes())

        self._add_sensor(metrics.PVOutputUploads())
        self._add_sensor(metrics.PVOutputUploadErrors())
        self._add_sensor(metrics.PVOutputUploadSkipped())
        self._add_sensor(metrics.PVOutputUploadMax())
        self._add_sensor(metrics.PVOutputUploadMean())
        self._add_sensor(metrics.PVOutputUploadMin())

        self._add_sensor(metrics.StateStoreSaves())
        self._add_sensor(metrics.StateStoreSaveErrors())
        self._add_sensor(metrics.StateStoreSaveMax())
        self._add_sensor(metrics.StateStoreSaveMean())
        self._add_sensor(metrics.StateStoreSaveMin())
        self._add_sensor(metrics.StateStoreLoads())
        self._add_sensor(metrics.StateStoreLoadHitPercentage())
        self._add_sensor(metrics.StateStoreLoadErrors())
        self._add_sensor(metrics.StateStoreDeletes())
        self._add_sensor(metrics.StateStoreDeleteErrors())

        self._add_sensor(metrics.Started())
        self._add_sensor(metrics.ProtocolVersionSensor(protocol_version))
        self._add_sensor(metrics.ProtocolPublished(protocol_version))

        self._add_sensor(metrics.ResetMetrics())

    def on_commencement(self, transport: Any, mqtt_client: mqtt.Client) -> None:
        """Mark the service online."""
        logger.info(f"{self.log_identity} Commenced")
        mqtt_client.publish("sigenergy2mqtt/status", "online", qos=0, retain=True)

    def on_completion(self, transport: Any, mqtt_client: mqtt.Client) -> None:
        """Mark the service offline on shutdown."""
        logger.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")
        mqtt_client.publish("sigenergy2mqtt/status", "offline", qos=0, retain=True)
