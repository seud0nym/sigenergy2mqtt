from .service import Service, ServiceTopics, Topic
from random import randint
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import time


class PVOutputStatusService(Service):
    def __init__(self, plant_index: int, logger: logging.Logger):
        super().__init__("PVOutput Add Status Service", plant_index, unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        self._consumption: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.consumption, "consumption", logger)
        self._generation: ServiceTopics[str, Topic] = ServiceTopics(self, True, "generation", logger)
        self._temperature: ServiceTopics[str, Topic] = ServiceTopics(self, True, "temperature", logger)
        self._voltage: ServiceTopics[str, Topic] = ServiceTopics(self, True, "voltage", logger)

    # region Registrations

    def register_consumption(self, topic: str, gain: float) -> None:
        self._consumption.register(topic, gain)
        self.logger.debug(f"{self.__class__.__name__} - Registered consumption topic: {topic} ({gain=})")

    def register_generation(self, topic: str, gain: float) -> None:
        self._generation.register(topic, gain)
        self.logger.debug(f"{self.__class__.__name__} - Registered generation topic: {topic} ({gain=})")

    def register_temperature(self, topic: str) -> None:
        self._temperature.register(topic, 1.0)
        self.logger.debug(f"{self.__class__.__name__} - Registered temperature topic: {topic}")

    def register_voltage(self, topic: str) -> None:
        self._voltage.register(topic, 1.0)
        self.logger.debug(f"{self.__class__.__name__} - Registered voltage topic: {topic}")

    # endregion

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            self.logger.debug(f"{self.__class__.__name__} - Commenced (Interval = {Config.pvoutput.interval_minutes} minutes)")
            wait = self.seconds_until_status_upload()
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
                    self.logger.info(f"{self.__class__.__name__} - Sleep interrupted")
                except asyncio.TimeoutError:
                    self.logger.warning(f"{self.__class__.__name__} - Failed to acquire lock within timeout")
            self.logger.debug(f"{self.__class__.__name__} - Completed: Flagged as offline ({self.online=})")
            return

        async def update_pvoutput() -> None:
            now = time.localtime()
            self.logger.debug(f"{self.__class__.__name__} - Creating payload...")
            payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
            async with self.lock(timeout=5):
                if self._generation.enabled:
                    payload["v1"], _ = self._generation.sum()
                if self._consumption.enabled:
                    payload["v3"], _ = self._consumption.sum()
                if self._temperature.enabled:
                    payload["v5"], _ = self._temperature.average(1)
                if self._voltage.enabled:
                    payload["v6"], _ = self._voltage.average(1)
            if payload["v1"] or payload["v3"]:  # At least one of the values v1, v2, v3 or v4 must be present
                await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
            else:
                self.logger.warning(f"{self.__class__.__name__} - No generation or consumption data to upload, skipping...")

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def seconds_until_status_upload(self) -> float:
        interval = Config.pvoutput.interval_minutes
        current_time = time.time()  # Current time in seconds since epoch
        minutes = int(current_time // 60)  # Total minutes since epoch
        next_boundary = (minutes // interval + 1) * interval  # Next interval boundary
        next_time = (next_boundary * 60) + randint(0, 15)  # Convert back to seconds with a random offset of up to 15 seconds for variability
        seconds = 60 if Config.pvoutput.testing else float(next_time - current_time)
        self.logger.debug(f"{self.__class__.__name__} - Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return seconds

    def subscribe(self, mqtt, mqtt_handler) -> None:
        self._consumption.subscribe(mqtt, mqtt_handler)
        self._generation.subscribe(mqtt, mqtt_handler)
        self._temperature.subscribe(mqtt, mqtt_handler)
        self._voltage.subscribe(mqtt, mqtt_handler)
