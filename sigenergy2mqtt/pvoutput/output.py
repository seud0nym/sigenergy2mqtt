from .service import Service
from .service_topics import Calculation, ServiceTopics
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

        self._latest_peak_at: str = None
        self._previous_payload: dict = None
        self._service_topics: dict[str, ServiceTopics] = {
            OutputField.GENERATION: ServiceTopics(self, False, logger, value_key=OutputField.GENERATION),
            OutputField.EXPORTS: ServiceTopics(self, Config.pvoutput.exports, logger, value_key=OutputField.EXPORTS),
            OutputField.PEAK_POWER: ServiceTopics(self, True, logger, value_key=OutputField.PEAK_POWER, datetime_key="pt", calculation=Calculation.SUM | Calculation.PEAK),
            OutputField.IMPORTS: ServiceTopics(self, Config.pvoutput.imports, logger, value_key=OutputField.IMPORTS),
            OutputField.CONSUMPTION: ServiceTopics(self, Config.pvoutput.consumption_enabled, logger, value_key=OutputField.CONSUMPTION),
        }
        for field, topic_list in topics.items():
            if field in self._service_topics:
                for topic in topic_list:
                    self._service_topics[field].register(topic)
            else:
                self.logger.warning(f"{self.__class__.__name__} IGNORED unrecognized {field} with topic {topic.topic}")

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
            next = now + interval
        else:
            if Config.pvoutput.testing:
                next = now + 60
            else:
                next = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, Config.pvoutput.output_hour, minute, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
                if next <= now:
                    today = datetime.fromtimestamp(next)
                    tomorrow = today + timedelta(days=1, seconds=randint(-15, 15))  # Add a random offset of up to 15 seconds for variability
                    next = tomorrow.timestamp()
            self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))} ({next - now}s)")
        return next

    async def _upload_and_verify(self, payload: dict[str, int | str], bypass_verify: bool = False) -> None:
        for _ in range(1, 6, 1):
            if await self.upload_payload("https://pvoutput.org/service/r2/addoutput.jsp", payload):
                if bypass_verify:
                    break
                else:
                    self.logger.debug(f"{self.__class__.__name__} Verifying uploaded {payload=}")
                    url = f"https://pvoutput.org/service/r2/getoutput.jsp?df={payload['d']}&dt={payload['d']}"
                    for validate in range(1, 6, 1):
                        matches = True
                        self.logger.debug(f"{self.__class__.__name__} Waiting for 60s before checking that the upload has been processed successfully...")
                        await asyncio.sleep(0.1 if Config.pvoutput.testing else 60)
                        try:
                            if Config.pvoutput.testing:
                                self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} simulation for testing mode, not sending request to {url=}")
                                if validate > 1:
                                    v = re.split(
                                        r"[,]",
                                        f"{payload['d']},{payload.get('g', 'NaN')},{payload.get('c', 'NaN')},{payload.get('e', 'NaN')},0,{payload.get('pp', 'NaN')},{payload.get('pt', '')},Showers,12,16,{payload.get('ip', 'NaN')},0,0,0",
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
                                result["g"] = int(v[1]) if len(v) > 1 and v[1] != "NaN" else None
                                result["e"] = int(v[3]) if len(v) > 3 and v[3] != "NaN" else None
                                result["pp"] = int(v[5]) if len(v) > 5 and v[5] != "NaN" else None
                                result["ip"] = int(v[10]) if len(v) > 10 and v[10] != "NaN" else None
                                for topic in [t for t in self._service_topics.values() if t.enabled]:
                                    if topic._value_key in payload and topic._value_key in result:
                                        if payload[topic._value_key] == result[topic._value_key]:
                                            self.logger.debug(
                                                f"{self.__class__.__name__} Verified payload['{topic._value_key}']={payload[topic._value_key]} == result['{topic._value_key}']={result[topic._value_key]}"
                                            )
                                        else:
                                            self.logger.debug(
                                                f"{self.__class__.__name__} Verification failure: payload['{topic._value_key}']={payload[topic._value_key]} != result['{topic._value_key}']={result[topic._value_key]}"
                                            )
                                            matches = False
                                            break
                            if matches:
                                self.logger.debug(f"{self.__class__.__name__} Verified uploaded {payload=}")
                                break
                            elif validate < 5:
                                self.logger.debug(f"{self.__class__.__name__} Verification attempt #{validate} FAILED, retrying...")
                        except requests.exceptions.HTTPError as exc:
                            self.logger.error(f"{self.__class__.__name__} HTTP Error: {exc}")
                        except requests.exceptions.ConnectionError as exc:
                            self.logger.error(f"{self.__class__.__name__} Error Connecting: {exc}")
                        except requests.exceptions.Timeout as exc:
                            self.logger.error(f"{self.__class__.__name__} Timeout Error: {exc}")
                        except Exception as exc:
                            self.logger.error(f"{self.__class__.__name__} {exc}")
                    if matches:
                        break

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
                        bypass_verify: bool = time.localtime(tomorrow).tm_yday == now_struct.tm_yday  # Bypass verification except on last upload of the day
                        if self._is_payload_changed(payload) or not bypass_verify:  # Only upload if changed or verification required
                            await self._upload_and_verify(payload, bypass_verify)
                            if Config.pvoutput.output_hour == -1:
                                self._previous_payload = payload
                        else:
                            self.logger.info(f"{self.__class__.__name__} SKIPPED uploading {payload=} - Unchanged from last update")
                        next = tomorrow
                    elif int(now) % (30 if Config.pvoutput.testing else 900) == 0:
                        for topic in [t for k, t in self._service_topics.items() if t.enabled and k != OutputField.PEAK_POWER]:
                            topic.check_is_updating(5, now_struct)
                        total, at, _ = self._service_topics[OutputField.PEAK_POWER].aggregate(exclude_zero=False)
                        if total is not None and total > 0 and self._latest_peak_at != at:
                            self._latest_peak_at = at
                            self._logger.info(f"{self.__class__.__name__} Peak Power {total:.0f}W recorded at {at}")
                        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))} ({next - now}s)")
                    if last:
                        was = time.localtime(last)
                        if was.tm_yday != now_struct.tm_yday:
                            self.logger.info(f"{self.__class__.__name__} Resetting service topic states to 0.0...")
                            self._previous_payload = None
                            async with self.lock(timeout=5):
                                for topic in self._service_topics.values():
                                    topic.reset()
                                self._persistent_state_file.unlink(missing_ok=True)
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
