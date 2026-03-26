import asyncio
import logging
import re
import time
from typing import Awaitable, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import DeviceRegistry
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.mqtt import MqttHandler

from .hass_history_sync import HassHistorySync
from .influx_base import InfluxBase


class InfluxService(InfluxBase):
    """MQTT-to-InfluxDB bridge that subscribes to sensor state topics and persists values.

    One :class:`InfluxService` instance is created per Modbus plant so that
    each plant maintains its own :attr:`~InfluxBase._topic_cache` and logger
    hierarchy.  On startup the service optionally triggers a one-shot backfill
    from the Home Assistant InfluxDB database via :class:`HassHistorySync`.
    """

    def __init__(self, logger: logging.Logger, plant_index: int = -1) -> None:
        """Initialise the service for the given plant index.

        Args:
            logger: Pre-configured logger (typically ``influxdb.plant<N>``).
            plant_index: Zero-based index identifying which Modbus plant this
                service belongs to.
        """
        name = f"Sigenergy InfluxDB Updater Service (Plant {plant_index})"
        unique = f"influxdb_updater_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.Updater", logger)

        self._history_sync: HassHistorySync | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _matches_filter(self, sensor: object, obj: str, uid: str, patterns: list[str]) -> bool:
        """Return ``True`` if the sensor matches any of the given regex patterns.

        Patterns are tested against the sensor's class name, ``object_id``, and
        ``unique_id`` in turn.  The first match short-circuits further checks.

        Args:
            sensor: Sensor instance whose class name is tested.
            obj: Sensor ``object_id`` string.
            uid: Sensor ``unique_id`` string.
            patterns: List of regex patterns from the include/exclude config.

        Returns:
            ``True`` if any pattern matches any of the three identifiers.
        """
        return any(re.search(pat, sensor.__class__.__name__) or re.search(pat, obj) or re.search(pat, uid) for pat in patterns)

    # ------------------------------------------------------------------
    # Service lifecycle
    # ------------------------------------------------------------------

    async def _keep_running(
        self,
        modbus_client: ModbusClient | None,
        mqtt_client: mqtt.Client,
    ) -> None:
        """Main service coroutine: initialise, optionally sync history, then idle.

        Runs until :attr:`~Device.online` becomes ``False`` (set externally on
        shutdown).  On exit, unsubscribes all MQTT topics and cancels any
        in-flight history sync task.

        Args:
            modbus_client: Modbus client for the plant (unused directly, passed
                for interface compatibility).
            mqtt_client: Active MQTT client used for unsubscription on shutdown.
        """
        self.logger.info(f"{self.log_identity} Commenced")

        if not await self.async_init():
            self.logger.error(f"{self.log_identity} Initialisation failed — service will not write to InfluxDB")
            return

        sync_task: asyncio.Task | None = None
        if self._writer_type:
            if active_config.influxdb.load_hass_history:
                # Create history sync helper and share our established connection.
                self._history_sync = HassHistorySync(self.logger, self.plant_index)
                self._history_sync.copy_connection_from(self)
                sync_task = asyncio.create_task(self._history_sync.sync_from_homeassistant(self._topic_cache))
            else:
                self.logger.info(f"{self.log_identity} Loading history from Home Assistant is disabled")

        while self.online:
            try:
                task = asyncio.create_task(asyncio.sleep(1))
                self.sleeper_task = task
                await task
            except asyncio.CancelledError:
                self.logger.debug(f"{self.log_identity} sleep interrupted")
                break
            finally:
                self.sleeper_task = None

        for topic in self._topic_cache.keys():
            mqtt_client.unsubscribe(topic)
        self.logger.info(f"{self.log_identity} Unsubscribed from {len(self._topic_cache)} topics")
        self._topic_cache.clear()

        if sync_task:
            if not sync_task.done():
                self.logger.info(f"{self.log_identity} Cancelling background sync task")
                sync_task.cancel()
                try:
                    await sync_task
                except asyncio.CancelledError:
                    pass
            elif sync_task.exception():
                self.logger.error(f"{self.log_identity} Sync task failed: {sync_task.exception()}")

        self.logger.info(f"{self.log_identity} Completed: Flagged as offline ({self.online=})")

    # ------------------------------------------------------------------
    # MQTT handling
    # ------------------------------------------------------------------

    async def handle_mqtt(
        self,
        modbus_client: ModbusClient | None,
        mqtt_client: mqtt.Client,
        payload: str,
        topic: str,
        mqtt_handler: MqttHandler,
    ) -> bool:
        """Process an incoming MQTT message and write the value to InfluxDB.

        The measurement name is derived from the sensor's unit of measurement
        (with ``/`` replaced by ``_``).  Numeric payloads are stored as
        ``value`` (float); non-numeric payloads are stored as ``value_str``
        (string).

        Args:
            modbus_client: Modbus client for the plant (unused, for interface compatibility).
            mqtt_client: Active MQTT client (unused, for interface compatibility).
            payload: Raw string payload from the MQTT broker.
            topic: Full MQTT topic string.
            mqtt_handler: MQTT handler (unused, for interface compatibility).

        Returns:
            ``True`` if the value was successfully queued for writing,
            ``False`` on any error.
        """
        try:
            sensor = self._topic_cache.get(topic)
            if not sensor:
                self.logger.warning(f"{self.log_identity} Received update for unknown topic '{topic}' (no cache entry)")
                return False

            timestamp = int(time.time())
            tags: dict[str, str] = {}
            fields: dict[str, int | float | str] = {}

            # Fall back to default measurement when uom is absent or empty.
            uom = sensor.get("uom") or active_config.influxdb.default_measurement
            measurement = uom.replace("/", "_")

            try:
                fields["value"] = float(payload)
            except (ValueError, TypeError):
                fields["value_str"] = payload

            tags["entity_id"] = cast(str, sensor.get("object_id"))

            line = self.to_line_protocol(measurement, tags, fields, timestamp)
            if sensor.get("debug_logging"):
                self.logger.debug(f"{self.log_identity} [{topic}] Writing line protocol: {line}")
            await self.write_line(line)

        except Exception as e:
            self.logger.error(f"{self.log_identity} Failed to handle MQTT message from {topic}: {e}")
            return False
        return True

    # ------------------------------------------------------------------
    # Device interface stubs
    # ------------------------------------------------------------------

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        """No-op: InfluxDB service does not publish availability to MQTT."""

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """No-op: InfluxDB service does not publish Home Assistant discovery."""

    # ------------------------------------------------------------------
    # Scheduling and subscription
    # ------------------------------------------------------------------

    def schedule(
        self,
        modbus_client: ModbusClient | None,
        mqtt_client: mqtt.Client,
    ) -> list[Awaitable[None]]:
        """Return the list of awaitables that drive this service.

        Args:
            modbus_client: Modbus client for the plant.
            mqtt_client: Active MQTT client.

        Returns:
            A single-element list containing the :meth:`_keep_running` coroutine.
        """
        return [self._keep_running(modbus_client, mqtt_client)]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Discover all publishable sensors for this plant and subscribe to their topics.

        Sensors are filtered against the configured include/exclude regex lists
        before subscription.  Each accepted sensor is added to
        :attr:`~InfluxBase._topic_cache` so that :meth:`handle_mqtt` can look
        up its metadata by topic.

        Args:
            mqtt_client: Active MQTT client used to register subscriptions.
            mqtt_handler: Handler that maps topics to callback coroutines.
        """
        devices = DeviceRegistry.get(self.plant_index)
        if not devices:
            return

        for device in devices:
            try:
                for s in device.get_all_sensors().values():
                    obj: str = cast(str, s["object_id"])
                    uid: str = cast(str, getattr(s, "unique_id", None))
                    tpc: str = cast(str, getattr(s, "state_topic", None))

                    if not tpc:
                        self.logger.debug(f"{self.log_identity} Skipping sensor '{obj}': no state_topic")
                        continue

                    if not getattr(s, "publishable", False):
                        self.logger.debug(f"{self.log_identity} [{tpc}] Skipping because object_id '{obj}' is not publishable")
                        continue

                    if active_config.influxdb.include and not self._matches_filter(s, obj, uid, active_config.influxdb.include):  # type: ignore[reportGeneralTypeIssues]
                        self.logger.info(f"{self.log_identity} [{tpc}] Skipping because object_id '{obj}' is not in include list")
                        continue

                    if active_config.influxdb.exclude and self._matches_filter(s, obj, uid, active_config.influxdb.exclude):  # type: ignore[reportGeneralTypeIssues]
                        self.logger.info(f"{self.log_identity} [{tpc}] Skipping because object_id '{obj}' is excluded")
                        continue

                    self._topic_cache[tpc] = {
                        "uom": s["unit_of_measurement"] if s["unit_of_measurement"] else active_config.influxdb.default_measurement,
                        "object_id": obj,
                        "unique_id": uid,
                        "debug_logging": s.debug_logging,
                    }
                    mqtt_handler.register(mqtt_client, tpc, self.handle_mqtt)

            except Exception as e:
                self.logger.warning(f"{self.log_identity} Failed to subscribe sensors for device '{device}': {e}")
                continue

        self.logger.info(f"{self.log_identity} Subscribed to {len(self._topic_cache)} topics")
