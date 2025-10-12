from .metrics import Metrics
from sigenergy2mqtt.config import Config, SIGENERGY_MODBUS_PROTOCOL, SIGENERGY_MODBUS_PROTOCOL_PUBLISHED
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus.lock_factory import ModbusLockFactory
from sigenergy2mqtt.mqtt import MqttClient
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import json
import logging
import time


class MetricsService(Device):
    _unique_id: str = f"{Config.home_assistant.unique_id_prefix}_metrics"

    _discovery = {
        "dev": {
            "name": "Sigenergy Metrics",
            "ids": [_unique_id],
            "mf": "seud0nym",
            "mdl": "sigenergy2mqtt",
            "mdl_id": Config.origin["sw"],
            "cu": "https://github.com/seud0nym/sigenergy2mqtt",
        },
        "o": Config.origin,
        "cmps": {
            "sigenergy2mqtt_modbus_reads_sec": {
                "platform": "sensor",
                "name": "Modbus Reads/second",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_reads_sec",
                "object_id": "sigenergy2mqtt_modbus_reads_sec",
                "unique_id": "sigenergy2mqtt_modbus_reads_sec",
                "icon": "mdi:timer-play-outline",
                "state_topic": "sigenergy2mqtt/metrics/modbus_reads_sec",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_read_errors": {
                "platform": "sensor",
                "name": "Modbus Read Errors",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_read_errors",
                "object_id": "sigenergy2mqtt_modbus_read_errors",
                "unique_id": "sigenergy2mqtt_modbus_read_errors",
                "icon": "mdi:counter",
                "state_topic": "sigenergy2mqtt/metrics/modbus_read_errors",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_read_max": {
                "platform": "sensor",
                "name": "Modbus Read Max",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_read_max",
                "object_id": "sigenergy2mqtt_modbus_read_max",
                "unique_id": "sigenergy2mqtt_modbus_read_max",
                "icon": "mdi:timer-plus-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_read_max",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_read_mean": {
                "platform": "sensor",
                "name": "Modbus Read Mean",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_read_mean",
                "object_id": "sigenergy2mqtt_modbus_read_mean",
                "unique_id": "sigenergy2mqtt_modbus_read_mean",
                "icon": "mdi:timer-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_read_mean",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_read_min": {
                "platform": "sensor",
                "name": "Modbus Read Min",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_read_min",
                "object_id": "sigenergy2mqtt_modbus_read_min",
                "unique_id": "sigenergy2mqtt_modbus_read_min",
                "icon": "mdi:timer-minus-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_read_min",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_write_errors": {
                "platform": "sensor",
                "name": "Modbus Write Errors",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_write_errors",
                "object_id": "sigenergy2mqtt_modbus_write_errors",
                "unique_id": "sigenergy2mqtt_modbus_write_errors",
                "icon": "mdi:counter",
                "state_topic": "sigenergy2mqtt/metrics/modbus_write_errors",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_write_max": {
                "platform": "sensor",
                "name": "Modbus Write Max",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_write_max",
                "object_id": "sigenergy2mqtt_modbus_write_max",
                "unique_id": "sigenergy2mqtt_modbus_write_max",
                "icon": "mdi:timer-plus-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_write_max",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_write_mean": {
                "platform": "sensor",
                "name": "Modbus Write Mean",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_write_mean",
                "object_id": "sigenergy2mqtt_modbus_write_mean",
                "unique_id": "sigenergy2mqtt_modbus_write_mean",
                "icon": "mdi:timer-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_write_mean",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_write_min": {
                "platform": "sensor",
                "name": "Modbus Write Min",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_write_min",
                "object_id": "sigenergy2mqtt_modbus_write_min",
                "unique_id": "sigenergy2mqtt_modbus_write_min",
                "icon": "mdi:timer-minus-outline",
                "device_class": "duration",
                "unit_of_measurement": "ms",
                "state_topic": "sigenergy2mqtt/metrics/modbus_write_min",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_locks": {
                "platform": "sensor",
                "name": "Modbus Active Locks",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_locks",
                "object_id": "sigenergy2mqtt_modbus_locks",
                "unique_id": "sigenergy2mqtt_modbus_locks",
                "icon": "mdi:eye-lock",
                "state_topic": "sigenergy2mqtt/metrics/modbus_locks",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_started": {
                "platform": "sensor",
                "name": "Started",
                "default_entity_id": "sensor.sigenergy2mqtt_started",
                "object_id": "sigenergy2mqtt_started",
                "unique_id": "sigenergy2mqtt_started",
                "device_class": "timestamp",
                "entity_category": "diagnostic",
                "icon": "mdi:calendar-clock",
                "state_topic": "sigenergy2mqtt/metrics/started",
                "availability_topic": "sigenergy2mqtt/status",
            },
            "sigenergy2mqtt_modbus_protocol": {
                "platform": "sensor",
                "name": "Protocol Version",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_protocol",
                "object_id": "sigenergy2mqtt_modbus_protocol",
                "unique_id": "sigenergy2mqtt_modbus_protocol",
                "entity_category": "diagnostic",
                "icon": "mdi:book-information-variant",
                "state_topic": "sigenergy2mqtt/metrics/modbus_protocol",
            },
            "sigenergy2mqtt_modbus_protocol_published": {
                "platform": "sensor",
                "name": "Protocol Published",
                "default_entity_id": "sensor.sigenergy2mqtt_modbus_protocol_published",
                "object_id": "sigenergy2mqtt_modbus_protocol_published",
                "unique_id": "sigenergy2mqtt_modbus_protocol_published",
                "entity_category": "diagnostic",
                "icon": "mdi:book-clock",
                "state_topic": "sigenergy2mqtt/metrics/modbus_protocol_published",
            },
        },
    }

    def __init__(self):
        super().__init__("Sigenergy Metrics", -1, MetricsService._unique_id, "sigenergy2mqtt", "Metrics")

    def publish_availability(self, mqtt: MqttClient, ha_state: str, qos: int = 2) -> None:
        pass

    def publish_discovery(self, mqtt: MqttClient, clean=False) -> Any:
        topic = f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
        if clean or not Config.metrics_enabled:
            logging.debug(f"{self.name} - Publishing empty discovery ({Config.metrics_enabled=} {clean=})")
            info = mqtt.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        if Config.metrics_enabled:
            logging.debug(f"{self.name} - Publishing discovery")
            discovery_json = json.dumps(MetricsService._discovery, allow_nan=False, indent=2, sort_keys=False)
            info = mqtt.publish(topic, discovery_json, qos=2, retain=True)
        return info

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        def get_value(object_id: str) -> Any:
            match object_id:
                case "sigenergy2mqtt_modbus_locks":
                    value = f"{ModbusLockFactory.get_waiter_count()}"
                case "sigenergy2mqtt_modbus_reads_sec":
                    value = Metrics.sigenergy2mqtt_modbus_reads / (time.monotonic() - Metrics._started)
                case "sigenergy2mqtt_modbus_protocol":
                    value = SIGENERGY_MODBUS_PROTOCOL
                case "sigenergy2mqtt_modbus_protocol_published":
                    value = SIGENERGY_MODBUS_PROTOCOL_PUBLISHED
                case _:
                    value = getattr(Metrics, object_id, None)
                    if value == float("inf"):
                        value = 0.0
            if value is None:
                logging.warning(f"{self.name} - No value found for {object_id}")
                return None
            return f"{value:.2f}" if isinstance(value, float) else str(value)

        async def publish_updates(modbus: Any, mqtt: MqttClient) -> None:
            logging.info(f"{self.name} Service Commenced")
            while self.online:
                mqtt.publish("sigenergy2mqtt/status", "online", qos=0, retain=True)
                try:
                    for object_id, discovery in MetricsService._discovery["cmps"].items():
                        value = get_value(object_id)
                        if value is not None:
                            mqtt.publish(discovery["state_topic"], f"{value:.2f}" if isinstance(value, float) else str(value), qos=0, retain=False)
                    await asyncio.sleep(1.0)
                except asyncio.CancelledError:
                    logging.info(f"{self.name} - Sleep interrupted")
                except asyncio.TimeoutError:
                    logging.warning(f"{self.name} - Failed to acquire lock within timeout")
                except Exception as e:
                    logging.error(f"{self.name} - Error during publish: {repr(e)}")
            mqtt.publish("sigenergy2mqtt/status", "offline", qos=0, retain=True)
            logging.info(f"{self.name} Service Completed: Flagged as offline ({self.online=})")
            return

        if Config.metrics_enabled:
            logging.debug(f"{self.name} - Scheduling updates")
            tasks = [publish_updates(modbus, mqtt)]
        else:
            logging.debug(f"{self.name} - Disabled, no tasks scheduled")
            tasks = []
        return tasks
