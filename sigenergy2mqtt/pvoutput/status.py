from .service import Service, ServiceTopics
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import time


class PVOutputStatusService(Service):
    def __init__(self, logger: logging.Logger):
        super().__init__("PVOutput Add Status Service", unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        self._previous_payload: dict = None
        self._service_topics: dict[str, ServiceTopics] = {
            "generation": ServiceTopics(self, True, "generation", logger, value_key="v1", averaged=False, decimals=0),
            "consumption": ServiceTopics(self, True if Config.pvoutput.consumption in ("consumption", "imported") else False, "consumption", logger, averaged=False, value_key="v3", decimals=0),
            "temperature": ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, "temperature", logger, value_key="v5", decimals=1),
            "voltage": ServiceTopics(self, True, "voltage", logger, value_key="v6", decimals=1),
            "v7": ServiceTopics(self, True if Config.pvoutput.extended["v7"] else False, "v7", logger, value_key="v7", requires_donation=True, decimals=0),
            "v8": ServiceTopics(self, True if Config.pvoutput.extended["v8"] else False, "v8", logger, value_key="v8", requires_donation=True, decimals=0),
            "v9": ServiceTopics(self, True if Config.pvoutput.extended["v9"] else False, "v9", logger, value_key="v9", requires_donation=True, decimals=0),
            "v10": ServiceTopics(self, True if Config.pvoutput.extended["v10"] else False, "v10", logger, value_key="v10", requires_donation=True, decimals=0),
            "v11": ServiceTopics(self, True if Config.pvoutput.extended["v11"] else False, "v11", logger, value_key="v11", requires_donation=True, decimals=0),
            "v12": ServiceTopics(self, True if Config.pvoutput.extended["v12"] else False, "v12", logger, value_key="v12", requires_donation=True, decimals=0),
        }

    def register(self, key: str, topic: str, gain: float = 1.0) -> None:
        self._service_topics[key].register(topic, gain)

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            wait, donator = await self.seconds_until_status_upload()
            self.logger.info(f"{self.__class__.__name__} Commenced (Interval = {self._interval} minutes)")
            while self.online:
                try:
                    if wait <= 0:
                        now = time.localtime()
                        payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
                        async with self.lock(timeout=5):
                            for topic in [t for t in self._service_topics.values() if t.enabled and (not t.requires_donation or donator)]:
                                topic.add_to_payload(payload, self._interval, now)
                        if ("v1" in payload and payload["v1"]) or ("v3" in payload and payload["v3"]):  # At least one of the values v1, v2, v3 or v4 must be present
                            await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
                        else:
                            self.logger.warning(f"{self.__class__.__name__} No generation or consumption data to upload, skipping...")
                        wait, donator = await self.seconds_until_status_upload()
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

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    def subscribe(self, mqtt, mqtt_handler) -> None:
        for topic in [t for t in self._service_topics.values() if t.enabled]:
            topic.subscribe(mqtt, mqtt_handler)
