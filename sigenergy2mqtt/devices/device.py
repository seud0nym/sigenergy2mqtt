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
from sigenergy2mqtt.config import active_config
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
    """A typed list of readable sensors that tracks Modbus address range metadata.

    For Modbus sensor groups, maintains the contiguous address range
    (first_address, last_address), the shared device_address, and the shared
    input_type as sensors are appended. This metadata is used by publish_updates
    to perform a single read-ahead register fetch covering all sensors in the
    group, rather than individual per-sensor reads.

    All ModbusSensorMixin instances in a group must share the same device_address
    and input_type; mixing them raises ValueError. Non-Modbus sensors may be
    grouped together but cannot be mixed with Modbus sensors in the same group.
    """

    def __init__(self, *sensors: ReadableSensorMixin | ModbusSensorMixin):
        """Initialise the group and append each provided sensor via the overridden append().

        Args:
            *sensors: Zero or more readable sensors to include in the group.
                      All constraints enforced by append() apply at construction time.
        """
        super().__init__()
        self.first_address: int = -1
        self.last_address: int = -1
        self.device_address: int = -1
        self.input_type: InputType = InputType.NONE
        for sensor in sensors:
            self.append(sensor)

    @property
    def register_count(self) -> int:
        """The number of Modbus registers spanning first_address to last_address inclusive.

        Returns -1 if no publishable Modbus sensors have been appended yet.
        """
        if self.first_address != -1 and self.last_address != -1:
            return self.last_address - self.first_address + 1
        else:
            return -1

    def append(self, object):
        """Append a sensor and update Modbus address range metadata if applicable.

        For publishable ModbusSensorMixin instances, updates first_address and
        last_address to ensure they span the new sensor's register range, and
        validates that device_address and input_type are consistent with existing
        members.

        Args:
            object: The sensor to append. Must be a ReadableSensorMixin instance.

        Raises:
            ValueError: If object is not a ReadableSensorMixin.
            ValueError: If object is a ModbusSensorMixin with a different device_address
                        than existing Modbus sensors in this group.
            ValueError: If object is a ModbusSensorMixin with a different input_type
                        than existing Modbus sensors in this group.
            ValueError: If object is a non-Modbus sensor being added to a group that
                        already contains ModbusSensorMixin instances, or vice versa.
        """
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
    """Abstract base class for all Sigenergy devices.

    Inherits from dict to allow direct serialisation as the Home Assistant MQTT
    discovery device payload. Keys follow the HA device registry short-form
    (e.g. "name", "ids", "mf", "mdl") as well as their long-form equivalents.

    Manages the full lifecycle of a device's sensors: registration, grouping for
    efficient Modbus reads, MQTT discovery publication, availability reporting,
    scheduled polling, and graceful shutdown.

    Subclasses must be concrete (non-abstract) and are expected to register their
    sensors during __init__ via the _add_read_sensor, _add_writeonly_sensor, and
    _add_derived_sensor helpers.
    """

    def __init__(self, name: str, plant_index: int, unique_id: str, manufacturer: str, model: str, protocol_version: Protocol, **kwargs):
        """Initialise the device and register it in the DeviceRegistry.

        Args:
            name: Human-readable device name. May be translated via _t() and
                  prefixed by active_config.home_assistant.device_name_prefix.
            plant_index: Index into active_config.modbus identifying which Modbus plant
                         this device belongs to. Negative values or out-of-range
                         values result in self.registers being None.
            unique_id: Globally unique identifier for this device, used as the
                       Home Assistant device identifier.
            manufacturer: Manufacturer string published in the HA device registry.
            model: Model string published in the HA device registry.
            protocol_version: The Modbus protocol version supported by this device,
                              used to filter sensors that require a newer protocol.
            **kwargs: Additional HA device registry attributes (e.g. sw_version,
                      serial_number). Recognised short- and long-form keys are stored
                      directly on the dict; unrecognised keys are logged and ignored.
        """
        self.plant_index = plant_index
        self.protocol_version = protocol_version
        self.registers: RegisterAccess | None = None if plant_index < 0 or plant_index >= len(active_config.modbus) else active_config.modbus[plant_index].registers

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
        self["name"] = self.name = name if active_config.home_assistant.device_name_prefix == "" else f"{active_config.home_assistant.device_name_prefix} {name}"

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
        """Whether the device is currently considered online.

        Returns True if _online is an un-cancelled Future (the normal online state),
        False if _online is False (explicitly set offline) or None (never brought
        online), or if the Future has been cancelled.
        """
        if isinstance(self._online, bool):
            return self._online
        if isinstance(self._online, asyncio.Future):
            return not self._online.cancelled()
        return False

    @online.setter
    def online(self, value: bool | asyncio.Future) -> None:
        """Set the online status of the device.

        Setting to a Future marks the device as online and clears the shutdown
        event, allowing polling loops to run.

        Setting to False triggers a coordinated graceful shutdown: the shutdown
        event is set (causing polling loops to exit at their next iteration), all
        sensor sleeper tasks are cancelled to wake loops immediately, child devices
        are recursively taken offline, and the device's own sleeper task is
        cancelled. The _online flag is then set to False.

        Setting to True is not permitted; use a Future to bring a device online.

        Args:
            value: A Future to bring the device online, or False to take it offline.

        Raises:
            ValueError: If value is True or any type other than bool or asyncio.Future.
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
        """The asyncio Task currently sleeping on behalf of this device, if any."""
        return self._sleeper_task

    @sleeper_task.setter
    def sleeper_task(self, value: asyncio.Task | None) -> None:
        self._sleeper_task = value

    @property
    def rediscover(self) -> bool:
        """Whether this device should republish its HA discovery payload on the next poll cycle."""
        return self._rediscover

    @rediscover.setter
    def rediscover(self, value: bool) -> None:
        """Set the rediscover flag.

        When set to True, the next completed poll cycle in publish_updates will
        call publish_discovery(). Logged at INFO when enabled, DEBUG when cleared.

        Args:
            value: Boolean flag value.

        Raises:
            ValueError: If value is not a bool.
        """
        if not isinstance(value, bool):
            raise ValueError("rediscover must be a boolean")
        self._rediscover = value
        if active_config.home_assistant.enabled:
            if value:
                logging.info(f"{self.name} set to rediscover")
            else:
                logging.debug(f"{self.name} no longer set to rediscover")

    @property
    def sensors(self) -> dict[str, Sensor]:
        """All sensors directly owned by this device, keyed by unique_id.

        Does not include sensors from child devices. Use get_all_sensors() to
        include children.
        """
        return self.all_sensors

    @property
    def unique_id(self) -> str:
        """The primary unique identifier for this device.

        Prefers the first entry in the "ids" key (short form) if present,
        otherwise falls back to the first entry in "identifiers".
        """
        return self["ids"][0] if "ids" in self and len(self["ids"]) > 0 else self["identifiers"][0]

    @property
    def via_device(self) -> str | None:
        """The unique_id of this device's parent device, if it is a child device.

        Returns None if this device has no parent (i.e. is a root device).
        """
        return None if "via_device" not in self else cast(str, self["via_device"])

    @via_device.setter
    def via_device(self, value: str) -> None:
        self["via_device"] = value

    # endregion

    def _add_child_device(self, device: "Device") -> None:
        """Register another Device as a child of this device.

        Child devices appear under this device in the Home Assistant device registry
        via the via_device relationship. A device is only added as a child if it has
        at least one publishable sensor; devices with no publishable sensors are
        silently skipped with a debug log.

        Args:
            device: The device to register as a child.

        Raises:
            ValueError: If device is self.
        """
        if device == self:
            raise ValueError("Cannot add self as a child device")
        sensors = device.get_all_sensors(search_children=True)
        if any(s.publishable for s in sensors.values()):
            device.via_device = self.unique_id
            self.children.append(device)
        else:
            logging.debug(f"{self.name} cannot add child device {device.name} - No publishable sensors defined")

    def _add_to_all_sensors(self, sensor: Sensor) -> None:
        """Register a sensor in all_sensors after applying configuration and MQTT setup.

        Applies any sensor overrides from self.registers, sets sensor.parent_device,
        and configures MQTT topics. If the sensor's unique_id is already present
        (including in child devices), the sensor is not re-added.

        Args:
            sensor: The sensor to register.
        """
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
        """Register a DerivedSensor that computes its value from one or more source sensors.

        Filters out None entries from from_sensors (which arise when optional source
        sensors are not defined for a given protocol version) and validates protocol
        version compatibility. The derived sensor is attached to each source sensor
        via add_derived_sensor() and registered in all_sensors.

        Args:
            sensor: The DerivedSensor to register.
            *from_sensors: The source sensors whose values feed into the derived sensor.
                           None values are removed before processing.
            search_children: Whether to search child devices when looking up source
                             sensors by unique_id.
        """
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
        """Register a readable sensor, optionally placing it in a named scan group.

        Ungrouped sensors are added to read_sensors and polled individually.
        Grouped sensors are collected in group_sensors under the given group key;
        the group is later used by _create_sensor_scan_groups to form a single
        Modbus read request covering all sensors in the group.

        Args:
            sensor: The sensor to register. Must implement ReadableSensorMixin.
            group: Optional named group key. If None the sensor is registered
                   as a standalone readable sensor.

        Returns:
            True if the sensor was registered successfully, False if the sensor
            does not implement ReadableSensorMixin.
        """
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
        """Register a write-only sensor that accepts commands but publishes no state.

        Write-only sensors are stored in write_sensors and subscribed to their
        command topic in subscribe(). They do not participate in polling.

        Args:
            sensor: The sensor to register. Must be a WriteOnlySensor instance.
        """
        if not isinstance(sensor, WriteOnlySensor):
            logging.error(f"{self.name} cannot add {sensor.unique_id} ({sensor.unique_id}) - not a WriteOnlySensor")
        else:
            self.write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def _create_sensor_scan_groups(self) -> dict[str, list[ReadableSensorMixin]]:
        """Build optimised Modbus scan groups for all readable sensors on this device and its children.

        Groups are constructed to minimise the number of Modbus read requests:
        sensors with contiguous register addresses on the same device and of the
        same input type are batched into a single group, subject to the
        MAX_MODBUS_REGISTERS_PER_REQUEST limit. If active_config.modbus[plant_index].
        disable_chunking is True, each sensor gets its own group.

        Named groups (registered via _add_read_sensor with a group key) are always
        kept intact and take priority. Auto-generated groups use the key format
        "{device_address:03d}_{first_address:05d}".

        ReservedSensors at the start of a new group are skipped (they cannot lead
        a group). ReservedSensors trailing a group are removed in post-processing.
        Empty groups are deleted.

        Non-Modbus readable sensors are collected into a single "non_modbus_sensors"
        group at the end.

        Returns:
            A dict mapping group name to list of ReadableSensorMixin instances.
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
                active_config.modbus[self.plant_index].disable_chunking  # If chunking is disabled, always create a new group
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

    async def _init_next_publish_times(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, *sensors: Sensor) -> tuple[dict[ReadableSensorMixin, float], list[ReadableSensorMixin], bool]:
        """Initialise per-sensor scheduling state for a new publish_updates loop.

        For each readable sensor, assigns a staggered initial publish time to spread
        load across the first few seconds. Publishes the current cached state
        immediately for any sensor that already has a value. Identifies sensors with
        EnergyDailyAccumulationSensor derived sensors so they can be force-published
        on day change. Determines whether debug logging should be enabled for the
        group.

        Args:
            modbus_client: The Modbus client, passed through to initial publish calls.
            mqtt_client:   The MQTT client, passed through to initial publish calls.
            *sensors:      All sensors in the scan group.

        Returns:
            A tuple of:
            - next_publish_times: dict mapping each ReadableSensorMixin to its next
              scheduled publish timestamp.
            - daily_sensors: list of sensors with EnergyDailyAccumulationSensor
              derived sensors that need special day-rollover handling.
            - debug_logging: True if any sensor in the group has debug logging enabled.
        """
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
        """Return the subset of sensors that are due for publishing on this iteration.

        A sensor is due if its force_publish flag is set, or if its scheduled next
        publish time is at or before now. Sensors that are not publishable are always
        skipped.

        Args:
            next_publish_times: Mapping of sensor to next scheduled publish timestamp.
            now:                Current timestamp from time.time().
            name:               Scan group name, used in debug log messages.
            debug_logging:      Whether to emit debug logs for force_publish events.

        Returns:
            List of sensors due for publishing on this iteration.
        """
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
        """Perform a single bulk Modbus register read covering all due Modbus sensors.

        Acquires the Modbus lock and calls read_ahead_registers() to pre-populate
        the client's read cache for the entire address range of the group. Individual
        sensor publish() calls issued after this will hit the cache rather than
        generating separate wire requests.

        If exception code 2 (ILLEGAL DATA ADDRESS) is returned, read-ahead is
        permanently disabled for this group by returning False. Other non-zero
        exception codes are logged as warnings but read-ahead remains enabled.

        If no due sensors are Modbus sensors, the read-ahead is skipped and the
        current enabled state is preserved.

        Args:
            due_sensors:   Sensors due for publishing on this iteration.
            modbus_client: The Modbus client to perform the read against.
            modbus_sensors: The ReadableSensorGroup holding address range metadata.
            modbus_lock:   The lock serialising access to the Modbus client.
            name:          Scan group name, used in log messages.
            debug_logging: Whether to emit timing debug logs.

        Returns:
            True if read-ahead should remain enabled for future iterations,
            False if it should be permanently disabled (ILLEGAL DATA ADDRESS).
        """
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

    async def _reconnect_modbus_with_backoff(self, modbus_client: ModbusClientType) -> bool:
        """Attempt to reconnect to the Modbus server using exponential backoff.

        Makes up to MAX_RECONNECTION_ATTEMPTS connection attempts. The delay between
        attempts starts at INITIAL_RECONNECT_DELAY and doubles after each failure,
        capped at MAX_RECONNECT_DELAY. Returns immediately on success or if the
        device goes offline during reconnection.

        This method is called while holding the Modbus lock, which prevents
        concurrent reconnection attempts from other sensor group tasks on the
        same plant.

        Args:
            modbus_client: The Modbus client to reconnect.

        Returns:
            True if the connection was re-established, False if all attempts were
            exhausted or the device went offline during reconnection.
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
        """Return all sensors owned by this device, optionally including child devices.

        Args:
            search_children: If True (default), recursively includes sensors from
                             all child devices. Child sensors do not overwrite parent
                             sensors if unique_ids collide (parent takes precedence
                             due to dict.update ordering).

        Returns:
            A new dict mapping unique_id to Sensor.
        """
        if search_children:
            all_sensors = self.all_sensors.copy()
            for child in self.children:
                all_sensors.update(child.get_all_sensors(search_children=True))
            return all_sensors
        else:
            return self.all_sensors

    def get_sensor(self, unique_id: str, search_children: bool = False) -> Sensor | None:
        """Look up a sensor by unique_id, including alarm sub-sensors.

        Search order:
        1. Direct lookup in self.all_sensors.
        2. If search_children, direct lookup in each child's sensors dict.
        3. Linear scan of AlarmCombinedSensor instances in self.all_sensors for
           a matching alarm sub-sensor.
        4. If search_children, same alarm scan across each child's all_sensors.

        Args:
            unique_id: The unique_id of the sensor to find.
            search_children: Whether to extend the search to child devices.

        Returns:
            The matching Sensor, or None if not found.
        """
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
        """Handle a Home Assistant availability state change notification.

        When HA comes online, waits a short random jitter period (to avoid thundering
        herd on broker restart) then republishes discovery and forces all sensors to
        republish their current state. This recovers HA's view of the device after
        an HA restart or MQTT broker reconnect.

        See: https://www.home-assistant.io/integrations/mqtt/#birth-and-last-will-messages

        Args:
            modbus_client: The Modbus client, if available, passed through to sensor
                           publish calls.
            mqtt_client:   The MQTT client used for publishing.
            ha_state:      The HA availability state string, typically "online" or
                           "offline".
            source:        Descriptive string identifying the source of the state
                           change, used for logging.
            mqtt_handler:  The MqttHandler used to coordinate discovery publication.

        Returns:
            True if the online handler completed successfully, False if it was
            cancelled (e.g. during device shutdown) or if ha_state is not "online".
        """
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
        """Publish MQTT attribute messages for all sensors on this device.

        Args:
            mqtt_client: The MQTT client used for publishing.
            clean:       If True, publishes empty/null payloads to clear retained
                         attribute messages.
            propagate:   If True (default), recursively publishes attributes for
                         all child devices.
        """
        for sensor in self.sensors.values():
            sensor.publish_attributes(mqtt_client, clean=clean)
        if propagate:
            for device in self.children:
                device.publish_attributes(mqtt_client, clean=clean, propagate=propagate)

    def publish_availability(self, mqtt_client: mqtt.Client, ha_state: str | None, qos: int = 2) -> None:
        """Publish this device's availability status to its HA availability topic.

        Publishes to "{discovery_prefix}/device/{unique_id}/availability" with
        retain=True. Recursively publishes availability for all child devices.

        Args:
            mqtt_client: The MQTT client used for publishing.
            ha_state:    The availability state string (e.g. "online", "offline",
                         or None to clear the retained message).
            qos:         MQTT QoS level. Defaults to 2.
        """
        logging.info(f"{self.name} publishing {ha_state} availability")
        mqtt_client.publish(f"{active_config.home_assistant.discovery_prefix}/device/{self.unique_id}/availability", ha_state, qos, True)
        for device in self.children:
            device.publish_availability(mqtt_client, ha_state)

    def publish_discovery(self, mqtt_client: mqtt.Client, clean: bool = False) -> mqtt.MQTTMessageInfo | None:
        """Publish or clear the Home Assistant MQTT discovery payload for this device.

        In normal mode (clean=False), collects discovery components from all sensors,
        assembles the full device discovery JSON (including "dev", "o", and "cmps"
        keys), and publishes it with retain=True to the HA discovery topic. If no
        publishable components exist, publishes a null payload to clear any stale
        retained discovery message.

        In clean mode (clean=True), clears the availability topic first, then
        publishes a null payload to clear the discovery topic.

        If debug logging is enabled, the discovery JSON is also written to disk at
        active_config.persistent_state_path for inspection.

        Calls publish_attributes() for this device (without propagating to children,
        since children will publish their own attributes when their own discovery is
        published). Recursively calls publish_discovery() on all child devices.

        Args:
            mqtt_client: The MQTT client used for publishing.
            clean:       If True, clears retained discovery and availability messages
                         instead of publishing new ones.

        Returns:
            The MQTTMessageInfo from the final mqtt_client.publish() call, or None.
        """
        topic = f"{active_config.home_assistant.discovery_prefix}/device/{self.unique_id}/config"
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
                discovery["o"] = active_config.origin
                discovery["cmps"] = components
                discovery_json = json.dumps(discovery, allow_nan=False, indent=2, sort_keys=False)
                logging.debug(f"{self.name} publishing discovery")
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    discovery_dump = Path(active_config.persistent_state_path, f"{self.unique_id}.discovery.json")
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
        """Main sensor polling loop for a single scan group.

        Runs continuously while the device is online and the shutdown event is not
        set. On each iteration:
        1. Checks for a day change and forces immediate republish of any sensors
           with EnergyDailyAccumulationSensor derived sensors.
        2. Determines which sensors are due (by scheduled time or force_publish flag).
        3. If multiple Modbus sensors are due and read-ahead is enabled, performs a
           single bulk register read via _publish_read_ahead to pre-populate the
           Modbus client's read cache.
        4. Publishes each due sensor and schedules its next publish time.
        5. If rediscover is set, republishes discovery.
        6. On ModbusException, acquires the Modbus lock and attempts reconnection
           via _reconnect_modbus_with_backoff (lock is held for the duration to
           prevent concurrent reconnection attempts from sibling tasks).
        7. Sleeps until the next sensor is due, up to a maximum of 1 second to
           remain responsive to shutdown signals.

        Args:
            modbus_client: The Modbus client for register reads, or None for
                           non-Modbus devices.
            mqtt_client:   The MQTT client for publishing sensor state.
            name:          The scan group name, used in log messages.
            *sensors:      The sensors belonging to this scan group.
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

    async def republish_discovery(self, mqtt_client: mqtt.Client) -> None:
        """Periodically republish the HA discovery payload at the configured interval.

        Runs as a background coroutine alongside the sensor scan group tasks.
        Sleeps in 1-second increments and republishes when the configured interval
        has elapsed. Exits when the device goes offline, the shutdown event is set,
        or the task is cancelled.

        Args:
            mqtt_client: The MQTT client used for publishing discovery payloads.
        """
        wait = active_config.home_assistant.republish_discovery_interval
        while self.online and not self._shutdown_event.is_set() and active_config.home_assistant.republish_discovery_interval > 0:
            try:
                await asyncio.sleep(1)
                wait -= 1
                if wait <= 0:
                    logging.info(f"{self.name} re-publishing discovery")
                    self.publish_discovery(mqtt_client, clean=False)
                    wait = active_config.home_assistant.republish_discovery_interval
            except asyncio.CancelledError:
                logging.debug(f"{self.__class__.__name__} republish_discovery sleep interrupted")
                break

    def schedule(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Build the list of coroutines that drive this device's runtime behaviour.

        Creates one publish_updates coroutine per sensor scan group that contains at
        least one publishable sensor. If HA integration is enabled and a republish
        interval is configured, also creates a republish_discovery coroutine.

        These coroutines are intended to be gathered or scheduled by the caller
        as asyncio Tasks.

        Args:
            modbus_client: The Modbus client, or None for non-Modbus devices.
            mqtt_client:   The MQTT client used by all coroutines for publishing.

        Returns:
            A list of awaitables ready to be passed to asyncio.gather() or similar.
        """
        groups = self._create_sensor_scan_groups()
        tasks: list[Awaitable[None]] = []
        for name, sensors in groups.items():
            if any([s for s in sensors if s.publishable]):
                tasks.append(self.publish_updates(modbus_client, mqtt_client, name, *sensors))
            else:
                logging.debug(f"{self.name} Sensor Scan Group [{name}] skipped because no sensors are publishable (unique_ids={[s.unique_id for s in sensors]})")
        if active_config.home_assistant.enabled and active_config.home_assistant.republish_discovery_interval > 0:
            tasks.append(self.republish_discovery(mqtt_client))
        return tasks

    def subscribe(self, mqtt_client: mqtt.Client, mqtt_handler: MqttHandler) -> None:
        """Subscribe to all MQTT topics this device needs to receive messages on.

        Registers:
        - The HA status topic for online/offline state change notifications.
        - Each WritableSensorMixin's command topic for receiving set-value commands.
        - Each ObservableMixin sensor's observable topics for state notifications.

        Recursively subscribes child devices.

        Args:
            mqtt_client:  The MQTT client to subscribe on.
            mqtt_handler: The MqttHandler that manages topic-to-callback routing.
        """
        if active_config.home_assistant.enabled:
            result = mqtt_handler.register(mqtt_client, f"{active_config.home_assistant.discovery_prefix}/status", self.on_ha_state_change)
            logging.debug(f"{self.name} subscribed to topic {active_config.home_assistant.discovery_prefix}/status for Home Assistant state changes ({result=})")
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
    """Abstract base class for devices that communicate over Modbus.

    Extends Device with Modbus-specific sensor filtering: sensors whose protocol
    version exceeds the device's protocol_version are silently skipped, as are
    sensors whose type does not match the device's configured DeviceType filter.

    Subclasses must supply the concrete sensor registrations in their __init__.
    """

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
        """Initialise a Modbus device and validate its address and unique_id.

        Args:
            type:            Optional DeviceType filter. When set, only sensors
                             whose class is an instance of type.__class__ will be
                             added.
            name:            Human-readable device name, passed to Device.__init__.
            plant_index:     Modbus plant index, passed to Device.__init__.
            device_address:  Modbus device (unit) address. Must be in range 1–247.
            model:           Model string for the HA device registry.
            protocol_version: Modbus protocol version supported by this device.
            **kwargs:        Additional HA device registry attributes, plus an
                             optional "unique_id" key. If "unique_id" is provided
                             it must be a string starting with
                             active_config.home_assistant.unique_id_prefix; otherwise a
                             default unique_id is generated from the prefix, plant
                             index, device address, and class name.

        Raises:
            ValueError: If device_address is outside the range 1–247.
            ValueError: If a "unique_id" kwarg is provided but does not start with
                        active_config.home_assistant.unique_id_prefix.
        """
        if not (1 <= device_address <= 247):
            raise ValueError(f"Invalid device address {device_address}: must be between 1 and 247")

        if "unique_id" in kwargs:
            if not (isinstance(kwargs["unique_id"], str) and kwargs["unique_id"].startswith(active_config.home_assistant.unique_id_prefix)):
                raise ValueError(f"unique_id must be a string starting with '{active_config.home_assistant.unique_id_prefix}'")
            unique_id = kwargs["unique_id"]
            del kwargs["unique_id"]
        else:
            unique_id = f"{active_config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{self.__class__.__name__.lower()}"

        super().__init__(name, plant_index, unique_id, "Sigenergy", model, protocol_version, **kwargs)

        self.device_address = device_address
        self._device_type = type

    def _add_read_sensor(self, sensor: Sensor, group: str | None = None) -> bool:
        """Register a readable sensor, applying Modbus-specific type and protocol filters.

        Skips the sensor if its class is not an instance of the device's configured
        DeviceType, or if its protocol_version exceeds the device's protocol_version.
        Otherwise delegates to Device._add_read_sensor.

        Args:
            sensor: The sensor to register.
            group:  Optional named scan group key.

        Returns:
            True if the sensor was registered, False if it was filtered out or
            is not a ReadableSensorMixin.
        """
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
        """Register a write-only sensor, applying Modbus-specific type and protocol filters.

        Skips the sensor if its class is not an instance of the device's configured
        DeviceType, or if its protocol_version exceeds the device's protocol_version.
        Otherwise delegates to Device._add_writeonly_sensor.

        Args:
            sensor: The write-only sensor to register.
        """
        if self._device_type is not None and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.name} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
        else:
            super()._add_writeonly_sensor(sensor)


class DeviceRegistry:
    """Process-wide registry mapping plant indices to their associated Device instances.

    Provides a simple class-level store used during device construction and
    teardown. All access is through class methods; the registry is not intended
    to be instantiated.
    """

    # Use defaultdict to automatically handle missing keys without requiring
    # an existence check before appending. clear() reassigns this attribute
    # (rather than calling .clear() on it) to guarantee the type invariant is
    # restored even if external code has replaced it with a plain dict.
    _devices: dict[int, list[Device]] = defaultdict(list)

    @classmethod
    def add(cls, plant_index: int, device: Device) -> None:
        """Register a device under the given plant index.

        Called automatically from Device.__init__; callers should not need to
        invoke this directly.

        Args:
            plant_index: The plant index the device belongs to.
            device:      The Device instance to register.
        """
        cls._devices[plant_index].append(device)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered devices and reset the registry to a clean state.

        Reassigns _devices to a fresh defaultdict(list) to ensure the type
        invariant holds regardless of any prior external assignments to the
        class attribute.
        """
        cls._devices = defaultdict(list)

    @classmethod
    def get(cls, plant_index: int) -> list[Device]:
        """Return a copy of the device list for the given plant index.

        Args:
            plant_index: The plant index to query.

        Returns:
            A new list containing the Device instances registered under
            plant_index, or an empty list if the plant index is not known.
        """
        return list(cls._devices.get(plant_index, []))
