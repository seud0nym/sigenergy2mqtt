from .const import PERCENTAGE, DeviceClass, InputType, StateClass, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from pymodbus import ModbusException
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.pdu import ExceptionResponse
from sigenergy2mqtt.config import Config, RegisterAccess
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.modbus import LockFactory
from sigenergy2mqtt.mqtt import MqttClient
from typing import Any, Coroutine, Dict, Final
import abc
import asyncio
import datetime
import json
import logging
import sys
import time


class Sensor(Dict[str, any], metaclass=abc.ABCMeta):
    """Base superclass of all sensor definitions"""

    _used_object_ids = {}
    _used_unique_ids = {}

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        assert unique_id not in self._used_unique_ids or self._used_unique_ids[unique_id] == self.__class__.__name__, (
            f"{self.__class__.__name__} unique_id {unique_id} has already been used for class {self._used_unique_ids[unique_id]}"
        )
        assert unique_id.startswith(Config.home_assistant.unique_id_prefix), f"{self.__class__.__name__} unique_id {unique_id} does not start with '{Config.home_assistant.unique_id_prefix}'"
        assert object_id not in self._used_object_ids or self._used_object_ids[object_id] == self.__class__.__name__, (
            f"{self.__class__.__name__} object_id {object_id} has already been used for class {self._used_object_ids[object_id]}"
        )
        assert object_id.startswith(Config.home_assistant.entity_id_prefix), f"{self.__class__.__name__} object_id {object_id} does not start with '{Config.home_assistant.entity_id_prefix}'"
        assert icon is None or icon.startswith("mdi:"), f"{self.__class__.__name__} icon {icon} does not start with 'mdi:'"
        self._used_unique_ids[unique_id] = self.__class__.__name__
        self._used_object_ids[object_id] = self.__class__.__name__

        self._derived_sensors: Dict[str, "DerivedSensor"] = {}
        self._requisite_sensors: Dict[str, "RequisiteSensor"] = {}

        self._debug_logging = Config.sensor_debug_logging
        self._force_publish = False
        self._publishable = True
        self._persistent_publish_state_file = Path(Config.persistent_state_path, f"{unique_id}.publishable")
        self._states = []
        self._sleeper_task: Coroutine = None

        self._failures: int = 0
        self._max_failures: int = 10
        self._max_failures_retry_interval: int = 0
        self._next_retry: float = None

        self["platform"] = "sensor"
        self["name"] = name
        self["object_id"] = object_id
        self["unique_id"] = unique_id
        self["device_class"] = device_class
        self["icon"] = icon
        self["state_class"] = state_class
        self["unit_of_measurement"] = unit
        self["display_precision"] = precision
        self["enabled_by_default"] = Config.home_assistant.enabled_by_default

        self._gain = gain
        self._precision = precision

    # region Properties
    @property
    def debug_logging(self) -> bool:
        return self._debug_logging

    @property
    def device_class(self) -> DeviceClass:
        return self["device_class"]

    @property
    def force_publish(self) -> bool:
        return self._force_publish

    @force_publish.setter
    def force_publish(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("force_publish must be a bool")
        self._force_publish = value

    @property
    def gain(self) -> float:
        return 1 if self._gain is None else self._gain

    @property
    def latest_interval(self) -> float:
        return -1 if len(self._states) < 2 else self._states[-1][0] - self._states[-2][0]

    @property
    def latest_raw_state(self) -> float | int | str:
        return None if len(self._states) == 0 else self._states[-1][1]

    @latest_raw_state.setter
    def latest_raw_state(self, value):
        self._states[-1][1] = value

    @property
    def latest_time(self) -> float:
        return 0 if len(self._states) == 0 else self._states[-1][0]

    @property
    def name(self) -> str:
        return self["name"]

    @property
    def precision(self) -> int:
        return self["display_precision"]

    @property
    def publishable(self) -> bool:
        return self._publishable

    @publishable.setter
    def publishable(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("publishable must be a bool")
        self._publishable = value
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} publishable set to {value}")

    @property
    def sleeper_task(self) -> Coroutine[Any, Any, None]:
        return self._sleeper_task

    @sleeper_task.setter
    def sleeper_task(self, coroutine: Coroutine[Any, Any, None]) -> None:
        self._sleeper_task = coroutine

    @property
    def state_class(self) -> StateClass:
        return self["state_class"]

    @property
    def state_topic(self) -> str:
        return self["state_topic"]

    @property
    def unit(self) -> str:
        return self["unit_of_measurement"]

    @property
    def unique_id(self) -> str:
        return self["unique_id"]

    # endregion

    @abc.abstractmethod
    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        """Retrieves the current state of this sensor and updates the internal state history.

        Args:
            **kwargs    Implementation specific arguments.

        Returns:
            True if the state was updated, False if it was not.
        """
        pass

    def add_derived_sensor(self, sensor: "DerivedSensor") -> None:
        """Adds a derived sensor that depends upon this sensor.

        Args:
            sensor:     The DerivedSensor instance.
        """
        self._derived_sensors[sensor.__class__.__name__] = sensor
        if self._debug_logging:
            logging.debug(f"{sensor.__class__.__name__} added to {self.__class__.__name__} derived sensors")

    def add_requisite_sensor(self, sensor: "RequisiteSensor") -> None:
        """Adds a requisite sensor on which this sensor depends.

        Args:
            sensor:     The RequisiteSensor instance.
        """
        self._requisite_sensors[sensor.__class__.__name__] = sensor
        if self._debug_logging:
            logging.debug(f"{sensor.__class__.__name__} added to {self.__class__.__name__} requisite sensors")

    def apply_sensor_overrides(self, registers: RegisterAccess):
        for identifier in Config.sensor_overrides.keys():
            if identifier in self.__class__.__name__ or identifier in self["object_id"]:
                overrides = Config.sensor_overrides[identifier]
                if "debug-logging" in overrides and self._debug_logging != overrides["debug-logging"]:
                    self._debug_logging = overrides["debug-logging"]
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'debug-logging' override ({overrides['debug-logging']})")
                if "gain" in overrides and self._gain != overrides["gain"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'gain' override ({overrides['gain']})")
                    self._gain = overrides["gain"]
                if "icon" in overrides and self["icon"] != overrides["icon"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'icon' override ({overrides['icon']})")
                    self["icon"] = overrides["icon"]
                if "max-failures" in overrides and self._max_failures != overrides["max-failures"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'max-failures' override ({overrides['max-failures']})")
                    self._max_failures = overrides["max-failures"]
                if "max-failures-retry-interval" in overrides and self._max_failures_retry_interval != overrides["max-failures-retry-interval"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'max-failures-retry-interval' override ({overrides['max-failures-retry-interval']})")
                    self._max_failures_retry_interval = overrides["max-failures-retry-interval"]
                if "precision" in overrides and self._precision != overrides["precision"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'precision' override ({overrides['precision']})")
                    self._precision = overrides["precision"]
                    self["display_precision"] = self._precision
                if "publishable" in overrides and self._publishable != overrides["publishable"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'publishable' override ({overrides['publishable']})")
                    self._publishable = overrides["publishable"]
                if "unit-of-measurement" in overrides and self["unit_of_measurement"] != overrides["unit-of-measurement"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'unit-of-measurement' override ({overrides['unit-of-measurement']})")
                    self["unit_of_measurement"] = overrides["unit-of-measurement"]
        if self._publishable and registers:
            if isinstance(self, WritableSensorMixin) and not isinstance(self, WriteOnlySensor):
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - Applying device 'read-write' override ({registers.read_write})")
                self._publishable = registers.read_write
            elif isinstance(self, (ReadableSensorMixin, DerivedSensor)):
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - Applying device 'read-only' override ({registers.read_only})")
                self._publishable = registers.read_only
            elif isinstance(self, WriteOnlySensor):
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - Applying device 'write-only' override ({registers.write_only})")
                self._publishable = registers.write_only
            else:
                logging.warning(f"{self.__class__.__name__} - Failed to determine superclass to apply device publishable overrides")

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = f"{Config.home_assistant.discovery_prefix}/{self['platform']}/{device_id}/{self['object_id']}" if Config.home_assistant.enabled else f"sigenergy2mqtt/{self['object_id']}"
        self["state_topic"] = f"{base}/state"
        self["json_attributes_topic"] = f"{base}/attributes"
        self["availability_mode"] = "all"
        self["availability"] = [{"topic": f"{Config.home_assistant.discovery_prefix}/device/{device_id}/availability"}]
        return base

    def get_discovery(self, force_publish: bool = True) -> Dict[str, dict[str, Any]]:
        """Gets the Home Assistant MQTT auto-discovery components for this sensor.

        Returns:
            A dictionary keyed by sensor.unique_id with the values containing the discovery configuration.
        """
        assert "availability" in self, f"{self.__class__.__name__} MQTT topics are not configured?"
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} - getting discovery")
        components = self.get_discovery_components()
        if self.publishable and not Config.clean:
            self.force_publish = force_publish
            if self._persistent_publish_state_file.exists():
                self._persistent_publish_state_file.unlink(missing_ok=True)
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - removed {self._persistent_publish_state_file} ({self.publishable=} and {Config.clean=})")
        else:
            if self._persistent_publish_state_file.exists() or Config.clean:
                components = {}
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery ({self.publishable=} exists and {Config.clean=})")
            else:
                for id in components.keys():
                    components[id] = {"p": self["platform"]}
                with self._persistent_publish_state_file.open("w") as f:
                    f.write("0")
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery except {components} ({self.publishable=} exists and {Config.clean=})")
        return components

    def get_discovery_components(self) -> Dict[str, Dict[str, Any]]:
        return {self.unique_id: dict(dict((k, v) for k, v in self.items() if v is not None))}

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            raw:        If True, return the raw reading.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.
            **kwargs    Supplemental keyword arguments to pass to the get_reading method.

        Returns:
            The state of this sensor.
        """
        if republish and len(self._states) > 0:
            return self._states[-1][1]
        else:
            result = await self._update_internal_state(**kwargs)
            if result:
                for sensor in self._requisite_sensors.values():
                    result = result and sensor.update_base_sensor_state(self, **kwargs)
                return self._states[-1][1]
            else:
                return None

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        now = time.time()
        if self._failures < self._max_failures or (self._next_retry and self._next_retry <= now):
            try:
                value = await self.get_state(modbus=modbus, raw=False, republish=republish)
                if value is None and not self.force_publish:
                    if self._debug_logging:
                        logging.debug(f"Publishing {self.__class__.__name__} SKIPPED - Value is unchanged")
                else:
                    if self._failures > 0:
                        logging.info(f"Resetting failure count for {self.__class__.__name__} from {self._failures} to 0")
                        self._failures = 0
                        self._next_retry = None
                    if self._debug_logging:
                        logging.debug(f"Publishing {self.__class__.__name__} = {value}")
                    mqtt.publish(self["state_topic"], f"{value}", 0, False)
                for sensor in self._derived_sensors.values():
                    await sensor.publish(mqtt, modbus, republish=republish)
            except Exception as exc:
                logging.error(f"{self.__class__.__name__} Publishing SKIPPED - Failed to get state ({exc})")
                if modbus.connected:
                    self._failures += 1
                    self._next_retry = (
                        None
                        if self._failures < self._max_failures or self._max_failures_retry_interval == 0
                        else (now + (self._max_failures_retry_interval * max(1, self._failures - self._max_failures)))
                    )
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=}")
                if Config.home_assistant.enabled:
                    self.publish_attributes(mqtt, failures=self._failures, exception=f"{exc}")
                if self._failures >= self._max_failures:
                    logging.warning(
                        f"{self.__class__.__name__} publish DISABLED until {'restart' if self._next_retry is None else time.strftime('%c', time.localtime(self._next_retry))} - MAX_FAILURES exceeded: {self._failures}"
                    )
                    for sensor in self._derived_sensors.values():
                        logging.warning(
                            f"{sensor.__class__.__name__} publish DISABLED until {'restart' if self._next_retry is None else time.strftime('%c', time.localtime(self._next_retry))} - MAX_FAILURES exceeded ({self._failures}) for source sensor {self.__class__.__name__}"
                        )
            finally:
                self.force_publish = False
        elif self._debug_logging:
            logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=} {now=}")

    def publish_attributes(self, mqtt: MqttClient, **kwargs) -> None:
        """Publishes the attributes for this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            **kwargs:   key=value pairs that will be added as attributes.
        """
        if self.publishable and not Config.clean:
            value = {}
            value["sensor-class"] = self.__class__.__name__
            value["gain"] = self._gain
            if hasattr(self, "_scan_interval"):
                value["scan-interval"] = self._scan_interval
            for k, v in kwargs.items():
                value[k] = v
            if self._debug_logging:
                logging.debug(f"Publishing attributes of {self.__class__.__name__} = {value}")
            mqtt.publish(self["json_attributes_topic"], json.dumps(value, indent=4), 2, True)
        self.force_publish = False
        for sensor in self._derived_sensors.values():
            sensor.publish_attributes(mqtt)

    def set_latest_state(self, state: float | int | str) -> None:
        """Updates the latest state of this sensor, and passes the updated state to any derived sensors.

        Args:
            state:      The current state.
        """
        self.set_state(state)
        for sensor in self._derived_sensors.values():
            sensor.set_source_values(self, self._states)

    def set_state(self, state: float | int | str) -> None:
        """Updates the latest state of this sensor, WITHOUT passing the updated state to any derived sensors.

        Args:
            state:      The current state.
        """
        self._states.append((time.time(), state))
        if len(self._states) > 2:  # only keep the two latest values
            self._states = self._states[-2:]


class RequisiteSensor(Sensor):
    """Base superclass of all sensor definitions that are required by other sensors.

    Requisite sensors are NOT published.
    """

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        super().__init__(
            name,
            unique_id,
            object_id,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )

    async def update_base_sensor_state(self, base_sensor: Sensor, **kwargs) -> bool:
        """Updates the state of the base sensor with this sensors state.

            Implementations must update base_sensor.latest_raw_state with its original
            value combined with the state of this sensor.

        Args:
            base_sensor: The sensor to be updated with the state of this sensor.
            **kwargs     Supplemental keyword arguments to pass to the get_state method.

        Returns:
            True only if base_sensor.latest_raw_state was updated.
        """
        pass


class DerivedSensor(Sensor):
    """Base superclass of all sensor definitions that are derived from other sensors"""

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        super().__init__(
            name,
            unique_id,
            object_id,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )
        self["enabled_by_default"] = True

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            modbus:     The Modbus client for determining the current state.
            raw:        If True, return the raw state obtained from the Modbus interface.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.

        Returns:
            The state of this sensor.
        """
        if len(self._states) == 0:
            return 0
        else:
            return self._states[-1][1]

    @abc.abstractmethod
    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        """Applies the values from the source Sensor to this DerivedSensor.

        Args:
            sensor:     The Sensor that contributes to this DerivedSensor.
            values:     The list of current values to update this sensor.
        """
        pass


class ModBusSensor(Sensor):
    """Superclass of all Modbus sensor definitions"""

    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        assert device_address is not None and 1 <= device_address <= 247, f"Invalid device address {device_address}"
        assert address >= 30000, f"Invalid address {address}"
        assert count > 0, f"Invalid count {count}"
        assert data_type in ModbusClient.DATATYPE, f"Invalid data type {data_type}"

        unique_id = f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{address}"

        super().__init__(
            name,
            unique_id,
            object_id,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )
        self._address = address
        self._count = count
        self._data_type = data_type
        self._device_address = device_address
        self._input_type = input_type
        self._plant_index = plant_index

    @property
    def gain(self) -> float:
        return None if self._data_type == ModbusClient.DATATYPE.STRING else 1 if self._gain is None else self._gain

    def _check_register_response(self, rr: any, source: str) -> bool:
        if rr.isError() or isinstance(rr, ExceptionResponse):
            match rr.exception_code:
                case 1:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x01 ILLEGAL FUNCTION")
                    if self._debug_logging:
                        logging.debug(rr)
                    raise Exception("0x01 ILLEGAL FUNCTION")
                case 2:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x02 ILLEGAL DATA ADDRESS")
                    if self._debug_logging:
                        logging.debug(rr)
                    logging.warning(f"{self.__class__.__name__} - Setting max allowed failures to 0 for '{self.unique_id}' because of ILLEGAL DATA ADDRESS exception")
                    self._max_failures = 0
                    self._max_failures_retry_interval = 0
                    raise Exception("0x02 ILLEGAL DATA ADDRESS")
                case 3:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x03 ILLEGAL DATA VALUE")
                    if self._debug_logging:
                        logging.debug(rr)
                    raise Exception("0x03 ILLEGAL DATA VALUE")
                case 4:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x04 SLAVE DEVICE FAILURE")
                    if self._debug_logging:
                        logging.debug(rr)
                    raise Exception("0x04 SLAVE DEVICE FAILURE")
                case _:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned {rr}")
                    raise Exception(rr)
            return False
        else:
            return True


class ReadableSensorMixin(abc.ABC):
    def __init__(self: Sensor, scan_interval: int):
        assert scan_interval is not None and scan_interval >= 1, "Scan interval cannot be less than 1 second"
        self._scan_interval = scan_interval

        for identifier in Config.sensor_overrides.keys():
            if identifier in self.__class__.__name__ or identifier in self["object_id"]:
                overrides = Config.sensor_overrides[identifier]
                if "scan-interval" in overrides and self._scan_interval != overrides["scan-interval"]:
                    if self._debug_logging:
                        logging.debug(f"{self.__class__.__name__} - Applying {identifier} 'scan-interval' override ({overrides['scan-interval']})")
                    self._scan_interval = overrides["scan-interval"]

    @property
    def scan_interval(self):
        return self._scan_interval


class ReadOnlySensor(ModBusSensor, ReadableSensorMixin):
    """Superclass of all read-only sensor definitions"""

    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        scan_interval: int,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        ModBusSensor.__init__(self, name, object_id, input_type, plant_index, device_address, address, count, data_type, unit, device_class, state_class, icon, gain, precision)
        ReadableSensorMixin.__init__(self, scan_interval)

    async def _update_internal_state(self, **kwargs) -> bool | Exception:
        """Retrieves the current state of this sensor and updates the internal state history.

        Args:
            **kwargs    Implementation specific arguments.

        Returns:
            True if the state was updated, False if it was not.
        """
        assert "modbus" in kwargs, f"{self.__class__.__name__} - Required argument 'modbus' not supplied"
        result = False
        modbus: ModbusClient = kwargs["modbus"]

        now = time.time()
        if not self.force_publish:
            timestamp = 0 if len(self._states) == 0 else self._states[-1][0]
            if timestamp + self._scan_interval > now:
                return False

        if Config.devices[self._plant_index].log_level == logging.DEBUG:
            logging.debug(f"{self.__class__.__name__} - read_{self._input_type}_registers({self._address}, count={self._count}, slave={self._device_address})")
            start = time.time()
        lock = LockFactory.get_lock(modbus)
        try:
            await lock.acquire()
            if self._input_type == InputType.HOLDING:
                rr = await modbus.read_holding_registers(self._address, count=self._count, slave=self._device_address)
            elif self._input_type == InputType.INPUT:
                rr = await modbus.read_input_registers(self._address, count=self._count, slave=self._device_address)
            else:
                logging.error(f"{self.__class__.__name__} - Unknown input type '{self._input_type}'")
                raise Exception(f"Unknown input type '{self._input_type}'")
        finally:
            lock.release()
        if Config.devices[self._plant_index].log_level == logging.DEBUG:
            elapsed = time.time() - start
            logging.debug(f"{self.__class__.__name__} - read_{self._input_type}_registers({self._address}, count={self._count}, slave={self._device_address}) took {elapsed:.3f}s")
        if self._check_register_response(rr, f"read_{self._input_type}_registers"):
            state_is = modbus.convert_from_registers(rr.registers, self._data_type)
            if self._data_type != ModbusClient.DATATYPE.STRING and self.gain != 1:
                state_is = state_is / self.gain
            self.set_latest_state(
                state_is if self._data_type == ModbusClient.DATATYPE.STRING else round(state_is, self._precision),
            )
            result = True

        return result


class PVCurrentSensor(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int, address: int, string_number: int):
        assert 1 <= string_number <= 16, "string_number must be between 1 and 16"
        super().__init__(
            name="Current",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_current",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=10,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=DeviceClass.CURRENT,
            state_class=None,
            icon="mdi:current-dc",
            gain=100,
            precision=2,
        )


class PVVoltageSensor(ReadOnlySensor, HybridInverter, PVInverter):
    def __init__(self, plant_index: int, device_address: int, address: int, string_number: int):
        assert 1 <= string_number <= 16, "string_number must be between 1 and 16"
        super().__init__(
            name="Voltage",
            object_id=f"{Config.home_assistant.entity_id_prefix}_{plant_index}_inverter_{device_address}_pv{string_number}_voltage",
            input_type=InputType.INPUT,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusClient.DATATYPE.INT16,
            scan_interval=10,
            unit=UnitOfElectricPotential.VOLT,
            device_class=DeviceClass.VOLTAGE,
            state_class=None,
            icon="mdi:flash",
            gain=10,
            precision=1,
        )


class TimestampSensor(ReadOnlySensor):
    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        scan_interval: int,
    ):
        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit=None,
            device_class=DeviceClass.TIMESTAMP,
            state_class=None,
            icon="mdi:calendar-clock",
            gain=None,
            precision=None,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            modbus:     The Modbus client for determining the current state.
            raw:        If True, return the raw state obtained from the Modbus interface.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.

        Returns:
            The state of this sensor.
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None or value == 0:
            return None
        else:
            dt_object = datetime.datetime.fromtimestamp(value, datetime.timezone.utc)
            return dt_object.isoformat()


class ObservableMixin(abc.ABC):
    @abc.abstractmethod
    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        pass

    @abc.abstractmethod
    def observable_topics(self) -> set[str]:
        return set()


class WritableSensorMixin(ModBusSensor):
    @property
    def command_topic(self) -> str:
        topic: str = self["command_topic"]
        assert topic and not topic.isspace(), f"{self.__class__.__name__} command topic is not defined"
        return topic

    def _encode_value(self, value: int | float | str) -> list[int]:
        if isinstance(value, (int, float)) and self.gain != 1:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} applying gain of {self.gain} to {value} before encoding")
            value = int(value * self.gain)

        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} attempting to encode {value} [{self._data_type}]")

        if self._data_type == ModbusClient.DATATYPE.UINT16 and isinstance(value, int) and 0 <= value <= 255:
            # Unsigned 8-bit ints do not need encoding
            registers = [value]
        else:
            builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
            match self._data_type:
                case ModbusClient.DATATYPE.UINT16:
                    builder.add_16bit_uint(int(value))
                case ModbusClient.DATATYPE.INT16:
                    builder.add_16bit_int(int(value))
                case ModbusClient.DATATYPE.UINT32:
                    builder.add_32bit_uint(int(value))
                case ModbusClient.DATATYPE.INT32:
                    builder.add_32bit_int(int(value))
                case ModbusClient.DATATYPE.UINT64:
                    builder.add_64bit_uint(int(value))
                case ModbusClient.DATATYPE.INT64:
                    builder.add_64bit_int(int(value))
                case ModbusClient.DATATYPE.STRING:
                    builder.add_string(str(value))
            registers = builder.to_registers()

        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} encoded {value} as {registers}")

        return registers

    async def _write_registers(self, modbus: ModbusClient, value: float | int | str, mqtt: MqttClient) -> bool:
        # slave = 0 if self._device_address == 247 else self._device_address
        # no_response_expected = True if slave == 0 else False
        slave = self._device_address
        no_response_expected = False
        logging.info(f"{self.__class__.__name__} - write_registers {self._address=} {value=} ({self.latest_raw_state=}) {slave=}")
        registers = self._encode_value(value)
        try:
            if len(registers) == 1:
                if Config.devices[self._plant_index].log_level == logging.DEBUG:
                    logging.debug(f"{self.__class__.__name__} - write_register({self._address}, value={registers}, slave={slave}, no_response_expected={no_response_expected})")
                    start = time.time()
                rr = await modbus.write_register(self._address, registers[0], slave=slave, no_response_expected=no_response_expected)
                if Config.devices[self._plant_index].log_level == logging.DEBUG:
                    elapsed = time.time() - start
                    logging.debug(f"{self.__class__.__name__} - write_register({self._address}, value={registers}, slave={slave}, no_response_expected={no_response_expected}) took {elapsed:.3f}s")
                result = self._check_register_response(rr, "write_register")
            else:
                if Config.devices[self._plant_index].log_level == logging.DEBUG:
                    logging.debug(f"{self.__class__.__name__} - write_register({self._address}, value={registers}, slave={slave}, no_response_expected={no_response_expected})")
                    start = time.time()
                rr = await modbus.write_registers(self._address, registers, slave, no_response_expected=no_response_expected)
                if Config.devices[self._plant_index].log_level == logging.DEBUG:
                    elapsed = time.time() - start
                    logging.debug(f"{self.__class__.__name__} - write_registers({self._address}, value={registers}, slave={slave}, no_response_expected={no_response_expected}) took {elapsed:.3f}s")
                result = self._check_register_response(rr, "write_registers")
            if result:
                self.force_publish = True
                await self.publish(mqtt, modbus)
            return result
        except ModbusException as exc:
            logging.error(f"{self.__class__.__name__} write_registers threw {exc!s}")
            raise

    def configure_mqtt_topics(self, device_id: str) -> None:
        base = super().configure_mqtt_topics(device_id)
        self["command_topic"] = f"{base}/set"
        return base

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source == self["command_topic"]:
            return await self._write_registers(modbus, value, mqtt)
        else:
            logging.error(f"{self.__class__.__name__} - attempt to set_value({value}) from unknown topic {source}")
            return False


class WriteOnlySensor(WritableSensorMixin):
    """Superclass of all write-only sensor definitions"""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        icon_on: str = "mdi:power-on",
        icon_off: str = "mdi:power-off",
    ):
        super().__init__(
            name,
            object_id,
            InputType.HOLDING,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            unit=None,
            device_class=None,
            state_class=None,
            icon=None,
            gain=None,
            precision=None,
        )
        assert icon_on is not None and icon_on.startswith("mdi:"), f"{self.__class__.__name__} on icon {icon_on} does not start with 'mdi:'"
        assert icon_off is not None and icon_off.startswith("mdi:"), f"{self.__class__.__name__} off icon {icon_off} does not start with 'mdi:'"
        self["platform"] = "button"
        self["enabled_by_default"] = True
        self._icons = {"Off": icon_off, "On": icon_on}

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components = {}
        for action in ["On", "Off"]:
            lower_action = action.lower()
            config = {}
            for k, v in self.items():
                if v is not None:
                    if k == "name":
                        config[k] = f"{v} {action}"
                    elif k == "object_id" or k == "unique_id":
                        config[k] = f"{v}_{lower_action}"
                    else:
                        config[k] = v
            config["icon"] = self._icons[action]
            config["payload_press"] = action
            components[f"{self.unique_id}_{action}"] = config
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} - Discovered {components=}")
        return components

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: str, source: str) -> bool:
        if value == "Off":
            return await super().set_value(modbus, mqtt, 0, source)
        elif value == "On":
            return await super().set_value(modbus, mqtt, 1, source)
        else:
            logging.error(f"{self.__class__.__name__} - Ignored attempt to set value to {value}: Must be either 'On' or 'Off'")
        return False


class RemoteEMSMixin(Sensor):
    """Mixin to flag the class that will control Read-Write sensor availability"""

    pass


class ReadWriteSensor(ReadOnlySensor, WritableSensorMixin):
    """Superclass of all read-write sensor definitions"""

    def __init__(
        self,
        remote_ems: RemoteEMSMixin,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        scan_interval: int,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )
        assert remote_ems is None or isinstance(remote_ems, RemoteEMSMixin), f"{self.__class__.__name__} remote_ems is not an instance of RemoteEMSMixin"
        self._remote_ems = remote_ems
        self["enabled_by_default"] = True

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if self._remote_ems is not None:
            assert self._remote_ems.state_topic and not self._remote_ems.state_topic.isspace(), "RemoteEMS state_topic has not been configured"
            self["availability"].append({"topic": self._remote_ems.state_topic, "payload_available": 1, "payload_not_available": 0})
        return base


class NumericSensor(ReadWriteSensor):
    """Superclass of all numeric read-write sensor definitions"""

    def __init__(
        self,
        remote_ems: RemoteEMSMixin,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        scan_interval: int,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
        min: float = 0.0,
        max: float = 100.0,
    ):
        super().__init__(
            remote_ems,
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )
        self["platform"] = "number"
        self["min"] = min
        self["max"] = max
        self["mode"] = "slider" if unit == PERCENTAGE else "box"
        self["step"] = 1 if precision is None else 10**-precision

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        state = await super().get_state(raw=raw, republish=republish, **kwargs)
        if isinstance(state, (float, int)):
            if state < self["min"]:
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - {state=} < {self['min']=} so adjusted")
                state = self["min"]
            elif state > self["max"]:
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - {state=} > {self['max']=} so adjusted")
                state = self["max"]
        return state

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: str, source: str) -> bool:
        if value is not None:
            try:
                state = float(value)
                if self.gain != 1:
                    state = state * self.gain
                return await super().set_value(modbus, mqtt, state, source)
            except Exception as e:
                logging.error(f"{self.__class__.__name__} - Attempt to set value to {value} FAILED: {e}")
        else:
            logging.error(f"{self.__class__.__name__} - Ignored attempt to set None value to {value}")
        return False


class SwitchSensor(ReadWriteSensor):
    """Superclass of all enabled/disabled read-write sensor definitions"""

    def __init__(
        self,
        remote_ems: RemoteEMSMixin,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusClient.DATATYPE,
        scan_interval: int,
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
    ):
        super().__init__(
            remote_ems,
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            count,
            data_type,
            scan_interval,
            unit,
            device_class,
            state_class,
            icon,
            gain,
            precision,
        )
        self["platform"] = "switch"
        self["payload_off"] = "0"
        self["payload_on"] = "1"
        self["state_off"] = "0"
        self["state_on"] = "1"


class AlarmSensor(ReadOnlySensor, metaclass=abc.ABCMeta):
    """Superclass of all Alarm definitions."""

    NO_ALARM: Final = "No Alarm"

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
        )

    @abc.abstractmethod
    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        pass

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            modbus:     The Modbus client for determining the current state.
            raw:        If True, return the raw state obtained from the Modbus interface.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.

        Returns:
            The state of this sensor.
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None or value == 0:
            return self.NO_ALARM
        else:
            active_alarms = []
            for bit_position in range(16):
                if value & (1 << bit_position):
                    description = self.decode_alarm_bit(bit_position)
                    if description:
                        active_alarms.append(description)
            if not active_alarms:
                return "Unknown Alarm"
            else:
                return ", ".join(active_alarms)


class Alarm1Sensor(AlarmSensor):
    """Superclass of all Alarm 1 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address)

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:  # PCS
            case 0:
                return "1001: Software version mismatch"
            case 1:
                return "1002: Low insulation resistance"
            case 2:
                return "1003: Over-temperature"
            case 3:
                return "1004: Equipment fault"
            case 4:
                return "1005: System grounding fault"
            case 5:
                return "1006: PV string over-voltage"
            case 6:
                return "1007: PV string reversely connected"
            case 7:
                return "1008: PV string back-filling"
            case 8:
                return "1009: AFCI fault"
            case 9:
                return "1010: Grid power outage"
            case 10:
                return "1011: Grid over-voltage"
            case 11:
                return "1012: Grid under-voltage"
            case 12:
                return "1013: Grid over-frequency"
            case 13:
                return "1014: Grid under-frequency"
            case 14:
                return "1015: Grid voltage imbalance"
            case 15:
                return "1016: DC component of output current out of limit"
            case _:
                return None


class Alarm2Sensor(AlarmSensor):
    """Superclass of all Alarm 2 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address)

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:  # PCS
            case 0:
                return "1017: Leak current out of limit"
            case 1:
                return "1018: Communication abnormal"
            case 2:
                return "1019: System internal protection"
            case 3:
                return "1020: AFCI self-checking circuit fault"
            case 4:
                return "1021: Off-grid protection"
            case 5:
                return "1022: Manual operation protection"
            case 7:
                return "1024: Abnormal phase sequence"
            case 8:
                return "1025: Short circuit to PE"
            case 9:
                return "1026: Soft start failure"
            case _:
                return None


class Alarm3Sensor(AlarmSensor):
    """Superclass of all Alarm 3 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address)
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:  # ESS
            case 0:
                return "2001: Software version mismatch"
            case 1:
                return "2002: Low insulation resistance to ground"
            case 2:
                return "2003: Temperature too high"
            case 3:
                return "2004: Equipment fault"
            case 4:
                return "2005: Under-temperature"
            case 5:
                return "2008: Internal protection"
            case 6:
                return "2009: Thermal runaway"
            case _:
                return None


class Alarm4Sensor(AlarmSensor):
    """Superclass of all Alarm 4 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address)
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:  # Gateway
            case 0:
                return "3001: Software version mismatch"
            case 1:
                return "3002: Temperature too high"
            case 2:
                return "3003: Equipment fault"
            case 3:
                return "3004: Excessive leakage current in off-grid output"
            case 4:
                return "3005: N line grounding fault"
            case 5:
                return "3006: Abnormal phase sequence of grid wiring"
            case 6:
                return "3007: Abnormal phase sequence of inverter wiring"
            case 7:
                return "3008: Grid phase loss"
            case _:
                return None


class Alarm5Sensor(AlarmSensor):
    """Superclass of all Alarm 5 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address)
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int):
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        match bit_position:  # DC Charger
            case 0:
                return "5101: Software version mismatch"
            case 1:
                return "5102: Low insulation resistance to ground"
            case 2:
                return "5103: Over-temperature"
            case 3:
                return "5104: Equipment fault"
            case 4:
                return "5105: Charging fault"
            case 5:
                return "5106: Equipment protection"
            case _:
                return None


class AlarmCombinedSensor(Sensor, ReadableSensorMixin, HybridInverter, PVInverter):
    def __init__(self, name: str, unique_id: str, object_id: str, *alarms: AlarmSensor):
        Sensor.__init__(
            self,
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
        )
        ReadableSensorMixin.__init__(self, scan_interval=10)
        self["enabled_by_default"] = True
        self._alarms = list(alarms)

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            raw:        If True, return the raw reading.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.
            **kwargs    Supplemental keyword arguments to pass to the get_reading method.

        Returns:
            The state of this sensor.
        """
        if republish and len(self._states) > 0:
            return self._states[-1][1]
        else:
            result = AlarmSensor.NO_ALARM
            for alarm in self._alarms:
                state = await alarm.get_state(raw=False, republish=False, **kwargs)
                if state != AlarmSensor.NO_ALARM:
                    if result == AlarmSensor.NO_ALARM:
                        result = state
                    else:
                        result = ", ".join([result, state])
            self.set_state(result)
            return self._states[-1][1]


class RunningStateSensor(ReadOnlySensor):
    """Superclass of all Running State sensors."""

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusClient.DATATYPE.UINT16,
            scan_interval=10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:power-settings",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            modbus:     The Modbus client for determining the current state.
            raw:        If True, return the raw state obtained from the Modbus interface.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.

        Returns:
            The state of this sensor.
        """
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif value == 0:
            return "Standby"
        elif value == 1:
            return "Normal"
        elif value == 2:
            return "Fault"
        elif value == 3:
            return "Power-Off"
        else:
            return f"Unknown State code: {value}"


class ResettableAccumulationSensor(DerivedSensor, ObservableMixin):
    """Superclass of all sensor definitions that are derived by accumulating a power sensor, and whose current state can be reset"""

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=DeviceClass.ENERGY,
        state_class=StateClass.TOTAL_INCREASING,
        icon="mdi:sigma",
        gain=1000,
        precision=2,
    ):
        super().__init__(name, unique_id, object_id, unit, device_class, state_class, icon, gain, precision)
        self._source = source
        self._reset_topic = f"sigenergy2mqtt/{self['object_id']}/reset"

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        updater: dict[str, Any] = {
            "platform": "number",
            "name": f"Set {self.name}",
            "object_id": f"{self['object_id']}_reset",
            "unique_id": f"{self.unique_id}_reset",
            "icon": "mdi:numeric",
            "unit_of_measurement": self.unit,
            "display_precision": self.precision,
            "command_topic": self._reset_topic,
            "min": 0,
            "max": sys.float_info.max,
            "mode": "box",
            "step": 10**-self.precision,
            "enabled_by_default": self.publishable,
        }
        components: Dict[str, dict[str, Any]] = super().get_discovery_components()
        components[updater["unique_id"]] = updater
        return components

    def observable_topics(self) -> set[str]:
        topics = super().observable_topics()
        topics.add(self._reset_topic)
        return topics

    def publish_attributes(self, mqtt, **kwargs):
        return super().publish_attributes(mqtt, reset_topic=self._reset_topic, reset_unit=self.unit)


class EnergyLifetimeAccumulationSensor(ResettableAccumulationSensor):
    """Superclass of all sensor definitions that are derived by accumulating a power sensor"""

    _current_total_lock = asyncio.Lock()

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=DeviceClass.ENERGY,
        state_class=StateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
        gain=1000,
        precision=2,
    ):
        super().__init__(name, unique_id, object_id, source, unit, device_class, state_class, icon, gain, precision)
        self._current_total: float = 0.0
        self._persistent_state_file = Path(Config.persistent_state_path, f"{self.unique_id}.state")
        if self._persistent_state_file.is_file():
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} - Setting current total from {self._persistent_state_file}")
            with self._persistent_state_file.open("r") as f:
                try:
                    self._current_total = float(f.read())
                except ValueError as error:
                    logging.warning(f"{self.__class__.__name__} failed to read {self._persistent_state_file}: {error}")
        else:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} persistent state file {self._persistent_state_file} not found")
        self.set_latest_state(round(self._current_total / self.gain, self.precision))

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source in self.observable_topics():
            new_total = (value if value is float else float(value)) * self.gain
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({new_total=})")
            await self._persist_current_total(new_total)
            self._current_total = new_total
            self.set_latest_state(round(self._current_total / self.gain, self.precision))
            self.force_publish = True
            return True
        else:
            return False

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if sensor is not self._source:
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        elif len(values) < 2:
            return False  # Need at least two points to calculate

        previous = values[-2][1] * sensor.gain
        current = values[-1][1] * sensor.gain
        average = (previous + current) / 2
        interval_hours = sensor.latest_interval / 3600
        increase = average * interval_hours
        new_total = self._current_total + increase

        if new_total < self._current_total and self.state_class == StateClass.TOTAL_INCREASING:
            logging.error(
                f"Sensor {self.__class__.__name__} has negative value in new sum total (Was = {self._current_total} Previous = {previous} Current = {current} Interval = {sensor.latest_interval:.2f}s New Total = {new_total}) from {sensor.__class__.__name__} but state_class is {self.state_class}???"
            )
            return False
        else:
            asyncio.run_coroutine_threadsafe(self._persist_current_total(new_total), asyncio.get_running_loop())
            self._current_total = new_total
            self.set_latest_state(round(self._current_total / self.gain, self.precision))
            return True

    async def _persist_current_total(self, new_total: float) -> None:
        async with self._current_total_lock:
            with self._persistent_state_file.open("w") as f:
                f.write(str(new_total))


class EnergyDailyAccumulationSensor(ResettableAccumulationSensor):
    """Superclass of all sensor definitions that are derived by accumulating a daily total from a power sensor"""

    futures: set[Future] = set()

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=DeviceClass.ENERGY,
        state_class=StateClass.TOTAL_INCREASING,
        icon="mdi:sigma",
        gain=1000,
        precision=2,
    ):
        super().__init__(name, unique_id, object_id, source, unit, device_class, state_class, icon, gain, precision)
        self._state_at_midnight_lock = asyncio.Lock()
        self._state_at_midnight: float = 0.0 if source.latest_raw_state is None else source.latest_raw_state
        self._persistent_state_file = Path(Config.persistent_state_path, f"{source.unique_id}.atmidnight")
        if self._persistent_state_file.is_file():
            fmt = time.localtime(self._persistent_state_file.stat().st_mtime)
            now = time.localtime()
            if fmt.tm_year == now.tm_year and fmt.tm_mon == now.tm_mon and fmt.tm_mday == now.tm_mday:
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - Setting last midnight state from {self._persistent_state_file}")
                with self._persistent_state_file.open("r") as f:
                    try:
                        self._state_at_midnight = float(f.read())
                    except ValueError as error:
                        logging.warning(f"Sensor {self.__class__.__name__} failed to read {self._persistent_state_file}: {error}")
            else:
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} - Ignored last midnight state file {self._persistent_state_file} because it is stale ({fmt})")
                self._persistent_state_file.unlink(missing_ok=True)
        else:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} persistent state file {self._persistent_state_file} not found")
        self._state_now: float = ((source.latest_raw_state if source.latest_raw_state else 0) * source.gain) - self._state_at_midnight
        self.set_latest_state(round(self._state_now / self.gain, self.precision))
        if not self._persistent_state_file.is_file():
            self.futures.add(asyncio.run_coroutine_threadsafe(self._update_state_at_midnight(self._state_at_midnight), asyncio.get_running_loop()))

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str) -> bool:
        if source in self.observable_topics():
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} notified of updated state {value} {self.unit}")
            self._state_now = (value if value is float else float(value)) * self.gain
            source_state = self._source.latest_raw_state * self._source.gain
            updated_midnight_state = source_state - self._state_now
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} {source_state=} (from {self._source.unique_id}) {self._state_now=} {updated_midnight_state=}")
            await self._update_state_at_midnight(updated_midnight_state)
            self.set_latest_state(round(self._state_now / self.gain, self.precision))
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({self._state_now=})")
            self.force_publish = True
            return True
        else:
            return False

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        if not self._persistent_state_file.is_file():
            await self._update_state_at_midnight(self._state_at_midnight)
        return await super().publish(mqtt, modbus, republish)

    def set_source_values(self, sensor: ModBusSensor, values: list) -> bool:
        if sensor is not self._source:
            logging.error(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False

        now_state = values[-1][1] * sensor.gain

        if len(values) > 1:
            was = time.localtime(values[-2][0])
            now = time.localtime(values[-1][0])
            if was.tm_year != now.tm_year or was.tm_mon != now.tm_mon or was.tm_mday != now.tm_mday:
                asyncio.run_coroutine_threadsafe(self._update_state_at_midnight(now_state), asyncio.get_running_loop())

        self._state_now = now_state - self._state_at_midnight
        self.set_latest_state(round(self._state_now / self.gain, self.precision))

    async def _update_state_at_midnight(self, midnight_state: float) -> None:
        async with self._state_at_midnight_lock:
            with self._persistent_state_file.open("w") as f:
                f.write(str(midnight_state))
            self._state_at_midnight = midnight_state


class BatteryEnergyAccumulationSensor(Sensor, ReadableSensorMixin, ObservableMixin, HybridInverter):
    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        *sources: ReadOnlySensor,
    ):
        @dataclass
        class State:
            gain: float = None
            value: float = None

        self._topics: dict[str, State] = {}

        interval = 5
        enabled = True
        for sensor in sources:
            unit = sensor.unit
            device_class = sensor.device_class
            state_class = sensor.state_class
            icon = sensor["icon"]
            gain = sensor.gain
            precision = sensor.precision
            enabled = enabled and sensor["enabled_by_default"]
            self._topics[sensor.state_topic] = State(sensor.gain, None)
            interval += sensor.scan_interval

        Sensor.__init__(self, name, unique_id, object_id, unit, device_class, state_class, icon, gain, precision)
        ReadableSensorMixin.__init__(self, interval)
        self["enabled_by_default"] = enabled

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, topic: str) -> bool | Exception | ExceptionResponse:
        if topic in self._topics:
            state = self._topics[topic]
            gain = state.gain
            state.value = (value if isinstance(value, float) else float(value)) * gain
            if sum(1 for value in self._topics.values() if value.value is None) == 0:
                self.set_latest_state(round(sum(value.value for value in self._topics.values()) / self.gain, self._precision))
                if self._debug_logging:
                    logging.debug(f"Publishing {self.__class__.__name__} FORCED - {[value.value for value in self._topics.values()]} = {self.latest_raw_state}")
                self.force_publish = True
            return True
        else:
            logging.error(f"{self.__class__.__name__} notified on topic '{topic}', but it is not observable???")
        return False

    def observable_topics(self) -> set[str]:
        topics = ObservableMixin.observable_topics(self)
        for topic in self._topics.keys():
            topics.add(topic)
        return topics

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        """Publishes this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            modbus:     The Modbus client for determining the current state.
            republish:  If True, do NOT acquire the current state, but instead re-publish the previous state.
        """
        if sum(1 for value in self._topics.values() if value.value is None) > 0:
            if self._debug_logging:
                logging.debug(f"Publishing {self.__class__.__name__} SKIPPED - {[value.value for value in self._topics.values()]}")
            return  # until all values populated, can't do calculation
        await super().publish(mqtt, modbus, republish=True)
        # reset internal values to missing for next calculation
        if self._debug_logging:
            logging.debug(f"Resetting {self.__class__.__name__} topic values")
        for topic in self._topics.keys():
            state = self._topics[topic]
            state.value = None


class PVPowerSensor:
    """Marker class"""

    pass
