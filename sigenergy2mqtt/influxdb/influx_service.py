import asyncio
import logging
import re
import time
from typing import Awaitable, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import DeviceRegistry
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.mqtt import MqttHandler

from .hass_history_sync import HassHistorySync
from .influx_base import InfluxBase


class InfluxService(InfluxBase):
    """MQTT to InfluxDB bridge service that subscribes to sensor topics and writes to InfluxDB."""

    def __init__(self, logger: logging.Logger, plant_index: int = -1):
        # Create one service instance per plant_index so each caches its own sensors
        name = f"Sigenergy InfluxDB Updater Service (Plant {plant_index})"
        unique = f"influxdb_updater_{plant_index}"
        super().__init__(name, plant_index, unique, "sigenergy2mqtt", "InfluxDB.Updater", logger)

        # History sync helper (shares our session, config, and write methods)
        self._history_sync: HassHistorySync | None = None

    async def _keep_running(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client) -> None:
        self.logger.info(f"{self.name} Commenced")

        await self.async_init()

        sync_task = None
        if self._writer_type:
            if Config.influxdb.load_hass_history:
                # Create history sync helper that shares our connection state
                self._history_sync = HassHistorySync(self.logger, self.plant_index)
                # Copy connection settings from this service
                self._history_sync._session = self._session
                self._history_sync._writer_type = self._writer_type
                self._history_sync._write_url = self._write_url
                self._history_sync._write_headers = self._write_headers
                self._history_sync._write_auth = self._write_auth
                # Start sync with our topic cache
                sync_task = asyncio.create_task(self._history_sync.sync_from_homeassistant(self._topic_cache))
            else:
                self.logger.info(f"{self.name} Loading history from homeassistant database is disabled")

        while self.online:
            try:
                task = asyncio.create_task(asyncio.sleep(1))
                self.sleeper_task = task
                await task
            except asyncio.CancelledError:
                self.logger.debug(f"{self.name} sleep interrupted")
                break
            finally:
                self.sleeper_task = None

        for topic in self._topic_cache.keys():
            mqtt_client.unsubscribe(topic)
        self.logger.info(f"{self.name} Unsubscribed from {len(self._topic_cache)} topics")

        if sync_task:
            if not sync_task.done():
                self.logger.info(f"{self.name} Cancelling background sync task")
                sync_task.cancel()
                try:
                    await sync_task
                except asyncio.CancelledError:
                    pass
            elif sync_task.exception():
                self.logger.error(f"{self.name} Sync task failed: {sync_task.exception()}")

        self.logger.info(f"{self.name} Completed: Flagged as offline ({self.online=})")

    async def handle_mqtt(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, payload: str, topic: str, mqtt_handler: MqttHandler) -> bool:
        try:
            sensor = self._topic_cache.get(topic)
            if not sensor:
                self.logger.warning(f"{self.name} Received update for unknown topic '{topic}' (no cache entry)")
                return False

            timestamp = int(time.time())
            tags: dict[str, str] = {}
            fields: dict[str, int | float | str] = {}
            measurement = cast(str, sensor.get("uom")).replace("/", "_")

            try:
                fv = float(payload)
                fields["value"] = fv
            except Exception:
                fields["value_str"] = payload
            tags["entity_id"] = cast(str, sensor.get("object_id"))

            line = self.to_line_protocol(measurement, tags, fields, timestamp)
            if sensor.get("debug_logging"):
                self.logger.debug(f"{self.name} [{topic}] Writing line protocol: {line}")
            await self.write_line(line)
        except Exception as e:
            self.logger.error(f"{self.name} Failed to handle MQTT message from {topic}: {e}")
            return False
        return True

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        pass

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        pass

    def schedule(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        return [self._keep_running(modbus_client, mqtt_client)]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        devices = DeviceRegistry.get(self.plant_index)
        if not devices:
            return
        for device in devices:
            try:
                for s in device.get_all_sensors().values():
                    obj: str = cast(str, s["object_id"])
                    uid: str = cast(str, getattr(s, "unique_id"))
                    tpc: str = cast(str, getattr(s, "state_topic"))

                    if not getattr(s, "publishable", False):
                        self.logger.debug(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is not publishable")
                        continue

                    if Config.influxdb.include and not any(re.search(ident, s.__class__.__name__) or re.search(ident, obj) or re.search(ident, uid) for ident in Config.influxdb.include):
                        self.logger.info(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is not in include list")
                        continue
                    if Config.influxdb.exclude and any(re.search(ident, s.__class__.__name__) or re.search(ident, obj) or re.search(ident, uid) for ident in Config.influxdb.exclude):
                        self.logger.info(f"{self.name} [{tpc}] Skipping because object_id '{obj}' is excluded")
                        continue

                    self._topic_cache[tpc] = {
                        "uom": s["unit_of_measurement"] if s["unit_of_measurement"] else Config.influxdb.default_measurement,
                        "object_id": obj,
                        "unique_id": uid,
                        "debug_logging": s.debug_logging,
                    }
                    mqtt_handler.register(mqtt_client, tpc, self.handle_mqtt)
            except Exception:
                continue
        self.logger.info(f"{self.name} Subscribed to {len(self._topic_cache)} topics")
