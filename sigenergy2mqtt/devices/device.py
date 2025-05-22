from .types import DeviceType
from pymodbus import ModbusException
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from random import randint, uniform
from sigenergy2mqtt.config import Config, RegisterAccess
from sigenergy2mqtt.modbus import LockFactory
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from sigenergy2mqtt.sensors.base import ReadableSensorMixin, Sensor, DerivedSensor, ObservableMixin, ReadOnlySensor, WritableSensorMixin, WriteOnlySensor
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Self
import abc
import asyncio
import json
import logging
import statistics
import time


class Device(Dict[str, any], metaclass=abc.ABCMeta):
    def __init__(
        self,
        name: str,
        plant_index: int,
        unique_id: str,
        manufacturer: str,
        model: str,
        **kwargs,
    ):
        self._plant_index = plant_index
        self._registers = None if plant_index >= len(Config.devices) else Config.devices[plant_index].registers

        self._children: List[Device] = []

        self._all_sensors: Dict[str, Sensor] = {}
        self._group_sensors: Dict[str, List[ReadableSensorMixin]] = {}
        self._read_sensors: Dict[str, ReadableSensorMixin] = {}
        self._write_sensors: Dict[str, WritableSensorMixin] = {}

        self._force_publish = False
        self._online: asyncio.Future = None

        self["name"] = name if Config.home_assistant.device_name_prefix == "" else f"{Config.home_assistant.device_name_prefix} {name}"
        self["ids"] = [unique_id]
        self["mf"] = manufacturer
        self["mdl"] = model

        for k, v in kwargs.items():
            self[k] = v

        logging.debug(f"Created Device {self}")

    # region Properties
    @property
    def name(self) -> str:
        return self["name"]

    @property
    def online(self) -> bool:
        return self._online
    
    @property
    def registers(self) -> RegisterAccess:
        return self._registers

    @online.setter
    def online(self, value: bool | asyncio.Future) -> None:
        if isinstance(value, bool):
            if value: # True
                raise ValueError("online must be a Future to enable")
            else: # False
                logging.debug(f"{self.name} set to offline")
                for sensor in self.sensors.values():
                    if sensor.sleeper_task is not None:
                        sensor.sleeper_task.cancel()
                self._online.cancel()
                self._online = False
        elif isinstance(value, asyncio.Future):
            logging.debug(f"{self.name} set to online ({value})")
            self._online = value
        else:
           raise ValueError("online must be a Future or False")
    @property
    def sensors(self) -> Dict[str, Sensor]:
        return self._all_sensors

    @property
    def unique_id(self) -> str:
        return self["ids"][0]

    @property
    def via_device(self) -> str:
        return None if "via_device" not in self else self["via_device"]

    @via_device.setter
    def via_device(self, value) -> None:
        self["via_device"] = value

    # endregion

    def _add_child_device(self, device: Self) -> None:
        assert device != self, "Cannot add self as a child device"
        device.via_device = self.unique_id
        self._children.append(device)

    def _add_derived_sensor(self, sensor: DerivedSensor, *source_sensors: Sensor, search_children: bool = False) -> None:
        if len(source_sensors) == 0:
            logging.error(f"{self.__class__.__name__} - Cannot add {sensor.__class__.__name__} - No source sensors defined")
        else:
            for to_sensor in source_sensors:
                found = self.get_sensor(to_sensor.unique_id, search_children=search_children)
                if not found:
                    logging.error(f"{self.__class__.__name__} - Cannot add {sensor.__class__.__name__} - {to_sensor.__class__.__name__} is not a defined Sensor for {self.__class__.__name__}")
                else:
                    if issubclass(type(sensor), DerivedSensor):
                        to_sensor.add_derived_sensor(sensor)
                        self._add_to_all_sensors(sensor)
                    else:
                        logging.error(f"{self.__class__.__name__} - Cannot add {sensor.__class__.__name__} - not a DerivedSensor")

    def _add_read_sensor(self, sensor: ReadableSensorMixin, group: str = None) -> None:
        if not issubclass(type(sensor), ReadableSensorMixin):
            logging.error(f"{self.__class__.__name__} - Cannot add {sensor.__class__.__name__} - not a ReadableSensorMixin")
        else:
            if group is None:
                self._read_sensors[sensor.unique_id] = sensor
                self._add_to_all_sensors(sensor)
            else:
                if group not in self._group_sensors:
                    self._group_sensors[group] = []
                self._group_sensors[group].append(sensor)
                self._add_to_all_sensors(sensor)

    def _add_to_all_sensors(self, sensor: Sensor) -> None:
        if not self.get_sensor(sensor.unique_id, search_children=True):
            sensor.apply_sensor_overrides(self._registers)
            sensor.parent_device = self
            sensor.configure_mqtt_topics(self.unique_id)
            self._all_sensors[sensor.unique_id] = sensor

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if not issubclass(type(sensor), WriteOnlySensor):
            logging.error(f"{self.__class__.__name__} - Cannot add {sensor.unique_id} ({sensor.unique_id}) - not a WriteOnlySensor")
        else:
            self._write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def get_sensor(self, unique_id: str, search_children: bool = False) -> Sensor:
        if unique_id in self._all_sensors:
            return self._all_sensors[unique_id]
        elif search_children:
            for child in self._children:
                if unique_id in child.sensors:
                    return child.sensors[unique_id]
        return None

    async def on_ha_state_change(self, modbus: ModbusClient, mqtt: MqttClient, ha_state: str, source: str) -> bool:
        if ha_state == "online":
            time.sleep(randint(1, 10))  # https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages
            self.publish_discovery(mqtt)
            return True
        else:
            return False

    def publish_availability(self, mqtt: MqttClient, ha_state: str, qos: int = 2) -> None:
        mqtt.publish(f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/availability", ha_state, qos, True)
        for device in self._children:
            device.publish_availability(mqtt, ha_state)

    def publish_discovery(self, mqtt: MqttClient, force_publish: bool = True, clean: bool = False) -> List[Any]:
        topic = f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
        components = {}
        for sensor in self.sensors.values():
            components.update(sensor.get_discovery(force_publish=force_publish))
        if len(components) > 0:
            discovery = {}
            discovery["dev"] = self
            discovery["o"] = Config.origin
            discovery["cmps"] = components
            discovery_json = json.dumps(discovery, allow_nan=False, indent=2, sort_keys=False)
            if clean:
                logging.debug(f"Publishing empty discovery for {self.name} ({clean=})")
                mqtt.publish(topic, None, qos=1, retain=True)  # Clear retained messages
            logging.info(f"Publishing discovery for {self.name} ({force_publish=})")
            info = mqtt.publish(topic, discovery_json, qos=2, retain=True)
        else:
            logging.debug(f"Publishing empty availability for {self.name} (No components found)")
            self.publish_availability(mqtt, None, qos=1)
            logging.debug(f"Publishing empty discovery for {self.name} (No components found)")
            info = mqtt.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        for device in self._children:
            info = device.publish_discovery(mqtt)
        for sensor in self.sensors.values():
            sensor.publish_attributes(mqtt)
        return info

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        mqtt_handler.register(mqtt, f"{Config.home_assistant.discovery_prefix}/status", self.on_ha_state_change)
        for sensor in self.sensors.values():
            if isinstance(sensor, WritableSensorMixin):
                try:
                    mqtt_handler.register(mqtt, sensor.command_topic, sensor.set_value)
                    if sensor.debug_logging:
                        logging.debug(f"Sensor {sensor.name} subscribed to topic {sensor.command_topic} for writing")
                except Exception as e:
                    logging.error(f"Sensor {sensor.name} failed to subscribe to topic {sensor.command_topic}: {e}")
            if isinstance(sensor, ObservableMixin):
                for topic in sensor.observable_topics():
                    try:
                        mqtt_handler.register(mqtt, topic, sensor.notify)
                        if sensor.debug_logging:
                            logging.debug(f"Sensor {sensor.name} subscribed to topic {topic} for notification")
                    except Exception as e:
                        logging.error(f"Sensor {sensor.name} failed to subscribe to topic {topic}: {e}")
        for device in self._children:
            device.subscribe(mqtt, mqtt_handler)

    def schedule(self, modbus: ModbusClient, mqtt: MqttClient) -> List[Callable[[ModbusClient, MqttClient, Iterable[Sensor]], Awaitable[None]]]:
        async def publish_updates(modbus: ModbusClient, mqtt: MqttClient, *sensors: Sensor) -> None:
            interval = 86400
            publishable: list[Sensor] = []
            debug_logging = False
            for sensor in sensors:
                debug_logging = debug_logging or sensor.debug_logging
                if sensor.publishable:
                    publishable.append(sensor)
                    if isinstance(sensor, (ReadOnlySensor, ReadableSensorMixin)):  # ReadOnlySensor and subclasses (e.g. ReadWriteSensor)
                        interval = min(interval, sensor.scan_interval)
                    if sensor.latest_raw_state is not None:
                        await sensor.publish(mqtt, modbus, republish=True)
            if len(publishable) > 0:
                names = ",".join([sensor.__class__.__name__ for sensor in publishable])
                for sensor in publishable:
                    if isinstance(sensor, ReadOnlySensor) and interval != sensor.scan_interval:
                        logging.warning(f"Sensor {sensor.__class__.__name__} scan-interval ({sensor.scan_interval}s) ignored - the interval of {self.name} Sensor Group [{names}] is {interval}s")
                wait: float = uniform(0.5, min(5, interval))
                if debug_logging:
                    logging.debug(f"{self.name} Sensor Scan Group [{names}] initial wait is {wait} seconds")
                actual_elapsed: list[float] = []
                if debug_logging:
                    logging.debug(f"{self.name} Sensor Scan Group [{names}] commenced (Interval = {interval} seconds)")
                while self.online:
                    started = time.time()  # Grab the started time first, so that elapsed contains ALL activity
                    for sensor in publishable:
                        if sensor.force_publish:
                            if debug_logging:
                                logging.debug(f"{self.name} Sensor Scan Group [{names}] wait interrupted at {wait:.2f}s because force_publish set on {sensor.__class__.__name__}")
                            wait = 0  # If any sensor requires a force publish, process all of them now
                            break
                    if wait <= 0:
                        try:
                            for sensor in sensors:
                                if isinstance(sensor, ReadableSensorMixin) and sensor.publishable:  # ReadOnlySensor and subclasses (e.g. ReadWriteSensor, etc.)
                                    await sensor.publish(mqtt, modbus)
                                    actual_elapsed.append(sensor.latest_interval)
                                    if len(actual_elapsed) > 100:
                                        actual_elapsed = actual_elapsed[-100:]
                            average_excess = max(0.0, statistics.fmean(actual_elapsed) - interval)
                            elapsed = time.time() - started
                            if elapsed > interval and modbus.connected:
                                logging.warning(f"{self.name} Sensor Scan Group [{names}] exceeded scan interval ({interval}s) Elapsed = {elapsed:.2f}s Average Excess Time = {average_excess:.2f}s")
                            wait = interval
                        except ModbusException as e:
                            lock = LockFactory.get_lock(modbus)
                            try:
                                await lock.acquire()
                                if not modbus.connected and self.online:
                                    logging.info(f"{self.name} Sensor Scan Group [{names}] handling {e!s}: Attempting to reconnect...")
                                    while not modbus.connected:
                                        modbus.close()
                                        await asyncio.sleep(0.5)
                                        await modbus.connect()
                                        await asyncio.sleep(1)
                                    logging.info(f"{self.name} Sensor Scan Group [{names}] reconnected to Modbus")
                            finally:
                                lock.release()
                    sleep = min(wait, 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
                    wait -= sleep
                    if wait > 0:
                        task = asyncio.create_task(asyncio.sleep(sleep))
                        for sensor in sensors:
                            sensor.sleeper_task = task
                        try:
                            await task
                        except asyncio.CancelledError:
                            if debug_logging:
                                logging.debug(f"{self.name} Sensor Scan Group [{names}] sleep interrupted")
                        finally:
                            for sensor in sensors:
                                sensor.sleeper_task = None
                if debug_logging:
                    logging.debug(f"{self.name} Sensor Scan Group [{names}] completed - {self.name} flagged as offline ({self.online=})")
            else:
                if debug_logging:
                    logging.debug(f"{self.name} Sensor Scan Group [{','.join([sensor.name for sensor in sensors])}] skipped (No publishable sensors found)")
            return

        async def republish_discovery(mqtt: MqttClient) -> None:
            wait = Config.home_assistant.republish_discovery_interval
            while self.online and Config.home_assistant.republish_discovery_interval > 0:
                await asyncio.sleep(1)
                wait -= 1
                if wait <= 0:
                    logging.info(f"Re-publishing discovery for {self.name}")
                    self.publish_discovery(mqtt, force_publish=False)
                    wait = Config.home_assistant.republish_discovery_interval

        combined_sensors: Dict[str, ReadableSensorMixin] = self._read_sensors.copy()
        combined_groups: Dict[str, List[ReadableSensorMixin]] = self._group_sensors.copy()
        for device in self._children:
            combined_sensors.update(device._read_sensors)
            for group, sensor_list in device._group_sensors.items():
                if group not in combined_groups:
                    combined_groups[group] = []
                combined_groups[group].extend(sensor_list)

        tasks = [publish_updates(modbus, mqtt, sensor) for sensor in combined_sensors.values()]
        for sensors in combined_groups.values():
            tasks.append(publish_updates(modbus, mqtt, *sensors))
        if Config.home_assistant.enabled and Config.home_assistant.republish_discovery_interval > 0:
            tasks.append(republish_discovery(mqtt))
        return tasks


class ModBusDevice(Device, metaclass=abc.ABCMeta):
    """Abstract definition of a Sigenergy device"""

    def __init__(
        self,
        type: DeviceType,
        name: str,
        plant_index: int,
        device_address: int,
        model: str,
        **kwargs,
    ):
        assert 1 <= device_address <= 247, f"Invalid device address {device_address}"

        if "unique_id" in kwargs:
            assert isinstance(kwargs["unique_id"], str) and kwargs["unique_id"].startswith(Config.home_assistant.unique_id_prefix), (
                f"unique_id must be a string, starting with '{Config.home_assistant.unique_id_prefix}'"
            )
            unique_id = kwargs["unique_id"]
            del kwargs["unique_id"]
        else:
            unique_id = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}"

        super().__init__(name, plant_index, unique_id, "Sigenergy", model, **kwargs)

        self._device_address = device_address
        self._type = type

    @property
    def device_address(self) -> int:
        return self._device_address

    def _add_to_all_sensors(self, sensor: Sensor) -> None:
        super()._add_to_all_sensors(sensor)

    def _add_read_sensor(self, sensor: ReadableSensorMixin, group: str = None) -> None:
        if self._type is not None and not isinstance(sensor, self._type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.__class__.__name__} - Skipped adding {sensor.__class__.__name__} - not a {self._type.__class__.__name__}")
        super()._add_read_sensor(sensor, group)

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if self._type is not None and not isinstance(sensor, self._type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.__class__.__name__} - Skipped adding {sensor.__class__.__name__} - not a {self._type.__class__.__name__}")
        else:
            super()._add_writeonly_sensor(sensor)
