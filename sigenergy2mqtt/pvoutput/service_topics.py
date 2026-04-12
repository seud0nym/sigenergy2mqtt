"""Topic aggregation helpers used by PVOutput services.

This module defines calculation modes and mutable topic collections that
aggregate MQTT samples into PVOutput payload fields.
"""

import json
import logging
import math
import time
from datetime import timedelta
from enum import Flag, auto
from typing import Any, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common.output_field import OutputField
from sigenergy2mqtt.common.status_field import StatusField
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.persistence import Category, state_store

from .service import Service
from .topic import Topic


class Calculation(Flag):
    """Bitwise flags describing how topic values are aggregated."""

    SUM = auto()
    AVERAGE = auto()
    DIFFERENCE = auto()
    PEAK = auto()
    CONVERT_TO_WATTS = auto()
    L_L_AVG = auto()


class ServiceTopics(dict[str, Topic]):
    """Collection of MQTT topics aggregated into one PVOutput field."""

    def __init__(
        self,
        service: Service,
        enabled: bool,
        logger: logging.Logger,
        value_key: OutputField | StatusField,
        datetime_key: str | None = None,
        calc: Calculation = Calculation.SUM,
        decimals: int = 0,
        negative: bool = False,
        donation: bool = False,
        periods: list["TimePeriodServiceTopics"] | None = None,
        persist: bool = False,
    ):
        """Initialize aggregation behaviour for one PVOutput payload field.

        Args:
            service: Parent PVOutput service owning this topic group.
            enabled: Whether this topic group is active.
            logger: Logger used for diagnostics.
            value_key: PVOutput payload key represented by this group.
            datetime_key: Optional companion payload key for timestamps.
            calc: Aggregation strategy flags.
            decimals: Decimal precision for rounded payload values.
            negative: Whether negative values are allowed in payload output.
            donation: Whether this field requires PVOutput donation status.
            periods: Optional child groups for tariff/time-period breakout.
            persist: Whether state should always be persisted to disk.
        """
        super().__init__()
        self._allow_negative = negative
        self._always_persist = persist
        self._bypass_updating_check = Calculation.PEAK in calc
        self._calculation = calc
        self._datetime_key = datetime_key
        self._decimals = decimals
        self._enabled = enabled
        self._last_update_warning: float | None = None
        self._logger = logger
        self._name = value_key.name
        self._persistence_key: str | None = None
        self.requires_donation = donation
        self._service = service
        self._value_key = value_key
        self._time_periods = periods or []

    @property
    def calculation(self) -> Calculation:
        """Return active calculation flags for this topic group.

        Args:
            None.
        """
        return self._calculation

    @calculation.setter
    def calculation(self, value: Calculation) -> None:
        """Set calculation flags used to aggregate topic values.

        Args:
            value: New aggregation flags.
        """
        assert isinstance(value, Calculation), "Calculation must be a Calculation enum value"
        self._calculation = value

    @property
    def decimals(self) -> int:
        """Return configured decimal precision for payload rounding.

        Args:
            None.
        """
        return self._decimals

    @decimals.setter
    def decimals(self, value: int) -> None:
        """Set decimal precision for generated payload values.

        Args:
            value: Number of decimal places to keep.
        """
        assert isinstance(value, int), "Decimals must be an integer value"
        self._decimals = value

    @property
    def enabled(self) -> bool:
        """Return whether this topic group participates in uploads.

        Args:
            None.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable or disable this topic group.

        Args:
            value: New enabled state.
        """
        assert isinstance(value, bool), "Enabled must be a boolean value"
        self._enabled = value

    def _average_into(self, payload: dict[str, float | int | str], value_key: OutputField | StatusField, datetime_key: str | None = None) -> bool:
        """Write an averaged value into *payload* when valid data exists.

        Args:
            payload: Payload being assembled.
            value_key: Target payload field for the numeric value.
            datetime_key: Optional payload field for the timestamp.
        """
        total, at, count = self.aggregate(exclude_zero=True)
        if count > 0 and total is not None and (self._allow_negative or total >= 0.0):
            payload[value_key.value] = round(total / count, self.decimals if self.decimals > 0 else None)
            if datetime_key is not None and at is not None:
                payload[datetime_key] = at
                if active_config.pvoutput.calc_debug_logging:
                    self._logger.debug(
                        f"{self._service.log_identity} Averaged {self._name}: {total} / {count} = {payload[value_key.value]} into {value_key.value=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                    )
            elif active_config.pvoutput.calc_debug_logging:
                self._logger.debug(
                    f"{self._service.log_identity} Averaged {self._name}: {total} / {count} = {payload[value_key.value]} into {value_key.value=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key.value in payload:
                del payload[value_key.value]
                self._logger.info(f"{self._service.log_identity} Removed '{value_key.value}' from payload because {count=} and {total=} (allow_negative={self._allow_negative})")
            return False

    def _squared_root_into(self, payload: dict[str, float | int | str], value_key: OutputField | StatusField, datetime_key: str | None = None) -> bool:
        """Write a line-to-line average voltage estimate into *payload*.

        Args:
            payload: Payload being assembled.
            value_key: Target payload field for the numeric value.
            datetime_key: Optional payload field for the timestamp.
        """
        total, at, count = self.aggregate(exclude_zero=False, square=True)
        if count > 0 and total is not None and (self._allow_negative or total >= 0.0):
            payload[value_key.value] = round(math.sqrt(total) / math.sqrt(3), self.decimals if self.decimals > 0 else None)
            if datetime_key is not None and at is not None:
                payload[datetime_key] = at
                if active_config.pvoutput.calc_debug_logging:
                    self._logger.debug(
                        f"{self._service.log_identity} L-L Averaged {self._name}: √{total} / √3 = {payload[value_key.value]} into {value_key.value=} ({datetime_key}={at}) {[(f'{v.state}^2', time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                    )
            elif active_config.pvoutput.calc_debug_logging:
                self._logger.debug(
                    f"{self._service.log_identity} L-L Averaged {self._name}: √{total} / √3 = {payload[value_key.value]} into {value_key.value=} {[(f'{v.state}^2', time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key.value in payload:
                del payload[value_key.value]
                self._logger.info(f"{self._service.log_identity} Removed '{value_key.value}' from payload because {count=} and {total=} (allow_negative={self._allow_negative})")
            return False

    def _sum_into(self, payload: dict[str, float | int | str], value_key: OutputField | StatusField, datetime_key: str | None = None) -> bool:
        """Write a summed or differential value into *payload*.

        Args:
            payload: Payload being assembled.
            value_key: Target payload field for the numeric value.
            datetime_key: Optional payload field for the timestamp.
        """
        total, at, count = self.aggregate(exclude_zero=False)
        if count > 0 and total is not None and (self._allow_negative or total >= 0.0):
            payload[value_key.value] = round(total, self.decimals if self.decimals > 0 else None)
            if datetime_key is not None and at is not None:
                payload[datetime_key] = at
                if active_config.pvoutput.calc_debug_logging:
                    self._logger.debug(
                        f"{self._service.log_identity} Summed {self._name}: {total} into {value_key.value=} ({datetime_key}={at}) {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                    )
            elif active_config.pvoutput.calc_debug_logging:
                self._logger.debug(
                    f"{self._service.log_identity} Summed {self._name}: {total} into {value_key.value=} {[(v.state, time.strftime('%H:%M', v.timestamp) if v.timestamp else None) for v in self.values()]}"
                )
            return True
        else:
            if value_key.value in payload:
                del payload[value_key.value]
                self._logger.info(f"{self._service.log_identity} Removed '{value_key.value}' from payload because {count=} and {total=} (allow_negative={self._allow_negative})")
            return False

    def add_to_payload(self, payload: dict[str, float | int | str], interval_minutes: int, now: time.struct_time) -> bool:
        """Add this field's current aggregate to the outbound payload.

        Args:
            payload: Payload being assembled.
            interval_minutes: Expected update interval for staleness checks.
            now: Current timestamp used for staleness checks.
        """
        if self._value_key not in (None, "") and (self._bypass_updating_check or self.check_is_updating(interval_minutes, now)):
            if Calculation.AVERAGE in self.calculation:
                return self._average_into(payload, self._value_key, self._datetime_key)
            elif Calculation.L_L_AVG in self.calculation:
                return self._squared_root_into(payload, self._value_key, self._datetime_key)
            else:  # SUM
                return self._sum_into(payload, self._value_key, self._datetime_key)
        else:
            return False

    def aggregate(self, exclude_zero: bool, square: bool = False, never_return_none: bool = False) -> tuple[float | None, str | None, int]:
        """Aggregate topic states and return total, latest time, and count.

        Args:
            exclude_zero: Whether to ignore zero-valued states.
            square: Whether to square each value before summing.
            never_return_none: Whether to return ``0.0`` instead of ``None``.
        """
        if not self.enabled:
            return 0.0 if never_return_none else None, None, 0
        if len(self) == 0:
            self._logger.debug(f"{self._service.log_identity} No {self._name} topics registered, skipping aggregation")
            return 0.0 if never_return_none else None, None, 0
        at: str = "00:00"
        count: int = 0
        total: float = 0.0
        for topic in self.values():
            if topic.timestamp is not None and (not exclude_zero or (topic.state is not None and topic.state > 0.0) or Calculation.DIFFERENCE in self.calculation):
                state: float = topic.state if topic.state is not None and (self._allow_negative or topic.state >= 0.0) else 0.0
                if active_config.pvoutput.calc_debug_logging and state != topic.state:
                    self._logger.debug(f"{self._service.log_identity} Using {state=} for {self._value_key.name} because {topic.state=} (allow_negative={self._allow_negative})")
                if Calculation.DIFFERENCE in self.calculation:
                    state_was: float | None = topic.previous_state if topic.previous_state is None or self._allow_negative or topic.previous_state >= 0.0 else 0.0
                    time_was: time.struct_time | None = topic.previous_timestamp
                    topic.previous_state = state
                    topic.previous_timestamp = topic.timestamp
                    if active_config.pvoutput.calc_debug_logging and state_was != topic.previous_state:
                        self._logger.debug(f"{self._service.log_identity} Using {state_was=} for {self._value_key.name} because {topic.previous_state=} (allow_negative={self._allow_negative})")
                    if state_was is not None and time_was is not None and (topic.timestamp.tm_yday == time_was.tm_yday or 0 < (time.mktime(topic.timestamp) - time.mktime(time_was)) < 3600):
                        if active_config.pvoutput.calc_debug_logging:
                            self._logger.debug(f"{self._service.log_identity} Calculated difference for {self._name}: (current-previous=state) {state}-{state_was}={state - state_was} ({topic.topic})")
                        state -= state_was
                        if Calculation.CONVERT_TO_WATTS in self.calculation:
                            hours = (time.mktime(topic.timestamp) - time.mktime(time_was)) / 3600.0
                            if hours > 0:
                                if active_config.pvoutput.calc_debug_logging:
                                    self._logger.debug(f"{self._service.log_identity} Converted {self._name}: (energy/hours=power) {state}/{hours:.3f}={state / hours} ({topic.topic})")
                                state /= hours
                            elif active_config.pvoutput.calc_debug_logging:
                                self._logger.warning(f"{self._service.log_identity} Skipped converting {self._name} energy to power: {hours:.3f} ({topic.topic}) ????")
                    else:
                        continue
                if square:
                    total += state**2 * topic.gain
                else:
                    total += state * topic.gain
                if active_config.pvoutput.calc_debug_logging:
                    self._logger.debug(f"{self._service.log_identity} Applied gain to {self._name}: {state}*{topic.gain}={state * topic.gain} ({topic.topic}) and added to running {total=}")
                at = time.strftime("%H:%M", topic.timestamp)
                count += 1
        if count > 0:
            return total, at, count
        else:
            return 0.0 if never_return_none else None, None, count

    def check_is_updating(self, interval_minutes: int, now_struct: time.struct_time) -> bool:
        """Warn when topic updates appear stale for the configured interval.

        Args:
            interval_minutes: Expected update interval for this metric.
            now_struct: Current timestamp used for age calculations.
        """
        if self.enabled:
            now = time.mktime(now_struct)
            if now - active_config.pvoutput.started < 120:
                if active_config.pvoutput.update_debug_logging:
                    self._logger.debug(f"{self._service.log_identity} Skipping updating check for {self._name} because service just started")
                return True
            interval_seconds = interval_minutes * 60
            updated = 0
            for topic in self.values():
                scan_interval = topic.scan_interval if topic.scan_interval is not None else interval_seconds
                if topic.timestamp is not None:
                    seconds = int(now - time.mktime(topic.timestamp if topic.restore_timestamp is None or topic.timestamp > topic.restore_timestamp else topic.restore_timestamp))
                    minutes = int(seconds / 60.0)
                    if seconds <= scan_interval:
                        if active_config.pvoutput.update_debug_logging:
                            self._logger.debug(f"{self._service.log_identity} Topic {topic.topic} for {self._name} last updated {seconds}s ago ({scan_interval=}s)")
                        updated += 1
                    elif (self._last_update_warning is None or (now - self._last_update_warning) > 3600) and minutes > 0:
                        self._logger.warning(f"{self._service.log_identity} Topic {topic.topic} for {self._name} has not been updated for {minutes}m??? ({scan_interval=}s)")
                        self._last_update_warning = now
                elif not isinstance(self, TimePeriodServiceTopics) and (self._last_update_warning is None or (now - self._last_update_warning) > 3600):
                    self._logger.warning(f"{self._service.log_identity} Topic {topic.topic} for {self._name} has never been updated??? ({scan_interval=}s)")
                    self._last_update_warning = now
            if updated == 0 and self._last_update_warning != now:
                self._logger.debug(f"{self._service.log_identity} {self._name} failed updating check (topics {updated=} now={now_struct} {interval_seconds=}): {self}")
            return updated > 0
        else:
            return False

    def register(self, topic: Topic) -> None:
        """Register a topic and immediately restore persisted state.

        Args:
            topic: Topic descriptor to track and restore.
        """
        if self.enabled:
            if topic is None or topic.topic == "" or topic.topic.isspace():
                self._logger.warning(f"{self._service.log_identity} IGNORED subscription request for empty topic")
            else:
                self[topic.topic] = topic
                self._logger.debug(f"{self._service.log_identity} Registered {self._name} topic: {topic.topic} ({self.calculation} gain={topic.gain} scan_interval={topic.scan_interval})")
                if self.calculation & (Calculation.DIFFERENCE | Calculation.PEAK) or len(self._time_periods) > 0:
                    self.restore_state(topic)
                if self._time_periods:
                    for child in self._time_periods:
                        child.register(Topic(topic.topic, gain=topic.gain, precision=topic.precision, scan_interval=topic.scan_interval))
        else:
            self._logger.debug(f"{self._service.log_identity} IGNORED subscription request for '{topic.topic}' because {self._name} uploading is disabled")

    def restore_state(self, topic):
        """Restore persisted topic state from StateStore.

        Args:
            topic: Topic descriptor that determines the persistence key.
        """
        sid = str(self._service.unique_id)
        if sid.startswith("<MagicMock"):
            sid = "mock_service"
        name = str(self._name)
        if name.startswith("<MagicMock"):
            name = "mock_name"

        key = f"{sid}-{name}.state"
        self._persistence_key = key

        content = state_store.load_sync(Category.PVOUTPUT, key, stale_after=timedelta(hours=24), debug=active_config.pvoutput.log_level == logging.DEBUG)
        if content is not None:
            try:
                saved = json.loads(content, object_hook=Topic.json_decoder)
                if topic.topic in saved:
                    topic = saved[topic.topic]
                    self[topic.topic] = topic
                    self._logger.debug(
                        f"{self._service.log_identity} Restored {self._name} topic {topic.topic} (gain={topic.gain}) with {topic.state=} at {time.strftime('%H:%M', topic.timestamp) if topic.timestamp else 'None'}"
                    )
            except (json.JSONDecodeError, ValueError) as error:
                self._logger.warning(f"{self._service.log_identity} Failed to decode persisted state for {key}: {error}")
        else:
            self._logger.debug(f"{self._service.log_identity} No persisted state found for {key}")

    def reset(self) -> None:
        """Reset all tracked topic states and clear persistence files.

        Args:
            None.
        """
        for topic in self.values():
            topic.state = 0.0
            topic.timestamp = time.localtime()
            topic.previous_state = None
            topic.previous_timestamp = None
        for child in self._time_periods:
            child.reset()
        if self._persistence_key:
            state_store.delete_sync(Category.PVOUTPUT, self._persistence_key, debug=active_config.pvoutput.log_level == logging.DEBUG)

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Subscribe each registered topic to MQTT updates.

        Args:
            mqtt_client: MQTT client used to create subscriptions.
            mqtt_handler: MQTT handler used to register callbacks.
        """
        for topic in self.keys():
            if self.enabled:
                if topic.startswith("__ha_sensor__:"):
                    self._logger.debug(f"{self._service.log_identity} Skipping MQTT subscription for Home Assistant Supervisor source {topic} ({self._name})")
                    continue
                result = mqtt_handler.register(mqtt_client, topic, self.handle_update)
                self._logger.debug(f"{self._service.log_identity} Subscribed to topic {topic} to record {self._name} ({result=})")
            else:
                self._logger.debug(f"{self._service.log_identity} Not subscribing to topic {topic} because {self._name} uploading is disabled")

    async def handle_update(self, modbus_client: Any, mqtt_client: mqtt.Client | None, value: float | int | str, topic: str, handler: MqttHandler | None) -> bool:
        """Handle a new MQTT value and update aggregate state.

        Args:
            modbus_client: Modbus client reference (unused).
            mqtt_client: MQTT client reference (unused).
            value: Raw value received from MQTT.
            topic: MQTT topic that produced the value.
            handler: MQTT handler instance (unused).
        """
        if self.enabled:
            state = value if isinstance(value, float) else float(value)
            if Calculation.PEAK not in self.calculation or (self[topic].state is not None and state > cast(float, self[topic].state)):
                if active_config.pvoutput.update_debug_logging:
                    self._logger.debug(f"{self._service.log_identity} Updating {self._name} from topic {topic} {value=}")
                async with self._service.lock(timeout=1):
                    state_was = self[topic].state
                    self[topic].state = state
                    self[topic].timestamp = time.localtime()
                    if self._persistence_key and ((self._always_persist and state_was != state) or (self.calculation & (Calculation.DIFFERENCE | Calculation.PEAK)) or len(self._time_periods) > 0):
                        payload = json.dumps(self, default=Topic.json_encoder)
                        state_store.save_sync(Category.PVOUTPUT, self._persistence_key, payload, debug=active_config.pvoutput.update_debug_logging)
            elif active_config.pvoutput.update_debug_logging and state and Calculation.PEAK in self.calculation:
                ts = self[topic].timestamp
                if self[topic].restore_timestamp is not None and (ts is None or cast(time.struct_time, ts) < cast(time.struct_time, self[topic].restore_timestamp)):  # pyrefly: ignore
                    ts = self[topic].restore_timestamp

                if ts is not None:
                    seconds = time.mktime(time.localtime()) - time.mktime(cast(time.struct_time, ts))  # pyrefly: ignore
                    if int(seconds) % 60 == 0:
                        self._logger.debug(f"{self._service.log_identity} Ignoring {self._name} from topic {topic}: {state=} (<= Previous peak={self[topic].state})")
            if self._time_periods:
                current_period = active_config.pvoutput.current_time_period
                other_periods_total = sum((child.aggregate(True, never_return_none=True)[0] or 0.0) for child in self._time_periods if child._value_key not in current_period) / self[topic].gain
                this_period_state = max(state - other_periods_total, 0.0)
                if active_config.pvoutput.update_debug_logging:
                    cp_log = f"{current_period[0].value if len(current_period) > 0 and current_period[0] is not None else '-'}/{current_period[1].value if len(current_period) > 1 else '-'}"
                    self._logger.debug(f"{self._service.log_identity} Updating {self._name} children: {state=} {other_periods_total=} {this_period_state=} current_period={cp_log} {topic=}")
                for child in self._time_periods:
                    if child._value_key in current_period:
                        await child.handle_update(modbus_client, mqtt_client, this_period_state, topic, handler)
                    else:
                        await child.handle_update(modbus_client, mqtt_client, max(cast(float, child[topic].state) if child[topic].state is not None else 0.0, 0.0), topic, handler)
            return True
        else:
            return False


class TimePeriodServiceTopics(ServiceTopics):
    """ServiceTopics variant used for tariff time-period subfields."""

    def __init__(
        self,
        service: Service,
        enabled: bool,
        logger: logging.Logger,
        value_key: OutputField | StatusField,
        datetime_key: str | None = None,
        calc: Calculation = Calculation.SUM,
        decimals: int = 0,
        donation: bool = False,
    ):
        """Initialize a persistent child topic group for one tariff period.

        Args:
            service: Parent PVOutput service owning this topic group.
            enabled: Whether this period group is active.
            logger: Logger used for diagnostics.
            value_key: PVOutput payload key for this period.
            datetime_key: Optional companion payload key for timestamps.
            calc: Aggregation strategy flags.
            decimals: Decimal precision for rounded payload values.
            donation: Whether this field requires PVOutput donation status.
        """
        super().__init__(service, enabled, logger, value_key, datetime_key, calc, decimals, donation, persist=True)

    def register(self, topic: Topic) -> None:
        """Register a topic and immediately restore persisted state.

        Args:
            topic: Topic descriptor to track and restore.
        """
        if self.enabled:
            super().register(topic)
            self.restore_state(topic)

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """No-op: parent topic groups perform MQTT subscription.

        Args:
            mqtt_client: MQTT client instance (unused).
            mqtt_handler: MQTT handler instance (unused).
        """
        pass
