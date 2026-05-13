"""Monitor service for tracking expected sensor MQTT updates and service health."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Awaitable

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.base import ReadableSensorMixin

from .monitored_sensor import MonitoredSensor


class MonitorService(Device):
    """Background service that warns when expected sensor topics go silent.

    Args:
        devices: Devices whose readable/publishable sensors should be monitored.
    """

    def __init__(self, devices: list[Device]):
        """Initialize the monitor service and internal topic registry.

        Args:
            devices: Devices that expose sensors to subscribe to.
        """

        super().__init__("Sigenergy Monitor", -1, f"{active_config.home_assistant.unique_id_prefix}_monitor", "sigenergy2mqtt", "Monitor", Protocol.N_A)
        self._devices: list[Device] = devices
        self._lock = asyncio.Lock()
        self._topics: dict[str, MonitoredSensor] = {}
        self._health_state_topic = "sigenergy2mqtt/health/state"
        self._health_attributes_topic = "sigenergy2mqtt/health/attributes"
        self._health_file = Path("/tmp/sigenergy2mqtt-health.json")
        self._monitor_topic_updates = active_config.log_level == logging.DEBUG and active_config.repeated_state_publish_interval >= 0
        # Health publication should remain reasonably frequent and independent
        # of repeated-state payload cadence so Docker HEALTHCHECKs remain timely.
        self._health_publish_interval = 30

    async def _monitor(self, modbus_client: Any, mqtt_client: Any, *sensors: Any):
        """Check for overdue topics and log warning/recovery events.

        Args:
            modbus_client: Unused; part of the shared ``Device`` scheduler signature.
            mqtt_client: Unused; part of the shared ``Device`` scheduler signature.
            *sensors: Unused; optional positional values from the scheduler.
        """

        logging.info(f"{self.log_identity} Sleeping for 30s before commencing...")
        try:
            task = asyncio.create_task(asyncio.sleep(30))
            self.sleeper_task = task
            await task
        except asyncio.CancelledError:
            logging.debug(f"{self.log_identity} sleep interrupted")
            return
        finally:
            self.sleeper_task = None

        while self.online:
            async with self._lock:
                overdue: dict[str, MonitoredSensor] = {t: s for t, s in self._topics.items() if self._monitor_topic_updates and s.is_overdue}
            if any(overdue):
                for topic, sensor in overdue.items():
                    sensor.notified = True
                    logging.warning(f"{self.log_identity} '{sensor.name}' has not been seen for {sensor.overdue}s (scan_interval={sensor.scan_interval}s {topic=})")
            await self._publish_health(mqtt_client, len(overdue))
            try:
                task = asyncio.create_task(asyncio.sleep(self._health_publish_interval))
                self.sleeper_task = task
                await task
            except asyncio.CancelledError:
                logging.debug(f"{self.log_identity} sleep interrupted")
                break
            finally:
                self.sleeper_task = None

    async def _publish_health(self, mqtt_client: mqtt.Client, overdue_count: int) -> None:
        modbus_connected = all(client.connected for client in ModbusClientFactory._clients.values())
        mqtt_connected = bool(mqtt_client and mqtt_client.is_connected())
        status = "healthy" if overdue_count == 0 and mqtt_connected and modbus_connected else "degraded"
        now = int(time.time())
        payload = {
            "status": status,
            "mqtt_connected": mqtt_connected,
            "modbus_connected": modbus_connected,
            "overdue_topics": overdue_count,
            "monitored_topics": len(self._topics),
            "timestamp": now,
        }
        try:
            self._health_file.write_text(json.dumps(payload), encoding="utf-8")
            if mqtt_client:
                mqtt_client.publish(self._health_state_topic, status, qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, json.dumps(payload), qos=1, retain=True)
        except Exception as ex:
            logging.debug(f"{self.log_identity} unable to publish health payload: {ex}")

    async def on_ha_state_change(self, modbus_client: Any | None, mqtt_client: mqtt.Client, ha_state: str, source: str, mqtt_handler: MqttHandler) -> bool:
        """Handle Home Assistant state updates.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
            ha_state: Home Assistant state payload.
            source: MQTT topic source for the update.
            mqtt_handler: MQTT handler coordinating subscriptions and dispatch.

        Returns:
            Always ``True`` for this service.
        """

        return True

    async def on_topic_update(self, modbus_client: Any | None, mqtt_client: mqtt.Client, value: str, source: str, mqtt_handler: MqttHandler) -> bool:
        """Update the ``last_seen`` timestamp for a monitored topic.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
            value: Received MQTT payload.
            source: Topic that emitted the payload.
            mqtt_handler: MQTT handler coordinating subscriptions and dispatch.

        Returns:
            ``True`` if the topic is known and was updated; otherwise ``False``.
        """

        if source in self._topics:
            sensor = self._topics[source]
            if sensor.notified:
                logging.info(f"{self.log_identity} '{sensor.name}' seen after {sensor.overdue}s (scan_interval={sensor.scan_interval}s {source=})")
            async with self._lock:
                sensor.last_seen = time.time()
                sensor.notified = False
            return True
        else:
            logging.warning(f"{self.log_identity} updated from  topic {source}, but topic is not registered !!!")
        return False

    def on_commencement(self, modbus_client: Any | None, mqtt_client: mqtt.Client) -> None:
        """Log when the monitor service has started.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
        """

        logging.info(f"{self.log_identity} Service Commenced")

    def on_completion(self, modbus_client: Any | None, mqtt_client: mqtt.Client) -> None:
        """Log when the monitor service has stopped.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
        """

        logging.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: bytes | str, qos: int = 2) -> None:
        """No-op availability publisher for the monitor service.

        Args:
            mqtt_client: MQTT client instance.
            ha_state: Optional Home Assistant state.
            qos: Requested MQTT quality-of-service level.
        """

        pass

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """No-op discovery publisher for the monitor service.

        Args:
            mqtt_client: MQTT client instance.
            clean: Whether discovery messages should be removed.

        Returns:
            ``None`` because discovery is not published for this service.
        """

        pass

    def schedule(self, modbus_client: Any, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Return the monitor coroutine(s) to schedule for this service.

        Args:
            modbus_client: Modbus client instance.
            mqtt_client: MQTT client instance.

        Returns:
            A list with a single monitor coroutine, unless repeated-state
            publishing is disabled for unchanged values.
        """

        return [self._monitor(modbus_client, mqtt_client, [])]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Subscribe to all publishable readable sensor state topics.

        Args:
            mqtt_client: MQTT client used for subscriptions.
            mqtt_handler: Helper used to register topic callbacks.
        """

        if not self._monitor_topic_updates:
            logging.info(f"{self.log_identity} Topic-overdue monitoring disabled (repeated_state_publish_interval={active_config.repeated_state_publish_interval}); publishing connectivity health only")
            return

        for d in self._devices:
            device = d.log_identity
            sensors = 0
            for s in [sensor for sensor in d.get_all_sensors().values() if isinstance(sensor, ReadableSensorMixin) and sensor.publishable]:
                sensor = s.log_identity
                scan_interval = s.scan_interval
                topic = s.state_topic
                if topic in self._topics:
                    logging.error(f"{self.log_identity} Sensor '{device} - {sensor}' has the same topic as '{self._topics[topic].name}' ({topic=}) ????")
                else:
                    self._topics[topic] = MonitoredSensor(device, sensor, scan_interval)
                    sensors += 1
                    mqtt_handler.register(mqtt_client, topic, handler=self.on_topic_update)
            if sensors > 0:
                logging.info(f"{self.log_identity} Monitoring {sensors} topic{'s' if sensors > 1 else ''} for {d.log_identity}")
        logging.info(f"{self.log_identity} Monitoring {len(self._topics)} topics")
