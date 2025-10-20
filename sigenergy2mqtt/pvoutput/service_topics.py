from .service import Service
from .topic import Topic
from enum import Flag, auto
from pathlib import Path
from sigenergy2mqtt.config import Config, OutputField, StatusField
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any
import json
import logging
import time


class Calculation(Flag):
    SUM = auto()
    AVERAGE = auto()
    DIFFERENCE = auto()
    PEAK = auto()
    CONVERT_TO_WATTS = auto()


class ServiceTopics(dict[str, Topic]):
    def __init__(
        self,
        service: Service,
        enabled: bool,
        logger: logging.Logger,
        value_key: OutputField | StatusField = None,
        datetime_key: str = None,
        calculation: Calculation = Calculation.SUM,
        decimals: int = 0,
        requires_donation: bool = False,
    ):
        self._bypass_updating_check = Calculation.PEAK in calculation
        self._calculation = calculation
        self._datetime_key = datetime_key
        self._decimals = decimals
        self._enabled = enabled
        self._last_update_warning: float = None
        self._logger = logger
        self._name = value_key.name
        self._persistent_state_file: Path = None
        self._requires_donation = requires_donation
        self._service = service
        self._value_key = value_key

    @property
    def calculation(self) -> Calculation:
        return self._calculation

    @calculation.setter
    def calculation(self, value: Calculation) -> None:
        assert isinstance(value, Calculation), "Calculation must be a Calculation enum value"
        self._calculation = value

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
            payload[value_key.value] = round(total / count, self._decimals if self._decimals > 0 else None)
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
            self._logger.info(f"{self._service.__class__.__name__} Removed '{value_key.value}' from payload because {count=} and {total=}")
            return False

    def _sum_into(self, payload: dict[str, any], value_key: OutputField | StatusField, datetime_key: str = None) -> bool:
        total, at, count = self.aggregate(exclude_zero=False)
        if count > 0 and total is not None:
            payload[value_key.value] = round(total, self._decimals if self._decimals > 0 else None)
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
            self._logger.info(f"{self._service.__class__.__name__} Removed '{value_key.value}' from payload because {count=} and {total=}")
            return False

    def add_to_payload(self, payload: dict[str, any], interval_minutes: int, now: time.struct_time) -> bool:
        if self._bypass_updating_check or self.check_is_updating(interval_minutes, now):
            if Calculation.AVERAGE in self._calculation:
                return self._average_into(payload, self._value_key, self._datetime_key)
            else:  # SUM
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
        count: float = 0.0
        total: float = 0.0
        for topic in self.values():
            if topic.timestamp is not None and (not exclude_zero or topic.state > 0.0 or Calculation.DIFFERENCE in self._calculation):
                state: float = topic.state
                if Calculation.DIFFERENCE in self._calculation:
                    state_was: float = topic.previous_state
                    time_was: time.struct_time = topic.previous_timestamp
                    topic.previous_state = topic.state
                    topic.previous_timestamp = topic.timestamp
                    if state_was is not None and time_was is not None and topic.timestamp.tm_yday == time_was.tm_yday:
                        self._logger.debug(
                            f"{self._service.__class__.__name__} Calculated difference for {self._name}: (current-previous=state) {state}-{state_was}={state - state_was} ({topic.topic})"
                        )
                        state -= state_was
                        if Calculation.CONVERT_TO_WATTS in self._calculation:
                            hours = (time.mktime(topic.timestamp) - time.mktime(time_was)) / 3600.0
                            if hours > 0:
                                self._logger.debug(f"{self._service.__class__.__name__} Converted {self._name}: (energy/hours=power) {state}/{hours:.3f}={state / hours} ({topic.topic})")
                                state /= hours
                            else:
                                self._logger.warning(f"{self._service.__class__.__name__} Skipped converting {self._name} energy to power: {hours:.3f} ({topic.topic}) ????")
                    else:
                        continue
                self._logger.debug(f"{self._service.__class__.__name__} Applying gain to {self._name}: {state}*{topic.gain}={state * topic.gain} ({topic.topic}) and adding to running {total=}")
                total += state * topic.gain
                at = time.strftime("%H:%M", topic.timestamp)
                self._logger.debug(f"{self._service.__class__.__name__} Running total for {self._name}: {total=} ({count=} {at=})")
                count += 1
        if count > 0:
            return total, at, count
        else:
            return None, None, count

    def check_is_updating(self, interval_minutes: int, now: time.struct_time) -> bool:
        if self.enabled:
            interval_seconds = interval_minutes * 60
            updated = 0
            for value in self.values():
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
            return updated > 0
        else:
            return False

    def register(self, topic: Topic) -> None:
        if self.enabled:
            if topic is None or topic.topic == "" or topic.topic.isspace():
                self._logger.warning(f"{self._service.__class__.__name__} IGNORED subscription request for empty topic")
            else:
                self[topic.topic] = topic
                self._logger.debug(f"{self._service.__class__.__name__} Registered {self._name} topic: {topic.topic} ({self._calculation} {topic.gain=})")
                if self._calculation & (Calculation.DIFFERENCE | Calculation.PEAK):
                    self._persistent_state_file = Path(Config.persistent_state_path, f"{self._service.unique_id}-{self._name}.state")
                    if self._value_key == OutputField.PEAK_POWER:
                        obsolete = Path(Config.persistent_state_path, "pvoutput_output-peak_power.state")
                        if obsolete.is_file() and not self._persistent_state_file.is_file():
                            obsolete.rename(self._persistent_state_file.resolve())
                    if self._persistent_state_file.is_file():
                        fmt = time.localtime(self._persistent_state_file.stat().st_mtime)
                        now = time.localtime()
                        if fmt.tm_yday == now.tm_yday:
                            with self._persistent_state_file.open("r") as f:
                                try:
                                    saved: ServiceTopics = json.load(f, object_hook=Topic.json_decoder)
                                    self._logger.debug(f"{self._service.__class__.__name__} Loaded {self._persistent_state_file}")
                                    if topic.topic in saved:
                                        topic = saved[topic.topic]
                                        self[topic.topic] = topic
                                        self._logger.debug(
                                            f"{self._service.__class__.__name__} Restored {self._name} topic {topic.topic} (gain={topic.gain}) with {topic.state=} at {time.strftime('%H:%M', topic.timestamp) if topic.timestamp else 'None'} and {topic.previous_state=} at {time.strftime('%H:%M', topic.previous_timestamp) if topic.previous_timestamp else 'None'}"
                                        )
                                except ValueError as error:
                                    self._logger.warning(f"{self._service.__class__.__name__} Failed to read {self._persistent_state_file}: {error}")
                        else:
                            self._logger.debug(f"{self._service.__class__.__name__} Ignored {self._persistent_state_file} because it is stale ({fmt})")
                            self._persistent_state_file.unlink(missing_ok=True)
                    else:
                        self._logger.debug(f"{self._service.__class__.__name__} Persistent state file {self._persistent_state_file} not found")
        else:
            self._logger.debug(f"{self._service.__class__.__name__} IGNORED subscription request for '{topic.topic}' because {self._name} uploading is disabled")

    def reset(self) -> None:
        for topic in self.values():
            topic.state = 0.0
            topic.timestamp = time.localtime()
            topic.previous_state = None
            topic.previous_timestamp = None
        if hasattr(self, "_persistent_state_file") and self._persistent_state_file is not None and self._persistent_state_file.is_file():
            self._persistent_state_file.unlink(missing_ok=True)

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        for topic in self.keys():
            if self.enabled:
                result = mqtt_handler.register(mqtt, topic, self.update)
                self._logger.debug(f"{self._service.__class__.__name__} Subscribed to topic '{topic}' to record {self._name} ({result=})")
            else:
                self._logger.debug(f"{self._service.__class__.__name__} Not subscribing to topic '{topic}' because {self._name} uploading is disabled")

    async def update(self, modbus: Any, mqtt: MqttClient, value: float | int | str, topic: str, handler: MqttHandler) -> bool:
        if self.enabled:
            state = value if isinstance(value, float) else float(value)
            if state and (Calculation.PEAK not in self._calculation or state > self[topic].state):
                if Config.pvoutput.update_debug_logging:
                    self._logger.debug(f"{self._service.__class__.__name__} Updating {self._name} from '{topic}' {value=}")
                async with self._service.lock(timeout=1):
                    self[topic].state = state
                    self[topic].timestamp = time.localtime()
                    if self._calculation & (Calculation.DIFFERENCE | Calculation.PEAK):
                        with self._persistent_state_file.open("w") as f:
                            json.dump(self, f, default=Topic.json_encoder)
            elif Config.pvoutput.update_debug_logging and state and Calculation.PEAK in self._calculation:
                self._logger.debug(f"{self._service.__class__.__name__} Ignored {self._name} from '{topic}': {state=} (<= Previous peak={self[topic].state})")
            return True
        else:
            return False
