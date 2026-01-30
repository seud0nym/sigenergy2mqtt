import asyncio
import logging
import time
from typing import Any, Awaitable

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.base import ReadableSensorMixin

from .monitored_sensor import MonitoredSensor


class MonitorService(Device):
    def __init__(self, devices: list[Device]):
        super().__init__("Sigenergy Monitor", -1, f"{Config.home_assistant.unique_id_prefix}_monitor", "sigenergy2mqtt", "Monitor", Protocol.N_A)
        self._devices: list[Device] = devices
        self._lock = asyncio.Lock()
        self._topics: dict[str, MonitoredSensor] = {}

    async def _monitor(self, modbus_client: Any, mqtt_client: Any, *sensors: Any):
        logging.info(f"{self.__class__.__name__} Commenced")
        while self.online:
            async with self._lock:
                overdue: dict[str, MonitoredSensor] = {t: s for t, s in self._topics.items() if s.is_overdue}
            if any(overdue):
                for topic, sensor in overdue.items():
                    sensor.notified = True
                    logging.warning(f"{self.__class__.__name__} '{sensor.name}' has not been seen for {sensor.overdue}s (scan_interval={sensor.scan_interval}s {topic=})")
            try:
                task = asyncio.create_task(asyncio.sleep(1))
                self.sleeper_task = task
                await task
            except asyncio.CancelledError:
                logging.debug(f"{self.__class__.__name__} sleep interrupted")
                break
            finally:
                self.sleeper_task = None
        logging.info(f"{self.__class__.__name__} Completed: Flagged as offline ({self.online=})")

    async def on_ha_state_change(self, modbus_client: Any | None, mqtt_client: mqtt.Client, ha_state: str, source: str, mqtt_handler: MqttHandler) -> bool:
        return True

    async def on_topic_update(self, modbus_client: Any | None, mqtt_client: mqtt.Client, value: str, source: str, mqtt_handler: MqttHandler) -> bool:
        if source in self._topics:
            sensor = self._topics[source]
            if sensor.notified:
                logging.info(f"{self.__class__.__name__} '{sensor.name}' seen after {sensor.overdue}s (scan_interval={sensor.scan_interval}s {source=})")
            async with self._lock:
                sensor.last_seen = time.time()
                sensor.notified = False
            return True
        else:
            logging.warning(f"{self.__class__.__name__} updated from  topic {source}, but topic is not registered !!!")
        return False

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        pass

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        pass

    def schedule(self, modbus_client: Any, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        return [self._monitor(modbus_client, mqtt_client, [])]

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        for d in self._devices:
            device = d.name
            sensors = 0
            for s in [sensor for sensor in d.get_all_sensors().values() if isinstance(sensor, ReadableSensorMixin) and sensor.publishable]:
                sensor = s.name
                scan_interval = s.scan_interval
                topic = s.state_topic
                if topic in self._topics:
                    logging.error(f"{self.__class__.__name__} Sensor '{device} - {sensor}' has the same topic as '{self._topics[topic].name}' ({topic=}) ????")
                else:
                    self._topics[topic] = MonitoredSensor(device, sensor, scan_interval)
                    sensors += 1
                    mqtt_handler.register(mqtt_client, topic, handler=self.on_topic_update)
            if sensors > 0:
                logging.info(f"{self.__class__.__name__} Monitoring {sensors} topic{'s' if sensors > 1 else ''} for '{d.name}'")
        logging.info(f"{self.__class__.__name__} Monitoring {len(self._topics)} topics")
