from .service import Service, ServiceTopics
from random import randint
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import re
import requests
import time


class PVOutputStatusService(Service):
    def __init__(self, logger: logging.Logger):
        super().__init__("PVOutput Add Status Service", unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        self._service_topics: dict[str, ServiceTopics] = {
            "generation": ServiceTopics(self, True, "generation", logger, value_key="v1", decimals=0),
            "consumption": ServiceTopics(self, True if Config.pvoutput.consumption in ("consumption", "imported") else False, "consumption", logger, value_key="v3", decimals=0),
            "temperature": ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, "temperature", logger, averaged=True, value_key="v5", decimals=1),
            "voltage": ServiceTopics(self, True, "voltage", logger, averaged=True, value_key="v6", decimals=1),
            "v7": ServiceTopics(self, True if Config.pvoutput.extended["v7"] else False, "v7", logger, averaged=True, value_key="v7", requires_donation=True, decimals=0),
            "v8": ServiceTopics(self, True if Config.pvoutput.extended["v8"] else False, "v8", logger, averaged=True, value_key="v8", requires_donation=True, decimals=0),
            "v9": ServiceTopics(self, True if Config.pvoutput.extended["v9"] else False, "v9", logger, averaged=True, value_key="v9", requires_donation=True, decimals=0),
            "v10": ServiceTopics(self, True if Config.pvoutput.extended["v10"] else False, "v10", logger, averaged=True, value_key="v10", requires_donation=True, decimals=0),
            "v11": ServiceTopics(self, True if Config.pvoutput.extended["v11"] else False, "v11", logger, averaged=True, value_key="v11", requires_donation=True, decimals=0),
            "v12": ServiceTopics(self, True if Config.pvoutput.extended["v12"] else False, "v12", logger, averaged=True, value_key="v12", requires_donation=True, decimals=0),
        }

        self._interval: int = None  # Interval in minutes for PVOutput status updates

    def register(self, key: str, topic: str, gain: float = 1.0) -> None:
        self._service_topics[key].register(topic, gain)
        self.logger.debug(f"{self.__class__.__name__} Registered {key} topic: {topic} ({gain=})")

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            donator, wait = self.seconds_until_status_upload()
            self.logger.info(f"{self.__class__.__name__} Commenced (Interval = {self._interval} minutes)")
            while self.online:
                try:
                    if wait <= 0:
                        await update_pvoutput(donator)
                        donator, wait = self.seconds_until_status_upload()
                    sleep = min(wait, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                    wait -= sleep
                    if wait > 0:
                        await asyncio.sleep(sleep)
                except asyncio.CancelledError:
                    self.logger.info(f"{self.__class__.__name__} Sleep interrupted")
                except asyncio.TimeoutError:
                    self.logger.warning(f"{self.__class__.__name__} Failed to acquire lock within timeout")
                except Exception as e:
                    self.logger.error(f"{self.__class__.__name__} {e}")
                    if wait <= 0:
                        wait = 60
            self.logger.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")
            return

        async def update_pvoutput(donator: bool = False) -> None:
            now = time.localtime()
            payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
            async with self.lock(timeout=5):
                for topic in [t for t in self._service_topics.values() if t.enabled and (not t.requires_donation or donator)]:
                    topic.add_to_payload(payload, self._interval, now)
            if ("v1" in payload and payload["v1"]) or ("v3" in payload and payload["v3"]):  # At least one of the values v1, v2, v3 or v4 must be present
                await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
            else:
                self.logger.warning(f"{self.__class__.__name__} No generation or consumption data to upload, skipping...")

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def seconds_until_status_upload(self) -> float:
        """Calculate the seconds until the next PVOutput status upload."""
        url = "https://pvoutput.org/service/r2/getsystem.jsp"
        donator = 0
        if Config.pvoutput.testing:
            if self._interval is None:
                self._interval = 5
                donator = 0
            self.logger.info(f"{self.__class__.__name__} Testing mode, not sending request to {url=} - using default/previous interval of {self._interval} minutes and donator status {donator}")
        else:
            self.logger.debug(f"{self.__class__.__name__} Acquiring Status Interval from PVOutput ({url=})")
            try:
                with requests.get(url, headers=self.request_headers, timeout=10) as response:
                    section = re.split(r"[;]", response.text)
                    interval = int(re.split(r"[,]", section[0])[15])
                    if interval != self._interval:
                        self.logger.info(f"{self.__class__.__name__} Status Interval changed from {self._interval} to {interval} minutes")
                        self._interval = interval
                    donator = int(section[2])
            except Exception as exc:
                if self._interval is None:
                    self._interval = 5  # Default interval in minutes if not set
                self.logger.warning(
                    f"{self.__class__.__name__} Failed to acquire Status Interval and Donator Status from PVOutput: {exc} - using default/previous interval of {self._interval} minutes and donator status {donator}"
                )
        current_time = time.time()  # Current time in seconds since epoch
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // self._interval + 1) * self._interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(0, 15)  # Convert back to seconds with a random offset of up to 15 seconds for variability
        seconds = 60 if Config.pvoutput.testing else float(next_time - current_time)
        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return donator != 0, seconds

    def subscribe(self, mqtt, mqtt_handler) -> None:
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.subscribe(mqtt, mqtt_handler)
