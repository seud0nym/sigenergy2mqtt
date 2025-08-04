from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, is_dataclass
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any
import asyncio
import logging
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

    async def upload_payload(self, url: str, payload: dict[str, any]) -> None:
        self.logger.info(f"{self.__class__.__name__} Uploading {payload=}")
        for i in range(1, 4, 1):
            try:
                if Config.pvoutput.testing:
                    self.logger.info(f"{self.__class__.__name__} Testing mode, not sending upload to {url=}")
                    break
                else:
                    self.logger.debug(f"{self.__class__.__name__} Attempt #{i} to {url=}...")
                    with requests.post(url, headers=self.request_headers, data=payload, timeout=10) as response:
                        limit = int(response.headers["X-Rate-Limit-Limit"])
                        remaining = int(response.headers["X-Rate-Limit-Remaining"])
                        at = float(response.headers["X-Rate-Limit-Reset"])
                        reset = round(at - time.time())
                        if response.status_code == 200:
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


class ServiceTopics(dict[str, Topic]):
    def __init__(self, service: Service, enabled: bool, name: str, logger: logging.Logger):
        self._service = service
        self._enabled = enabled
        self._name = name
        self._logger = logger
        self._last_update_warning: float = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        assert isinstance(value, bool), "Enabled must be a boolean value"
        self._enabled = value

    def check_is_updating(self, interval_minutes: int, now: time.struct_time) -> None:
        if self.enabled:
            for value in self.values():
                if value.timestamp is not None:
                    seconds = int(time.mktime(now) - time.mktime(value.timestamp))
                    minutes = int(seconds / 60.0)
                    if minutes > interval_minutes and (self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600):
                        self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has not been updated for {minutes}m???")
                        self._last_update_warning = time.time()
                    else:
                        self._logger.debug(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} last updated {seconds}s ago")
                elif self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600:
                    self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has never been updated???")
                    self._last_update_warning = time.time()

    def register(self, topic: str, gain: float) -> bool:
        if self.enabled:
            if topic is None or topic == "" or topic.isspace():
                self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for empty topic")
            elif topic not in self:
                self[topic] = Topic(topic, gain)
        else:
            self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for '{topic}' because {self._name} uploading is disabled")

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in self.keys():
            if self.enabled:
                result = mqtt_handler.register(mqtt, topic, self.update)
                self._logger.debug(f"{self._service.__class__.__name__} Subscribed to topic '{topic}' to record {self._name} ({result=})")
            else:
                self._logger.debug(f"{self._service.__class__.__name__} Not subscribing to topic '{topic}' because {self._name} uploading is disabled")

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
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(
                f"{self._service.__class__.__name__} Aggregated {self._name}: {total=} {count=} {at=} ({[(v.state, time.strftime('%H:%M', value.timestamp) if value.timestamp else None) for v in self.values()]})"
            )
        if count > 0:
            return total, at, count
        else:
            return None, None, count

    def average_into(self, payload: dict[str, any], value_key: str, datetime_key: str = None, decimals: int = 1) -> bool:
        total, at, count = self.aggregate(exclude_zero=True)
        if count > 0 and total is not None:
            payload[value_key] = round(total / count, decimals)
            if datetime_key is not None:
                payload[datetime_key] = at
            return True
        else:
            if value_key in payload:
                del payload[value_key]
            self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key}' from payload because {count=} and {total=}")
            return False

    def sum_into(self, payload: dict[str, any], value_key: str, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=False)
        if count > 0 and total is not None:
            payload[value_key] = round(total)
            if datetime_key is not None:
                payload[datetime_key] = at
            return True
        else:
            if value_key in payload:
                del payload[value_key]
            self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key}' from payload because {count=} and {total=}")
            return False

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
