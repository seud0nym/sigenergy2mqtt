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
from sigenergy2mqtt.config.config import is_docker
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.mqtt import MqttHandler, mqtt_health_registry, mqtt_setup, mqtt_teardown
from sigenergy2mqtt.sensors.base import ReadableSensorMixin

from .monitored_sensor import MonitoredSensor


class MonitorService(Device):
    """Background service that monitors system health.

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
        self._current_status = "unknown"
        # Health publication should remain reasonably frequent and independent
        # of repeated-state payload cadence so Docker HEALTHCHECKs remain timely.
        self._health_publish_interval = active_config.health_check.interval
        self._health_check_failures = 0
        self._started = time.monotonic()

    async def _monitor(self, mqtt_client: mqtt.Client) -> None:
        """Check for overdue topics and log warning/recovery events.

        Args:
            mqtt_client: MQTT client instance.
        """

        logging.info(f"{self.log_identity} Sleeping for 5s before commencing...")
        try:
            task = asyncio.create_task(asyncio.sleep(5))
            self.sleeper_task = task
            await task
        except asyncio.CancelledError:
            logging.debug(f"{self.log_identity} sleep interrupted")
            return
        finally:
            self.sleeper_task = None

        while self.online:
            await self._publish_health(mqtt_client)
            try:
                task = asyncio.create_task(asyncio.sleep(self._health_publish_interval))
                self.sleeper_task = task
                await task
            except asyncio.CancelledError:
                logging.debug(f"{self.log_identity} sleep interrupted")
                break
            finally:
                self.sleeper_task = None

    def _check_modbus(self) -> bool:
        """Checks that all Modbus Client instances are connected"""
        clients = ModbusClientFactory._clients.values()
        if not clients:
            return False
        now = time.monotonic()
        modbus_healthy_connections = 0
        for client in clients:
            health = client.snapshot()
            cid = health.client_id
            if not client.connected:
                logging.warning(f"{self.log_identity} Modbus connection {cid} disconnected ({health.close_count}x total)")
            elif health.last_read_at and (now - health.last_read_at) > self._health_publish_interval:
                logging.warning(f"{self.log_identity} Modbus connection {cid} connected but no reads for {self._health_publish_interval}s")
            else:
                logging.debug(f"{self.log_identity} Modbus connection {cid} healthy (connected {health.connect_count}x)")
                modbus_healthy_connections += 1
        return bool(modbus_healthy_connections == len(clients))

    def _check_mqtt(self, mqtt_client: mqtt.Client) -> bool:
        """Checks that all MQTT client connections are healthy"""
        mqtt_snapshot = mqtt_health_registry.snapshot()
        if not mqtt_snapshot:
            return False
        now = time.monotonic()
        mqtt_healthy_connections = 0
        for cid, health in mqtt_snapshot.items():
            is_monitor = bool(cid.encode("utf-8") == mqtt_client._client_id)
            max = 2 * self._health_publish_interval if is_monitor else self._health_publish_interval
            if not health.connected:
                logging.warning(f"{self.log_identity} MQTT Client ID {cid} disconnected ({health.disconnect_count}x total)")
            elif is_monitor and (self._started + self._health_publish_interval) > now:
                logging.debug(f"{self.log_identity} MQTT Client ID {cid} not checked (nothing published yet)")
                mqtt_healthy_connections += 1
            else:
                ack = bool(health.last_publish_ack_at and (now - health.last_publish_ack_at) <= max)
                msg = bool(health.last_message_at and (now - health.last_message_at) <= max)
                if not ack and not msg:
                    if not ack:
                        logging.warning(f"{self.log_identity} MQTT Client ID {cid} connected but no publish acknowledgement received for {max}s")
                    if not msg:
                        logging.warning(f"{self.log_identity} MQTT Client ID {cid} connected but no messages sent for {max}s")
                else:
                    logging.debug(f"{self.log_identity} MQTT Client ID {cid} healthy (connected {health.connect_count}x)")
                    mqtt_healthy_connections += 1
        return bool(mqtt_healthy_connections == len(mqtt_snapshot))

    async def _check_topic_health(self) -> int:
        """Checks for overdue topics (sensors that haven't been seen in their scan_interval)"""
        if time.monotonic() < (self._started + self._health_publish_interval):
            logging.debug(
                f"{self.log_identity} Topic health check not due yet (only started {time.monotonic() - self._started:0.2f}s ago) - next check in {self._health_publish_interval - (time.monotonic() - self._started):0.2f}s"
            )
            return 0
        async with self._lock:
            overdue: dict[str, MonitoredSensor] = {t: s for t, s in self._topics.items() if self._monitor_topic_updates and s.is_overdue}
        if any(overdue):
            for topic, sensor in overdue.items():
                sensor.notified = True
                logging.warning(f"{self.log_identity} '{sensor.name}' has not been seen for {sensor.overdue}s (scan_interval={sensor.scan_interval}s {topic=})")
        return len(overdue)

    async def _publish_health(self, mqtt_client: mqtt.Client) -> None:
        is_enabled = active_config.health_check.enabled or is_docker()
        if not is_enabled:
            if self._monitor_topic_updates:
                await self._check_topic_health()
            return

        is_docker_env = is_docker()
        try:
            async with asyncio.timeout(active_config.health_check.timeout):
                modbus_connected = self._check_modbus()
                mqtt_connected = self._check_mqtt(mqtt_client)
                overdue_count = await self._check_topic_health()
        except TimeoutError:
            logging.warning(f"{self.log_identity} Health check timed out after {active_config.health_check.timeout}s")
            modbus_connected = False
            mqtt_connected = False
            overdue_count = 0

        if overdue_count == 0 and mqtt_connected and modbus_connected:
            status = "healthy"
            logging.log(logging.INFO if self._current_status != status else logging.DEBUG, f"{self.log_identity} Status is HEALTHY (topic_{overdue_count=} {mqtt_connected=} {modbus_connected=})")
        else:
            status = "degraded"
            logging.warning(f"{self.log_identity} Status is DEGRADED (topic_{overdue_count=} {mqtt_connected=} {modbus_connected=})")

        payload = {
            "status": status,
            "mqtt_connected": mqtt_connected,
            "modbus_connected": modbus_connected,
            "overdue_topics": overdue_count,
            "monitored_topics": len(self._topics),
            "timestamp": int(time.time()),
        }
        try:
            self._health_file.write_text(json.dumps(payload), encoding="utf-8")
            logging.debug(f"{self.log_identity} Published health payload to {self._health_file}")
            if mqtt_client:
                mqtt_client.publish(self._health_state_topic, status, qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, json.dumps(payload), qos=1, retain=True)
                logging.debug(f"{self.log_identity} Published health payload to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} {self._health_attributes_topic}")
        except Exception as ex:
            logging.warning(f"{self.log_identity} Failed to publish health payload: {ex}")
        self._current_status = status

        if not is_docker_env:
            if status == "healthy":
                self._health_check_failures = 0
            else:
                if time.monotonic() - self._started > active_config.health_check.start_period:
                    self._health_check_failures += 1
                    logging.warning(f"{self.log_identity} Health check failure count: {self._health_check_failures}/{active_config.health_check.retries}")
                    if self._health_check_failures >= active_config.health_check.retries:
                        from sigenergy2mqtt.main.restart import restart_controller  # lazy import to avoid circular dependency
                        restart_controller.request("Health check failed repeatedly")

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

    @classmethod
    async def clean(cls) -> None:
        """Clean up the monitor service."""
        # Remove any health file matching the pattern in /tmp recursively
        tmp_dir = Path("/tmp")
        for health_file in tmp_dir.rglob("*health.json*"):
            try:
                logging.debug(f"MonitorService: Removing health file {health_file}")
                health_file.unlink(missing_ok=True)
                logging.info(f"MonitorService: Health file {health_file} removed successfully")
            except OSError as exc:
                logging.error(f"MonitorService: Failed to remove health file {health_file}: {exc}")
        # Proceed with MQTT topic cleanup as before
        service = cls([])
        try:
            logging.debug(f"MonitorService: Removing health file {service._health_file}")
            service._health_file.unlink(missing_ok=True)
            logging.info(f"MonitorService: Health file {service._health_file} removed successfully")
        except OSError as exc:
            logging.error(f"MonitorService: Failed to remove health file {service._health_file}: {exc}")
        try:
            client_id = f"{active_config.mqtt.client_id_prefix}_Monitor"
            client, handler = await mqtt_setup(client_id, None, asyncio.get_running_loop())
            try:
                for topic in (service._health_state_topic, service._health_attributes_topic):
                    logging.debug(f"MonitorService: Removing topic {topic}")
                    info = client.publish(topic, b"", qos=2, retain=True)
                    if info.rc == mqtt.MQTT_ERR_SUCCESS:
                        info.wait_for_publish(timeout=5.0)
                        logging.info(f"MonitorService: Topic {topic} removed successfully")
                    else:
                        logging.error(f"MonitorService: Failed to clean topic {topic}")
            except Exception as exc:
                logging.warning(f"MonitorService: Failed to clean topics: {exc}")
            finally:
                await mqtt_teardown(client, handler)
        except Exception as exc:
            logging.warning(f"MonitorService: MQTT connection failed ({exc}) — cleaned disk only")
            return

    def on_completion(self, modbus_client: Any | None, mqtt_client: mqtt.Client) -> None:
        """Log when the monitor service has stopped and clear stale health messages.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
        """

        logging.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")
        try:
            if mqtt_client:
                mqtt_client.publish(self._health_state_topic, b"", qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, b"", qos=1, retain=True)
                logging.debug(f"{self.log_identity} Cleared health topics on completion")
        except Exception as ex:
            logging.warning(f"{self.log_identity} Failed to clear health payload: {ex}")

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
            modbus_client: Modbus client instance (unused).
            mqtt_client: MQTT client instance.

        Returns:
            A list with a single monitor coroutine, or an empty list if performing no functions.
        """
        is_enabled = active_config.health_check.enabled or is_docker()
        if not is_enabled and not self._monitor_topic_updates:
            return []
        return [self._monitor(mqtt_client)]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Subscribe to all publishable readable sensor state topics and clear health checks if disabled.

        Args:
            mqtt_client: MQTT client used for subscriptions.
            mqtt_handler: Helper used to register topic callbacks.
        """
        is_enabled = active_config.health_check.enabled or is_docker()
        if not is_enabled:
            logging.info(f"{self.log_identity} Health check disabled, clearing retained health messages")
            try:
                mqtt_client.publish(self._health_state_topic, b"", qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, b"", qos=1, retain=True)
            except Exception as ex:
                logging.warning(f"{self.log_identity} Failed to clear health payload on subscribe: {ex}")

        if not self._monitor_topic_updates:
            logging.debug(f"{self.log_identity} Topic-overdue monitoring disabled (log_level={logging.getLevelName(active_config.log_level)} repeated_state_publish_interval={active_config.repeated_state_publish_interval})")
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
