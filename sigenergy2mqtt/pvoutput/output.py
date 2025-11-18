from .service import Service
from .service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics
from .topic import Topic
from datetime import datetime, timedelta
from random import randint
from sigenergy2mqtt.config import Config, OutputField
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import re
import requests
import time


class PVOutputOutputService(Service):
    def __init__(self, logger: logging.Logger, topics: dict[OutputField, list[Topic]]):
        super().__init__("PVOutput Add Output Service", unique_id="pvoutput_output", model="PVOutput.AddOutput", logger=logger)

        _c = ServiceTopics(self, False, logger, value_key=OutputField.CONSUMPTION)  # Disable EoD consumption update because it is updated via the status service
        _eh = TimePeriodServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORT_HIGH_SHOULDER)
        _eo = TimePeriodServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORT_OFF_PEAK)
        _ep = TimePeriodServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORT_PEAK)
        _es = TimePeriodServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORT_SHOULDER)
        _e = ServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORTS, time_periods=(_eh, _eo, _ep, _es))
        _g = ServiceTopics(self, False, logger, value_key=OutputField.GENERATION)  # Disable EoD generation update because it is updated via the status service
        _ih = TimePeriodServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORT_HIGH_SHOULDER)
        _io = TimePeriodServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORT_OFF_PEAK)
        _ip = TimePeriodServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORT_PEAK)
        _is = TimePeriodServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORT_SHOULDER)
        _i = ServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORTS, time_periods=(_ih, _io, _ip, _is))  # Dummy parent for import periods
        _pp = ServiceTopics(self, True, logger, value_key=OutputField.PEAK_POWER, datetime_key="pt", calculation=Calculation.SUM | Calculation.PEAK)

        self._latest_peak_at: str = None
        self._previous_payload: dict = None
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
                self.logger.debug(f"{self.__class__.__name__} IGNORED unrecognized {field} with topic {topic.topic}")

    def _is_payload_changed(self, payload: dict[str, str | int]) -> bool:
        if payload and self._previous_payload and len(payload) == len(self._previous_payload):
            for key, value in self._previous_payload.items():
                if key not in payload or payload[key] != value:
                    break
            else:
                return False
        return True

    async def _next_output_upload(self, minute: int = 58) -> float:
        t = time.localtime()
        now = time.mktime(t)
        if Config.pvoutput.output_hour == -1:  # Update at status interval
            interval, _ = await self.seconds_until_status_upload(rand_min=16, rand_max=30)
            next = now + 120 + interval  # Wait 2 minutes plus the interval to ensure status upload has completed
        else:
            if Config.pvoutput.testing:
                next = now + 60
            else:
                next = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, Config.pvoutput.output_hour, minute, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
                if next <= now:
                    today = datetime.fromtimestamp(next)
                    tomorrow = today + timedelta(days=1, seconds=randint(-15, 15))  # Add a random offset of up to 15 seconds for variability
                    next = tomorrow.timestamp()
        return next

    async def _upload(self, payload: dict[str, int | str], last_upload_of_day: bool = False) -> None:
        upload_retries: int = 5 if last_upload_of_day else 2
        changed: bool = self._is_payload_changed(payload)
        matches: bool = None
        for attempt in range(1, upload_retries + 1, 1):
            if changed:
                uploaded = await self.upload_payload("https://pvoutput.org/service/r2/addoutput.jsp", payload)
            else:
                uploaded = None
                self.logger.info(f"{self.__class__.__name__} Skipped uploading unchanged {payload=}")
            if last_upload_of_day or not changed:
                matches = await self._verify(payload, force=last_upload_of_day)
                if matches:
                    break
                else:
                    changed = True  # Force re-upload if verification failed
                    if last_upload_of_day and attempt > 1:
                        break
            elif uploaded or not changed:
                break
        self.logger.debug(f"{self.__class__.__name__} Upload completed for {payload=}: {changed=} {uploaded=} attempts={attempt} verified={matches} ({last_upload_of_day=})")
        if changed and Config.pvoutput.output_hour == -1:
            self._previous_payload = payload

    async def _verify(self, payload: dict[str, int | str], force: bool = False) -> bool:
        self.logger.debug(f"{self.__class__.__name__} Verifying uploaded {payload=}")
        url = f"https://pvoutput.org/service/r2/getoutput.jsp?df={payload['d']}&dt={payload['d']}{'&timeofexport=1' if Config.pvoutput.exports else ''}"
        verify_retries: int = 3 if force else 1
        initial_wait: float = 0.1 if not force or Config.pvoutput.testing else 120.0
        subsequent_wait: float = 0.1 if Config.pvoutput.testing else 60.0
        for validate in range(1, verify_retries + 1, 1):
            matches: bool = True
            wait: float = initial_wait if validate == 1 else subsequent_wait
            self.logger.debug(f"{self.__class__.__name__} Waiting for {wait}s before checking that the upload has been processed successfully...")
            await asyncio.sleep(wait)
            try:
                if Config.pvoutput.testing:
                    self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} simulation for testing mode, not sending request to {url=}")
                    if validate > 1:
                        v = re.split(
                            r"[,]",
                            f"{payload['d']},{payload.get('g', 'NaN')},{payload.get('c', 'NaN')},{payload.get('e', 'NaN')},0,{payload.get('pp', 'NaN')},{payload.get('pt', '')},Showers,12,16,{payload.get('ip', 'NaN')},{payload.get('io', 'NaN')},{payload.get('is', 'NaN')},{payload.get('ih', 'NaN')},{payload.get('ep', 'NaN')},{payload.get('eo', 'NaN')},{payload.get('es', 'NaN')},{payload.get('eh', 'NaN')}",
                        )
                    else:
                        self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} simulation FAILED")
                        matches = False
                else:
                    self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} to {url=}...")
                    with requests.get(url, headers=self.request_headers, timeout=10) as response:
                        limit, remaining, at, reset = self.get_response_headers(response)
                        if response.status_code == 200:
                            self.logger.debug(
                                f"{self.__class__.__name__} Verification attempt #{validate} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s) response={response.text}"
                            )
                            v = re.split(r"[,]", response.text)
                        else:
                            self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} FAILED status_code={response.status_code} reason={response.reason}")
                            matches = False
                if matches:
                    result = {}
                    result["d"] = v[0]
                    result["e"] = int(v[3]) if Config.pvoutput.exports and len(v) > 3 and v[3] != "NaN" else None
                    result["pp"] = int(v[5]) if len(v) > 5 and v[5] != "NaN" else None
                    result["ip"] = int(v[10]) if Config.pvoutput.imports and len(v) > 10 and v[10] != "NaN" else None
                    result["io"] = int(v[11]) if Config.pvoutput.imports and len(v) > 11 and v[11] != "NaN" else None
                    result["is"] = int(v[12]) if Config.pvoutput.imports and len(v) > 12 and v[12] != "NaN" else None
                    result["ih"] = int(v[13]) if Config.pvoutput.imports and len(v) > 13 and v[13] != "NaN" else None
                    result["ep"] = int(v[14]) if Config.pvoutput.exports and len(v) > 14 and v[14] != "NaN" else None
                    result["eo"] = int(v[15]) if Config.pvoutput.exports and len(v) > 15 and v[15] != "NaN" else None
                    result["es"] = int(v[16]) if Config.pvoutput.exports and len(v) > 16 and v[16] != "NaN" else None
                    result["eh"] = int(v[17]) if Config.pvoutput.exports and len(v) > 17 and v[17] != "NaN" else None
                    for topic in [t for t in self._service_topics.values() if t.enabled]:
                        if topic._value_key in payload and topic._value_key in result:
                            if payload[topic._value_key] != result[topic._value_key]:
                                self.logger.debug(
                                    f"{self.__class__.__name__} Verification FAILED: payload['{topic._value_key}']={payload[topic._value_key]} != result['{topic._value_key}']={result[topic._value_key]}"
                                )
                                matches = False
                if matches:
                    self.logger.info(f"{self.__class__.__name__} Verification SUCCESS {payload=} downloaded={result} ({response.text})")
                    break
                elif validate < verify_retries:
                    self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} of uploaded {payload=} FAILED, retrying...")
                else:
                    self.logger.error(f"{self.__class__.__name__} Verification FAILED after {validate} attempts for uploaded {payload=} downloaded={result} ({response.text})")
            except requests.exceptions.HTTPError as exc:
                self.logger.error(f"{self.__class__.__name__} HTTP Error: {exc}")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.__class__.__name__} Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.__class__.__name__} Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.__class__.__name__} {exc}")
        return matches

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Callable[[Any, MqttClient, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: MqttClient, *sensors: Any) -> None:
            minute: int = randint(51, 58)
            next: float = await self._next_output_upload(minute)
            last: float = None
            self.logger.info(f"{self.__class__.__name__} Commenced (Updating at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))})")
            while self.online:
                try:
                    now_struct: time.struct_time = time.localtime()
                    now: float = time.mktime(now_struct)
                    if now >= next:
                        interval: int = self._interval if self._interval is not None else 1440
                        payload = {"d": time.strftime("%Y%m%d", now_struct)}
                        async with self.lock(timeout=5):
                            for topic in [t for t in self._service_topics.values() if t.enabled]:
                                topic.add_to_payload(payload, interval, now_struct)
                        tomorrow = await self._next_output_upload(minute)
                        last_update_of_day: bool = time.localtime(tomorrow).tm_yday != now_struct.tm_yday  # Bypass verification except on last upload of the day
                        await self._upload(payload, last_update_of_day)
                        next = tomorrow
                        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))} ({next - now:.2f}s)")
                    elif int(now) % (30 if Config.pvoutput.testing else 900) == 0:
                        for topic in [t for k, t in self._service_topics.items() if t.enabled and k != OutputField.PEAK_POWER]:
                            topic.check_is_updating(5, now_struct)
                        total, at, _ = self._service_topics[OutputField.PEAK_POWER].aggregate(exclude_zero=False)
                        if total is not None and total > 0 and self._latest_peak_at != at:
                            self._latest_peak_at = at
                            self._logger.info(f"{self.__class__.__name__} Peak Power {total:.0f}W recorded at {at}")
                    if last:
                        was = time.localtime(last)
                        if was.tm_yday != now_struct.tm_yday:
                            self.logger.info(f"{self.__class__.__name__} Resetting service topic states to 0.0...")
                            self._previous_payload = None
                            async with self.lock(timeout=5):
                                for topic in self._service_topics.values():
                                    topic.reset()
                    last = now
                    sleep: float = min(next - now, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                    if sleep > 0:
                        await asyncio.sleep(sleep)
                except asyncio.CancelledError:
                    self.logger.info(f"{self.__class__.__name__} Sleep interrupted")
                except asyncio.TimeoutError:
                    self.logger.warning(f"{self.__class__.__name__} Failed to acquire lock within timeout")
                except Exception as e:
                    self.logger.error(f"{self.__class__.__name__}  Sleeping for 60s after exception: {e}")
                    await asyncio.sleep(60)
            self.logger.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")
            return

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.subscribe(mqtt, mqtt_handler)
