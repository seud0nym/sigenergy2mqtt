from .service import Service, ServiceTopics, Topic
from pathlib import Path
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import json
import logging
import time


class PVOutputOutputService(Service):
    def __init__(self, plant_index: int, logger: logging.Logger):
        super().__init__("PVOutput Add Output Service", plant_index, unique_id="pvoutput_output", model="PVOutput.AddOutput", logger=logger)

        self._consumption: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.consumption, "consumption", logger)
        self._exports: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.exports, "exports", logger)
        self._generation: ServiceTopics[str, Topic] = ServiceTopics(self, True, "generation", logger)
        self._power: ServiceTopics[str, Topic] = ServiceTopics(self, Config.pvoutput.peak_power, "peak power", logger)
        self._power.update = self.set_power

        self._persistent_state_file = Path(Config.persistent_state_path, f"pvoutput_output_{plant_index}-peak_power.state")
        if self._persistent_state_file.is_file():
            fmt = time.localtime(self._persistent_state_file.stat().st_mtime)
            now = time.localtime()
            if fmt.tm_year == now.tm_year and fmt.tm_mon == now.tm_mon and fmt.tm_mday == now.tm_mday:
                with self._persistent_state_file.open("r") as f:
                    try:
                        power = json.load(f, object_hook=Topic.json_decoder)
                        self.logger.info(f"{self.__class__.__name__} - Loaded {self._persistent_state_file}")
                        for topic in power.values():
                            self._power[topic.topic] = topic
                            self.logger.info(f"{self.__class__.__name__} - Initialised {topic.topic} to {topic.state=}")
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

    def register_exports(self, topic: str, gain: float) -> None:
        self._exports.register(topic, gain)

    def register_generation(self, topic: str, gain: float) -> None:
        self._generation.register(topic, gain)

    def register_power(self, topic: str, gain: float) -> None:
        self._power.register(topic, gain)
        if len(self._power) > 1:
            Config.pvoutput.peak_power = False
            self._power.enabled = False
            self.logger.warning(f"{self.__class__.__name__} - DISABLED peak-power reporting: Cannot determine peak power from multiple systems")

    # endregion

    def schedule(self, modbus: Any, mqtt: MqttClient) -> List[Callable[[Any, MqttClient, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: MqttClient, *sensors: Any) -> None:
            self.logger.debug(f"{self.__class__.__name__} - Commenced (Updating at {Config.pvoutput.output_hour}:45)")
            wait = self.seconds_until_daily_output_upload()
            while self.online:
                if Config.pvoutput.peak_power or Config.pvoutput.consumption or Config.pvoutput.exports:
                    try:
                        if wait <= 0:
                            await update_pvoutput()
                            wait = self.seconds_until_daily_output_upload()
                        sleep = min(wait, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                        wait -= sleep
                        if wait > 0:
                            await asyncio.sleep(sleep)
                    except asyncio.CancelledError:
                        self.logger.info(f"{self.__class__.__name__} - Sleep interrupted")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"{self.__class__.__name__} - Failed to acquire lock within timeout")
                else:
                    self.logger.info(f"{self.__class__.__name__} - No data to publish ({Config.pvoutput.consumption=} {Config.pvoutput.exports=} {Config.pvoutput.peak_power=})")
                    self.online = False
                    break
            self.logger.debug(f"{self.__class__.__name__} - Completed: Flagged as offline ({self.online=})")
            return

        async def update_pvoutput():
            self.logger.debug(f"{self.__class__.__name__} - Creating payload...")
            now = time.localtime()
            payload = {"d": time.strftime("%Y%m%d", now)}
            async with self.lock(timeout=5):
                payload["g"], _ = self._generation.sum()
                if Config.pvoutput.exports:
                    payload["e"], _ = self._exports.sum()
                if Config.pvoutput.consumption:
                    payload["c"], _ = self._consumption.sum()
                if Config.pvoutput.peak_power:
                    payload["pp"], payload["pt"] = self._power.sum()
            await self.upload_payload("https://pvoutput.org/service/r2/addoutput.jsp", payload)
            self.logger.debug(f"{self.__class__.__name__} - Resetting peak power history...")
            async with self.lock(timeout=5):
                for topic in self._power.values():
                    topic.state = 0.0
                    topic.timestamp = None
                self._persistent_state_file.unlink(missing_ok=True)

        tasks = [publish_updates(modbus, mqtt)]
        return tasks

    async def set_power(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str) -> bool:
        if Config.pvoutput.peak_power:
            power = value if isinstance(value, float) else float(value)
            if self._power[topic].state < power:
                self.logger.debug(f"{self.__class__.__name__} - set_power from '{topic}' {value=} (Previous peak={self._power[topic].state})")
                async with self.lock(timeout=1):
                    self._power[topic].state = power
                    self._power[topic].timestamp = time.localtime()
                    with self._persistent_state_file.open("w") as f:
                        json.dump(self._power, f, default=Topic.json_encoder)
            elif Config.pvoutput.update_debug_logging:
                self.logger.debug(f"{self.__class__.__name__} - Ignored set_power from '{topic}': {value} < {self._power[topic].state}")

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler):
        self._consumption.subscribe(mqtt, mqtt_handler)
        self._exports.subscribe(mqtt, mqtt_handler)
        self._generation.subscribe(mqtt, mqtt_handler)
        self._power.subscribe(mqtt, mqtt_handler)
