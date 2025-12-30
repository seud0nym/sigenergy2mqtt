from .service_topics import Calculation, ServiceTopics
from .service import Service
from .topic import Topic
from sigenergy2mqtt.config import Config, StatusField, VoltageSource
from typing import Any, Awaitable, Callable, Iterable, List
import asyncio
import logging
import time


class PVOutputStatusService(Service):
    def __init__(self, logger: logging.Logger, topics: dict[StatusField, list[Topic]], extended_data: dict[StatusField, str]):
        super().__init__("PVOutput Add Status Service", unique_id="pvoutput_status", model="PVOutput.AddStatus", logger=logger)

        _v1 = ServiceTopics(self, False, logger, value_key=StatusField.GENERATION_ENERGY)
        _v2 = ServiceTopics(self, True, logger, value_key=StatusField.GENERATION_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
        _v3 = ServiceTopics(self, False and Config.pvoutput.consumption_enabled, logger, value_key=StatusField.CONSUMPTION_ENERGY)
        _v4 = ServiceTopics(self, Config.pvoutput.consumption_enabled, logger, value_key=StatusField.CONSUMPTION_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS)
        _v5 = ServiceTopics(self, True if Config.pvoutput.temperature_topic else False, logger, value_key=StatusField.TEMPERATURE, calc=Calculation.AVERAGE, decimals=1, negative=True)
        _v6 = ServiceTopics(self, True, logger, value_key=StatusField.VOLTAGE, calc=Calculation.L_L_AVG if Config.pvoutput.voltage == VoltageSource.L_L_AVG else Calculation.AVERAGE, decimals=1)
        _v7 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V7] else False, logger, value_key=StatusField.V7, calc=Calculation.AVERAGE, donation=True, negative=True)
        _v8 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V8] else False, logger, value_key=StatusField.V8, calc=Calculation.AVERAGE, donation=True, negative=True)
        _v9 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V9] else False, logger, value_key=StatusField.V9, calc=Calculation.AVERAGE, donation=True, negative=True)
        _v10 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V10] else False, logger, value_key=StatusField.V10, calc=Calculation.AVERAGE, donation=True, negative=True)
        _v11 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V11] else False, logger, value_key=StatusField.V11, calc=Calculation.AVERAGE, donation=True, negative=True)
        _v12 = ServiceTopics(self, True if Config.pvoutput.extended[StatusField.V12] else False, logger, value_key=StatusField.V12, calc=Calculation.AVERAGE, donation=True, negative=True)
        _b1 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_POWER, calc=Calculation.SUM | Calculation.DIFFERENCE | Calculation.CONVERT_TO_WATTS, decimals=1, donation=True, negative=True)
        _b2 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_SOC, calc=Calculation.AVERAGE, donation=True, decimals=1)
        _b3 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_CAPACITY, donation=True)
        _b4 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_CHARGED, donation=True)
        _b5 = ServiceTopics(self, True, logger, value_key=StatusField.BATTERY_DISCHARGED, donation=True)
        _b6 = ServiceTopics(self, False, logger, value_key=StatusField.BATTERY_STATE, donation=True)

        self._previous_payload: dict = None
        self._service_topics: dict[str, ServiceTopics] = {
            StatusField.GENERATION_ENERGY: _v1,
            StatusField.GENERATION_POWER: _v2,
            StatusField.CONSUMPTION_ENERGY: _v3,
            StatusField.CONSUMPTION_POWER: _v4,
            StatusField.TEMPERATURE: _v5,
            StatusField.VOLTAGE: _v6,
            StatusField.V7: _v7,
            StatusField.V8: _v8,
            StatusField.V9: _v9,
            StatusField.V10: _v10,
            StatusField.V11: _v11,
            StatusField.V12: _v12,
            StatusField.BATTERY_POWER: _b1,
            StatusField.BATTERY_SOC: _b2,
            StatusField.BATTERY_CAPACITY: _b3,
            StatusField.BATTERY_CHARGED: _b4,
            StatusField.BATTERY_DISCHARGED: _b5,
            StatusField.BATTERY_STATE: _b6,
        }

        for field, topic_list in topics.items():
            if field in self._service_topics:
                if field in extended_data and extended_data[field] == "energy":
                    self._service_topics[field].calculation = Calculation.SUM | Calculation.DIFFERENCE
                for topic in topic_list:
                    self._service_topics[field].register(topic)
                    if topic.precision is not None:
                        self._service_topics[field].decimals = topic.precision
            else:
                self.logger.debug(f"{self.__class__.__name__} IGNORED unrecognized {field} with topic {topic.topic}")

    def _create_payload(self, now: time.struct_time) -> tuple[dict[str, any], dict[str, dict[str, tuple[float | int, time.struct_time]]]]:
        payload: dict[str, any] = {"d": time.strftime("%Y%m%d", now), "t": time.strftime("%H:%M", now)}
        topics: list[ServiceTopics] = [t for t in self._service_topics.values() if t.enabled and (not t.requires_donation or Service._donator)]
        snapshot: dict[str, dict[str, tuple[float | int, time.struct_time]]] = {
            st.value: {t.topic: (t.previous_state, t.previous_timestamp) for t in st_topics.values()}
            for st, st_topics in self._service_topics.items()
            if st_topics.enabled and (not st_topics.requires_donation or Service._donator)
        }
        for topic in topics:
            topic.add_to_payload(payload, Service._interval, now)
        return payload, snapshot

    async def seconds_until_status_upload(self, rand_min: int = 1, rand_max: int = 15) -> tuple[float, int]:
        seconds, next_time = await super().seconds_until_status_upload(rand_min, rand_max)
        self.logger.debug(f"{self.__class__.__name__} Next update at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_time))} ({seconds:.2f}s)")
        return seconds, next_time

    def schedule(self, modbus: Any, mqtt: Any) -> List[Callable[[Any, Any, Iterable[Any]], Awaitable[None]]]:
        async def publish_updates(modbus: Any, mqtt: Any, *sensors: Any) -> None:
            self.logger.info(f"{self.__class__.__name__} Commenced")
            wait, _ = await self.seconds_until_status_upload()
            while self.online:
                try:
                    if wait <= 0:
                        now = time.localtime()
                        async with self.lock(timeout=5):
                            payload, snapshot = self._create_payload(now)
                        if (  # At least one of the values v1, v2, v3 or v4 must be present
                            payload.get(StatusField.GENERATION_ENERGY.value) is not None
                            or payload.get(StatusField.GENERATION_POWER.value) is not None
                            or payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None
                            or (payload.get(StatusField.CONSUMPTION_POWER.value) is not None and Config.pvoutput.consumption_enabled)
                        ):
                            if payload.get(StatusField.GENERATION_ENERGY.value) is not None and payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None:
                                payload["c1"] = 1
                            elif payload.get(StatusField.GENERATION_ENERGY.value) is not None and StatusField.CONSUMPTION_ENERGY.value not in payload:
                                payload["c1"] = 2
                            elif payload.get(StatusField.CONSUMPTION_ENERGY.value) is not None:
                                payload["c1"] = 3
                            if payload.get(StatusField.CONSUMPTION_POWER.value, 0) < 0:
                                self.logger.warning(
                                    f"{self.__class__.__name__} Adjusted {StatusField.CONSUMPTION_POWER.name} (payload['{StatusField.CONSUMPTION_POWER.value}']) to 0 from {payload[StatusField.CONSUMPTION_POWER]} to comply with PVOutput requirements"
                                )
                                payload[StatusField.CONSUMPTION_POWER] = 0  # PVOutput does not accept negative consumption power values
                            uploaded = await self.upload_payload("https://pvoutput.org/service/r2/addstatus.jsp", payload)
                            if not uploaded:
                                self.logger.debug(f"{self.__class__.__name__} Restoring previous state of topics due to failed upload")
                                async with self.lock(timeout=5):
                                    for st, topics_dict in self._service_topics.items():
                                        for topic in topics_dict.values():
                                            if st.value in snapshot and topic.topic in snapshot[st.value]:
                                                topic.previous_state, topic.previous_timestamp = snapshot[st.value][topic.topic]
                        else:
                            self.logger.warning(f"{self.__class__.__name__} No generation{' or consumption data' if Config.pvoutput.consumption_enabled else ''} to upload, skipping... ({payload=})")
                        wait, _ = await self.seconds_until_status_upload()
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
