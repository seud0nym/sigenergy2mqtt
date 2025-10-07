from .service import Service
from .topic import Topic
from sigenergy2mqtt.config import Config, OutputField, StatusField
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any
import logging
import time


class ServiceTopics(dict[str, Topic]):
    def __init__(
        self,
        service: Service,
        enabled: bool,
        name: str,
        logger: logging.Logger,
        requires_donation: bool = False,
        averaged: bool = True,
        value_key: str = None,
        datetime_key: str = None,
        decimals: int = 0,
        bypass_updating_check: bool = False,
    ):
        self._last_update_warning: float = None
        self._service = service
        self._enabled = enabled
        self._name = name
        self._logger = logger
        self._requires_donation = requires_donation
        self._averaged = averaged
        self._value_key = value_key
        self._datetime_key = datetime_key
        self._decimals = decimals
        self._bypass_updating_check = bypass_updating_check

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        assert isinstance(value, bool), "Enabled must be a boolean value"
        self._enabled = value

    @property
    def requires_donation(self) -> bool:
        return self._requires_donation

    def _average_into(self, payload: dict[str, any], value_key: OutputField | StatusField, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=True)
        if count > 0 and total is not None:
            value = round(total / count, self._decimals)
            payload[value_key.value] = int(value) if self._decimals == 0 else value
            if datetime_key is not None:
                payload[datetime_key] = at
                self._logger.debug(
                    f"{self._service.__class__.__name__} Averaged {self._name}: {total} / {count} = {payload[value_key.value]} into {value_key.value=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            else:
                self._logger.debug(
                    f"{self._service.__class__.__name__} Averaged {self._name}: {total} / {count} = {payload[value_key.value]} into {value_key.value=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key in payload:
                del payload[value_key.value]
                self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key.value}' from payload because {count=} and {total=}")
            return False

    def _sum_into(self, payload: dict[str, any], value_key: OutputField | StatusField, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=False)
        if count > 0 and total is not None:
            payload[value_key.value] = int(total) if self._decimals == 0 else round(total, self._decimals)
            if datetime_key is not None:
                payload[datetime_key] = at
                self._logger.debug(
                    f"{self._service.__class__.__name__} Summed {self._name}: {total} into {value_key.value=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            else:
                self._logger.debug(
                    f"{self._service.__class__.__name__} Summed {self._name}: {total} into {value_key.value=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key in payload:
                del payload[value_key.value]
                self._logger.warning(f"{self._service.__class__.__name__} Removed '{value_key.value}' from payload because {count=} and {total=}")
            return False

    def add_to_payload(self, payload: dict[str, any], interval_minutes: int, now: time.struct_time) -> bool:
        if self._bypass_updating_check or self.check_is_updating(interval_minutes, now):
            if self._averaged:
                return self._average_into(payload, self._value_key, self._datetime_key)
            else:
                return self._sum_into(payload, self._value_key, self._datetime_key)
        else:
            return False

    def aggregate(self, exclude_zero: bool) -> tuple[float, str, int]:
        if not self.enabled:
            return None, None, 0
        if len(self) == 0:
            self._logger.debug(f"{self._service.__class__.__name__} No {self._name} topics registered, skipping aggregation")
            return None, None, 0
        at: str = "00:00"
        count: int = 0
        total: float = 0.0
        for value in self.values():
            if value.timestamp is not None and (not exclude_zero or value.state > 0.0):
                total += value.state * value.gain
                at = time.strftime("%H:%M", value.timestamp)
                count += 1
        if count > 0:
            return total, at, count
        else:
            return None, None, count

    def check_is_updating(self, interval_minutes: int, now: time.struct_time) -> bool:
        if self.enabled:
            interval_seconds = interval_minutes * 60
            topics = 0
            updated = 0
            for value in self.values():
                topics += 1
                if value.timestamp is not None:
                    seconds = int(time.mktime(now) - time.mktime(value.timestamp))
                    minutes = int(seconds / 60.0)
                    if seconds < interval_seconds:
                        updated += 1
                    else:
                        if self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600:
                            self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has not been updated for {minutes}m???")
                            self._last_update_warning = time.time()
                elif self._last_update_warning is None or (time.time() - self._last_update_warning) > 3600:
                    self._logger.warning(f"{self._service.__class__.__name__} Topic '{value.topic}' for {self._name} has never been updated???")
                    self._last_update_warning = time.time()
            return topics == updated
        else:
            return False

    def register(self, topic: str, gain: float) -> bool:
        if self.enabled:
            if topic is None or topic == "" or topic.isspace():
                self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for empty topic")
            elif topic not in self:
                self[topic] = Topic(topic, gain)
                self._logger.debug(f"{self._service.__class__.__name__} Registered {self._name} topic: {topic} ({'averaged' if self._averaged else 'summed'} {gain=})")
        else:
            self._logger.debug(f"{self._service.__class__.__name__} Ignored subscription request for '{topic}' because {self._name} uploading is disabled")

    def reset(self) -> None:
        for value in self.values():
            value.state = 0.0
            value.timestamp = time.localtime()

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in self.keys():
            if self.enabled:
                result = mqtt_handler.register(mqtt, topic, self.update)
                self._logger.debug(f"{self._service.__class__.__name__} Subscribed to topic '{topic}' to record {self._name} ({result=})")
            else:
                self._logger.debug(f"{self._service.__class__.__name__} Not subscribing to topic '{topic}' because {self._name} uploading is disabled")

    async def update(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str, handler: MqttHandler) -> bool:
        if self.enabled:
            if Config.pvoutput.update_debug_logging:
                self._logger.debug(f"{self._service.__class__.__name__} Updating {self._name} from '{topic}' {value=}")
            state = value if isinstance(value, float) else float(value)
            if state >= 0.0:
                async with self._service.lock(timeout=1):
                    self[topic].state = state
                    self[topic].timestamp = time.localtime()
            return True
        else:
            return False
