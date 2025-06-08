from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timedelta
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
    def __init__(self, name: str, plant_index: int, unique_id: str, model: str, logger: logging.Logger):
        super().__init__(name, plant_index, unique_id, "sigenergy2mqtt", model)
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

    def publish_discovery(self, mqtt: MqttClient, force_publish=True, clean=False) -> Any:
        pass

    # endregion

    def seconds_until_daily_output_upload(self) -> float:
        t = time.localtime()
        now = time.mktime(t)
        next = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, Config.pvoutput.output_hour, 45, 0, t.tm_wday, t.tm_yday, t.tm_isdst))
        if next <= now:
            today = datetime.fromtimestamp(next)
            tomorrow = today + timedelta(days=1)
            next = tomorrow.timestamp()
        seconds = 60 if Config.pvoutput.testing else next - now
        self.logger.debug(f"{self.__class__.__name__} - Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))} ({seconds}s)")
        return seconds

    def seconds_until_status_upload(self) -> float:
        seconds = 60 if Config.pvoutput.testing else float(Config.pvoutput.interval_minutes * 60)
        self.logger.debug(f"{self.__class__.__name__} - Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + seconds))} ({seconds}s)")
        return seconds        

    async def upload_payload(self, url: str, payload: dict[str, any]) -> None:
        for i in range(1, 4, 1):
            try:
                self.logger.debug(f"{self.__class__.__name__} - Attempt #{i} to {url} with {payload=}")
                if Config.pvoutput.testing:
                    self.logger.debug(f"{self.__class__.__name__} - Attempt #{i} Testing mode, not sending request")
                    break
                else:
                    with requests.post(url, headers=self.request_headers, data=payload, timeout=10) as response:
                        if response.status_code == 200:
                            self.logger.debug(f"{self.__class__.__name__} - Attempt #{i} OKAY {response.status_code=} {response.headers=}")
                            break
                        else:
                            self.logger.warning(f"{self.__class__.__name__} - Attempt #{i} FAILED {response.status_code=} {response.reason=}")
                        reset = round(float(response.headers["X-Rate-Limit-Reset"]) - time.time())
                        if int(response.headers["X-Rate-Limit-Remaining"]) < 10:
                            self.logger.warning(f"{self.__class__.__name__} - Only {response.headers['X-Rate-Limit-Remaining']} requests left, reset after {reset} seconds")
                            await asyncio.sleep(reset)
                        else:
                            response.raise_for_status()
                            break
            except requests.exceptions.HTTPError as exc:
                self.logger.error(f"{self.__class__.__name__} - HTTP Error: {exc}")
            except requests.exceptions.ConnectionError as exc:
                self.logger.error(f"{self.__class__.__name__} - Error Connecting: {exc}")
            except requests.exceptions.Timeout as exc:
                self.logger.error(f"{self.__class__.__name__} - Timeout Error: {exc}")
            except Exception as exc:
                self.logger.error(f"{self.__class__.__name__} - {exc}")
            if i <= 2:
                self.logger.info(f"{self.__class__.__name__} - Retrying in 10 seconds")
                await asyncio.sleep(10)
        else:
            self.logger.error(f"{self.__class__.__name__} - Failed to upload to {url} after 3 attempts")


class ServiceTopics(dict):
    def __init__(self, service: Service, enabled: bool, name: str, logger: logging.Logger):
        self._service = service
        self._enabled = enabled
        self._name = name
        self._logger = logger

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        assert value is bool
        self._enabled = value

    def register(self, topic: str, gain: float) -> bool:
        if self._enabled:
            if topic not in self:
                self[topic] = Topic(topic, gain)
        else:
            self._logger.debug(f"{self._service.__class__.__name__} - Ignored subscription request for '{topic}' because {self._name} uploading is disabled")

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in self.keys():
            if self._enabled:
                mqtt_handler.register(mqtt, topic, self.update)
                self._logger.debug(f"{self._service.__class__.__name__} - Subscribed to topic '{topic}' to record {self._name}")
            else:
                self._logger.debug(f"{self._service.__class__.__name__} - Not subscribing to topic '{topic}' because {self._name} uploading is disabled")

    def sum(self) -> tuple[float, str]:
        total: float = 0.0
        at: str = "00:00"
        for value in self.values():
            total += round(value.state * value.gain)
            at = time.strftime("%H:%M", value.timestamp)
        return total, at

    async def update(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if self._enabled:
            if Config.pvoutput.update_debug_logging:
                self._logger.debug(f"{self._service.__class__.__name__} - Updating {self._name} from '{topic}' {value=}")
            async with self._service.lock(timeout=1):
                self[topic].state = value if isinstance(value, float) else float(value)
                self[topic].timestamp = time.localtime()
            return True
        else:
            return False
