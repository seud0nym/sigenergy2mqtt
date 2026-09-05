"""Monitor service for tracking expected sensor MQTT updates and service health."""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable
from dataclasses import replace
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException

from sigenergy2mqtt.common import PERCENTAGE, ProtocolVersion, UnitOfTemperature, service_health_registry
from sigenergy2mqtt.config import active_config, is_docker
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.diagnostics import diagnostics_registry
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.mqtt import MqttHandler, mqtt_health_registry, mqtt_setup, mqtt_teardown
from sigenergy2mqtt.sensors.base import DerivedSensor, ReadableSensorMixin

from .dashboard import extract_dashboard_state
from .sensor import MonitoredSensor

logger = logging.getLogger(__name__)


class MonitorService(Device):
    """Background service that monitors system health."""

    def __init__(self, devices: list[Device]):
        """Initialize the monitor service and internal topic registry.

        Args:
            devices: Devices that expose sensors to subscribe to.
        """
        logger.setLevel(active_config.diagnostics.log_level)

        super().__init__("Sigenergy Monitor", -1, f"{active_config.home_assistant.unique_id_prefix}_monitor", "sigenergy2mqtt", "Monitor", ProtocolVersion.N_A)
        self._devices: list[Device] = devices
        self._lock = asyncio.Lock()
        self._topics: dict[str, MonitoredSensor] = {}
        self._topics_snapshot: dict[str, Any] = {"timestamp": time.monotonic(), "snapshot": None}
        self._health_state_topic = "sigenergy2mqtt/health/state"
        self._health_attributes_topic = "sigenergy2mqtt/health/attributes"
        self._health_payload: dict[str, Any] = {"status": "unknown"}
        self._monitor_topic_updates = active_config.monitor_topic_updates
        self._current_status = "unknown"
        self._health_contributors: dict[str, bool] = {}
        # Health publication should remain reasonably frequent and independent
        # of repeated-state payload cadence so Docker HEALTHCHECKs remain timely.
        self._health_publish_interval = active_config.health_check.interval
        self._health_check_failures = 0
        self._started = time.monotonic()
        self._last_published_at: float = 0.0  # 0 = never published; guaranteed stale until first _publish_health call
        self._no_alarm_i18n = _t("AlarmSensor.no_alarm")  # Can't use constant because it gets initialised before i18n is available

        diagnostics_registry.register("monitor", self._collect_diagnostics)

    def _check_modbus(self) -> tuple[bool, int]:
        """Checks that all Modbus Client instances are connected"""
        clients = ModbusClientFactory._clients.values()
        if not clients:
            return False, 0
        now = time.monotonic()
        modbus_healthy_connections = 0
        for client in clients:
            health = client.snapshot()
            cid = health.client_id
            if not client.connected:
                logger.warning(f"{self.log_identity} Modbus connection {cid} disconnected ({health.close_count}x total)")
            elif health.last_read_at and (now - health.last_read_at) > self._health_publish_interval:
                logger.warning(f"{self.log_identity} Modbus connection {cid} connected but no reads for {self._health_publish_interval}s")
            else:
                logger.debug(f"{self.log_identity} Modbus connection {cid} healthy (connected {health.connect_count}x)")
                modbus_healthy_connections += 1
        return bool(modbus_healthy_connections == len(clients)), len(clients)

    def _check_mqtt(self, mqtt_client: mqtt.Client) -> tuple[bool, int]:
        """Checks that all MQTT client connections are healthy"""
        mqtt_snapshot = mqtt_health_registry.snapshot()
        if not mqtt_snapshot:
            return False, 0
        now = time.monotonic()
        mqtt_healthy_connections = 0
        for cid, health in mqtt_snapshot.items():
            is_monitor = bool(cid.encode("utf-8") == mqtt_client._client_id)
            max = 2 * self._health_publish_interval if is_monitor else self._health_publish_interval
            if not health.connected:
                logger.warning(f"{self.log_identity} MQTT Client ID {cid} disconnected ({health.disconnect_count}x total)")
            elif is_monitor and (self._started + self._health_publish_interval) > now:
                logger.debug(f"{self.log_identity} MQTT Client ID {cid} not checked (first interval)")
                mqtt_healthy_connections += 1
            elif health.last_message_at and health.last_publish_ack_at and health.last_publish_ack_at < health.last_message_at and (now - health.last_message_at) > max:
                logger.warning(f"{self.log_identity} MQTT Client ID {cid} connected but no publish acknowledgement received for {(now - health.last_message_at):0.2f}s")
            else:
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    if health.last_message_at and health.last_publish_ack_at:
                        logger.debug(
                            f"{self.log_identity} MQTT Client ID {cid} healthy (connected {health.connect_count}x, last message {now - health.last_message_at:0.2f}s ago, last ack {now - health.last_publish_ack_at:0.2f}s ago)"
                        )
                    else:
                        logger.debug(f"{self.log_identity} MQTT Client ID {cid} healthy (connected {health.connect_count}x)")
                mqtt_healthy_connections += 1
        return bool(mqtt_healthy_connections == len(mqtt_snapshot)), len(mqtt_snapshot)

    def _check_service_health(self) -> tuple[bool, dict[str, bool]]:
        """Evaluate optional service health contributors."""
        contributors: dict[str, bool] = {}
        healthy = True

        if active_config.pvoutput.enabled and active_config.pvoutput.health_monitoring:
            pvoutput_healthy = service_health_registry.get_health("pvoutput", True)
            contributors["pvoutput"] = bool(pvoutput_healthy)
            healthy = healthy and pvoutput_healthy

        if active_config.influxdb.enabled and active_config.influxdb.health_monitoring:
            keys_to_check = []
            if active_config.modbus:
                keys_to_check.extend(f"influxdb_{i}" for i in range(len(active_config.modbus)))
            snapshot = service_health_registry.snapshot()
            if "influxdb" in snapshot or not keys_to_check:
                keys_to_check.append("influxdb")

            for key in keys_to_check:
                plant_healthy = service_health_registry.get_health(key, True)
                contributors[key] = bool(plant_healthy)
                healthy = healthy and plant_healthy

        self._health_contributors = contributors
        return healthy, contributors

    async def _check_topic_health(self) -> int:
        """Checks for overdue topics (sensors that haven't been seen in their scan_interval)"""
        if time.monotonic() < (self._started + self._health_publish_interval):
            logger.debug(
                f"{self.log_identity} Topic health check not due yet (only started {time.monotonic() - self._started:0.2f}s ago) - next check in {self._health_publish_interval - (time.monotonic() - self._started):0.2f}s"
            )
            return 0
        async with self._lock:
            overdue: dict[str, MonitoredSensor] = {t: s for t, s in self._topics.items() if self._monitor_topic_updates and s.is_overdue}
        if any(overdue):
            for topic, sensor in overdue.items():
                sensor.notified = True
                logger.warning(f"{self.log_identity} '{sensor.name}' has not been seen for {sensor.overdue}s (scan_interval={sensor.scan_interval}s {topic=})")
        return len(overdue)

    async def _collect_dashboard_states(self) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest selected plant states."""
        if self._topics_snapshot["snapshot"] is None or self._topics_snapshot["timestamp"] + active_config.diagnostics.refresh_interval < time.monotonic():
            async with self._lock:
                snapshot = {topic: replace(sensor) for topic, sensor in self._topics.items()}
            self._topics_snapshot = {"timestamp": time.monotonic(), "snapshot": snapshot}
        else:
            snapshot = self._topics_snapshot["snapshot"]

        state = extract_dashboard_state(snapshot)
        logger.debug(f"{self.log_identity} Dashboard state snapshot: {state}")
        return state

    async def _collect_diagnostics(self) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest health payload.

        Registered with the ``diagnostics_registry`` so the web dashboard,
        WebSocket feed, and JSON export all surface this without the web
        layer needing any knowledge of MQTT/Modbus/health-check internals.

        If the monitor loop has stopped or hung — detected by ``_last_published_at``
        being older than two ``_health_publish_interval`` periods — the cached
        payload's status is overridden with ``"unknown"`` so a dead monitor is
        not falsely reported as healthy.
        """
        payload = dict(self._health_payload)
        age = time.monotonic() - self._last_published_at
        if age > 2 * self._health_publish_interval:
            payload["status"] = "unknown"
            payload["Stale"] = True
        payload["Monitored Topics"] = len(self._topics)
        payload["config"] = {
            "health_check_interval_secs": active_config.health_check.interval,
            "sigenergy2mqtt_version": active_config.version,
        }
        return payload

    async def _collect_plant_states(self) -> dict[str, Any]:
        """Diagnostics provider callback: exposes the latest selected plant states."""
        if self._topics_snapshot["snapshot"] is None or self._topics_snapshot["timestamp"] + active_config.diagnostics.refresh_interval < time.monotonic():
            async with self._lock:
                snapshot = {topic: replace(sensor) for topic, sensor in self._topics.items()}
            self._topics_snapshot = {"timestamp": time.monotonic(), "snapshot": snapshot}
        else:
            snapshot = self._topics_snapshot["snapshot"]

        states: dict[str, Any] = {}

        def _format_value(sensor: MonitoredSensor) -> str:
            if sensor.unit == "kWh" and isinstance(sensor.last_state, (int, float)) and sensor.last_state > 1000:
                return f"{sensor.last_state / 1000:.2f} MWh"
            if sensor.last_state is None:
                return "unknown"
            if sensor.unit is None:
                return str(sensor.last_state)
            if sensor.unit is PERCENTAGE or sensor.unit == UnitOfTemperature.CELSIUS or sensor.unit == UnitOfTemperature.FAHRENHEIT:
                return f"{sensor.last_state}{sensor.unit}"
            return f"{sensor.last_state} {sensor.unit}"

        def _updates_states(classname: str, description: str | None = None) -> None:
            values = {s.name: (s.description if description is None else description, _format_value(s)) for s in snapshot.values() if classname in s.sensor_name}
            if len(values) == 1:
                key, state = next(iter(values.values()))
                states[key] = state
            elif len(values) > 1:
                for name, value in values.items():
                    plant = name.split("plant=")[-1].rstrip("]")
                    states[f"{value[0]}_{plant}"] = value[1]

        _updates_states("PlantRunningState")
        states[_t("InverterAlarm5.name")] = "-" if len(snapshot) == 0 else "No" if all(s.last_state == self._no_alarm_i18n for s in snapshot.values() if "Alarm" in s.sensor_name) else "** YES **"
        _updates_states("GridStatus")
        _updates_states("GridActivity")
        _updates_states("PlantPVPower")
        _updates_states("ThirdPartyPVPower")
        _updates_states("TotalLifetimePVEnergy")
        _updates_states("TotalLoadConsumption")
        _updates_states("BatteryStatus")
        _updates_states("PlantBatterySoC")
        _updates_states("PlantBatterySoH")
        _updates_states("ESSTotalChargedEnergy")
        _updates_states("ESSTotalDischargedEnergy")
        _updates_states("ESSAverageCellTemperature")
        _updates_states("InverterTemperature", "Inverter Temperature")
        _updates_states("InverterFirmwareVersion", "Firmware")

        return states

    async def _monitor(self, mqtt_client: mqtt.Client) -> None:
        """Check for overdue topics and log warning/recovery events.

        Args:
            mqtt_client: MQTT client instance.
        """

        logger.info(f"{self.log_identity} Sleeping for 5s before commencing...")
        try:
            task = asyncio.create_task(asyncio.sleep(5))
            self.sleeper_task = task
            await task
        except asyncio.CancelledError:
            logger.debug(f"{self.log_identity} sleep interrupted")
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
                logger.debug(f"{self.log_identity} sleep interrupted")
                break
            finally:
                self.sleeper_task = None

    async def _publish_health(self, mqtt_client: mqtt.Client) -> None:
        """Publishes the health status to the JSON file and MQTT.

        Args:
            mqtt_client: MQTT client instance.
        """
        is_enabled = active_config.health_check.enabled or is_docker()  # is_docker() is cached so safe to call repeatedly
        if not is_enabled:
            self._health_payload = {"status": "disabled"}
            if self._monitor_topic_updates:
                await self._check_topic_health()
            return

        # Sync checks: fast lock-protected snapshots, not interruptible by asyncio.timeout
        # but cannot stall meaningfully, so no executor needed.
        modbus_connected, modbus_connections = self._check_modbus()
        mqtt_connected, mqtt_connections = self._check_mqtt(mqtt_client)
        services_healthy, service_contributors = self._check_service_health()
        try:
            async with asyncio.timeout(active_config.health_check.timeout):
                overdue_count = await self._check_topic_health()
        except TimeoutError:
            logger.warning(f"{self.log_identity} Overdue topic health check timed out after {active_config.health_check.timeout}s")
            overdue_count = -1

        if overdue_count == 0 and mqtt_connected and modbus_connected and services_healthy:
            status = "healthy"
            if self._current_status != status:
                logger.info(f"{self.log_identity} Status is HEALTHY")
            else:
                logger.debug(f"{self.log_identity} Status is HEALTHY (topic_{overdue_count=} {mqtt_connected=} {modbus_connected=} {service_contributors=})")
        else:
            status = "degraded"
            logger.warning(f"{self.log_identity} Status is DEGRADED (topic_{overdue_count=} {mqtt_connected=} {modbus_connected=} {service_contributors=})")

        payload = {
            "status": status,
            "Uptime_secs": time.monotonic() - self._started,
            "Modbus Connections": modbus_connections,
            "MQTT Connections": mqtt_connections,
            "Monitored Topics": len(self._topics),
            "Overdue Topics": overdue_count,
            "Modbus Connected": modbus_connected,
            "MQTT Connected": mqtt_connected,
        }
        if len(service_contributors) > 0:
            payload["Services Healthy"] = services_healthy
            for key, value in service_contributors.items():
                payload[f"Service '{key}' Healthy"] = value
        self._last_published_at = time.monotonic()
        self._health_payload = payload
        try:
            if mqtt_client:
                mqtt_client.publish(self._health_state_topic, status, qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, json.dumps(payload), qos=1, retain=True)
                logger.debug(f"{self.log_identity} Published health payload to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} {self._health_attributes_topic}")
        except (OSError, UnicodeError, MQTTException, TypeError, ValueError) as ex:
            logger.warning(f"{self.log_identity} Failed to publish health payload: {ex}")
        self._current_status = status

        if not is_docker():  # is_docker() is cached so safe to call repeatedly
            if status == "healthy":
                self._health_check_failures = 0
            else:
                if time.monotonic() - self._started > active_config.health_check.start_period:
                    self._health_check_failures += 1
                    logger.warning(f"{self.log_identity} Health check failure count: {self._health_check_failures}/{active_config.health_check.retries}")
                    if self._health_check_failures >= active_config.health_check.retries:
                        from sigenergy2mqtt.main.restart import restart_controller  # lazy import to avoid circular dependency

                        restart_controller.request("Health check failed repeatedly")
                        self._health_check_failures = 0  # reset to suppress repeat calls until restart completes

    @classmethod
    async def clean(cls) -> None:
        """Clean up the monitor service (clears retained MQTT health topics)."""
        service = cls([])
        try:
            client_id = f"{active_config.mqtt.client_id_prefix}_Monitor"
            client, handler = await mqtt_setup(client_id, None, asyncio.get_running_loop())
            try:
                for topic in (service._health_state_topic, service._health_attributes_topic):
                    logger.debug(f"MonitorService: Removing topic {topic}")
                    info = client.publish(topic, b"", qos=2, retain=True)
                    if info.rc == mqtt.MQTT_ERR_SUCCESS:
                        info.wait_for_publish(timeout=5.0)
                        logger.info(f"MonitorService: Topic {topic} removed successfully")
                    else:
                        logger.error(f"MonitorService: Failed to clean topic {topic}")
            except (OSError, UnicodeError, MQTTException, TypeError, ValueError) as exc:
                logger.warning(f"MonitorService: Failed to clean topics: {exc}")
            finally:
                await mqtt_teardown(client, handler)
        except (OSError, UnicodeError, MQTTException, TypeError, ValueError) as exc:
            logger.warning(f"MonitorService: MQTT connection failed ({exc}) — cleaned disk only")
            return

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
                logger.info(f"{self.log_identity} '{sensor.name}' seen after {sensor.overdue}s (scan_interval={sensor.scan_interval}s {source=})")
            state: float | str
            try:
                state = float(value)
            except ValueError:
                state = value
            async with self._lock:
                sensor.last_seen = time.time()
                sensor.last_state = state
                sensor.notified = False
            return True
        else:
            logger.warning(f"{self.log_identity} updated from  topic {source}, but topic is not registered !!!")
        return False

    def on_commencement(self, modbus_client: Any | None, mqtt_client: mqtt.Client) -> None:
        """Log when the monitor service has started.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
        """
        diagnostics_registry.register("plant", self._collect_plant_states)
        diagnostics_registry.register("solar", self._collect_dashboard_states)

    def on_completion(self, modbus_client: Any | None, mqtt_client: mqtt.Client) -> None:
        """Log when the monitor service has stopped and clear stale health messages.

        Args:
            modbus_client: Optional Modbus client instance.
            mqtt_client: MQTT client instance.
        """

        logger.info(f"{self.log_identity} Service Completed: Flagged as offline ({self.online=})")
        try:
            if mqtt_client:
                mqtt_client.publish(self._health_state_topic, b"", qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, b"", qos=1, retain=True)
                logger.debug(f"{self.log_identity} Cleared health topics on completion")
        except (OSError, UnicodeError, MQTTException, TypeError, ValueError) as ex:
            logger.warning(f"{self.log_identity} Failed to clear health payload: {ex}")

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: bytes | str, qos: int = 2) -> None:
        """No-op availability publisher for the monitor service.

        Args:
            mqtt_client: MQTT client instance.
            ha_state: Optional Home Assistant state.
            qos: Requested MQTT quality-of-service level.
        """

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """No-op discovery publisher for the monitor service.

        Args:
            mqtt_client: MQTT client instance.
            clean: Whether discovery messages should be removed.

        Returns:
            ``None`` because discovery is not published for this service.
        """

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
            logger.info(f"{self.log_identity} Health check disabled, clearing retained health messages")
            try:
                mqtt_client.publish(self._health_state_topic, b"", qos=1, retain=True)
                mqtt_client.publish(self._health_attributes_topic, b"", qos=1, retain=True)
            except (OSError, UnicodeError, MQTTException, TypeError, ValueError) as ex:
                logger.warning(f"{self.log_identity} Failed to clear health payload on subscribe: {ex}")
        if not self._monitor_topic_updates:
            logger.debug(
                f"{self.log_identity} Topic-overdue monitoring disabled (monitor_topic_updates={active_config.monitor_topic_updates} repeated_state_publish_interval={active_config.repeated_state_publish_interval})"
            )
            return

        for d in self._devices:
            device = d.log_identity
            sensors = 0
            for s in [sensor for sensor in d.get_all_sensors().values() if isinstance(sensor, (DerivedSensor, ReadableSensorMixin)) and sensor.publishable and sensor.monitorable]:
                sensor = s.log_identity
                scan_interval = s.scan_interval if isinstance(s, ReadableSensorMixin) else max([src.scan_interval for src in s.bound_source_sensors if isinstance(src, ReadableSensorMixin)], default=600)
                unit = s.unit
                topic = s.state_topic
                if topic in self._topics:
                    logger.error(f"{self.log_identity} Sensor '{device} - {sensor}' has the same topic as '{self._topics[topic].name}' ({topic=}) ????")
                else:
                    self._topics[topic] = MonitoredSensor(
                        device_name=device,
                        sensor_name=sensor,
                        description=s.name,
                        scan_interval=scan_interval,
                        unit=str(unit) if unit else None,
                    )
                    sensors += 1
                    mqtt_handler.register(mqtt_client, topic, handler=self.on_topic_update)
            if sensors > 0:
                logger.debug(f"{self.log_identity} Monitoring {sensors} topic{'s' if sensors > 1 else ''} for {d.log_identity}")
        logger.info(f"{self.log_identity} Subscribed to {len(self._topics)} topics")
