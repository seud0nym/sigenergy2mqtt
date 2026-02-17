import abc
import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from random import randint, uniform
from typing import Any, Awaitable, cast

import paho.mqtt.client as mqtt
from pymodbus import ModbusException

from sigenergy2mqtt.common import DeviceType, Protocol, RegisterAccess
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusLock, ModbusLockFactory
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

# Constants for reconnection strategy
MAX_RECONNECTION_ATTEMPTS = 10
INITIAL_RECONNECT_DELAY = 0.5
MAX_RECONNECT_DELAY = 60.0
RECONNECT_BACKOFF_MULTIPLIER = 2.0

# Constants for Home Assistant republish timing
HA_REPUBLISH_MIN_JITTER = 0.0
HA_REPUBLISH_MAX_JITTER = 3.0


class ReadableSensorGroup(list[ReadableSensorMixin | ModbusSensorMixin]):
    def __init__(self, *sensors: ReadableSensorMixin | ModbusSensorMixin):
        super().__init__()
        self.first_address: int = -1
        self.last_address: int = -1
        self.device_address: int = -1
        self.input_type: InputType = InputType.NONE
        for sensor in sensors:
            self.append(sensor)

    @property
    def register_count(self) -> int:
        if self.first_address != -1 and self.last_address != -1:
            return self.last_address - self.first_address + 1
        else:
            return -1

    @property
    def scan_interval(self) -> int:
        if len(self) == 0:
            return 86400
        return min(sensor.scan_interval for sensor in self if isinstance(sensor, ReadableSensorMixin))

    def append(self, object):
        if not isinstance(object, ReadableSensorMixin):
            raise ValueError(f"Only ReadableSensorMixin instances can be added to ReadableSensorGroup, got {type(object)}")
        if isinstance(object, ModbusSensorMixin):
            if object.publishable:
                if self.first_address == -1 or object.address < self.first_address:
                    self.first_address = object.address
                if self.last_address == -1 or (object.address + object.count - 1) > self.last_address:
                    self.last_address = object.address + object.count - 1
                if self.device_address == -1:
                    self.device_address = object.device_address
                elif self.device_address != object.device_address:
                    raise ValueError(f"All ModbusSensorMixin instances in a ReadableSensorGroup must have the same device address, expected {self.device_address}, got {object.device_address}")
                if self.input_type == InputType.NONE:
                    self.input_type = object.input_type
                elif self.input_type != object.input_type:
                    raise ValueError(f"All ModbusSensorMixin instances in a ReadableSensorGroup must have the same input type, expected {self.input_type}, got {object.input_type}")
        elif any(s for s in self if isinstance(s, ModbusSensorMixin)):
            raise ValueError("Cannot add non-ModbusSensorMixin to a ReadableSensorGroup that already contains ModbusSensorMixin instances")
        return super().append(object)


class Device(dict[str, str | list[str]], metaclass=abc.ABCMeta):
    def __init__(self, name: str, plant_index: int, unique_id: str, manufacturer: str, model: str, protocol_version: Protocol, **kwargs):
        self.plant_index = plant_index
        self.protocol_version = protocol_version
        self.registers: RegisterAccess | None = None if plant_index < 0 or plant_index >= len(Config.modbus) else Config.modbus[plant_index].registers

        self.children: list[Device] = []

        self.all_sensors: dict[str, Sensor] = {}
        self.group_sensors: dict[str, list[ReadableSensorMixin]] = {}
        self.read_sensors: dict[str, ReadableSensorMixin] = {}
        self.write_sensors: dict[str, WritableSensorMixin] = {}

        self._rediscover = False
        self._online: asyncio.Future | bool | None = None
        self._sleeper_task: asyncio.Task | None = None
        self._shutdown_event: asyncio.Event = asyncio.Event()

        name = _t(f"{self.__class__.__name__}.name", name, plant_index=plant_index, **kwargs)
        self["name"] = self.name = name if Config.home_assistant.device_name_prefix == "" else f"{Config.home_assistant.device_name_prefix} {name}"

        self["identifiers"] = [unique_id]
        self["manufacturer"] = manufacturer
        self["model"] = model
        for k, v in kwargs.items():
            if k in [
                "cu",
                "configuration_url",
                "cns",
                "connections",
                "ids",
                "identifiers",
                "name",
                "mf",
                "manufacturer",
                "mdl",
                "model",
                "mdl_id",
                "model_id",
                "hw",
                "hw_version",
                "sw",
                "sw_version",
                "sa",
                "suggested_area",
                "sn",
                "serial_number",
            ]:
                self[k] = v
            else:
                logging.debug(f"{self.name} - Ignored unknown device attribute: {k} (probably translation placeholder)")

        logging.debug(f"Created Device {self}")
        DeviceRegistry.add(self.plant_index, self)

    # region Properties
    @property
    def online(self) -> bool:
        if isinstance(self._online, bool):
            return self._online
        if isinstance(self._online, asyncio.Future):
            return not self._online.cancelled()
        return False

    @online.setter
    def online(self, value: bool | asyncio.Future) -> None:
        """
        Set the online status of the device.

        - When setting to False, triggers shutdown event and waits for tasks to complete
        - When setting to Future, enables the device
        """
        if isinstance(value, bool):
            if value:  # True
                raise ValueError("online must be a Future to enable")
            else:  # False - Trigger graceful shutdown
                if self._online is False:
                    return  # Already offline

                logging.debug(f"{self.name} initiating graceful shutdown")

                # Cancel the online future to stop new operations
                if isinstance(self._online, asyncio.Future):
                    self._online.cancel()

                # Signal all running tasks to stop
                self._shutdown_event.set()

                # Cancel sensor sleeper tasks
                for sensor in self.get_all_sensors(search_children=True).values():
                    if sensor.sleeper_task is not None:
                        sensor.sleeper_task.cancel()

                # Recursively shut down children
                for device in self.children:
                    device.online = False

                # Cancel own sleeper task
                if self._sleeper_task is not None:
                    self._sleeper_task.cancel()

                # Mark as offline
                self._online = False

                logging.debug(f"{self.name} set to offline")

        elif isinstance(value, asyncio.Future):
            logging.debug(f"{self.name} set to online")
            self._online = value
            self._shutdown_event.clear()
        else:
            raise ValueError("online must be a Future or False")

    @property
    def sleeper_task(self) -> asyncio.Task | None:
        return self._sleeper_task

    @sleeper_task.setter
    def sleeper_task(self, value: asyncio.Task | None) -> None:
        self._sleeper_task = value

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
        return self["ids"][0] if "ids" in self and len(self["ids"]) > 0 else self["identifiers"][0]

    @property
    def via_device(self) -> str | None:
        return None if "via_device" not in self else cast(str, self["via_device"])

    @via_device.setter
    def via_device(self, value: str) -> None:
        self["via_device"] = value

    # endregion

    def _add_child_device(self, device: "Device") -> None:
        if device == self:
            raise ValueError("Cannot add self as a child device")
        sensors = device.get_all_sensors(search_children=True)
        if any(s.publishable for s in sensors.values()):
            device.via_device = self.unique_id
            self.children.append(device)
        else:
            logging.debug(f"{self.name} cannot add child device {device.name} - No publishable sensors defined")

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

    def _add_derived_sensor(self, sensor: DerivedSensor, *from_sensors: Sensor | None, search_children: bool = False) -> None:
        none_sensors = len([s for s in from_sensors if s is None])
        if none_sensors:
            logging.debug(f"{self.name} removed {none_sensors} undefined source sensor{'s' if none_sensors != 1 else ''} for {sensor.__class__.__name__}")
            source_sensors: list[Sensor] = [s for s in from_sensors if s is not None]
        else:
            source_sensors = cast(list[Sensor], from_sensors)
        if self.protocol_version > Protocol.N_A:
            if sensor.protocol_version > self.protocol_version:
                if sensor.debug_logging:
                    logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
                return
            elif any(s for s in source_sensors if s.protocol_version > self.protocol_version):
                if sensor.debug_logging:
                    logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - one or more source sensors have Protocol version > {self.protocol_version}")
                return
        if len(source_sensors) == 0:
            logging.error(f"{self.name} cannot add {sensor.__class__.__name__} - No source sensors defined")
        else:
            for to_sensor in source_sensors:
                found = self.get_sensor(to_sensor.unique_id, search_children=search_children)
                if not found:
                    logging.warning(f"{self.name} cannot add {sensor.__class__.__name__} - {to_sensor.__class__.__name__} is not a defined Sensor for {self.__class__.__name__}")
                elif isinstance(sensor, DerivedSensor):
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

    def _add_writeonly_sensor(self, sensor: WriteOnlySensor) -> None:
        if not isinstance(sensor, WriteOnlySensor):
            logging.error(f"{self.name} cannot add {sensor.unique_id} ({sensor.unique_id}) - not a WriteOnlySensor")
        else:
            self.write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def _create_sensor_scan_groups(self) -> dict[str, list[ReadableSensorMixin]]:
        """
        Creates optimized sensor scan groups for Modbus reading.
        """
        all_child_sensors = self.get_all_sensors(search_children=True)
        combined_sensors: dict[str, ReadableSensorMixin] = {uid: s for uid, s in all_child_sensors.items() if isinstance(s, ReadableSensorMixin)}

        # Recursively collect group sensors
        combined_groups: dict[str, list[ReadableSensorMixin]] = {}

        def collect_groups(device: Device):
            for group, sensor_list in device.group_sensors.items():
                if group not in combined_groups:
                    combined_groups[group] = []
                combined_groups[group].extend(sensor_list)
            for child in device.children:
                collect_groups(child)

        collect_groups(self)

        named_group_sensors: dict[int, ModbusSensorMixin] = {  # Multiple sensors with the same address are not possible and would in any event be detected in the Sensor constructor
            s.address: s for sublist in combined_groups.values() for s in sublist if isinstance(s, ModbusSensorMixin)
        }
        first_address: int = -1
        next_address: int = -1
        device_address: int = -1
        input_type: InputType = InputType.NONE
        group_name: str | None = None

        # Create Modbus sensor scan groups for sensors that are not already in a named group
        # Grouped by device_address and contiguous addresses only (scan_interval handled per-sensor in publish_updates)
        for sensor in sorted(
            [s for s in combined_sensors.values() if isinstance(s, ModbusSensorMixin) and s not in [gs for lst in combined_groups.values() for gs in lst]],
            key=lambda s: (s.device_address, s.address),
        ):
            if (  # Conditions for creating a new sensor scan group
                Config.modbus[self.plant_index].disable_chunking  # If chunking is disabled, always create a new group
                or group_name is None  # First sensor
                or first_address == -1  # Safety check for uninitialized first_address
                or sensor.device_address != device_address  # Device address changed
                or sensor.input_type != input_type  # Input type changed
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
            if group_name is not None and first_address != -1:  # Validate first_address
                combined_groups[group_name].append(sensor)

            next_address = sensor.address + sensor.count
            while next_address in named_group_sensors:  # Include any named group sensors that fall within the range
                if first_address == -1 or (next_address - first_address + named_group_sensors[next_address].count) > MAX_MODBUS_REGISTERS_PER_REQUEST:
                    break
                else:
                    next_address += named_group_sensors[next_address].count
            device_address = sensor.device_address
            input_type = sensor.input_type

        # Post-process groups to remove trailing ReservedSensors and empty groups
        for g_name in list(combined_groups.keys()):
            group = combined_groups[g_name]
            while group and isinstance(group[-1], ReservedSensor):
                group.pop()
            if not group:
                del combined_groups[g_name]

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

    async def _reconnect_modbus_with_backoff(self, modbus_client: ModbusClientType) -> bool:
        """
        Implements exponential backoff and retry limits for Modbus reconnection.

        Returns:
            True if reconnection successful, False if max retries exceeded or device went offline
        """
        attempt = 0
        delay = INITIAL_RECONNECT_DELAY

        logging.info(f"{self.name} attempting to reconnect to Modbus...")

        while attempt < MAX_RECONNECTION_ATTEMPTS and self.online:
            attempt += 1
            try:
                modbus_client.close()
                logging.debug(f"{self.name} Modbus reconnection attempt {attempt}/{MAX_RECONNECTION_ATTEMPTS}")
                await modbus_client.connect()
                if modbus_client.connected:
                    logging.info(f"{self.name} successfully reconnected to Modbus on attempt {attempt}")
                    return True
            except asyncio.CancelledError:
                logging.debug(f"{self.name} Modbus reconnection cancelled")
                return False
            except Exception as e:
                logging.warning(f"{self.name} Modbus reconnection attempt {attempt} failed: {repr(e)}")

            # Exponential backoff with cap
            if attempt < MAX_RECONNECTION_ATTEMPTS and self.online:
                sleep_time = min(delay, MAX_RECONNECT_DELAY)
                logging.debug(f"{self.name} waiting {sleep_time:.1f}s before next reconnection attempt")
                try:
                    await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    logging.debug(f"{self.name} Modbus reconnection backoff cancelled")
                    return False
                delay *= RECONNECT_BACKOFF_MULTIPLIER

        if attempt >= MAX_RECONNECTION_ATTEMPTS:
            logging.error(f"{self.name} failed to reconnect to Modbus after {MAX_RECONNECTION_ATTEMPTS} attempts")

        return False

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
            seconds = float(randint(int(HA_REPUBLISH_MIN_JITTER), int(HA_REPUBLISH_MAX_JITTER)) + (randint(0, 10) / 10))
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
        logging.info(f"{self.name} publishing {ha_state} availability")
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
        """
        Main sensor publishing loop with Modbus read optimization.
        """
        # Setup for Modbus read-ahead optimization
        modbus_sensors: ReadableSensorGroup = ReadableSensorGroup(*[s for s in sensors if isinstance(s, ModbusSensorMixin)])
        multiple: bool = len(modbus_sensors) > 1 and modbus_sensors.register_count != -1 and 1 <= modbus_sensors.register_count <= MAX_MODBUS_REGISTERS_PER_REQUEST

        # Initialize per-sensor next publish times, find any daily sensors, and determine if debug logging is needed for this group
        next_publish_times, daily_sensors, debug_logging = await self._init_next_publish_times(modbus_client, mqtt_client, *sensors)

        if debug_logging:
            logging.debug(
                f"{self.name} Sensor Scan Group [{name}] instantiated (multiple={multiple} first_address={modbus_sensors.first_address} last_address={modbus_sensors.last_address} count={modbus_sensors.register_count} sensors={len(sensors)} daily_sensors={len(daily_sensors)})"
            )

        lock = ModbusLockFactory.get(modbus_client)
        last_day = time.localtime(time.time()).tm_yday

        # Main publishing loop - respects shutdown event
        while self.online and not self._shutdown_event.is_set():
            now = time.time()

            # Check for day change (affects daily sensors)
            now_struct = time.localtime(now)
            day_changed = now_struct.tm_yday != last_day
            if day_changed:
                last_day = now_struct.tm_yday
                for sensor in daily_sensors:
                    if sensor.publishable:
                        next_publish_times[sensor] = now  # Force immediate publish
                        if debug_logging:
                            logging.debug(f"{self.name} Sensor Scan Group [{name}] day changed, forcing {sensor.__class__.__name__} to publish")

            # Determine which sensors are due for publishing
            due_sensors: list[ReadableSensorMixin] = self._get_sensors_to_publish_now(next_publish_times, now, name, debug_logging)

            if due_sensors:
                try:
                    if multiple and modbus_client:
                        multiple = await self._publish_read_ahead(due_sensors, modbus_client, modbus_sensors, lock, name, debug_logging)

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
                        logging.debug(f"{self.name} Sensor Scan Group [{name}] handling {e!s}: Acquiring lock before attempting to reconnect... ({lock.waiters=})")
                        async with lock.lock(timeout=None):
                            if not modbus_client.connected and self.online:
                                # Retain lock while attempting to reconnect to prevent multiple concurrent reconnection attempts from other tasks
                                reconnected = await self._reconnect_modbus_with_backoff(modbus_client)
                                if not reconnected and self.online:
                                    logging.error(f"{self.name} failed to reconnect to Modbus, sensor updates paused")
                except Exception as e:
                    logging.error(f"{self.name} Sensor Scan Group [{name}] encountered an error: {repr(e)}")

            # Sleep until the next sensor is due (max 1 second to stay responsive to shutdown)
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

    async def _init_next_publish_times(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, *sensors: Sensor) -> tuple[dict[ReadableSensorMixin, float], list[ReadableSensorMixin], bool]:
        debug_logging: bool = False
        daily_sensors: list[ReadableSensorMixin] = []
        next_publish_times: dict[ReadableSensorMixin, float] = {}
        now = time.time()
        for sensor in sensors:
            debug_logging = debug_logging or sensor.debug_logging or any(ds.debug_logging for ds in sensor.derived_sensors.values())
            if isinstance(sensor, ReadableSensorMixin):
                # Track sensors with EnergyDailyAccumulationSensor derived sensors
                if any(isinstance(ds, EnergyDailyAccumulationSensor) for ds in sensor.derived_sensors.values()):
                    daily_sensors.append(sensor)
                # Initialize with staggered start times
                next_publish_times[sensor] = now + uniform(0.5, min(5, sensor.scan_interval))
                # Publish initial state if available
                if sensor.publishable and sensor.latest_raw_state is not None:
                    await sensor.publish(mqtt_client, modbus_client, republish=True)
        return next_publish_times, daily_sensors, debug_logging

    def _get_sensors_to_publish_now(self, next_publish_times: dict[ReadableSensorMixin, float], now: float, name: str, debug_logging: bool) -> list[ReadableSensorMixin]:
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
        return due_sensors

    async def _publish_read_ahead(
        self, due_sensors: list[ReadableSensorMixin], modbus_client: ModbusClientType, modbus_sensors: ReadableSensorGroup, modbus_lock: ModbusLock, name: str, debug_logging: bool
    ) -> bool:
        read_ahead_enabled = True  # Must be currently enabled, otherwise should not have been called (multiple == True in calling method)
        due_modbus = [s for s in due_sensors if isinstance(s, ModbusSensorMixin)]
        if len(due_modbus) > 0:
            debug_read_ahead = any(s for s in due_modbus if s.debug_logging)
            async with modbus_lock.lock():
                read_ahead_start = 0.0
                if debug_logging:
                    read_ahead_start = time.time()
                exception_code = await modbus_client.read_ahead_registers(
                    modbus_sensors.first_address, count=modbus_sensors.register_count, device_id=modbus_sensors.device_address, input_type=modbus_sensors.input_type, trace=debug_read_ahead
                )
                if exception_code == 0:
                    if debug_read_ahead:
                        logging.debug(
                            f"{self.name} Sensor Scan Group [{name}] pre-read {modbus_sensors.first_address} to {modbus_sensors.last_address} ({modbus_sensors.register_count} registers) took {time.time() - read_ahead_start:.2f}s"
                        )
                else:
                    match exception_code:
                        case -1:
                            reason = "NO RESPONSE FROM DEVICE"
                        case 1:
                            reason = "0x01 ILLEGAL FUNCTION"
                        case 2:
                            reason = "0x02 ILLEGAL DATA ADDRESS (pre-reads now disabled)"
                            read_ahead_enabled = False
                        case 3:
                            reason = "0x03 ILLEGAL DATA VALUE"
                        case 4:
                            reason = "0x04 SLAVE DEVICE FAILURE"
                        case _:
                            reason = f"UNKNOWN PROBLEM ({exception_code=})"
                    logging.warning(
                        f"{self.name} Sensor Scan Group [{name}] failed to pre-read {modbus_sensors.first_address} to {modbus_sensors.last_address} ({modbus_sensors.register_count} registers) - {reason}"
                    )
        return read_ahead_enabled

    async def republish_discovery(self, mqtt_client: mqtt.Client) -> None:
        wait = Config.home_assistant.republish_discovery_interval
        while self.online and not self._shutdown_event.is_set() and Config.home_assistant.republish_discovery_interval > 0:
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
        if not (1 <= device_address <= 247):
            raise ValueError(f"Invalid device address {device_address}: must be between 1 and 247")

        if "unique_id" in kwargs:
            if not (isinstance(kwargs["unique_id"], str) and kwargs["unique_id"].startswith(Config.home_assistant.unique_id_prefix)):
                raise ValueError(f"unique_id must be a string starting with '{Config.home_assistant.unique_id_prefix}'")
            unique_id = kwargs["unique_id"]
            del kwargs["unique_id"]
        else:
            unique_id = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}"

        super().__init__(name, plant_index, unique_id, "Sigenergy", model, protocol_version, **kwargs)

        self.device_address = device_address
        self._device_type = type

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
    # Use defaultdict to automatically handle missing keys
    _devices: dict[int, list[Device]] = defaultdict(list)

    @classmethod
    def add(cls, plant_index: int, device: Device) -> None:
        # No need to check if the key exists first
        cls._devices[plant_index].append(device)

    @classmethod
    def clear(cls) -> None:
        cls._devices = defaultdict(list)

    @classmethod
    def get(cls, plant_index: int) -> list[Device]:
        # .get() handles missing keys, list() returns a defensive copy
        return list(cls._devices.get(plant_index, []))
