"""PVOutput addoutput service implementation.

This service aggregates daily import/export/consumption/generation metrics and
uploads them to PVOutput via ``addoutput.jsp``.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from random import randint
from typing import Any, Awaitable

import paho.mqtt.client as mqtt
import requests

from sigenergy2mqtt.common.output_field import OutputField
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttHandler

from .service import Service
from .service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics
from .topic import Topic


class PVOutputOutputService(Service):
    """Upload daily PVOutput output records from aggregated MQTT topic state."""
    def __init__(self, logger: logging.Logger, topics: dict[OutputField, list[Topic]]):
        """Build output field aggregators and register configured MQTT topics.

        Args:
            logger: Logger used by the output service.
            topics: Mapping of PVOutput output fields to source MQTT topics.
        """
        super().__init__("PVOutput Add Output Service", unique_id="pvoutput_output", model="PVOutput.AddOutput", logger=logger)

        _c = ServiceTopics(self, False, logger, value_key=OutputField.CONSUMPTION)  # Disable EoD consumption update because it is updated via the status service
        _eh = TimePeriodServiceTopics(self, active_config.pvoutput.exports, logger, value_key=OutputField.EXPORT_HIGH_SHOULDER)
        _eo = TimePeriodServiceTopics(self, active_config.pvoutput.exports, logger, value_key=OutputField.EXPORT_OFF_PEAK)
        _ep = TimePeriodServiceTopics(self, active_config.pvoutput.exports, logger, value_key=OutputField.EXPORT_PEAK)
        _es = TimePeriodServiceTopics(self, active_config.pvoutput.exports, logger, value_key=OutputField.EXPORT_SHOULDER)
        _e = ServiceTopics(self, active_config.pvoutput.exports, logger, value_key=OutputField.EXPORTS, periods=[_eh, _eo, _ep, _es])
        _g = ServiceTopics(self, False, logger, value_key=OutputField.GENERATION)  # Disable EoD generation update because it is updated via the status service
        _ih = TimePeriodServiceTopics(self, active_config.pvoutput.imports, logger, value_key=OutputField.IMPORT_HIGH_SHOULDER)
        _io = TimePeriodServiceTopics(self, active_config.pvoutput.imports, logger, value_key=OutputField.IMPORT_OFF_PEAK)
        _ip = TimePeriodServiceTopics(self, active_config.pvoutput.imports, logger, value_key=OutputField.IMPORT_PEAK)
        _is = TimePeriodServiceTopics(self, active_config.pvoutput.imports, logger, value_key=OutputField.IMPORT_SHOULDER)
        _i = ServiceTopics(self, active_config.pvoutput.imports, logger, value_key=OutputField.IMPORTS, periods=[_ih, _io, _ip, _is])  # Dummy parent for import periods
        _pp = ServiceTopics(self, True, logger, value_key=OutputField.PEAK_POWER, datetime_key="pt", calc=Calculation.SUM | Calculation.PEAK)

        self._latest_peak_at: str | None = None
        self._previous_payload: dict | None = None
        self._service_topics: dict[str, ServiceTopics] = {
            OutputField.GENERATION: _g,
            OutputField.IMPORTS: _i,
            OutputField.EXPORTS: _e,
            OutputField.PEAK_POWER: _pp,
            OutputField.CONSUMPTION: _c,
            OutputField.IMPORT_PEAK: _ip,
            OutputField.IMPORT_OFF_PEAK: _io,
            OutputField.IMPORT_SHOULDER: _is,
            OutputField.IMPORT_HIGH_SHOULDER: _ih,
            OutputField.EXPORT_PEAK: _ep,
            OutputField.EXPORT_OFF_PEAK: _eo,
            OutputField.EXPORT_SHOULDER: _es,
            OutputField.EXPORT_HIGH_SHOULDER: _eh,
        }

        for field, topic_list in topics.items():
            if field in self._service_topics:
                for topic in topic_list:
                    self._service_topics[field].register(topic)
            else:
                self.logger.debug(f"{self.log_identity} IGNORED unrecognized {field}")

    def _create_payload(self, now_struct: time.struct_time, interval: int) -> dict[str, float | int | str]:
        """Create a dated output payload from currently aggregated topic values.

        Args:
            now_struct: Current local timestamp.
            interval: PVOutput interval (minutes) used for calculations.
        """
        payload: dict[str, float | int | str] = {"d": time.strftime("%Y%m%d", now_struct)}
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.add_to_payload(payload, interval, now_struct)
        return payload

    def _is_payload_changed(self, payload: dict[str, float | int | str]) -> bool:
        """Return ``True`` when payload differs from the last uploaded payload.

        Args:
            payload: Candidate payload to compare against cached payload.
        """
        if payload and self._previous_payload and len(payload) == len(self._previous_payload):
            for key, value in self._previous_payload.items():
                if key not in payload or payload[key] != value:
                    break
            else:
                return False
        return True

    async def _next_output_upload(self, minute: int = 58) -> float:
        """Calculate the next timestamp when output data should be uploaded.

        Args:
            minute: Minute within the configured hour for end-of-day uploads.
        """
        t = time.localtime()
        now = time.mktime(t)
        if active_config.pvoutput.output_hour == -1:  # Update at status interval
            interval, _ = await self.seconds_until_status_upload(rand_min=16, rand_max=30)
            next = now + 120 + interval  # Wait 2 minutes plus the interval to ensure status upload has completed
        else:
            if active_config.pvoutput.testing:
                next = now + 60
            else:
                next = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, active_config.pvoutput.output_hour, minute, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
                if next <= now:
                    today = datetime.fromtimestamp(next)
                    tomorrow = today + timedelta(days=1, seconds=randint(-15, 15))  # Add a random offset of up to 15 seconds for variability
                    next = tomorrow.timestamp()
        return next

    async def _verify(self, payload: dict[str, float | int | str], force: bool = False) -> bool:
        """Verify uploaded output data by reading it back from PVOutput.

        Args:
            payload: Payload that was uploaded.
            force: Whether to retry verification aggressively.
        """
        self.logger.debug(f"{self.log_identity} Verifying uploaded {payload=}")
        url = f"https://pvoutput.org/service/r2/getoutput.jsp?df={payload['d']}&dt={payload['d']}{'&timeofexport=1' if active_config.pvoutput.exports else ''}"
        verify_retries: int = 3 if force else 1
        initial_wait: float = 0.1 if not force or active_config.pvoutput.testing else 120.0
        subsequent_wait: float = 0.1 if active_config.pvoutput.testing else 60.0
        matches: bool = False
        for validate in range(1, verify_retries + 1, 1):
            wait: float = initial_wait if validate == 1 else subsequent_wait
            self.logger.debug(f"{self.log_identity} Waiting for {wait}s before checking that the upload has been processed successfully...")
            await asyncio.sleep(wait)
            result = {}
            try:
                if active_config.pvoutput.testing:
                    self.logger.debug(f"{self.log_identity} Verification attempt #{validate} simulation for testing mode, not sending request to {url=}")
                    if validate > 1:
                        v = re.split(
                            r"[,]",
                            f"{payload['d']},{payload.get('g', 'NaN')},{payload.get('c', 'NaN')},{payload.get('e', 'NaN')},0,{payload.get('pp', 'NaN')},{payload.get('pt', '')},Showers,12,16,{payload.get('ip', 'NaN')},{payload.get('io', 'NaN')},{payload.get('is', 'NaN')},{payload.get('ih', 'NaN')},{payload.get('ep', 'NaN')},{payload.get('eo', 'NaN')},{payload.get('es', 'NaN')},{payload.get('eh', 'NaN')}",
                        )
                        matches = True
                    else:
                        self.logger.debug(f"{self.log_identity} Verification attempt #{validate} simulation FAILED")
                        matches = False
                else:
                    self.logger.debug(f"{self.log_identity} Verification attempt #{validate} to {url=}...")
                    response = await asyncio.to_thread(requests.get, url, headers=self.request_headers, timeout=10)
                    limit, remaining, at, reset = self.get_response_headers(response)
                    if response.status_code == 200:
                        self.logger.debug(
                            f"{self.log_identity} Verification attempt #{validate} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s) response={response.text}"
                        )
                        v = re.split(r"[,]", response.text)
                        result["d"] = v[0]
                        result["e"] = int(v[3]) if active_config.pvoutput.exports and len(v) > 3 and v[3] != "NaN" else None
                        result["pp"] = int(v[5]) if len(v) > 5 and v[5] != "NaN" else None
                        result["ip"] = int(v[10]) if active_config.pvoutput.imports and len(v) > 10 and v[10] != "NaN" else None
                        result["io"] = int(v[11]) if active_config.pvoutput.imports and len(v) > 11 and v[11] != "NaN" else None
                        result["is"] = int(v[12]) if active_config.pvoutput.imports and len(v) > 12 and v[12] != "NaN" else None
                        result["ih"] = int(v[13]) if active_config.pvoutput.imports and len(v) > 13 and v[13] != "NaN" else None
                        result["ep"] = int(v[14]) if active_config.pvoutput.exports and len(v) > 14 and v[14] != "NaN" else None
                        result["eo"] = int(v[15]) if active_config.pvoutput.exports and len(v) > 15 and v[15] != "NaN" else None
                        result["es"] = int(v[16]) if active_config.pvoutput.exports and len(v) > 16 and v[16] != "NaN" else None
                        result["eh"] = int(v[17]) if active_config.pvoutput.exports and len(v) > 17 and v[17] != "NaN" else None
                        matches = True
                    else:
                        self.logger.debug(f"{self.log_identity} Verification attempt #{validate} FAILED status_code={response.status_code} reason={response.reason}")
                        matches = False
                if matches:
                    for topic in [t for t in self._service_topics.values() if t.enabled]:
                        key = topic._value_key.value
                        if key in payload and key in result:
                            if payload[key] != result[key]:
                                self.logger.debug(f"{self.log_identity} Verification FAILED: payload['{key}']={payload[key]} != result['{key}']={result[key]}")
                                matches = False
                if matches:
                    try:
                        self.logger.info(f"{self.log_identity} Verification SUCCESS {payload=} downloaded={result} ({response.text})")  # type: ignore # pyrefly: ignore
                    except NameError:
                        self.logger.info(f"{self.log_identity} Verification SUCCESS {payload=} downloaded={result}")
                    break
                elif validate < verify_retries:
                    self.logger.debug(f"{self.log_identity} Verification attempt #{validate} of uploaded {payload=} FAILED, retrying...")
                else:
                    try:
                        self.logger.error(f"{self.log_identity} Verification FAILED after {validate} attempts for uploaded {payload=} ({response.text})")  # type: ignore # pyrefly: ignore
                    except NameError:
                        self.logger.error(f"{self.log_identity} Verification FAILED after {validate} attempts for uploaded {payload=}")
            except requests.exceptions.HTTPError as exc:
                self.logger.error(f"{self.log_identity} HTTP Error: {exc}")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.log_identity} Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.log_identity} Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.log_identity} {exc}")
        return matches

    async def _upload(self, payload: dict[str, float | int | str], last_upload_of_day: bool = False) -> None:
        """Upload output payload and optionally verify the final daily upload.

        Args:
            payload: Output payload to upload.
            last_upload_of_day: Whether this is the final daily upload.
        """
        upload_retries: int = 5 if last_upload_of_day else 2
        uploaded: bool = False
        changed: bool = self._is_payload_changed(payload)
        matches: bool = False
        attempt: int = 0
        for i in range(1, upload_retries + 1, 1):
            attempt = i
            if changed:
                uploaded = await self.upload_payload("https://pvoutput.org/service/r2/addoutput.jsp", payload)
            else:
                uploaded = False
                self.logger.info(f"{self.log_identity} Skipped uploading unchanged {payload=}")
            if last_upload_of_day:
                matches = await self._verify(payload, force=last_upload_of_day)
                if matches:
                    break
                else:
                    changed = True  # Force re-upload if verification failed
                    if last_upload_of_day and attempt > 1:
                        break
            elif uploaded:
                break
        self.logger.debug(f"{self.log_identity} Upload completed for {payload=}: {changed=} {uploaded=} attempts={attempt} verified={matches} ({last_upload_of_day=})")
        if changed and active_config.pvoutput.output_hour == -1:
            self._previous_payload = payload

    def schedule(self, modbus_client: Any, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Return asyncio tasks that periodically generate and upload output.

        Args:
            modbus_client: Modbus client reference (unused).
            mqtt_client: MQTT client reference (unused).
        """
        async def publish_updates(modbus_client: Any, mqtt_client: Any, *sensors: Any) -> None:
            minute: int = randint(56, 59)
            next: float = await self._next_output_upload(minute)
            last: float | None = None
            self.logger.info(f"{self.log_identity} Commenced (Updating at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))})")
            while self.online:
                try:
                    now_struct: time.struct_time = time.localtime()
                    now: float = time.mktime(now_struct)
                    if now >= next:
                        async with self.lock(timeout=5):
                            payload = self._create_payload(now_struct, Service._interval)
                        tomorrow = await self._next_output_upload(minute)
                        last_update_of_day: bool = time.localtime(tomorrow).tm_yday != now_struct.tm_yday  # Bypass verification except on last upload of the day
                        await self._upload(payload, last_update_of_day)
                        next = tomorrow
                        self.logger.debug(f"{self.log_identity} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))} ({next - now:.2f}s)")
                    elif int(now) % (30 if active_config.pvoutput.testing else 900) == 0:
                        for topic in [t for k, t in self._service_topics.items() if t.enabled and k != OutputField.PEAK_POWER]:
                            topic.check_is_updating(5, now_struct)
                        total, at, _ = self._service_topics[OutputField.PEAK_POWER].aggregate(exclude_zero=False)
                        if total is not None and total > 0 and self._latest_peak_at != at:
                            self._latest_peak_at = at
                            self.logger.info(f"{self.log_identity} Peak Power {total:.0f}W recorded at {at}")
                    if last:
                        was = time.localtime(last)
                        if was.tm_yday != now_struct.tm_yday:
                            self.logger.info(f"{self.log_identity} Resetting service topic states to 0.0 because the day has changed ({was.tm_yday} -> {now_struct.tm_yday})")
                            self._previous_payload = None
                            async with self.lock(timeout=5):
                                for topic in self._service_topics.values():
                                    topic.reset()
                    last = now
                    sleep: float = min(next - now, 1)
                    if sleep > 0:
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
                    self.logger.error(f"{self.log_identity}  Sleeping for 60s after exception: {e}")
                    await asyncio.sleep(60)
            self.logger.info(f"{self.log_identity} Completed: Flagged as offline ({self.online=})")
            return

        tasks: list[Awaitable[None]] = [publish_updates(modbus_client, mqtt_client)]
        return tasks

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Subscribe all enabled output topic groups to MQTT updates.

        Args:
            mqtt_client: MQTT client used to create subscriptions.
            mqtt_handler: MQTT handler used to register callbacks.
        """
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.subscribe(mqtt_client, mqtt_handler)
