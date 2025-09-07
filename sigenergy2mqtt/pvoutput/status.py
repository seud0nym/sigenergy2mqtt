from .service import Service, ServiceTopics, Topic
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

        self._consumption: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.consumption, "consumption", logger)
        self._generation: ServiceTopics[str, Topic] = ServiceTopics(self, True, "generation", logger)
        self._temperature: ServiceTopics[str, Topic] = ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, "temperature", logger)
        self._voltage: ServiceTopics[str, Topic] = ServiceTopics(self, True, "voltage", logger)

        self._interval: int = None  # Interval in minutes for PVOutput status updates

    # region Registrations

    def register_consumption(self, topic: str, gain: float) -> None:
        self._consumption.register(topic, gain)
        self.logger.debug(f"{self.__class__.__name__} Registered consumption topic: {topic} ({gain=})")

    def register_generation(self, topic: str, gain: float) -> None:
        self._generation.register(topic, gain)
        self.logger.debug(f"{self.__class__.__name__} Registered generation topic: {topic} ({gain=})")

    def register_temperature(self, topic: str) -> None:
        self._temperature.register(topic, 1.0)
        self.logger.debug(f"{self.__class__.__name__} Registered temperature topic: {topic}")

    def register_voltage(self, topic: str) -> None:
        self._voltage.register(topic, 1.0)
        self.logger.debug(f"{self.__class__.__name__} Registered voltage topic: {topic}")

    # endregion

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            wait = self.seconds_until_status_upload()
            self.logger.debug(f"{self.__class__.__name__} Commenced (Interval = {self._interval} minutes)")
            while self.online:
                try:
                    if wait <= 0:
                        await update_pvoutput()
                        wait = self.seconds_until_status_upload()
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
            self.logger.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")
            return

        async def update_pvoutput() -> None:
            now = time.localtime()
            self.logger.debug(f"{self.__class__.__name__} Creating payload...")
            payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
            async with self.lock(timeout=5):
                if self._generation.enabled and self._generation.check_is_updating(self._interval, now):
                    self._generation.sum_into(payload, "v1")
                if self._consumption.enabled and self._consumption.check_is_updating(self._interval, now):
                    self._consumption.sum_into(payload, "v3")
                if self._temperature.enabled and self._temperature.check_is_updating(self._interval, now):
                    self._temperature.average_into(payload, "v5")
                if self._voltage.enabled and self._voltage.check_is_updating(self._interval, now):
                    self._voltage.average_into(payload, "v6")
            if ("v1" in payload and payload["v1"]) or ("v3" in payload and payload["v3"]):  # At least one of the values v1, v2, v3 or v4 must be present
                await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
            else:
                self.logger.warning(f"{self.__class__.__name__} No generation or consumption data to upload, skipping...")

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def seconds_until_status_upload(self) -> float:
        """Calculate the seconds until the next PVOutput status upload."""
        url = "https://pvoutput.org/service/r2/getsystem.jsp"
        if Config.pvoutput.testing:
            if self._interval is None:
                self._interval = 5
            self.logger.info(f"{self.__class__.__name__} Testing mode, not sending request to {url=} - using default/previous interval of {self._interval} minutes")
        else:
            self.logger.debug(f"{self.__class__.__name__} Acquiring Status Interval from PVOutput ({url=})")
            try:
                with requests.get(url, headers=self.request_headers, timeout=10) as response:
                    interval = int(re.split(r"[;,]", response.text)[15])
                    if interval != self._interval:
                        self.logger.info(f"{self.__class__.__name__} Status Interval changed from {self._interval} to {interval} minutes")
                        self._interval = interval
            except Exception as exc:
                if self._interval is None:
                    self._interval = 5  # Default interval in minutes if not set
                self.logger.warning(f"{self.__class__.__name__} Failed to acquire Status Interval from PVOutput: {exc} - using default/previous interval of {self._interval} minutes")
        current_time = time.time()  # Current time in seconds since epoch
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // self._interval + 1) * self._interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(0, 15)  # Convert back to seconds with a random offset of up to 15 seconds for variability
        seconds = 60 if Config.pvoutput.testing else float(next_time - current_time)
        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return seconds

    def subscribe(self, mqtt, mqtt_handler) -> None:
        self._consumption.subscribe(mqtt, mqtt_handler)
        self._generation.subscribe(mqtt, mqtt_handler)
        self._temperature.subscribe(mqtt, mqtt_handler)
        self._voltage.subscribe(mqtt, mqtt_handler)
