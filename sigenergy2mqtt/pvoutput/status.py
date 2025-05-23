from dataclasses import dataclass
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import requests
import time


@dataclass
class Topic:
    topic: str
    gain: float
    state: float = 0


class PVOutputStatusService(Device):
    def __init__(self, plant_index: int, logger: logging.Logger):
        super().__init__("PVOutput Add Status service", plant_index, "pvoutput_status", "sigenergy2mqtt", "pvoutput.Status")
        self._logger = logger
        self._consumption: dict[str, Topic] = dict()
        self._generation: dict[str, Topic] = dict()
        self._lock = asyncio.Lock()

    def publish_availability(self, mqtt, ha_state, qos=2):
        pass

    def publish_discovery(self, mqtt, force_publish=True, clean=False):
        pass

    def register_consumption(self, topic: str, gain: float) -> None:
        if Config.pvoutput.consumption:
            self._consumption[topic] = Topic(topic, gain)
        else:
            self._logger.info(f"PVOutput Add Status Service - Ignored subscription request for '{topic}' because {Config.pvoutput.consumption=}")

    def register_generation(self, topic: str, gain: float) -> None:
        self._generation[topic] = Topic(topic, gain)

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            wait = Config.pvoutput.interval_minutes * 60
            self._logger.debug(f"PVOutput Add Status Service commenced (Interval = {wait} seconds)")
            while self.online:
                try:
                    if wait <= 0:
                        await update_pvoutput()
                        wait = Config.pvoutput.interval_minutes * 60
                    sleep = min(wait, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                    wait -= sleep
                    if wait > 0:
                        await asyncio.sleep(sleep)
                except asyncio.CancelledError:
                    self._logger.debug("PVOutput Add Status Service sleep interrupted")
            self._logger.debug(f"PVOutput Add Status Service completed - flagged as offline ({self.online=})")
            return

        async def update_pvoutput():
            headers = {
                "X-Pvoutput-Apikey": Config.pvoutput.api_key,
                "X-Pvoutput-SystemId": Config.pvoutput.system_id,
                "X-Rate-Limit": "1",
            }

            now = time.localtime()
            payload = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now), "c1": 1}
            async with self._lock:
                payload["v1"] = 0
                for value in self._generation.values():
                    payload["v1"] += round(value.state * value.gain)
                if Config.pvoutput.consumption:
                    payload["v3"] = 0
                    for value in self._consumption.values():
                        payload["v3"] += round(value.state * value.gain)

            for i in range(3):
                try:
                    self._logger.debug(f"PVOutput Add Status Service - Attempt #{i} with {payload=}")
                    if Config.pvoutput.testing:
                        self._logger.debug("PVOutput Add Status Service - Testing mode, not sending request")
                        break
                    else:
                        with requests.post("https://pvoutput.org/service/r2/addstatus.jsp", headers=headers, data=payload, timeout=10) as response:
                            self._logger.debug(f"PVOutput Add Status Service - Attempt #{i} {response.status_code=} {response.headers=}")
                            reset = round(float(response.headers["X-Rate-Limit-Reset"]) - time.time())
                            if int(response.headers["X-Rate-Limit-Remaining"]) < 10:
                                self._logger.warning(f"PVOutput Add Status Service - Only {response.headers['X-Rate-Limit-Remaining']} requests left, reset after {reset} seconds")
                            if response.status_code == 403:
                                self._logger.warning(f"PVOutput Add Status Service - Forbidden: {response.reason}")
                                asyncio.sleep(reset + 1)
                            else:
                                response.raise_for_status()
                                break
                except requests.exceptions.HTTPError as exc:
                    self._logger.error(f"PVOutput Add Status Service - HTTP Error: {exc}")
                except requests.exceptions.ConnectionError as exc:
                    self._logger.error(f"PVOutput Add Status Service - Error Connecting: {exc}")
                except requests.exceptions.Timeout as exc:
                    self._logger.error(f"PVOutput Add Status Service - Timeout Error: {exc}")
                except requests.exceptions.RequestException as exc:
                    self._logger.error(f"PVOutput Add Status Service - {exc}")
                asyncio.sleep(5)
            else:
                self._logger.error(f"PVOutput Add Status Service - Failed to call PVOutput API after {i} attempts")

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    async def set_consumption(self, modbus: any, mqtt: any, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.consumption:
            if Config.sensor_debug_logging:
                self._logger.debug(f"PVOutput Add Status Service - set_consumption from '{topic}' {value=}")
            async with self._lock:
                self._consumption[topic].state = value if isinstance(value, float) else float(value)
        elif Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Status Service - Ignoring set_consumption from '{topic}' {value=} because {Config.pvoutput.consumption=}")

    async def set_generation(self, modbus: any, mqtt: any, value: float | int | str, topic: str) -> bool:
        if Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Status Service - set_generation from '{topic}' {value=}")
        async with self._lock:
            self._generation[topic].state = value if isinstance(value, float) else float(value)

    def subscribe(self, mqtt, mqtt_handler):
        for topic in self._consumption.keys():
            mqtt_handler.register(mqtt, topic, self.set_consumption)
            self._logger.debug(f"PVOutput Add Status Service subscribed to topic '{topic}' to record consumption")
        for topic in self._generation.keys():
            mqtt_handler.register(mqtt, topic, self.set_generation)
            self._logger.debug(f"PVOutput Add Status Service subscribed to topic '{topic}' to record generation")
