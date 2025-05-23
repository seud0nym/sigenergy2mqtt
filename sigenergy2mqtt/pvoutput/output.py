from dataclasses import dataclass
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import MqttClient
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
    timestamp: time.struct_time = None


class PVOutputOutputService(Device):
    def __init__(self, plant_index: int, logger: logging.Logger):
        super().__init__("PVOutput Add Output service", plant_index, "pvoutput_output", "sigenergy2mqtt", "pvoutput.Output")
        self._logger = logger
        self._consumption: dict[str, Topic] = dict()
        self._exports: dict[str, Topic] = dict()
        self._generation: dict[str, Topic] = dict()
        self._power: dict[str, Topic] = dict()
        self._lock = asyncio.Lock()

    def publish_availability(self, mqtt: MqttClient, ha_state, qos=2):
        pass

    def publish_discovery(self, mqtt: MqttClient, force_publish=True, clean=False):
        pass

    def register_consumption(self, topic: str, gain: float) -> None:
        if Config.pvoutput.consumption:
            self._consumption[topic] = Topic(topic, gain)
        else:
            self._logger.info(f"PVOutput Add Output Service - Ignored subscription request for '{topic}' because {Config.pvoutput.consumption=}")

    def register_exports(self, topic: str, gain: float) -> None:
        if Config.pvoutput.exports:
            self._exports[topic] = Topic(topic, gain)
        else:
            self._logger.info(f"PVOutput Add Output Service - Ignored subscription request for '{topic}' because {Config.pvoutput.exports=}")

    def register_generation(self, topic: str, gain: float) -> None:
        if Config.pvoutput.peak_power or Config.pvoutput.consumption or Config.pvoutput.exports:
            self._generation[topic] = Topic(topic, gain)
        else:
            self._logger.info(f"PVOutput Add Output Service - Ignored subscription request for '{topic}' because {Config.pvoutput.consumption=} {Config.pvoutput.exports=} {Config.pvoutput.peak_power=}")

    def register_power(self, topic: str, gain: float) -> None:
        if Config.pvoutput.peak_power:
            self._power[topic] = Topic(topic, gain)
            if len(self._power) > 1:
                Config.pvoutput.peak_power = False
                self._logger.warning("PVOutput Add Output Service - DISABLED peak-power reporting: Cannot determine peak power from multiple systems")
        else:
            self._logger.info(f"PVOutput Add Output Service - Ignored subscription request for '{topic}' because {Config.pvoutput.peak_power=}")

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Callable[[Any, MqttClient, Iterable[Any]], Awaitable[None]]]:
        def seconds_until_publish():
            current_time = time.localtime()
            publish_time = time.mktime(
                (current_time.tm_year, current_time.tm_mon, current_time.tm_mday, Config.pvoutput.output_hour, 45, 0, current_time.tm_wday, current_time.tm_yday, current_time.tm_isdst)
            )
            return publish_time - time.mktime(current_time)

        async def publish_updates(modbus: Any, mqtt: MqttClient, *sensors: Any) -> None:
            wait = seconds_until_publish()
            self._logger.debug(f"PVOutput Add Output Service commenced ({time.strftime('%H:%M:%S', time.localtime(time.time() + wait))} is in {wait} seconds)")
            while self.online:
                if Config.pvoutput.peak_power or Config.pvoutput.consumption or Config.pvoutput.exports:
                    try:
                        if wait <= 0:
                            await update_pvoutput()
                            wait = seconds_until_publish()
                        sleep = min(wait, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                        wait -= sleep
                        if wait > 0:
                            await asyncio.sleep(sleep)
                    except asyncio.CancelledError:
                        self._logger.debug("PVOutput Add Output Service - Sleep interrupted")
                else:
                    self._logger.info(f"PVOutput Add Output Service - No data to publish ({Config.pvoutput.consumption=} {Config.pvoutput.exports=} {Config.pvoutput.peak_power=})")
                    self.online = False
                    break
            self._logger.debug(f"PVOutput Add Output Service completed - Flagged as offline ({self.online=})")
            return

        async def update_pvoutput():
            headers = {
                "X-Pvoutput-Apikey": Config.pvoutput.api_key,
                "X-Pvoutput-SystemId": Config.pvoutput.system_id,
                "X-Rate-Limit": "1",
            }

            now = time.localtime()
            payload = {"d": time.strftime("%Y%m%d", now)}
            async with self._lock:
                payload["g"] = 0.0
                for value in self._generation.values():
                    payload["g"] += round(value.state * value.gain)
                if Config.pvoutput.exports:
                    payload["e"] = 0.0
                    for value in self._exports.values():
                        payload["e"] += round(value.state * value.gain)
                if Config.pvoutput.consumption:
                    payload["c"] = 0.0
                    for value in self._consumption.values():
                        payload["c"] += round(value.state * value.gain)
                if Config.pvoutput.peak_power:
                    payload["pp"] = 0.0
                    payload["pt"] = "00:00"
                    for value in self._power.values():
                        payload["pp"] += round(value.state * value.gain)
                        payload["pt"] = time.strftime("%H:%M", value.timestamp)

            for i in range(3):
                try:
                    self._logger.debug(f"PVOutput Add Output Service - Attempt #{i} with {payload=}")
                    if Config.pvoutput.testing:
                        self._logger.debug("PVOutput Add Output Service - Testing mode, not sending request")
                        break
                    else:
                        with requests.post("https://pvoutput.org/service/r2/addoutput.jsp", headers=headers, data=payload, timeout=10) as response:
                            self._logger.debug(f"PVOutput Add Output Service - Attempt #{i} {response.status_code=} {response.headers=}")
                            reset = round(float(response.headers["X-Rate-Limit-Reset"]) - time.time())
                            if int(response.headers["X-Rate-Limit-Remaining"]) < 10:
                                self._logger.warning(f"PVOutput Add Output Service - Only {response.headers['X-Rate-Limit-Remaining']} requests left, reset after {reset} seconds")
                            if response.status_code == 403:
                                self._logger.warning(f"PVOutput Add Output Service - Forbidden: {response.reason}")
                                asyncio.sleep(reset + 1)
                            else:
                                response.raise_for_status()
                                break
                except requests.exceptions.HTTPError as exc:
                    self._logger.error(f"PVOutput Add Output Service - HTTP Error: {exc}")
                except requests.exceptions.ConnectionError as exc:
                    self._logger.error(f"PVOutput Add Output Service - Error Connecting: {exc}")
                except requests.exceptions.Timeout as exc:
                    self._logger.error(f"PVOutput Add Output Service - Timeout Error: {exc}")
                except requests.exceptions.RequestException as exc:
                    self._logger.error(f"PVOutput Add Output Service - {exc}")
                asyncio.sleep(5)
            else:
                self._logger.error(f"PVOutput Add Output Service - Failed to call PVOutput API after {i} attempts")

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    async def set_consumption(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.consumption:
            if Config.sensor_debug_logging:
                self._logger.debug(f"PVOutput Add Output Service - set_consumption from '{topic}' {value=}")
            async with self._lock:
                self._consumption[topic].state = value if isinstance(value, float) else float(value)
                self._consumption[topic].timestamp = time.localtime()
        elif Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Output Service - Ignoring set_consumption from '{topic}' {value=} because {Config.pvoutput.consumption=}")

    async def set_exported(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.exports:
            if Config.sensor_debug_logging:
                self._logger.debug(f"PVOutput Add Output Service - set_exported from '{topic}' {value=}")
            async with self._lock:
                self._exports[topic].state = value if isinstance(value, float) else float(value)
                self._exports[topic].timestamp = time.localtime()
        elif Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Output Service - Ignoring set_exported from '{topic}' {value=} because {Config.pvoutput.exports=}")

    async def set_generation(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.peak_power or Config.pvoutput.consumption or Config.pvoutput.exports:
            if Config.sensor_debug_logging:
                self._logger.debug(f"PVOutput Add Output Service - set_generation from '{topic}' {value=}")
            async with self._lock:
                self._generation[topic].state = value if isinstance(value, float) else float(value)
                self._generation[topic].timestamp = time.localtime()
        elif Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Output Service - Ignoring set_exported from '{topic}' {value=} because {Config.pvoutput.consumption=} {Config.pvoutput.exports=} {Config.pvoutput.peak_power=}")

    async def set_power(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.peak_power:
            if Config.sensor_debug_logging:
                self._logger.debug(f"PVOutput Add Output Service - set_power from '{topic}' {value=}")
            async with self._lock:
                power = value if isinstance(value, float) else float(value)
                if self._power[topic].state < power:
                    self._power[topic].state = power
                    self._power[topic].timestamp = time.localtime()
        elif Config.sensor_debug_logging:
            self._logger.debug(f"PVOutput Add Output Service - Ignoring set_exported from '{topic}' {value=} because {Config.pvoutput.peak_power=}")

    def subscribe(self, mqtt, mqtt_handler):
        for topic in self._consumption.keys():
            mqtt_handler.register(mqtt, topic, self.set_consumption)
            self._logger.debug(f"PVOutput Add Output Service subscribed to topic '{topic}' to record consumption")
        for topic in self._exports.keys():
            mqtt_handler.register(mqtt, topic, self.set_exported)
            self._logger.debug(f"PVOutput Add Output Service subscribed to topic '{topic}' to record exports")
        for topic in self._generation.keys():
            mqtt_handler.register(mqtt, topic, self.set_generation)
            self._logger.debug(f"PVOutput Add Output Service subscribed to topic '{topic}' to record generation")
        for topic in self._power.keys():
            mqtt_handler.register(mqtt, topic, self.set_power)
            self._logger.debug(f"PVOutput Add Output Service subscribed to topic '{topic}' to peak power")
