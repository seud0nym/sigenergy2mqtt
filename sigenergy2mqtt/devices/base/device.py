import abc
import asyncio
import logging
from typing import Awaitable, Literal, cast

import paho.mqtt.client as mqtt

from sigenergy2mqtt.common import DeviceType, HybridInverter, Protocol, PVInverter, RegisterAccess
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus import ModbusClient
from sigenergy2mqtt.mqtt import MqttHandler
from sigenergy2mqtt.sensors.base import AlarmCombinedSensor, DerivedSensor, ObservableMixin, ReadableSensorMixin, Sensor, WritableSensorMixin, WriteOnlySensor

from .ha_publisher import HaPublisherMixin
from .poller import SensorGroupPoller
from .registry import DeviceRegistry
from .scan_groups import create_sensor_scan_groups


class Device(HaPublisherMixin, dict[str, str | list[str]], metaclass=abc.ABCMeta):
    """Abstract base class for all Sigenergy devices.

    Inherits from dict to allow direct serialisation as the Home Assistant MQTT
    discovery device payload. Keys follow the HA device registry short-form
    (e.g. "name", "ids", "mf", "mdl") as well as their long-form equivalents.

    Manages the full lifecycle of a device's sensors: registration, grouping for
    efficient Modbus reads, MQTT discovery publication, availability reporting,
    scheduled polling, and graceful shutdown.

    HA publishing behaviour (publish_discovery, publish_availability, etc.) is
    provided by HaPublisherMixin. Scan group construction is delegated to
    create_sensor_scan_groups(). Per-group polling is driven by SensorGroupPoller.

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
        self._log_identity: str = ""
        self.refresh_log_identity()

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
                logging.debug(f"{self.log_identity} - Ignored unknown device attribute: {k} (probably translation placeholder)")

        logging.debug(f"Created Device {self}")
        DeviceRegistry.add(self.plant_index, self)

    def _build_log_identity(self) -> str:
        """Build a stable log identity for device and service classes."""
        device_address = getattr(self, "device_address", "n/a")
        return f"{self.__class__.__name__}[plant={self.plant_index},dev={device_address}]"

    def refresh_log_identity(self) -> None:
        """Refresh cached log identity."""
        self._log_identity = self._build_log_identity()

    @property
    def log_identity(self) -> str:
        """Get cached log identity."""
        return self._log_identity

    @staticmethod
    def _cancel_task(task: asyncio.Future) -> None:
        """Cancel an asyncio Future or Task in a thread-safe manner.

        When ``online`` is set to ``False`` from an OS signal handler (which
        runs on the main thread), the tasks being cancelled may be running on a
        different thread's event loop.  ``asyncio.Task.cancel()`` is **not**
        thread-safe — calling it from a foreign thread silently fails to
        schedule the ``CancelledError``, leaving the coroutine sleeping for its
        full duration.

        This helper detects the mismatch and dispatches the cancel through
        ``loop.call_soon_threadsafe()`` so the cancellation is injected into
        the correct event loop regardless of which thread is calling.

        Args:
            task: The :class:`asyncio.Future` or :class:`asyncio.Task` to cancel.
        """
        try:
            loop = task.get_loop()
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if running_loop is loop:
                task.cancel()
            else:
                loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:
            task.cancel()

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
    def online(self, value: Literal[False] | asyncio.Future) -> None:
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

                logging.debug(f"{self.log_identity} initiating graceful shutdown")

                # Cancel the online future to stop new operations
                if isinstance(self._online, asyncio.Future):
                    Device._cancel_task(self._online)

                # Signal all running tasks to stop
                self._shutdown_event.set()

                # Cancel sensor sleeper tasks
                for sensor in self.get_all_sensors(search_children=True).values():
                    if sensor.sleeper_task is not None:
                        Device._cancel_task(sensor.sleeper_task)

                # Recursively shut down children
                for device in self.children:
                    device.online = False

                # Cancel own sleeper task
                if self._sleeper_task is not None:
                    Device._cancel_task(self._sleeper_task)

                # Mark as offline
                self._online = False

                logging.debug(f"{self.log_identity} set to offline")

        elif isinstance(value, asyncio.Future):
            logging.debug(f"{self.log_identity} set to online")
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

        When set to True, the next completed poll cycle in SensorGroupPoller.run()
        will call publish_discovery(). Logged at INFO when enabled, DEBUG when cleared.

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
                logging.info(f"{self.log_identity} set to rediscover")
            else:
                logging.debug(f"{self.log_identity} no longer set to rediscover")

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
            logging.debug(f"{self.log_identity} cannot add child device {device.log_identity} - No publishable sensors defined")

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
                logging.debug(f"{self.log_identity} adding sensor {sensor.unique_id} ({sensor.__class__.__name__})")
            sensor.apply_sensor_overrides(self.registers)
            sensor.parent_device = self
            sensor.configure_mqtt_topics(self.unique_id)
            self.all_sensors[sensor.unique_id] = sensor
        elif sensor.debug_logging:
            logging.debug(f"{self.log_identity} skipped adding sensor {sensor.unique_id} ({sensor.__class__.__name__}) - already exists")

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
            logging.debug(f"{self.log_identity} removed {none_sensors} undefined source sensor{'s' if none_sensors != 1 else ''} for {sensor.__class__.__name__}")
            source_sensors: list[Sensor] = [s for s in from_sensors if s is not None]
        else:
            source_sensors = cast(list[Sensor], from_sensors)
        if self.protocol_version > Protocol.N_A:
            if sensor.protocol_version > self.protocol_version:
                if sensor.debug_logging:
                    logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
                return
            elif any(s for s in source_sensors if s.protocol_version > self.protocol_version):
                if sensor.debug_logging:
                    logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - one or more source sensors have Protocol version > {self.protocol_version}")
                return
        if not source_sensors:
            logging.error(f"{self.log_identity} cannot add {sensor.__class__.__name__} - No source sensors defined")
        else:
            for to_sensor in source_sensors:
                found = self.get_sensor(to_sensor.unique_id, search_children=search_children)
                if not found:
                    logging.warning(f"{self.log_identity} cannot add {sensor.__class__.__name__} - {to_sensor.__class__.__name__} is not a defined Sensor for {self.log_identity}")
                else:
                    to_sensor.add_derived_sensor(sensor)
                    self._add_to_all_sensors(sensor)

    def _add_read_sensor(self, sensor: Sensor, group: str | None = None) -> bool:
        """Register a readable sensor, optionally placing it in a named scan group.

        Ungrouped sensors are added to read_sensors and polled individually.
        Grouped sensors are collected in group_sensors under the given group key;
        the group is later used by create_sensor_scan_groups to form a single
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
            logging.error(f"{self.log_identity} cannot add {sensor.__class__.__name__} - not a ReadableSensorMixin")
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
            logging.error(f"{self.log_identity} cannot add {sensor.__class__.__name__} - not a WriteOnlySensor")
        else:
            self.write_sensors[sensor.unique_id] = sensor
            self._add_to_all_sensors(sensor)

    def get_all_sensors(self, search_children: bool = True) -> dict[str, Sensor]:
        """Return all sensors owned by this device, optionally including child devices.

        Args:
            search_children: If True (default), recursively includes sensors from
                             all child devices. Parent sensors take precedence over
                             child sensors on unique_id collision.

        Returns:
            A new dict mapping unique_id to Sensor.
        """
        if search_children:
            all_sensors: dict[str, Sensor] = {}
            for child in self.children:
                all_sensors.update(child.get_all_sensors(search_children=True))
            all_sensors.update(self.all_sensors)  # Parent takes precedence
            return all_sensors
        else:
            return self.all_sensors

    def get_sensor(self, target: str | type, search_children: bool = False) -> Sensor | None:
        """Look up a sensor by unique_id or by class type using isinstance matching.

        Search order:
        1. Direct lookup in self.all_sensors (by unique_id or isinstance).
        2. If search_children, direct lookup in each child's sensors dict.
        3. Linear scan of AlarmCombinedSensor instances in self.all_sensors for
        a matching alarm sub-sensor.
        4. If search_children, same alarm scan across each child's all_sensors.

        Args:
            target: Either the unique_id string of the sensor to find, or a
                    sensor class to match via isinstance. When a class is given,
                    the first matching sensor is returned.
            search_children: Whether to extend the search to child devices.

        Returns:
            The matching Sensor, or None if not found.
        """

        def _matches(sensor: Sensor) -> bool:
            if isinstance(target, str):
                return sensor.unique_id == target
            return isinstance(sensor, target)

        # 1. Search own sensors
        match = next((s for s in self.all_sensors.values() if _matches(s)), None)
        if match:
            return match

        # 2. Search children's direct sensors
        if search_children:
            for child in self.children:
                match = next((s for s in child.sensors.values() if _matches(s)), None)
                if match:
                    return match

        # 3. Search alarm sub-sensors in own sensors
        for alarm in (s for s in self.all_sensors.values() if isinstance(s, AlarmCombinedSensor)):
            match = next((a for a in alarm.alarms if _matches(a)), None)
            if match:
                return match

        # 4. Search alarm sub-sensors in children
        if search_children:
            for child in self.children:
                for alarm in (s for s in child.all_sensors.values() if isinstance(s, AlarmCombinedSensor)):
                    match = next((a for a in alarm.alarms if _matches(a)), None)
                    if match:
                        return match

        return None

    def on_commencement(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """Called when the device is brought online."""
        pass

    def on_completion(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> None:
        """Called when the device is taken offline."""
        pass

    def schedule(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client) -> list[Awaitable[None]]:
        """Build the list of coroutines that drive this device's runtime behaviour.

        Creates one SensorGroupPoller.run() coroutine per sensor scan group that
        contains at least one publishable sensor. If HA integration is enabled and
        a republish interval is configured, also creates a republish_discovery
        coroutine.

        These coroutines are intended to be gathered or scheduled by the caller
        as asyncio Tasks.

        Args:
            modbus_client: The Modbus client, or None for non-Modbus devices.
            mqtt_client:   The MQTT client used by all coroutines for publishing.

        Returns:
            A list of awaitables ready to be passed to asyncio.gather() or similar.
        """
        groups = create_sensor_scan_groups(self)
        poller = SensorGroupPoller(self)
        tasks: list[Awaitable[None]] = []
        for name, sensors in groups.items():
            if any(s.publishable for s in sensors):
                tasks.append(poller.run(modbus_client, mqtt_client, name, *sensors))
            else:
                logging.debug(f"{self.log_identity} Sensor Scan Group [{name}] skipped because no sensors are publishable (unique_ids={[s.unique_id for s in sensors]})")
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
            logging.debug(f"{self.log_identity} subscribed to topic {active_config.home_assistant.discovery_prefix}/status for Home Assistant state changes ({result=})")
        for sensor in self.sensors.values():
            if isinstance(sensor, WritableSensorMixin):
                try:
                    result = mqtt_handler.register(mqtt_client, sensor.command_topic, sensor.set_value)
                    if sensor.debug_logging:
                        logging.debug(f"{sensor.log_identity} subscribed to topic {sensor.command_topic} for writing ({result=})")
                except Exception as e:
                    logging.error(f"{sensor.log_identity} failed to subscribe to topic {sensor.command_topic}: {repr(e)}")
            if isinstance(sensor, ObservableMixin):
                for topic in sensor.observable_topics():
                    try:
                        result = mqtt_handler.register(mqtt_client, topic, sensor.notify)
                        if sensor.debug_logging:
                            logging.debug(f"{sensor.log_identity} subscribed to topic {topic} for notification ({result=})")
                    except Exception as e:
                        logging.error(f"{sensor.log_identity} failed to subscribe to topic {topic}: {repr(e)}")
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
        type: DeviceType,
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
        self.refresh_log_identity()
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
        if self._device_type is not None and isinstance(self._device_type, (HybridInverter, PVInverter)) and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
            return False
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
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
        if self._device_type is not None and isinstance(self._device_type, (HybridInverter, PVInverter)) and not isinstance(sensor, self._device_type.__class__):
            if sensor.debug_logging:
                logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - not a {self._device_type.__class__.__name__}")
        elif sensor.protocol_version > self.protocol_version:
            if sensor.debug_logging:
                logging.debug(f"{self.log_identity} skipped adding {sensor.__class__.__name__} - Protocol version {sensor.protocol_version} > {self.protocol_version}")
        else:
            super()._add_writeonly_sensor(sensor)
