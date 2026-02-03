import logging

import paho.mqtt.client as mqtt

import sigenergy2mqtt.metrics.metrics_sensors as sensors
from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.sensors.base import Sensor


class MetricsService(Device):
    def __init__(self, protocol_version: Protocol):
        unique_id = f"{Config.home_assistant.unique_id_prefix}_metrics"
        super().__init__("Sigenergy Metrics", -1, unique_id, "sigenergy2mqtt", "Metrics", protocol_version)

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

        self._add_read_sensor(sensors.Started())
        self._add_read_sensor(sensors.ProtocolVersion(protocol_version))
        self._add_read_sensor(sensors.ProtocolPublished())

        # Conditionally add InfluxDB sensors when InfluxDB is enabled
        if Config.influxdb.enabled:
            self._add_read_sensor(sensors.InfluxDBWrites())
            self._add_read_sensor(sensors.InfluxDBWriteErrors())
            self._add_read_sensor(sensors.InfluxDBWriteMax())
            self._add_read_sensor(sensors.InfluxDBWriteMean())
            self._add_read_sensor(sensors.InfluxDBQueries())
            self._add_read_sensor(sensors.InfluxDBQueryErrors())
            self._add_read_sensor(sensors.InfluxDBRetries())
            self._add_read_sensor(sensors.InfluxDBThroughput())

    async def publish_updates(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, name: str, *sensors: Sensor) -> None:
        logging.info(f"{self.name} Service Commenced")
        mqtt_client.publish("sigenergy2mqtt/status", "online", qos=0, retain=True)
        await super().publish_updates(modbus_client, mqtt_client, name, *sensors)
        mqtt_client.publish("sigenergy2mqtt/status", "offline", qos=0, retain=True)
        logging.info(f"{self.name} Service Completed: Flagged as offline ({self.online=})")
