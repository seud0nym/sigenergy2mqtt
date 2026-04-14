"""PVOutput addstatus service implementation.

The status service uploads periodic generation/consumption/voltage/battery
metrics to PVOutput using ``addstatus.jsp``.
"""

import asyncio
import logging
import os
import time
from typing import Any, Awaitable

import requests  # pyrefly: ignore

from sigenergy2mqtt.common.status_field import StatusField
from sigenergy2mqtt.common.voltage_source import VoltageSource
from sigenergy2mqtt.config import active_config

from .service import Service
from .service_topics import Calculation, ServiceTopics
from .topic import Topic


class PVOutputStatusService(Service):
    """Upload interval-based PVOutput status records from MQTT topic values."""

    def __init__(
        self,
        logger: logging.Logger,
        topics: dict[StatusField, list[Topic]],
        extended_data: dict[StatusField, str | None],
        ha_extended_entities: dict[StatusField, str] | None = None,
    ):
        """Configure status field aggregators and register discovered topics.

        Args:
            logger: Logger used by the status service.
            topics: Mapping of PVOutput status fields to source MQTT topics.
            extended_data: Metadata describing configured extended fields.
        """
        super().__init__("PVOutput Add Status Service", unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)
        self._ha_extended_entities = ha_extended_entities or {}
        self._ha_supervisor_warning_emitted = False

        _v1 = ServiceTopics(self, False, logger, value_key=StatusField.GENERATION_ENERGY)
        _v2 = ServiceTopics(self, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
        _v3 = ServiceTopics(self, False and active_config.pvoutput.consumption_enabled, logger, value_key=StatusField.CONSUMPTION_ENERGY)
        _v4 = ServiceTopics(self, active_config.pvoutput.consumption_enabled, logger, value_key=StatusField.CONSUMPTION_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
        _v5 = ServiceTopics(self, True if active_config.pvoutput.temperature_topic else False, logger, value_key=StatusField.TEMPERATURE, calc=Calculation.AVERAGE, decimals=1, negative=True)
        _v6 = ServiceTopics(self, True, logger, value_key=StatusField.VOLTAGE, calc=Calculation.L_L_AVG if active_config.pvoutput.voltage == VoltageSource.L_L_AVG else Calculation.AVERAGE, decimals=1)
        _v7 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V7] else False, logger, value_key=StatusField.V7, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _v8 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V8] else False, logger, value_key=StatusField.V8, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _v9 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V9] else False, logger, value_key=StatusField.V9, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _v10 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V10] else False, logger, value_key=StatusField.V10, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _v11 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V11] else False, logger, value_key=StatusField.V11, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _v12 = ServiceTopics(self, True if active_config.pvoutput.extended[StatusField.V12] else False, logger, value_key=StatusField.V12, calc=Calculation.AVERAGE, decimals=4, donation=True, negative=True)
        _b1 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS, decimals=1, donation=True, negative=True)
        _b2 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_SOC, calc=Calculation.AVERAGE, donation=True, decimals=1)
        _b3 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_CAPACITY, donation=True)
        _b4 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_CHARGED, donation=True)
        _b5 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_DISCHARGED, donation=True)
        _b6 = ServiceTopics(self, False, logger, value_key=StatusField.BATTERY_STATE, donation=True)

        self._previous_payload: dict | None = None
        self._service_topics: dict[str, ServiceTopics] = {
            StatusField.GENERATION_ENERGY: _v1,
            StatusField.GENERATION_POWER: _v2,
            StatusField.CONSUMPTION_ENERGY: _v3,
            StatusField.CONSUMPTION_POWER: _v4,
            StatusField.TEMPERATURE: _v5,
            StatusField.VOLTAGE: _v6,
            StatusField.V7: _v7,
            StatusField.V8: _v8,
            StatusField.V9: _v9,
            StatusField.V10: _v10,
            StatusField.V11: _v11,
            StatusField.V12: _v12,
            StatusField.BATTERY_POWER: _b1,
            StatusField.BATTERY_SOC: _b2,
            StatusField.BATTERY_CAPACITY: _b3,
            StatusField.BATTERY_CHARGED: _b4,
            StatusField.BATTERY_DISCHARGED: _b5,
            StatusField.BATTERY_STATE: _b6,
        }

        for field, topic_list in topics.items():
            if field in self._service_topics:
                if field in extended_data and extended_data[field] == "energy":
                    self._service_topics[field].calculation = Calculation.SUM | Calculation.DIFFERENCE
                for topic in topic_list:
                    self._service_topics[field].register(topic)
                    if topic.precision is not None:
                        self._service_topics[field].decimals = topic.precision
            else:
                self.logger.debug(f"{self.log_identity} IGNORED unrecognized {field}")

    async def _refresh_home_assistant_extended_fields(self) -> None:
        """Refresh HA sensor-backed extended field values via Supervisor API."""
        if not self._ha_extended_entities:
            return

        token = os.getenv("SUPERVISOR_TOKEN")
        if not token:
            if not self._ha_supervisor_warning_emitted:
                self.logger.warning(f"{self.log_identity} Home Assistant sensor source configured, but SUPERVISOR_TOKEN is not available")
                self._ha_supervisor_warning_emitted = True
            return

        base_url = os.getenv("SUPERVISOR_URL", "http://supervisor").rstrip("/")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        for field, entity_id in self._ha_extended_entities.items():
            url = f"{base_url}/core/api/states/{entity_id}"
            state_raw: Any = None
            try:
                response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=5)
                if response.status_code != 200:
                    self.logger.warning(f"{self.log_identity} Failed to read Home Assistant sensor '{entity_id}' via Supervisor API: status_code={response.status_code}")
                    continue
                state_raw = response.json().get("state")
                if state_raw in (None, "unknown", "unavailable"):
                    self.logger.debug(f"{self.log_identity} Ignoring Home Assistant sensor '{entity_id}' state={state_raw}")
                    continue
                topic = f"__ha_sensor__:{entity_id}"
                if field in self._service_topics and topic in self._service_topics[field]:
                    await self._service_topics[field].handle_update(None, None, float(state_raw), topic, None)
            except (TypeError, ValueError):
                self.logger.warning(f"{self.log_identity} Home Assistant sensor '{entity_id}' returned non-numeric state='{state_raw}'")
            except Exception as exc:
                self.logger.warning(f"{self.log_identity} Failed reading Home Assistant sensor '{entity_id}' via Supervisor API: {exc}")

    def _create_payload(self, now: time.struct_time) -> tuple[dict[str, Any], dict[str, dict[str, tuple[float | None, time.struct_time | None]]]]:
        """Build a status payload and snapshot state for rollback on failure.

        Args:
            now: Timestamp used to stamp the payload date/time values.
        """
        payload: dict[str, Any] = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now)}
        topics: list[ServiceTopics] = [t for t in self._service_topics.values() if t.enabled and (not t.requires_donation or Service._donator)]
        snapshot: dict[str, dict[str, tuple[float | None, time.struct_time | None]]] = {
            st: {t.topic: (t.previous_state, t.previous_timestamp) for t in st_topics.values()}
            for st, st_topics in self._service_topics.items()
            if st_topics.enabled and (not st_topics.requires_donation or Service._donator)
        }
        for topic in topics:
            topic.add_to_payload(payload, Service._interval, now)
        return payload, snapshot

    async def seconds_until_status_upload(self, rand_min: int = 1, rand_max: int = 15) -> tuple[float, int]:
        """Compute and log the next randomized status upload schedule.

        Args:
            rand_min: Minimum random offset (seconds) for next upload.
            rand_max: Maximum random offset (seconds) for next upload.
        """
        seconds, next_time = await super().seconds_until_status_upload(rand_min, rand_max)
        self.logger.debug(f"{self.log_identity} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return seconds, next_time

    def schedule(self, modbus_client: Any, mqtt_client: Any) -> list[Awaitable[None]]:
        """Return asyncio tasks that periodically upload status payloads.

        Args:
            modbus_client: Modbus client reference (unused).
            mqtt_client: MQTT client reference (unused).
        """

        async def publish_updates(modbus_client: Any, mqtt_client: Any, *sensors: Any) -> None:
            self.logger.info(f"{self.log_identity} Commenced")
            wait, _ = await self.seconds_until_status_upload()
            while self.online:
                try:
                    if wait <= 0:
                        await self._refresh_home_assistant_extended_fields()
                        now = time.localtime()
                        async with self.lock(timeout=5):
                            payload, snapshot = self._create_payload(now)
                        if (  # At least one of the values v1, v2, v3 or v4 must be present
                            payload.get(StatusField.GENERATION_ENERGY.value) is not None
                            or payload.get(StatusField.GENERATION_POWER.value) is not None
                            or payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None
                            or (payload.get(StatusField.CONSUMPTION_POWER.value) is not None and active_config.pvoutput.consumption_enabled)
                        ):
                            if payload.get(StatusField.GENERATION_ENERGY.value) is not None and payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None:
                                payload["c1"] = 1
                            elif payload.get(StatusField.GENERATION_ENERGY.value) is not None and StatusField.CONSUMPTION_ENERGY.value not in payload:
                                payload["c1"] = 2
                            elif payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None:
                                payload["c1"] = 3
                            if payload.get(StatusField.CONSUMPTION_POWER.value, 0) < 0:
                                self.logger.warning(
                                    f"{self.log_identity} Adjusted {StatusField.CONSUMPTION_POWER.name} (payload['{StatusField.CONSUMPTION_POWER.value}']) to 0 from {payload[StatusField.CONSUMPTION_POWER]} to comply with PVOutput requirements"
                                )
                                payload[StatusField.CONSUMPTION_POWER.value] = 0  # PVOutput does not accept negative consumption power values
                            uploaded = await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
                            if not uploaded:
                                self.logger.debug(f"{self.log_identity} Restoring previous state of topics due to failed upload")
                                async with self.lock(timeout=5):
                                    for st, topics_dict in self._service_topics.items():
                                        for topic in topics_dict.values():
                                            if st in snapshot and topic.topic in snapshot[st]:
                                                topic.previous_state, topic.previous_timestamp = snapshot[st][topic.topic]
                        else:
                            self.logger.warning(f"{self.log_identity} No generation{' or consumption data' if active_config.pvoutput.consumption_enabled else ''} to upload, skipping... ({payload=})")
                        wait, _ = await self.seconds_until_status_upload()
                    sleep = min(wait, 1)
                    wait -= sleep
                    if wait > 0:
                        task = asyncio.create_task(asyncio.sleep(sleep))
                        self.sleeper_task = task
                        try:
                            await task
                        finally:
                            self.sleeper_task = None
                except asyncio.CancelledError:
                    self.logger.info(f"{self.log_identity} Sleep interrupted")
                except asyncio.TimeoutError:
                    self.logger.warning(f"{self.log_identity} Failed to acquire lock within timeout")
                except Exception as e:
                    self.logger.error(f"{self.log_identity} {e}")
                    if wait <= 0:
                        wait = 60
            self.logger.info(f"{self.log_identity} Completed: Flagged as offline ({self.online=})")
            return

        tasks: list[Awaitable[None]] = [publish_updates(modbus_client, mqtt_client)]
        return tasks

    def subscribe(self, mqtt_client, mqtt_handler) -> None:
        """Subscribe all enabled status topic groups to MQTT updates.

        Args:
            mqtt_client: MQTT client used to create subscriptions.
            mqtt_handler: MQTT handler used to register callbacks.
        """
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.subscribe(mqtt_client, mqtt_handler)
