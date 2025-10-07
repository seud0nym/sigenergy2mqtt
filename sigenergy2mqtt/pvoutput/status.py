from .service_topics import ServiceTopics
from .service import Service
from sigenergy2mqtt.config import Config, StatusField
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import time


class PVOutputStatusService(Service):
    def __init__(self, logger: logging.Logger):
        super().__init__("PVOutput Add Status Service", unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        self._previous_payload: dict = None
        self._service_topics: dict[str, ServiceTopics] = {
            StatusField.GENERATION: ServiceTopics(self, True, "generation", logger, value_key=StatusField.GENERATION, averaged=False),
            StatusField.CONSUMPTION: ServiceTopics(self, Config.pvoutput.consumption_enabled, "consumption", logger, averaged=False, value_key=StatusField.CONSUMPTION),
            StatusField.TEMPERATURE: ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, "temperature", logger, value_key=StatusField.TEMPERATURE, decimals=1),
            StatusField.VOLTAGE: ServiceTopics(self, True, "voltage", logger, value_key=StatusField.VOLTAGE, decimals=1),
            StatusField.V7: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V7.value] else False, "v7", logger, value_key=StatusField.V7, requires_donation=True),
            StatusField.V8: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V8.value] else False, "v8", logger, value_key=StatusField.V8, requires_donation=True),
            StatusField.V9: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V9.value] else False, "v9", logger, value_key=StatusField.V9, requires_donation=True),
            StatusField.V10: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V10.value] else False, "v10", logger, value_key=StatusField.V10, requires_donation=True),
            StatusField.V11: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V11.value] else False, "v11", logger, value_key=StatusField.V11, requires_donation=True),
            StatusField.V12: ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V12.value] else False, "v12", logger, value_key=StatusField.V12, requires_donation=True),
        }

    def register(self, key: StatusField | str, topic: str, gain: float = 1.0) -> None:
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
                        if ("v1" in payload and payload["v1"]) or (
                            "v3" in payload and payload["v3"] and Config.pvoutput.consumption_enabled
                        ):  # At least one of the values v1, v2, v3 or v4 must be present
                            await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
                        else:
                            self.logger.warning(f"{self.__class__.__name__} No generation{' or consumption data' if Config.pvoutput.consumption_enabled else ''} to upload, skipping...")
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
