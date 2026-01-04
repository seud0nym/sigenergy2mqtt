from .types import DeviceType
from pathlib import Path
from pymodbus import ModbusException
from random import randint, uniform
from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.modbus import ModbusClient, ModbusLockFactory
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from sigenergy2mqtt.sensors.base import (
    AlarmCombinedSensor,
    DerivedSensor,
    EnergyDailyAccumulationSensor,
    ModbusSensor,
    ObservableMixin,
    ReadableSensorMixin,
    ReservedSensor,
    Sensor,
    WritableSensorMixin,
    WriteOnlySensor,
)
from sigenergy2mqtt.sensors.const import MAX_MODBUS_REGISTERS_PER_REQUEST
from typing import Awaitable, Callable, Iterable, Self
import abc
import asyncio
import json
import logging
import statistics
import time


class SensorGroup(list[ReadableSensorMixin]):
    def __init__(self, *sensors: ReadableSensorMixin):
        super().__init__(sensors)

    @property
    def scan_interval(self) -> int:
        if len(self) == 0:
            return 86400
        return min(sensor.scan_interval for sensor in self if isinstance(sensor, ReadableSensorMixin))

    def append(self, object):
        return super().append(object)


class Device(dict[str, any], metaclass=abc.ABCMeta):
    def __init__(self, name: str, plant_index: int, unique_id: str, manufacturer: str, model: str, protocol_version: Protocol, **kwargs):
        self.plant_index = plant_index
        self.protocol_version = protocol_version
        self.registers = None if plant_index >= len(Config.devices) else Config.devices[plant_index].registers

        self.children: list[Device] = []

        self.all_sensors: dict[str, Sensor] = {}
        self.group_sensors: dict[str, list[ReadableSensorMixin]] = {}
        self.read_sensors: dict[str, ReadableSensorMixin] = {}
        self.write_sensors: dict[str, WritableSensorMixin] = {}

        self._rediscover = False
        self._online: asyncio.Future = None

        self["name"] = name if Config.home_assistant.device_name_prefix == "" else f"{Config.home_assistant.device_name_prefix} {name}"
        self["ids"] = [unique_id]
        self["mf"] = manufacturer
        self["mdl"] = model

        for k, v in kwargs.items():
            self[k] = v

        logging.debug(f"Created Device {self}")
        DeviceRegistry.add(self.plant_index, self)

    # region Properties
    @property
    def name(self) -> str:
        return self["name"]

    @property
    def online(self) -> bool:
        return self._online

    @online.setter
    def online(self, value: bool | asyncio.Future) -> None:
        if isinstance(value, bool):
            if value:  # True
                raise ValueError("online must be a Future to enable")
            else:  # False
                logging.debug(f"{self.name} set to offline")
                if self._online:
                    self._online.cancel()
                self._online = False
                for sensor in self.sensors.values():
                    if sensor.sleeper_task is not None:
                        sensor.sleeper_task.cancel()
        elif isinstance(value, asyncio.Future):
            logging.debug(f"{self.name} set to online")
            self._online = value
        else:
            raise ValueError("online must be a Future or False")

    @property
    def rediscover(self) -> bool:
        return self._rediscover

    @rediscover.setter
    def rediscover(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("rediscover must be a boolean")
        self._rediscover = value
        if value:
            logging.info(f"{self.name} set to rediscover")
        else:
            logging.debug(f"{self.name} no longer set to rediscover")

    @property
    def sensors(self) -> dict[str, Sensor]:
        return self.all_sensors

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
        sensors = device.get_all_sensors(search_children=True)
        if any(s for s in sensors.values() if s.publishable):
            device.via_device = self.unique_id
            self.children.append(device)
        else:
            logging.debug(f"{self.name} - Cannot add child device {device.name} - No publishable sensors defined")

    def _add_derived_sensor(self, sensor: DerivedSensor, *from_sensors: Sensor, search_children: bool = False) -> None:
        none_sensors = len([s for s in from_sensors if s is None])
        if none_sensors:
            logging.debug(f"{self.name} - Removed {none_sensors} undefined source sensor{'s' if none_sensors != 1 else ''} for {sensor.__class__.__name__}")
            source_sensors = [s for s in from_sensors if s is not None]
        else:
            source_sensors = from_sensors
        if len(source_sensors) == 0:
            logging.error(f"{self.name} - Cannot add {sensor.__class__.__name__} - No source sensors defined")
        else:
            for to_sensor in source_sensors:
                found = self.get_sensor(to_sensor.unique_id, search_children=search_children)
                if not found:
                    logging.warning(f"{self.name} - Cannot add {sensor.__class__.__name__} - {to_sensor.__class__.__name__} is not a defined Sensor for {self.__class__.__name__}")
                else:
                    if isinstance(sensor, DerivedSensor):
                        to_sensor.add_derived_sensor(sensor)
                        self._add_to_all_sensors(sensor)
                    else:
                        logging.error(f"{self.name} - Cannot add {sensor.__class__.__name__} - not a DerivedSensor")

    def _add_read_sensor(self, sensor: ReadableSensorMixin, group: str = None) -> bool:
        if not isinstance(sensor, ReadableSensorMixin):
            logging.error(f"{self.name} - Cannot add {sensor.__class__.__name__} - not a ReadableSensorMixin")
            return False
        else:
            if group is None:
                self.read_sensors[sensor.unique_id] = sensor
                self._add_to_all_sensors(sensor)
            else:
                if group not in self.group_sensors:
                    self.group_sensors[group] = []
                self.group_sensors[group].append(sensor)
                self._add_to_all_sensors(sensor)
            return True

    def _add_to_all_sensors(self, sensor: Sensor) -> None:
        if not self.get_sensor(sensor.unique_id, search_children=True):
            sensor.apply_sensor_overrides(self.registers)
            sensor.parent_device = self
            sensor.configure_mqtt_topics(self.unique_id)
            self.all_sensors[sensor.unique_id] = sensor

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if not isinstance(sensor, WriteOnlySensor):
            logging.error(f"{self.name} - Cannot add {sensor.unique_id} ({sensor.unique_id}) - not a WriteOnlySensor")
        else:
            self.write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def _create_sensor_scan_groups(self) -> dict[str, list[ModbusSensor | ReadableSensorMixin]]:
        combined_sensors: dict[str, ModbusSensor | ReadableSensorMixin] = self.read_sensors.copy()
        combined_groups: dict[str, list[ModbusSensor | ReadableSensorMixin]] = self.group_sensors.copy()
        named_group_sensors: dict[int, ModbusSensor | ReadableSensorMixin] = {}
        first_address: int = None
        next_address: int = None
        device_address: int = None
        group_name: str = None
        scan_interval: int = None

        for device in self.children:
            combined_sensors.update(device.read_sensors)
            for group, sensor_list in device.group_sensors.items():
                if group not in combined_groups:
                    combined_groups[group] = []
                combined_groups[group].extend(sensor_list)
                named_group_sensors.update({s.address: s for s in sensor_list if isinstance(s, ModbusSensor)})

        for sensor in sorted([s for s in combined_sensors.values() if isinstance(s, ModbusSensor) and not isinstance(s, ReservedSensor)], key=lambda s: (s.scan_interval, s.device_address, s.address)):
            if (  # Conditions for creating a new sensor scan group
                Config.devices[self.plant_index].disable_chunking  # If chunking is disabled, always create a new group
                or group_name is None  # First sensor
                or device_address != sensor.device_address  # Device address changed
                or scan_interval != sensor.scan_interval  # Scan interval changed
                or sensor.address > next_address  # Non-contiguous addresses
                or (next_address - first_address + sensor.count) > MAX_MODBUS_REGISTERS_PER_REQUEST  # Modbus request size exceeded
            ):
                group_name = f"{sensor.device_address:03d}_{sensor.address:05d}_{sensor.scan_interval:05d}"
                combined_groups[group_name] = []
                first_address = sensor.address
            combined_groups[group_name].append(sensor)
            next_address = sensor.address + sensor.count
            while next_address in named_group_sensors:  # Include any named group sensors that fall within the range
                if (next_address - first_address + named_group_sensors[next_address].count) > MAX_MODBUS_REGISTERS_PER_REQUEST:
                    break
                else:
                    next_address += named_group_sensors[next_address].count
            device_address = sensor.device_address
            scan_interval = sensor.scan_interval

        group_name = None
        for sensor in sorted([s for s in combined_sensors.values() if isinstance(s, ReadableSensorMixin) and not isinstance(s, (AlarmCombinedSensor, ModbusSensor))], key=lambda s: (s.scan_interval)):
            if (  # Conditions for creating a new sensor scan group
                group_name is None  # First sensor
                or scan_interval != sensor.scan_interval  # Scan interval changed
            ):
                group_name = f"{sensor.__class__.__name__}_{sensor.scan_interval:05d}"
                combined_groups[group_name] = []
            combined_groups[group_name].append(sensor)
            scan_interval = sensor.scan_interval

        return combined_groups

    def get_all_sensors(self, search_children: bool = True) -> dict[str, Sensor]:
        """
        Returns all sensors in this device and its children.
        If search_children is False, only returns sensors in this device.
        """
        if search_children:
            all_sensors = self.all_sensors.copy()
            for child in self.children:
                all_sensors.update(child.get_all_sensors(search_children=True))
            return all_sensors
        else:
            return self.all_sensors

    def get_sensor(self, unique_id: str, search_children: bool = False) -> Sensor:
        if unique_id in self.all_sensors:
            return self.all_sensors[unique_id]
        elif search_children:
            for child in self.children:
                if unique_id in child.sensors:
                    return child.sensors[unique_id]
        for alarm in [s for s in self.all_sensors.values() if isinstance(s, AlarmCombinedSensor)]:
            if unique_id in [a.unique_id for a in alarm.alarms]:
                return next(a for a in alarm.alarms if a.unique_id == unique_id)
        if search_children:
            for child in self.children:
                for alarm in [s for s in child.all_sensors.values() if isinstance(s, AlarmCombinedSensor)]:
                    if unique_id in [a.unique_id for a in alarm.alarms]:
                        return next(a for a in alarm.alarms if a.unique_id == unique_id)
        return None

    async def on_ha_state_change(self, modbus: ModbusClient, mqtt: MqttClient, ha_state: str, source: str, mqtt_handler: MqttHandler) -> bool:
        if ha_state == "online":
            seconds = float(randint(0, 3) + (randint(0, 10) / 10))
            logging.info(f"{self.name} - Received online state from Home Assistant ({source=}): Republishing discovery and forcing republish of all sensors in {seconds:.1f}s")
            await asyncio.sleep(seconds)  # https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages
            await mqtt_handler.wait_for(2, self.name, self.publish_discovery, mqtt, clean=False)
            for sensor in self.sensors.values():
                await sensor.publish(mqtt, modbus=modbus, republish=True)
            return True
        else:
            return False

    def publish_attributes(self, mqtt: MqttClient, clean: bool = False, propagate: bool = True) -> None:
        for sensor in self.sensors.values():
            sensor.publish_attributes(mqtt, clean=clean)
        if propagate:
            for device in self.children:
                device.publish_attributes(mqtt, clean=clean, propagate=propagate)

    def publish_availability(self, mqtt: MqttClient, ha_state: str, qos: int = 2) -> None:
        mqtt.publish(f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/availability", ha_state, qos, True)
        for device in self.children:
            device.publish_availability(mqtt, ha_state)

    def publish_discovery(self, mqtt: MqttClient, clean: bool = False) -> any:
        topic = f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
        if clean:
            logging.debug(f"{self.name} - Cleaning availability")
            self.publish_availability(mqtt, None, qos=1)
            logging.debug(f"{self.name} - Cleaning discovery")
            info = mqtt.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        else:
            components = {}
            for sensor in self.sensors.values():
                components.update(sensor.get_discovery(mqtt))
            if len(components) > 0:
                discovery = {}
                discovery["dev"] = self
                discovery["o"] = Config.origin
                discovery["cmps"] = components
                discovery_json = json.dumps(discovery, allow_nan=False, indent=2, sort_keys=False)
                logging.debug(f"{self.name} - Publishing discovery")
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    discovery_dump = Path(Config.persistent_state_path, f"{self.unique_id}.discovery.json")
                    with discovery_dump.open("w") as f:
                        f.write(discovery_json)
                    logging.debug(f"{self.name} - Discovery JSON dumped to {discovery_dump.resolve()}")
                info = mqtt.publish(topic, discovery_json, qos=2, retain=True)
            else:
                logging.debug(f"{self.name} - Publishing empty availability (No components found)")
                self.publish_availability(mqtt, None, qos=1)
                logging.debug(f"{self.name} - Publishing empty discovery (No components found)")
                info = mqtt.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        self.publish_attributes(mqtt, clean, propagate=False)  # Don't propagate to children because it will happen automatically when child discovery is published
        for device in self.children:
            device.publish_discovery(mqtt, clean=clean)
        return info

    async def publish_updates(self, modbus: ModbusClient, mqtt: MqttClient, name: str, *sensors: ModbusSensor | ReadableSensorMixin) -> None:
        multiple: bool = len(sensors) > 1
        if multiple:
            first_address: int = min([s.address for s in sensors if isinstance(s, ModbusSensor) and s.publishable])
            last_address: int = max([s.address + s.count - 1 for s in sensors if isinstance(s, ModbusSensor) and s.publishable])
            count: int = last_address - first_address + 1
        elif isinstance(sensors[0], ModbusSensor):
            first_address: int = sensors[0].address
            count: int = sensors[0].count
            last_address: int = first_address + count - 1
        else:
            first_address: int = None
            count: int = None
            last_address: int = None
        interval: int = min([s.scan_interval for s in sensors])
        debug_logging: bool = False
        daily_sensors: bool = False
        for sensor in sensors:
            debug_logging = debug_logging or sensor.debug_logging or any(ds.debug_logging for ds in sensor._derived_sensors.values())
            daily_sensors = daily_sensors or any(isinstance(ds, EnergyDailyAccumulationSensor) for ds in sensor._derived_sensors.values())
            if sensor.publishable and sensor.latest_raw_state is not None:
                await sensor.publish(mqtt, modbus, republish=True)
        if debug_logging:
            logging.debug(f"{self.name} Sensor Scan Group [{name}] instantiated ({multiple=} {first_address=} {last_address=} {count=} sensors={len(sensors)})")
        last_publish: float = time.time()
        next_publish: float = last_publish + uniform(0.5, min(5, interval))
        actual_elapsed: list[float] = []
        if debug_logging:
            logging.debug(f"{self.name} Sensor Scan Group [{name}] commenced - first publish at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_publish))} (interval={interval}s {daily_sensors=})")
        lock = ModbusLockFactory.get(modbus)
        while self.online:
            now = time.time()  # Grab the started time first, so that elapsed contains ALL activity
            if any(sensor for sensor in sensors if sensor.force_publish):
                if debug_logging:
                    logging.debug(f"{self.name} Sensor Scan Group [{name}] wait interrupted with {next_publish - now:.2f}s remaining because force_publish set on {sensor.__class__.__name__}")
                next_publish = now  # If any sensor requires a force publish, process all of them now
            elif daily_sensors:
                now_struct: time.struct_time = time.localtime(now)
                was = time.localtime(last_publish)
                if was.tm_yday != now_struct.tm_yday:
                    logging.info(
                        f"{self.name} Sensor Scan Group [{name}] wait interrupted with {next_publish - now:.2f}s remaining because it contains at least one EnergyDailyAccumulationSensor and the day has changed ({was.tm_yday} -> {now_struct.tm_yday})"
                    )
                    next_publish = now
            if next_publish <= now:
                last_publish = now
                publishable_now = [s for s in sensors if s.publishable]
                try:
                    async with lock.lock():
                        if multiple and count <= MAX_MODBUS_REGISTERS_PER_REQUEST:
                            if debug_logging:
                                read_ahead_start = time.time()
                            exception_code = await modbus.read_ahead_registers(first_address, count=count, device_id=sensors[0].device_address, input_type=sensors[0].input_type, trace=debug_logging)
                            if exception_code == 0:
                                if debug_logging:
                                    logging.debug(f"{self.name} Sensor Scan Group [{name}] pre-read {first_address} to {last_address} ({count} registers) took {time.time() - read_ahead_start:.2f}s")
                            else:
                                match exception_code:
                                    case -1:
                                        reason = "NO RESPONSE FROM DEVICE"
                                    case 1:
                                        reason = "0x01 ILLEGAL FUNCTION"
                                    case 2:
                                        reason = "0x02 ILLEGAL DATA ADDRESS (pre-reads now disabled)"
                                        multiple = False
                                    case 3:
                                        reason = "0x03 ILLEGAL DATA VALUE"
                                    case 4:
                                        reason = "0x04 SLAVE DEVICE FAILURE"
                                    case _:
                                        reason = f"UNKNOWN PROBLEM ({exception_code=})"
                                logging.warning(f"{self.name} Sensor Scan Group [{name}] failed to pre-read {first_address} to {last_address} ({count} registers) - {reason}")
                        elif debug_logging:
                            logging.debug(f"{self.name} Sensor Scan Group [{name}] publishing sensors (interval={now - last_publish:.2f}s)")
                        for sensor in publishable_now:
                            await sensor.publish(mqtt, modbus)
                            if sensor.latest_interval is not None:
                                actual_elapsed.append(sensor.latest_interval)
                        elapsed = time.time() - now
                        average_excess = statistics.fmean(actual_elapsed) - interval if len(actual_elapsed) > 0 else 0
                        if elapsed > interval and modbus.connected:
                            logging.info(f"{self.name} Sensor Scan Group [{name}] exceeded scan interval ({interval=}s) {elapsed=:.2f}s {average_excess=:.3f}s")
                    if len(actual_elapsed) > 100:
                        actual_elapsed = actual_elapsed[-100:]
                    next_publish = time.time() + max(interval - elapsed, 0.5)
                    if debug_logging:
                        logging.debug(f"{self.name} Sensor Scan Group [{name}] {interval=}s {elapsed=:.2f}s next={next_publish - time.time():.2f}s {average_excess=:.3f}s")
                    if self.rediscover:
                        logging.debug(f"{self.name} Sensor Scan Group [{name}]: Acquiring lock to republish discovery... ({lock.waiters=})")
                        async with lock.lock(timeout=1):
                            self.rediscover = False
                            self.publish_discovery(mqtt, clean=False)
                except ModbusException as e:
                    lock = ModbusLockFactory.get(modbus)
                    logging.debug(f"{self.name} Sensor Scan Group [{name}] handling {e!s}: Acquiring lock before attempting to reconnect... ({lock.waiters=})")
                    async with lock.lock(timeout=None):
                        if not modbus.connected and self.online:
                            logging.info(f"{self.name} attempting to reconnect to Modbus...")
                            while not modbus.connected:
                                modbus.close()
                                await asyncio.sleep(0.5)
                                await modbus.connect()
                                await asyncio.sleep(1)
                            logging.info(f"{self.name} reconnected to Modbus")
                except Exception as e:
                    logging.error(f"{self.name} Sensor Scan Group [{name}] encountered an error: {repr(e)}")
            sleep = min(next_publish - time.time(), 1)  # Only sleep for a maximum of 1 second so that changes to self.online are handled more quickly
            if sleep > 0:
                task = asyncio.create_task(asyncio.sleep(sleep))
                for sensor in sensors:
                    sensor.sleeper_task = task
                try:
                    await task
                except asyncio.CancelledError:
                    if debug_logging:
                        logging.debug(f"{self.name} Sensor Scan Group [{name}] sleep interrupted")
                finally:
                    for sensor in sensors:
                        sensor.sleeper_task = None
        if debug_logging:
            logging.debug(f"{self.name} Sensor Scan Group [{name}] completed - {self.name} flagged as offline ({self.online=})")
        return

    async def republish_discovery(self, mqtt: MqttClient) -> None:
        wait = Config.home_assistant.republish_discovery_interval
        while self.online and Config.home_assistant.republish_discovery_interval > 0:
            await asyncio.sleep(1)
            wait -= 1
            if wait <= 0:
                logging.info(f"{self.name} - Re-publishing discovery")
                self.publish_discovery(mqtt, clean=False)
                wait = Config.home_assistant.republish_discovery_interval

    def schedule(self, modbus: ModbusClient, mqtt: MqttClient) -> list[Callable[[ModbusClient, MqttClient, Iterable[Sensor]], Awaitable[None]]]:
        groups = self._create_sensor_scan_groups()
        tasks = []
        for name, sensors in groups.items():
            if any([s for s in sensors if s.publishable]):
                tasks.append(self.publish_updates(modbus, mqtt, name, *sensors))
            else:
                logging.debug(f"{self.name} Sensor Scan Group [{name}] skipped because no sensors are publishable (unique_ids={[s.unique_id for s in sensors]})")
        if Config.home_assistant.enabled and Config.home_assistant.republish_discovery_interval > 0:
            tasks.append(self.republish_discovery(mqtt))
        return tasks

    def subscribe(self, mqtt: MqttClient, mqtt_handler: MqttHandler) -> None:
        if Config.home_assistant.enabled:
            result = mqtt_handler.register(mqtt, f"{Config.home_assistant.discovery_prefix}/status", self.on_ha_state_change)
            logging.debug(f"{self.name} subscribed to topic {Config.home_assistant.discovery_prefix}/status for Home Assistant state changes ({result=})")
        for sensor in self.sensors.values():
            if isinstance(sensor, WritableSensorMixin):
                try:
                    result = mqtt_handler.register(mqtt, sensor.command_topic, sensor.set_value)
                    if sensor.debug_logging:
                        logging.debug(f"Sensor {sensor.name} subscribed to topic {sensor.command_topic} for writing ({result=})")
                except Exception as e:
                    logging.error(f"Sensor {sensor.name} failed to subscribe to topic {sensor.command_topic}: {repr(e)}")
            if isinstance(sensor, ObservableMixin):
                for topic in sensor.observable_topics():
                    try:
                        result = mqtt_handler.register(mqtt, topic, sensor.notify)
                        if sensor.debug_logging:
                            logging.debug(f"Sensor {sensor.name} subscribed to topic {topic} for notification ({result=})")
                    except Exception as e:
                        logging.error(f"Sensor {sensor.name} failed to subscribe to topic {topic}: {repr(e)}")
        for device in self.children:
            device.subscribe(mqtt, mqtt_handler)


class ModbusDevice(Device, metaclass=abc.ABCMeta):
    """Abstract definition of a Sigenergy device"""

    def __init__(
        self,
        type: DeviceType,
        name: str,
        plant_index: int,
        device_address: int,
        model: str,
        protocol_version: Protocol,
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

        super().__init__(name, plant_index, unique_id, "Sigenergy", model, protocol_version, **kwargs)

        self.device_address = device_address
        self._device_type = type

    def _add_to_all_sensors(self, sensor: Sensor) -> None:
        super()._add_to_all_sensors(sensor)

    def _add_read_sensor(self, sensor: ReadableSensorMixin, group: str = None) -> bool:
        if self._device_type is not None and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.name} - Skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
            return False
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.name} - Skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {Config.protocol_version}")
            return False
        else:
            return super()._add_read_sensor(sensor, group)

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if self._device_type is not None and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.name} - Skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.name} - Skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {Config.protocol_version}")
        else:
            super()._add_writeonly_sensor(sensor)


class DeviceRegistry:
    _devices: dict[int, list[Device]] = dict()

    @classmethod
    def add(cls, plant_index: int, device: Device) -> None:
        if plant_index not in cls._devices:
            cls._devices[plant_index] = list()
        cls._devices[plant_index].append(device)

    @classmethod
    def get(cls, plant_index: int) -> tuple[Device]:
        if plant_index in cls._devices:
            return tuple(cls._devices[plant_index])
        return None
