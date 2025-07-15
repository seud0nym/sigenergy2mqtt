from .service import Service, ServiceTopics, Topic
from datetime import datetime, timedelta
from pathlib import Path
from random import randint
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import json
import logging
import time


class PVOutputStatusService(Service):
    def __init__(self, plant_index: int, logger: logging.Logger):
        super().__init__("PVOutput Add Status Service", plant_index, unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        self._consumption: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.consumption, "consumption", logger)
        self._generation: ServiceTopics[str, Topic] = ServiceTopics(self, True, "generation", logger)
        self._temperature: ServiceTopics[str, Topic] = ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, "temperature", logger)
        self._voltage: ServiceTopics[str, Topic] = ServiceTopics(self, True, "voltage", logger)

        self._previous_payload: dict[str, any] = {}
        self._persistent_state_file = Path(Config.persistent_state_path, f"pvoutput_status_{plant_index}.payload")
        if self._persistent_state_file.is_file():
            fmt = time.localtime(self._persistent_state_file.stat().st_mtime)
            now = time.localtime()
            if fmt.tm_year == now.tm_year and fmt.tm_mon == now.tm_mon and fmt.tm_mday == now.tm_mday:
                with self._persistent_state_file.open("r") as f:
                    try:
                        self._previous_payload = json.load(f)
                        self.logger.info(f"{self.__class__.__name__} - Loaded {self._persistent_state_file}")
                    except ValueError as error:
                        self.logger.warning(f"{self.__class__.__name__} - Failed to read {self._persistent_state_file}: {error}")
            else:
                self.logger.info(f"{self.__class__.__name__} - Ignored {self._persistent_state_file} because it is stale ({fmt})")
                self._persistent_state_file.unlink(missing_ok=True)
        else:
            self.logger.debug(f"{self.__class__.__name__} - Persistent state file {self._persistent_state_file} not found")

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
            if "t" in self._previous_payload:
                t1 = datetime.strptime(self._previous_payload["t"], "%H:%M")
                t2 = datetime.strptime(payload["t"], "%H:%M")
                if t2 < t1:
                    t2 += timedelta(days=1)
                delta = t2 - t1
                hours = delta.total_seconds() / 3600
            else:
                hours = None
            async with self.lock(timeout=5):
                if self._generation.enabled:
                    payload["v1"], _ = self._generation.sum()
                    if hours and "v1" in self._previous_payload:
                        payload["v2"] = round((payload["v1"] - self._previous_payload["v1"]) / hours)
                if self._consumption.enabled:
                    payload["v3"], _ = self._consumption.sum()
                    if hours and "v3" in self._previous_payload:
                        payload["v4"] = round((payload["v3"] - self._previous_payload["v3"]) / hours)
                if self._temperature.enabled:
                    payload["v5"], _ = self._temperature.average(1)
                if self._voltage.enabled:
                    payload["v6"], _ = self._voltage.average(1)
            if payload["v1"] or payload["v3"]:  # At least one of the values v1, v2, v3 or v4 must be present
                await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
                self._previous_payload = payload
                with self._persistent_state_file.open("w") as f:
                    json.dump(payload, f)
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
