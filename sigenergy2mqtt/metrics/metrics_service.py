"""
MQTT service device that publishes sigenergy2mqtt runtime metrics to Home Assistant.

:class:`MetricsService` wires together the individual :mod:`metrics_sensors`
sensor entities and handles the service lifecycle: marking the broker status
topic online/offline and initialising the :class:`~sigenergy2mqtt.metrics.Metrics`
timestamps at actual commencement time.
"""

import logging

import paho.mqtt.client as mqtt

import sigenergy2mqtt.metrics.metrics_sensors as sensors
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.metrics import Metrics
from sigenergy2mqtt.modbus import ModbusClient


class MetricsService(Device):
    """
    Virtual device that exposes sigenergy2mqtt runtime metrics as Home Assistant sensors.

    All sensor entities are registered in ``__init__``. InfluxDB sensors are
    only added when InfluxDB is enabled in the active configuration. The
    service publishes ``sigenergy2mqtt/status online`` on commencement and
    ``offline`` on completion so that all metrics sensors reflect availability
    correctly via their shared availability topic.
    """

    def __init__(self, protocol_version: Protocol):
        unique_id = f"{active_config.home_assistant.unique_id_prefix}_metrics"
        super().__init__("Sigenergy Metrics", -1, unique_id, "sigenergy2mqtt", "Metrics", protocol_version)

        self._add_read_sensor(sensors.InfluxDBWrites())
        self._add_read_sensor(sensors.InfluxDBWriteErrors())
        self._add_read_sensor(sensors.InfluxDBWriteMax())
        self._add_read_sensor(sensors.InfluxDBWriteMean())
        self._add_read_sensor(sensors.InfluxDBQueries())
        self._add_read_sensor(sensors.InfluxDBQueryErrors())
        self._add_read_sensor(sensors.InfluxDBRetries())
        self._add_read_sensor(sensors.InfluxDBThroughput())

        self._add_read_sensor(sensors.ModbusActiveLocks())
        self._add_read_sensor(sensors.ModbusCacheHits())
        self._add_read_sensor(sensors.ModbusPhysicalReads())
        self._add_read_sensor(sensors.ModbusReadsPerSecond())
        self._add_read_sensor(sensors.ModbusReadErrors())
        self._add_read_sensor(sensors.ModbusReadMax())
        self._add_read_sensor(sensors.ModbusReadMean())
        self._add_read_sensor(sensors.ModbusReadMin())
        self._add_read_sensor(sensors.ModbusWriteErrors())
        self._add_read_sensor(sensors.ModbusWriteMax())
        self._add_read_sensor(sensors.ModbusWriteMean())
        self._add_read_sensor(sensors.ModbusWriteMin())

        self._add_read_sensor(sensors.MQTTPublishFailures())
        self._add_read_sensor(sensors.MQTTPhysicalPublishes())

        self._add_read_sensor(sensors.Started())
        self._add_read_sensor(sensors.ProtocolVersion(protocol_version))
        self._add_read_sensor(sensors.ProtocolPublished(protocol_version))

        self._add_writeonly_sensor(sensors.ResetMetrics())

    def on_commencement(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """
        Initialise metrics timestamps and mark the service online.

        :meth:`Metrics.commence` is called here rather than at import time so
        that ``_started`` and ``sigenergy2mqtt_started`` reflect the actual
        service start rather than the earlier module-load time.
        """
        Metrics.commence()
        logging.info(f"{self.name} Service Commenced")
        mqtt_client.publish("sigenergy2mqtt/status", "online", qos=0, retain=True)

    def on_completion(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """Mark the service offline on shutdown."""
        logging.info(f"{self.name} Service Completed: Flagged as offline ({self.online=})")
        mqtt_client.publish("sigenergy2mqtt/status", "offline", qos=0, retain=True)
