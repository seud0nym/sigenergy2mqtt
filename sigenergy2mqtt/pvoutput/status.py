from .service import Service, ServiceTopics, Topic
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

    # region Registrations

    def register_consumption(self, topic: str, gain: float) -> None:
        self._consumption.register(topic, gain)

    def register_generation(self, topic: str, gain: float) -> None:
        self._generation.register(topic, gain)

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

        async def update_pvoutput():
            self.logger.debug(f"{self.__class__.__name__} - Creating payload...")
            now = time.localtime()
            payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
            async with self.lock(timeout=5):
                payload["v1"], _ = self._generation.sum()
                if Config.pvoutput.consumption:
                    payload["v3"], _ = self._consumption.sum()
            await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def subscribe(self, mqtt, mqtt_handler):
        self._consumption.subscribe(mqtt, mqtt_handler)
        self._generation.subscribe(mqtt, mqtt_handler)
