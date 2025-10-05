from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, is_dataclass
from random import randint
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any
import asyncio
import logging
import re
import requests
import time


@dataclass
class Topic:
    topic: str
    gain: float
    state: float = 0.0
    timestamp: time.struct_time = None

    @staticmethod
    def json_decoder(obj):
        if "topic" in obj and "gain" in obj and "state" in obj and "timestamp" in obj:
            topic = Topic(**obj)
            if isinstance(topic.timestamp, list):
                topic.timestamp = time.struct_time(topic.timestamp)
            return topic
        return obj

    @staticmethod
    def json_encoder(obj):
        if is_dataclass(obj):
            return asdict(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class Service(Device):
    _interval: int = None  # Interval in minutes for PVOutput status updates
    _interval_updated: float = None

    def __init__(self, name: str, unique_id: str, model: str, logger: logging.Logger):
        super().__init__(name, -1, unique_id, "sigenergy2mqtt", model)
        self._logger = logger
        self._lock = asyncio.Lock()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def request_headers(self) -> dict[str, str]:
        return {
            "X-Pvoutput-Apikey": Config.pvoutput.api_key,
            "X-Pvoutput-SystemId": Config.pvoutput.system_id,
            "X-Rate-Limit": "1",
        }

    @asynccontextmanager
    async def lock(self, timeout=None):
        acquired: bool = False
        try:
            if timeout is None:
                acquired = await self._lock.acquire()
            else:
                acquired = await asyncio.wait_for(self._lock.acquire(), timeout)
                if not acquired:
                    raise TimeoutError("Failed to acquire lock within the timeout period.")
            yield
        finally:
            if acquired and self._lock.locked():
                self._lock.release()

    # region Device overrides

    def publish_availability(self, mqtt: MqttClient, ha_state, qos=2) -> None:
        pass

    def publish_discovery(self, mqtt: MqttClient, clean=False) -> Any:
        pass

    # endregion

    def get_response_headers(self, response: requests.Response) -> tuple[int, int, float, float]:
        limit = int(response.headers["X-Rate-Limit-Limit"])
        remaining = int(response.headers["X-Rate-Limit-Remaining"])
        at = float(response.headers["X-Rate-Limit-Reset"])
        reset = round(at - time.time())
        return limit, remaining, at, reset

    async def seconds_until_status_upload(self, rand_min: int = 1, rand_max: int = 15) -> float:
        url = "https://pvoutput.org/service/r2/getsystem.jsp"
        donator = 0
        current_time = time.time()  # Current time in seconds since epoch
        async with self._lock:
            if Service._interval is None or Service._interval_updated is None or (Service._interval_updated + (Service._interval * 60)) < current_time:
                if Config.pvoutput.testing:
                    if not hasattr(self, "_interval") or Service._interval is None:
                        Service._interval = 5
                        Service._interval_updated = current_time
                        donator = 1
                    self.logger.info(
                        f"{self.__class__.__name__} Testing mode, not sending request to {url=} - using default/previous interval of {Service._interval} minutes and donator status {donator}"
                    )
                else:
                    self.logger.debug(f"{self.__class__.__name__} Acquiring Status Interval from PVOutput ({url=})")
                    try:
                        with requests.get(url, headers=self.request_headers, timeout=10) as response:
                            limit, remaining, at, reset = self.get_response_headers(response)
                            if response.status_code == 200:
                                section = re.split(r"[;]", response.text)
                                interval = int(re.split(r"[,]", section[0])[15])
                                if interval != Service._interval:
                                    self.logger.info(f"{self.__class__.__name__} Status Interval changed from {Service._interval} to {interval} minutes")
                                    Service._interval = interval
                                Service._interval_updated = current_time
                                donator = int(section[2])
                                self.logger.debug(
                                    f"{self.__class__.__name__} Acquired Status Interval OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                                )
                            else:
                                self.logger.warning(f"{self.__class__.__name__} FAILED to acquire Status Interval status_code={response.status_code} reason={response.reason}")
                    except Exception as exc:
                        if Service._interval is None:
                            Service._interval = 5  # Default interval in minutes if not set
                        self.logger.warning(
                            f"{self.__class__.__name__} Failed to acquire Status Interval and Donator Status from PVOutput: {exc} - using default/previous interval of {Service._interval} minutes and donator status {donator}"
                        )
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // Service._interval + 1) * Service._interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(rand_min, rand_max)  # Convert back to seconds with a random offset for variability
        seconds = 60 if Config.pvoutput.testing else float(next_time - current_time)
        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return seconds, donator != 0

    async def upload_payload(self, url: str, payload: dict[str, any]) -> bool:
        self.logger.info(f"{self.__class__.__name__} Uploading {payload=}")
        uploaded = False
        for i in range(1, 4, 1):
            try:
                if Config.pvoutput.testing:
                    uploaded = True
                    self.logger.info(f"{self.__class__.__name__} Testing mode, not sending upload to {url=}")
                    break
                else:
                    self.logger.debug(f"{self.__class__.__name__} Attempt #{i} to {url=}...")
                    with requests.post(url, headers=self.request_headers, data=payload, timeout=10) as response:
                        limit, remaining, at, reset = self.get_response_headers(response)
                        if response.status_code == 200:
                            uploaded = True
                            self.logger.debug(
                                f"{self.__class__.__name__} Attempt #{i} OKAY status_code={response.status_code} {limit=} {remaining=} reset={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)"
                            )
                            break
                        else:
                            self.logger.warning(f"{self.__class__.__name__} Attempt #{i} FAILED status_code={response.status_code} reason={response.reason}")
                        if int(response.headers["X-Rate-Limit-Remaining"]) < 10:
                            self.logger.warning(f"{self.__class__.__name__} Only {remaining} requests left, sleeping until {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(at))} ({reset}s)")
                            await asyncio.sleep(reset)
                        else:
                            response.raise_for_status()
                            break
            except requests.exceptions.HTTPError as exc:
                self.logger.error(f"{self.__class__.__name__} HTTP Error: {exc}")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.__class__.__name__} Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.__class__.__name__} Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.__class__.__name__} {exc}")
            if i <= 2:
                self.logger.info(f"{self.__class__.__name__} Retrying in 10 seconds")
                await asyncio.sleep(10)
        else:
            self.logger.error(f"{self.__class__.__name__} Failed to upload to {url} after 3 attempts")
        return uploaded


class ServiceTopics(dict[str, Topic]):
    def __init__(
        self,
        service: Service,
        enabled: bool,
        name: str,
        logger: logging.Logger,
        requires_donation: bool = False,
        averaged: bool = True,
        value_key: str = None,
        datetime_key: str = None,
        decimals: int = 1,
        bypass_updating_check: bool = False,
    ):
        self._last_update_warning: float = None
        self._service = service
        self._enabled = enabled
        self._name = name
        self._logger = logger
        self._requires_donation = requires_donation
        self._averaged = averaged
        self._value_key = value_key
        self._datetime_key = datetime_key
        self._decimals = decimals
        self._bypass_updating_check = bypass_updating_check

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        assert isinstance(value, bool), "Enabled must be a boolean value"
        self._enabled = value

    @property
    def requires_donation(self) -> bool:
        return self._requires_donation

    def _average_into(self, payload: dict[str, any], value_key: str, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=True)
        if count > 0 and total is not None:
            value = round(total / count, self._decimals)
            payload[value_key] = int(value) if self._decimals == 0 else value
            if datetime_key is not None:
                payload[datetime_key] = at
                self._logger.debug(
                    f"{self._service.__class__.__name__} Averaged {self._name}: {total} / {count} = {payload[value_key]} into {value_key=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            else:
                self._logger.debug(
                    f"{self._service.__class__.__name__} Averaged {self._name}: {total} / {count} = {payload[value_key]} into {value_key=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key in payload:
                del payload[value_key]
                self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key}' from payload because {count=} and {total=}")
            return False

    def _sum_into(self, payload: dict[str, any], value_key: str, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=False)
        if count > 0 and total is not None:
            payload[value_key] = int(total) if self._decimals == 0 else round(total, self._decimals)
            if datetime_key is not None:
                payload[datetime_key] = at
                self._logger.debug(
                    f"{self._service.__class__.__name__} Summed {self._name}: {total} into {value_key=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            else:
                self._logger.debug(
                    f"{self._service.__class__.__name__} Summed {self._name}: {total} into {value_key=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key in payload:
                del payload[value_key]
                self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key}' from payload because {count=} and {total=}")
            return False

    def add_to_payload(self, payload: dict[str, any], interval_minutes: int, now: time.struct_time) -> bool:
        if self._bypass_updating_check or self.check_is_updating(interval_minutes, now):
            if self._averaged:
                return self._average_into(payload, self._value_key, self._datetime_key)
            else:
                return self._sum_into(payload, self._value_key, self._datetime_key)
        else:
            return False

    def aggregate(self, exclude_zero: bool) -> tuple[float, str, int]:
        if not self.enabled:
            return None, None, 0
        if len(self) == 0:
            self._logger.debug(f"{self._service.__class__.__name__} No {self._name} topics registered, skipping aggregation")
            return None, None, 0
        at: str = "00:00"
        count: int = 0
        total: float = 0.0
        for value in self.values():
            if value.timestamp is not None and (not exclude_zero or value.state > 0.0):
                total += value.state * value.gain
                at = time.strftime("%H:%M", value.timestamp)
                count += 1
        if count > 0:
            return total, at, count
        else:
            return None, None, count

    def check_is_updating(self, interval_minutes: int, now: time.struct_time) -> bool:
        if self.enabled:
            interval_seconds = interval_minutes * 60
            topics = 0
            updated = 0
            for value in self.values():
                topics += 1
                if value.timestamp is not None:
                    seconds = int(time.mktime(now) - time.mktime(value.timestamp))
                    minutes = int(seconds / 60.0)
                    if seconds < interval_seconds:
                        updated += 1
                    else:
                        if self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600:
                            self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has not been updated for {minutes}m???")
                            self._last_update_warning = time.time()
                elif self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600:
                    self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has never been updated???")
                    self._last_update_warning = time.time()
            return topics == updated
        else:
            return False

    def register(self, topic: str, gain: float) -> bool:
        if self.enabled:
            if topic is None or topic == "" or topic.isspace():
                self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for empty topic")
            elif topic not in self:
                self[topic] = Topic(topic, gain)
                self._logger.debug(f"{self._service.__class__.__name__} Registered {self._name} topic: {topic} ({'averaged' if self._averaged else 'summed'} {gain=})")
        else:
            self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for '{topic}' because {self._name} uploading is disabled")

    def reset(self) -> None:
        for value in self.values():
            value.state = 0.0
            value.timestamp = time.localtime()

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in self.keys():
            if self.enabled:
                result = mqtt_handler.register(mqtt, topic, self.update)
                self._logger.debug(f"{self._service.__class__.__name__} Subscribed to topic '{topic}' to record {self._name} ({result=})")
            else:
                self._logger.debug(f"{self._service.__class__.__name__} Not subscribing to topic '{topic}' because {self._name} uploading is disabled")

    async def update(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str, handler: MqttHandler) -> bool:
        if self.enabled:
            if Config.pvoutput.update_debug_logging:
                self._logger.debug(f"{self._service.__class__.__name__} Updating {self._name} from '{topic}' {value=}")
            state = value if isinstance(value, float) else float(value)
            if state >= 0.0:
                async with self._service.lock(timeout=1):
                    self[topic].state = state
                    self[topic].timestamp = time.localtime()
            return True
        else:
            return False
