import abc
import asyncio
import json
import logging
import time
from pathlib import Path
from random import randint, uniform
from typing import Any, Awaitable, cast

import paho.mqtt.client as mqtt
from pymodbus import ModbusException

from sigenergy2mqtt.common import DeviceType, Protocol, RegisterAccess
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus import ModbusLockFactory
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.base import (
    AlarmCombinedSensor,
    DerivedSensor,
    EnergyDailyAccumulationSensor,
    ModbusSensorMixin,
    ObservableMixin,
    ReadableSensorMixin,
    ReservedSensor,
    Sensor,
    WritableSensorMixin,
    WriteOnlySensor,
)
from sigenergy2mqtt.sensors.const import MAX_MODBUS_REGISTERS_PER_REQUEST, InputType


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


class Device(dict[str, str | list[str]], metaclass=abc.ABCMeta):
    def __init__(self, name: str, plant_index: int, unique_id: str, manufacturer: str, model: str, protocol_version: Protocol, **kwargs):
        self.plant_index = plant_index
        self.protocol_version = protocol_version
        self.registers: RegisterAccess | None = None if plant_index < 0 or plant_index >= len(Config.devices) else Config.devices[plant_index].registers

        self.children: list[Device] = []

        self.all_sensors: dict[str, Sensor] = {}
        self.group_sensors: dict[str, list[ReadableSensorMixin]] = {}
        self.read_sensors: dict[str, ReadableSensorMixin] = {}
        self.write_sensors: dict[str, WritableSensorMixin] = {}

        self._rediscover = False
        self._online: asyncio.Future | bool | None = None

        self["name"] = self.name = name if Config.home_assistant.device_name_prefix == "" else f"{Config.home_assistant.device_name_prefix} {name}"
        self["ids"] = [unique_id]
        self["mf"] = manufacturer
        self["mdl"] = model

        for k, v in kwargs.items():
            self[k] = v

        logging.debug(f"Created Device {self}")
        DeviceRegistry.add(self.plant_index, self)

    # region Properties
    @property
    def online(self) -> bool:
        return self._online if isinstance(self._online, bool) else (self._online is not None)

    @online.setter
    def online(self, value: bool | asyncio.Future) -> None:
        if isinstance(value, bool):
            if value:  # True
                raise ValueError("online must be a Future to enable")
            else:  # False
                logging.debug(f"{self.name} set to offline")
                if isinstance(self._online, asyncio.Future):
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
        if Config.home_assistant.enabled:
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
    def via_device(self) -> str | None:
        return None if "via_device" not in self else cast(str, self["via_device"])

    @via_device.setter
    def via_device(self, value: str) -> None:
        self["via_device"] = value

    # endregion

    def _add_child_device(self, device: "Device") -> None:
        assert device != self, "Cannot add self as a child device"
        sensors = device.get_all_sensors(search_children=True)
        if any(s.publishable for s in sensors.values()):
            device.via_device = self.unique_id
            self.children.append(device)
        else:
            logging.debug(f"{self.name} cannot add child device {device.name} - No publishable sensors defined")

    def _add_derived_sensor(self, sensor: DerivedSensor, *from_sensors: Sensor | None, search_children: bool = False) -> None:
        none_sensors = len([s for s in from_sensors if s is None])
        if none_sensors:
            logging.debug(f"{self.name} removed {none_sensors} undefined source sensor{'s' if none_sensors != 1 else ''} for {sensor.__class__.__name__}")
            source_sensors: list[Sensor] = [s for s in from_sensors if s is not None]
        else:
            source_sensors = cast(list[Sensor], from_sensors)
        if len(source_sensors) == 0:
            logging.error(f"{self.name} cannot add {sensor.__class__.__name__} - No source sensors defined")
        else:
            for to_sensor in source_sensors:
                found = self.get_sensor(to_sensor.unique_id, search_children=search_children)
                if not found:
                    logging.warning(f"{self.name} cannot add {sensor.__class__.__name__} - {to_sensor.__class__.__name__} is not a defined Sensor for {self.__class__.__name__}")
                else:
                    if isinstance(sensor, DerivedSensor):
                        to_sensor.add_derived_sensor(sensor)
                        self._add_to_all_sensors(sensor)
                    else:
                        logging.error(f"{self.name} cannot add {sensor.__class__.__name__} - not a DerivedSensor")

    def _add_read_sensor(self, sensor: Sensor, group: str | None = None) -> bool:
        if not isinstance(sensor, ReadableSensorMixin):
            logging.error(f"{self.name} cannot add {sensor.__class__.__name__} - not a ReadableSensorMixin")
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
            if sensor.debug_logging:
                logging.debug(f"{self.name} adding sensor {sensor.unique_id} ({sensor.__class__.__name__})")
            sensor.apply_sensor_overrides(self.registers)
            sensor.parent_device = self
            sensor.configure_mqtt_topics(self.unique_id)
            self.all_sensors[sensor.unique_id] = sensor
        elif sensor.debug_logging:
            logging.debug(f"{self.name} skipped adding sensor {sensor.unique_id} ({sensor.__class__.__name__}) - already exists")

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if not isinstance(sensor, WriteOnlySensor):
            logging.error(f"{self.name} cannot add {sensor.unique_id} ({sensor.unique_id}) - not a WriteOnlySensor")
        else:
            self.write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def _create_sensor_scan_groups(self) -> dict[str, list[ReadableSensorMixin]]:
        combined_sensors: dict[str, ReadableSensorMixin] = self.read_sensors.copy()
        combined_groups: dict[str, list[ReadableSensorMixin]] = self.group_sensors.copy()
        named_group_sensors: dict[int, ModbusSensorMixin] = {s.address: s for sublist in self.group_sensors.values() for s in sublist if isinstance(s, ModbusSensorMixin)}
        first_address: int = -1
        next_address: int = -1
        device_address: int = -1
        group_name: str | None = None

        for device in self.children:
            combined_sensors.update(device.read_sensors)
            for group, sensor_list in device.group_sensors.items():
                if group not in combined_groups:
                    combined_groups[group] = []
                combined_groups[group].extend(sensor_list)
                named_group_sensors.update({s.address: s for s in sensor_list if isinstance(s, ModbusSensorMixin)})

        # Create Modbus sensor scan groups for sensors that are not already in a named group
        # Grouped by device_address and contiguous addresses only (scan_interval handled per-sensor in publish_updates)
        for sensor in sorted(
            [s for s in combined_sensors.values() if isinstance(s, (AlarmCombinedSensor, ModbusSensorMixin)) and s not in [gs for lst in combined_groups.values() for gs in lst]],
            key=lambda s: (s.device_address, s.address),
        ):
            if (  # Conditions for creating a new sensor scan group
                Config.devices[self.plant_index].disable_chunking  # If chunking is disabled, always create a new group
                or group_name is None  # First sensor
                or device_address != sensor.device_address  # Device address changed
                or sensor.address > next_address  # Non-contiguous addresses
                or (next_address - first_address + sensor.count) > MAX_MODBUS_REGISTERS_PER_REQUEST  # Modbus request size exceeded
            ):
                # Don't start a group with a ReservedSensor
                if isinstance(sensor, ReservedSensor):
                    continue

                group_name = f"{sensor.device_address:03d}_{sensor.address:05d}"
                combined_groups[group_name] = []
                first_address = sensor.address

            # If we skipped creating a group (because of ReservedSensor), we can't append
            if group_name is not None:
                combined_groups[group_name].append(sensor)

            next_address = sensor.address + sensor.count
            while next_address in named_group_sensors:  # Include any named group sensors that fall within the range
                if (next_address - first_address + named_group_sensors[next_address].count) > MAX_MODBUS_REGISTERS_PER_REQUEST:
                    break
                else:
                    next_address += named_group_sensors[next_address].count
            device_address = sensor.device_address

        # Post-process groups to remove trailing ReservedSensors and empty groups
        for group_name in combined_groups.keys():
            group = combined_groups[group_name]
            while group and isinstance(group[-1], ReservedSensor):
                group.pop()
            if not group:
                del combined_groups[group_name]

        # Create a single scan group for remaining non-Modbus readable sensors
        non_modbus_sensors = [
            s for s in combined_sensors.values() if not isinstance(s, ModbusSensorMixin) and isinstance(s, ReadableSensorMixin) and s not in [gs for lst in combined_groups.values() for gs in lst]
        ]
        if non_modbus_sensors:
            group_name = "non_modbus_sensors"
            combined_groups[group_name] = non_modbus_sensors

        sensors = len([s.unique_id for lst in combined_groups.values() for s in lst])
        groups = len(combined_groups)
        logging.info(f"{self.name} created {groups} Sensor Scan Group{'s' if groups != 1 else ''} containing {sensors} sensor{'s' if sensors != 1 else ''}")

        return combined_groups

    def get_all_sensors(self, search_children: bool = True) -> dict[str, Sensor]:
        if search_children:
            all_sensors = self.all_sensors.copy()
            for child in self.children:
                all_sensors.update(child.get_all_sensors(search_children=True))
            return all_sensors
        else:
            return self.all_sensors

    def get_sensor(self, unique_id: str, search_children: bool = False) -> Sensor | None:
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

    async def on_ha_state_change(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, ha_state: str, source: str, mqtt_handler: MqttHandler) -> bool:
        if ha_state == "online":
            seconds = float(randint(0, 3) + (randint(0, 10) / 10))
            logging.info(f"{self.name} received online state from Home Assistant ({source=}): Republishing discovery and forcing republish of all sensors in {seconds:.1f}s")
            try:
                await asyncio.sleep(seconds)  # https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages
                await mqtt_handler.wait_for(2, self.name, self.publish_discovery, mqtt_client, clean=False)
                for sensor in self.sensors.values():
                    await sensor.publish(mqtt_client, modbus_client=modbus_client, republish=True)
                return True
            except asyncio.CancelledError:
                logging.debug(f"{self.__class__.__name__} on_ha_state_change sleep interrupted")
                return False
        else:
            return False

    def publish_attributes(self, mqtt_client: mqtt.Client, clean: bool = False, propagate: bool = True) -> None:
        for sensor in self.sensors.values():
            sensor.publish_attributes(mqtt_client, clean=clean)
        if propagate:
            for device in self.children:
                device.publish_attributes(mqtt_client, clean=clean, propagate=propagate)

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        mqtt_client.publish(f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/availability", ha_state, qos, True)
        for device in self.children:
            device.publish_availability(mqtt_client, ha_state)

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        topic = f"{Config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
        if clean:
            logging.debug(f"{self.name} cleaning availability")
            self.publish_availability(mqtt_client, None, qos=1)
            logging.debug(f"{self.name} cleaning discovery")
            info = mqtt_client.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        else:
            components = {}
            for sensor in self.sensors.values():
                components.update(sensor.get_discovery(mqtt_client))
            if len(components) > 0:
                discovery: dict[str, Any] = {}
                discovery["dev"] = self
                discovery["o"] = Config.origin
                discovery["cmps"] = components
                discovery_json = json.dumps(discovery, allow_nan=False, indent=2, sort_keys=False)
                logging.debug(f"{self.name} publishing discovery")
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    discovery_dump = Path(Config.persistent_state_path, f"{self.unique_id}.discovery.json")
                    with discovery_dump.open("w") as f:
                        f.write(discovery_json)
                    logging.debug(f"{self.name} discovery JSON dumped to {discovery_dump.resolve()}")
                info = mqtt_client.publish(topic, discovery_json, qos=2, retain=True)
            else:
                logging.debug(f"{self.name} publishing empty availability (No components found)")
                self.publish_availability(mqtt_client, None, qos=1)
                logging.debug(f"{self.name} publishing empty discovery (No components found)")
                info = mqtt_client.publish(topic, None, qos=1, retain=True)  # Clear retained messages
        self.publish_attributes(mqtt_client, clean, propagate=False)  # Don't propagate to children because it will happen automatically when child discovery is published
        for device in self.children:
            device.publish_discovery(mqtt_client, clean=clean)
        return info

    async def publish_updates(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, name: str, *sensors: Sensor) -> None:
        # Setup for Modbus read-ahead optimization
        modbus_sensors = [s for s in sensors if isinstance(s, ModbusSensorMixin)]
        first_address: int = -1
        last_address: int = -1
        count: int = -1
        device_address: int = -1
        input_type: InputType = InputType.NONE

        if modbus_sensors:
            first_address = min([s.address for s in modbus_sensors if s.publishable])
            last_address = max([s.address + s.count - 1 for s in modbus_sensors if s.publishable])
            count = last_address - first_address + 1
            device_address, input_type = next((s.device_address, s.input_type) for s in modbus_sensors if s.address == first_address)

        multiple: bool = len(modbus_sensors) > 1 and 1 <= count <= MAX_MODBUS_REGISTERS_PER_REQUEST

        debug_logging: bool = False
        daily_sensors: list[ReadableSensorMixin] = []

        # Initialize per-sensor next publish times
        next_publish_times: dict[ReadableSensorMixin, float] = {}
        now = time.time()
        for sensor in sensors:
            debug_logging = debug_logging or sensor.debug_logging or any(ds.debug_logging for ds in sensor._derived_sensors.values())
            if isinstance(sensor, ReadableSensorMixin):
                # Track sensors with EnergyDailyAccumulationSensor derived sensors
                if any(isinstance(ds, EnergyDailyAccumulationSensor) for ds in sensor._derived_sensors.values()):
                    daily_sensors.append(sensor)
                # Initialize with staggered start times
                next_publish_times[sensor] = now + uniform(0.5, min(5, sensor.scan_interval))
                # Publish initial state if available
                if sensor.publishable and sensor.latest_raw_state is not None:
                    await sensor.publish(mqtt_client, modbus_client, republish=True)

        if debug_logging:
            logging.debug(f"{self.name} Sensor Scan Group [{name}] instantiated ({multiple=} {first_address=} {last_address=} {count=} sensors={len(sensors)} daily_sensors={len(daily_sensors)})")

        lock = ModbusLockFactory.get(modbus_client)
        last_day = time.localtime(now).tm_yday

        while self.online:
            now = time.time()
            now_struct = time.localtime(now)

            # Check for day change (affects daily sensors)
            day_changed = now_struct.tm_yday != last_day
            if day_changed:
                last_day = now_struct.tm_yday
                for sensor in daily_sensors:
                    if sensor.publishable:
                        next_publish_times[sensor] = now  # Force immediate publish
                        if debug_logging:
                            logging.debug(f"{self.name} Sensor Scan Group [{name}] day changed, forcing {sensor.__class__.__name__} to publish")

            # Determine which sensors are due for publishing
            due_sensors: list[ReadableSensorMixin] = []
            for sensor, next_time in next_publish_times.items():
                if not sensor.publishable:
                    continue
                if sensor.force_publish:
                    if debug_logging:
                        logging.debug(f"{self.name} Sensor Scan Group [{name}] force_publish set on {sensor.__class__.__name__}")
                    due_sensors.append(sensor)
                elif next_time <= now:
                    due_sensors.append(sensor)

            if due_sensors:
                try:
                    if modbus_client:
                        async with lock.lock():
                            # Optimize Modbus read-ahead for due Modbus sensors with contiguous addresses
                            due_modbus = [s for s in due_sensors if isinstance(s, ModbusSensorMixin)]
                            if multiple and len(due_modbus) > 0:
                                read_ahead_start = 0.0
                                if debug_logging:
                                    read_ahead_start = time.time()
                                exception_code = await modbus_client.read_ahead_registers(first_address, count=count, device_id=device_address, input_type=input_type, trace=debug_logging)
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

                    # Publish each due sensor and update its next publish time
                    for sensor in due_sensors:
                        await sensor.publish(mqtt_client, modbus_client)
                        next_publish_times[sensor] = now + sensor.scan_interval
                        sensor.force_publish = False

                    if self.rediscover:
                        self.rediscover = False
                        self.publish_discovery(mqtt_client, clean=False)

                except ModbusException as e:
                    if modbus_client:
                        lock = ModbusLockFactory.get(modbus_client)
                        logging.debug(f"{self.name} Sensor Scan Group [{name}] handling {e!s}: Acquiring lock before attempting to reconnect... ({lock.waiters=})")
                        async with lock.lock(timeout=None):
                            if not modbus_client.connected and self.online:
                                logging.info(f"{self.name} attempting to reconnect to Modbus...")
                                while not modbus_client.connected:
                                    modbus_client.close()
                                    await asyncio.sleep(0.5)
                                    await modbus_client.connect()
                                    await asyncio.sleep(1)
                                logging.info(f"{self.name} reconnected to Modbus")
                except Exception as e:
                    logging.error(f"{self.name} Sensor Scan Group [{name}] encountered an error: {repr(e)}")

            # Sleep until the next sensor is due (max 1 second to stay responsive to online changes)
            if next_publish_times:
                next_due = min(next_publish_times.values())
                sleep_duration = max(0.1, min(next_due - time.time(), 1))
            else:
                sleep_duration = 1

            if sleep_duration > 0:
                task = asyncio.create_task(asyncio.sleep(sleep_duration))
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

    async def republish_discovery(self, mqtt_client: mqtt.Client) -> None:
        wait = Config.home_assistant.republish_discovery_interval
        while self.online and Config.home_assistant.republish_discovery_interval > 0:
            try:
                await asyncio.sleep(1)
                wait -= 1
                if wait <= 0:
                    logging.info(f"{self.name} re-publishing discovery")
                    self.publish_discovery(mqtt_client, clean=False)
                    wait = Config.home_assistant.republish_discovery_interval
            except asyncio.CancelledError:
                logging.debug(f"{self.__class__.__name__} republish_discovery sleep interrupted")
                break

    def schedule(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        groups = self._create_sensor_scan_groups()
        tasks: list[Awaitable[None]] = []
        for name, sensors in groups.items():
            if any([s for s in sensors if s.publishable]):
                tasks.append(self.publish_updates(modbus_client, mqtt_client, name, *sensors))
            else:
                logging.debug(f"{self.name} Sensor Scan Group [{name}] skipped because no sensors are publishable (unique_ids={[s.unique_id for s in sensors]})")
        if Config.home_assistant.enabled and Config.home_assistant.republish_discovery_interval > 0:
            tasks.append(self.republish_discovery(mqtt_client))
        return tasks

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        if Config.home_assistant.enabled:
            result = mqtt_handler.register(mqtt_client, f"{Config.home_assistant.discovery_prefix}/status", self.on_ha_state_change)
            logging.debug(f"{self.name} subscribed to topic {Config.home_assistant.discovery_prefix}/status for Home Assistant state changes ({result=})")
        for sensor in self.sensors.values():
            if isinstance(sensor, WritableSensorMixin):
                try:
                    result = mqtt_handler.register(mqtt_client, sensor.command_topic, sensor.set_value)
                    if sensor.debug_logging:
                        logging.debug(f"Sensor {sensor.name} subscribed to topic {sensor.command_topic} for writing ({result=})")
                except Exception as e:
                    logging.error(f"Sensor {sensor.name} failed to subscribe to topic {sensor.command_topic}: {repr(e)}")
            if isinstance(sensor, ObservableMixin):
                for topic in sensor.observable_topics():
                    try:
                        result = mqtt_handler.register(mqtt_client, topic, sensor.notify)
                        if sensor.debug_logging:
                            logging.debug(f"Sensor {sensor.name} subscribed to topic {topic} for notification ({result=})")
                    except Exception as e:
                        logging.error(f"Sensor {sensor.name} failed to subscribe to topic {topic}: {repr(e)}")
        for device in self.children:
            device.subscribe(mqtt_client, mqtt_handler)


class ModbusDevice(Device, metaclass=abc.ABCMeta):
    def __init__(
        self,
        type: DeviceType | None,
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

    def _add_read_sensor(self, sensor: Sensor, group: str | None = None) -> bool:
        if self._device_type is not None and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
            return False
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
            return False
        else:
            return super()._add_read_sensor(sensor, group)

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if self._device_type is not None and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
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
    def get(cls, plant_index: int) -> list[Device]:
        if plant_index in cls._devices:
            return list(cls._devices[plant_index])
        return []
