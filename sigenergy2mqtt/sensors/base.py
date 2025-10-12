from .const import PERCENTAGE, DeviceClass, InputType, StateClass, UnitOfEnergy
from .sanity_check import SanityCheck
from concurrent.futures import Future
from pathlib import Path
from pymodbus.pdu import ExceptionResponse
from sigenergy2mqtt.config import Config, RegisterAccess
from sigenergy2mqtt.devices.types import HybridInverter, PVInverter
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.modbus import ModbusClient, ModbusLockFactory
from sigenergy2mqtt.mqtt import MqttClient, MqttHandler
from typing import Any, Coroutine, Dict, Final
import abc
import asyncio
import datetime
import html
import json
import logging
import re
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

        self._gain: float = gain
        self._precision: int = precision

        self._derived_sensors: Dict[str, "DerivedSensor"] = {}
        self._requisite_sensors: Dict[str, "RequisiteSensor"] = {}

        self._debug_logging: bool = Config.sensor_debug_logging

        self._force_publish: bool = False
        self._publishable: bool = True
        self._persistent_publish_state_file: Path = Path(Config.persistent_state_path, f"{unique_id}.publishable")

        self._states: list[tuple[float, float | int]] = []
        self._max_states: int = 2
        self._sanity: SanityCheck = SanityCheck()

        self._failures: int = 0
        self._max_failures: int = 10
        self._max_failures_retry_interval: int = 0
        self._next_retry: float = None

        self._qos: int = 0
        self._retain: bool = False

        self._sleeper_task: Coroutine = None

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
        return None if len(self._states) < 2 else self._states[-1][0] - self._states[-2][0]

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
            raise ValueError(f"{self.__class__.__name__}.publishable must be a bool")
        if self._publishable == value:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__}.publishable unchanged ({value})")
        else:
            self._publishable = value
            logging.debug(f"{self.__class__.__name__}.publishable set to {value}")

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

    def _apply_gain_and_precision(self, state, raw):
        """
        Applies gain and precision adjustments to a given state value if applicable.

        If the state is a float or int and the 'raw' flag is False, this method:
          - Divides the state by self._gain if self._gain is set and not equal to 1.
          - Rounds the state to self._precision decimal places if self._precision is set.

        Args:
            state (float or int): The value to be adjusted.
            raw (bool): Indicates whether the value is raw (unprocessed). If True, no adjustments are made.

        Returns:
            float or int: The adjusted state value after applying gain and precision, or the original state if conditions are not met.
        """
        if isinstance(state, (float, int)) and not raw:
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Applying gain={self._gain} and precision={self._precision} to {state=}")
            if self._gain is not None and self._gain != 1:
                state /= self._gain
            if self._precision is not None:
                state = round(state, self._precision)
        return state

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
        logging.debug(f"{sensor.__class__.__name__} added to {self.__class__.__name__} derived sensors")

    def add_requisite_sensor(self, sensor: "RequisiteSensor") -> None:
        """Adds a requisite sensor on which this sensor depends.

        Args:
            sensor:     The RequisiteSensor instance.
        """
        self._requisite_sensors[sensor.__class__.__name__] = sensor
        logging.debug(f"{sensor.__class__.__name__} added to {self.__class__.__name__} requisite sensors")

    def apply_sensor_overrides(self, registers: RegisterAccess):
        for identifier in Config.sensor_overrides.keys():
            if identifier in self.__class__.__name__ or identifier in self["object_id"] or identifier in self.unique_id:
                overrides = Config.sensor_overrides[identifier]
                if "debug-logging" in overrides and self._debug_logging != overrides["debug-logging"]:
                    self._debug_logging = overrides["debug-logging"]
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'debug-logging' override ({overrides['debug-logging']})")
                if "gain" in overrides and self._gain != overrides["gain"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'gain' override ({overrides['gain']})")
                    self._gain = overrides["gain"]
                if "icon" in overrides and self["icon"] != overrides["icon"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'icon' override ({overrides['icon']})")
                    self["icon"] = overrides["icon"]
                if "max-failures" in overrides and self._max_failures != overrides["max-failures"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'max-failures' override ({overrides['max-failures']})")
                    self._max_failures = overrides["max-failures"]
                if "max-failures-retry-interval" in overrides and self._max_failures_retry_interval != overrides["max-failures-retry-interval"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'max-failures-retry-interval' override ({overrides['max-failures-retry-interval']})")
                    self._max_failures_retry_interval = overrides["max-failures-retry-interval"]
                if "precision" in overrides and self._precision != overrides["precision"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'precision' override ({overrides['precision']})")
                    self._precision = overrides["precision"]
                    self["display_precision"] = self._precision
                if "publishable" in overrides and self.publishable != overrides["publishable"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'publishable' override ({overrides['publishable']})")
                    self.publishable = overrides["publishable"]
                if "sanity-check-delta" in overrides and self._sanity.delta != overrides["sanity-check-delta"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-delta' override ({overrides['sanity-check-delta']})")
                    self._sanity.delta = overrides["sanity-check-delta"]
                if "sanity-check-max-value" in overrides and self._sanity.max_value != overrides["sanity-check-max-value"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-max-value' override ({overrides['sanity-check-max-value']})")
                    self._sanity.max_value = overrides["sanity-check-max-value"]
                if "sanity-check-min-value" in overrides and self._sanity.min_value != overrides["sanity-check-min-value"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-min-value' override ({overrides['sanity-check-min-value']})")
                    self._sanity.min_value = overrides["sanity-check-min-value"]
                if "unit-of-measurement" in overrides and self["unit_of_measurement"] != overrides["unit-of-measurement"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'unit-of-measurement' override ({overrides['unit-of-measurement']})")
                    self["unit_of_measurement"] = overrides["unit-of-measurement"]
        if self.publishable and registers:
            if registers.no_remote_ems and (getattr(self, "_remote_ems", None) is not None or getattr(self, "_address", None) == 40029):
                logging.debug(f"{self.__class__.__name__} Applying device 'no-remote-ems' override ({registers.no_remote_ems})")
                self.publishable = False
            elif isinstance(self, WritableSensorMixin) and not isinstance(self, WriteOnlySensor):
                if not registers.read_write:
                    logging.debug(f"{self.__class__.__name__} Applying device 'read-write' override ({registers.read_write})")
                    self.publishable = registers.read_write
            elif isinstance(self, (ReadableSensorMixin, DerivedSensor)):
                if not registers.read_only:
                    logging.debug(f"{self.__class__.__name__} Applying device 'read-only' override ({registers.read_only})")
                    self.publishable = registers.read_only
            elif isinstance(self, WriteOnlySensor):
                if not registers.write_only:
                    logging.debug(f"{self.__class__.__name__} Applying device 'write-only' override ({registers.write_only})")
                    self.publishable = registers.write_only
            else:
                logging.warning(f"{self.__class__.__name__} Failed to determine superclass to apply device publishable overrides")

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = (
            f"{Config.home_assistant.discovery_prefix}/{self['platform']}/{device_id}/{self['object_id']}"
            if Config.home_assistant.enabled and not Config.home_assistant.use_simplified_topics
            else f"sigenergy2mqtt/{self['object_id']}"
        )
        self["state_topic"] = f"{base}/state"
        self["json_attributes_topic"] = f"{base}/attributes"
        self["availability_mode"] = "all"
        self["availability"] = [{"topic": f"{Config.home_assistant.discovery_prefix}/device/{device_id}/availability"}]
        return base

    def get_attributes(self) -> dict[str, Any]:
        """Gets the Home Assistant attributes for this sensor.

        Returns:
            A dictionary of attributes for this sensor.
        """
        attributes = {}
        attributes["sensor-class"] = self.__class__.__name__
        if self._gain:
            attributes["gain"] = self._gain
        if hasattr(self, "_scan_interval"):
            attributes["scan-interval"] = self._scan_interval
        if hasattr(self, "command_topic"):
            attributes["update-topic"] = self.command_topic
        return attributes

    def get_discovery(self, mqtt: MqttClient) -> Dict[str, dict[str, Any]]:
        """Gets the Home Assistant MQTT auto-discovery components for this sensor.

        Returns:
            A dictionary keyed by sensor.unique_id with the values containing the discovery configuration.
        """
        assert "availability" in self, f"{self.__class__.__name__} MQTT topics are not configured?"
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} Getting discovery")
        components = self.get_discovery_components()
        for config in components.values():
            if "object_id" in config:
                config["default_entity_id"] = f"{config['platform']}.{config['object_id']}"
        if self.publishable and not Config.clean:
            if self._persistent_publish_state_file.exists():
                self._persistent_publish_state_file.unlink(missing_ok=True)
                logging.debug(f"{self.__class__.__name__} Removed {self._persistent_publish_state_file} ({self.publishable=} and {Config.clean=})")
        else:
            if "json_attributes_topic" in self:
                mqtt.publish(self["json_attributes_topic"], None, qos=0, retain=False)  # Clear retained messages
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed any retained messages in topic '{self['json_attributes_topic']}'")
            if self._persistent_publish_state_file.exists() or Config.clean:
                components = {}
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery ({self._persistent_publish_state_file} exists and {Config.clean=})")
            else:
                for id in components.keys():
                    components[id] = {"p": self["platform"]}
                with self._persistent_publish_state_file.open("w") as f:
                    f.write("0")
                if self._debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery except {components} ({self._persistent_publish_state_file} exists and {Config.clean=})")
        return components

    def get_discovery_components(self) -> Dict[str, Dict[str, Any]]:
        components = dict((k, v) for k, v in self.items() if v is not None)
        if "options" in components and self["platform"] != "select":
            del components["options"]
        return {self.unique_id: dict(components)}

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        """Gets the state of this sensor.

        Args:
            raw:        If True, return the raw reading.
            republish:  If True, do NOT acquire the current state, but instead return the previous state.
            **kwargs    Supplemental keyword arguments to pass to the get_reading method.

        Returns:
            The state of this sensor.
        """
        state = None
        if republish and len(self._states) > 0:
            state = self._states[-1][1]
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Republishing previous state ({state=})")
        else:
            result = await self._update_internal_state(**kwargs)
            if result:
                for sensor in self._requisite_sensors.values():
                    result = result and sensor.update_base_sensor_state(self, **kwargs)
                state = self._states[-1][1]
        return self._apply_gain_and_precision(state, raw)

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
                if self.publishable:
                    state = await self.get_state(modbus=modbus, raw=False, republish=republish)
                    if state is None and not self.force_publish:
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} Publishing SKIPPED: State is None?")
                    else:
                        if self._failures > 0:
                            logging.info(f"{self.__class__.__name__} Resetting failure count from {self._failures} to 0 because valid state acquired ({state=})")
                            self._failures = 0
                            self._next_retry = None
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} Publishing {state=}")
                        mqtt.publish(self["state_topic"], f"{state}", self._qos, self._retain)
                for sensor in self._derived_sensors.values():
                    await sensor.publish(mqtt, modbus, republish=republish)
            except Exception as e:
                logging.warning(f"{self.__class__.__name__} Publishing SKIPPED: Failed to get state ({repr(e)})")
                if modbus.connected:
                    self._failures += 1
                    self._next_retry = (
                        None
                        if self._failures < self._max_failures or self._max_failures_retry_interval == 0
                        else (now + (self._max_failures_retry_interval * max(1, self._failures - self._max_failures)))
                    )
                    if self.debug_logging:
                        logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=}")
                else:
                    raise
                if Config.home_assistant.enabled:
                    self.publish_attributes(mqtt, failures=self._failures, exception=f"{repr(e)}")
                if self._failures >= self._max_failures:
                    logging.warning(
                        f"{self.__class__.__name__} Publish DISABLED until {'restart' if self._next_retry is None else time.strftime('%c', time.localtime(self._next_retry))} - MAX_FAILURES exceeded: {self._failures}"
                    )
                    for sensor in self._derived_sensors.values():
                        logging.warning(
                            f"{sensor.__class__.__name__} Publish DISABLED until {'restart' if self._next_retry is None else time.strftime('%c', time.localtime(self._next_retry))} - MAX_FAILURES exceeded ({self._failures}) for source sensor {self.__class__.__name__}"
                        )
            finally:
                self.force_publish = False
        elif self.debug_logging:
            logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=} {now=}")

    def publish_attributes(self, mqtt: MqttClient, **kwargs) -> None:
        """Publishes the attributes for this sensor.

        Args:
            mqtt:       The MQTT client for publishing the current state.
            **kwargs:   key=value pairs that will be added as attributes.
        """
        if self.publishable and not Config.clean:
            attributes = {key: html.unescape(value) if isinstance(value, str) else value for key, value in self.get_attributes().items()}
            for k, v in kwargs.items():
                attributes[k] = v
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Publishing {attributes=}")
            mqtt.publish(self["json_attributes_topic"], json.dumps(attributes, indent=4), 2, True)
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
        if self._sanity.check(state, self._states):
            if self._debug_logging:
                logging.debug(f"{self.__class__.__name__} Acquired raw {state=}")
            self._states.append((time.time(), state))
            if len(self._states) > self._max_states:
                self._states = self._states[-self._max_states :]

    def state2raw(self, state: float | int | str) -> float | int | str:
        """Converts a processed state back to its raw value.

        Args:
            state:      The processed state.

        Returns:
            The raw state.
        """
        if state is None:
            return None
        elif isinstance(state, str):
            if self._data_type == ModbusClient.DATATYPE.STRING:
                return state
            elif "options" in self and state in self["options"]:
                return self["options"].index(state)
        try:
            value = float(state) if "." in state else int(state)
        except ValueError:
            value = state
        if isinstance(value, (float, int)):
            if self.gain is not None and self.gain != 1:
                value *= self.gain
        return int(value)


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
            return self._apply_gain_and_precision(self._states[-1][1], raw)

    @abc.abstractmethod
    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        """Applies the values from the source Sensor to this DerivedSensor.

        Args:
            sensor:     The Sensor that contributes to this DerivedSensor.
            values:     The list of current values to update this sensor.
        """
        pass


class ModbusSensor(Sensor):
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
        unique_id_override: str = None,
    ):
        assert device_address is not None and 1 <= device_address <= 247, f"Invalid device address {device_address}"
        assert address >= 30000, f"Invalid address {address}"
        assert count > 0, f"Invalid count {count}"
        assert data_type in ModbusClient.DATATYPE, f"Invalid data type {data_type}"

        unique_id = unique_id_override if unique_id_override is not None else f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{address}"

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
        if rr is None:
            logging.error(f"{self.__class__.__name__} Modbus {source} failed to read registers (None response)")
            return False
        elif rr.isError() or isinstance(rr, ExceptionResponse):
            match rr.exception_code:
                case 1:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x01 ILLEGAL FUNCTION")
                    if self.debug_logging:
                        logging.debug(rr)
                    raise Exception("0x01 ILLEGAL FUNCTION")
                case 2:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x02 ILLEGAL DATA ADDRESS")
                    if self.debug_logging:
                        logging.debug(rr)
                    logging.warning(f"{self.__class__.__name__} Setting max allowed failures to 0 for '{self.unique_id}' because of ILLEGAL DATA ADDRESS exception")
                    self._max_failures = 0
                    self._max_failures_retry_interval = 0
                    raise Exception("0x02 ILLEGAL DATA ADDRESS")
                case 3:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x03 ILLEGAL DATA VALUE")
                    if self.debug_logging:
                        logging.debug(rr)
                    raise Exception("0x03 ILLEGAL DATA VALUE")
                case 4:
                    logging.error(f"{self.__class__.__name__} Modbus {source} returned 0x04 SLAVE DEVICE FAILURE")
                    if self.debug_logging:
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

        self._sanity.init(self["unit_of_measurement"], self["state_class"], self.gain, scan_interval)

        for identifier in Config.sensor_overrides.keys():
            if identifier in self.__class__.__name__ or identifier in self["object_id"]:
                overrides = Config.sensor_overrides[identifier]
                if "scan-interval" in overrides and self._scan_interval != overrides["scan-interval"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'scan-interval' override ({overrides['scan-interval']})")
                    self._scan_interval = overrides["scan-interval"]

    @property
    def scan_interval(self):
        return self._scan_interval


class ReadOnlySensor(ModbusSensor, ReadableSensorMixin):
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
        unique_id_override: str = None,
    ):
        ModbusSensor.__init__(
            self, name, object_id, input_type, plant_index, device_address, address, count, data_type, unit, device_class, state_class, icon, gain, precision, unique_id_override=unique_id_override
        )
        ReadableSensorMixin.__init__(self, scan_interval)

    async def _update_internal_state(self, **kwargs) -> bool | Exception:
        """Retrieves the current state of this sensor and updates the internal state history.

        Args:
            **kwargs    Implementation specific arguments.

        Returns:
            True if the state was updated, False if it was not.
        """
        assert "modbus" in kwargs, f"{self.__class__.__name__} Required argument 'modbus' not supplied"
        result = False
        modbus: ModbusClient = kwargs["modbus"]

        if self.debug_logging:
            logging.debug(
                f"{self.__class__.__name__} read_{self._input_type}_registers({self._address}, count={self._count}, device_id={self._device_address}) plant_index={self._plant_index} interval={self._scan_interval}s actual={None if len(self._states) == 0 else str(round(time.time() - self._states[-1][0], 2)) + 's'}"
            )

        try:
            start = time.monotonic()
            if self._input_type == InputType.HOLDING:
                rr = await modbus.read_holding_registers(self._address, count=self._count, device_id=self._device_address, trace=self.debug_logging)
            elif self._input_type == InputType.INPUT:
                rr = await modbus.read_input_registers(self._address, count=self._count, device_id=self._device_address, trace=self.debug_logging)
            else:
                logging.error(f"{self.__class__.__name__} Unknown input type '{self._input_type}'")
                raise Exception(f"Unknown input type '{self._input_type}'")
            elapsed = time.monotonic() - start
            await Metrics.modbus_read(self._count, elapsed)
            result = self._check_register_response(rr, f"read_{self._input_type}_registers")
            if result:
                self.set_latest_state(modbus.convert_from_registers(rr.registers, self._data_type))
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus read interrupted")
            result = False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus read failed to acquire lock within {self._scan_interval}s")
            result = False
        except Exception:
            await Metrics.modbus_read_error()
            raise

        if self.debug_logging:
            logging.debug(
                f"{self.__class__.__name__} read_{self._input_type}_registers({self._address}, count={self._count}, device_id={self._device_address}) plant_index={self._plant_index} interval={self._scan_interval}s actual={None if len(self._states) == 0 else str(round(time.time() - self._states[-1][0], 2)) + 's'} elapsed={(elapsed / 1000):.2f}ms {result=}"
            )
        return result

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["source"] = self._address
        return attributes


class ReservedSensor(ReadOnlySensor):
    """Base superclass of all sensor definitions that are reserved for future use.

    Reserved sensors are NOT published.
    """

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
        unique_id_override: str = None,
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
            unique_id_override=unique_id_override,
        )
        self._publishable = False  # Reserved sensors are not published

    @property
    def publishable(self) -> bool:
        return False

    @publishable.setter
    def publishable(self, value: bool):
        if value:
            raise ValueError("Cannot set publishable=True for ReservedSensor")

    def apply_sensor_overrides(self, registers):
        pass


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

    def state2raw(self, state) -> float | int | str:
        return int(datetime.datetime.fromisoformat(state).timestamp())


class ObservableMixin(abc.ABC):
    @abc.abstractmethod
    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        pass

    @abc.abstractmethod
    def observable_topics(self) -> set[str]:
        return set()


class WritableSensorMixin(ModbusSensor):
    @property
    def command_topic(self) -> str:
        topic: str = self["command_topic"]
        assert topic and not topic.isspace(), f"{self.__class__.__name__} command topic is not defined"
        return topic

    async def _write_registers(self, modbus: ModbusClient, value: float | int | str, mqtt: MqttClient) -> bool:
        max_wait = 2
        device_id = self._device_address
        no_response_expected = False
        logging.info(f"{self.__class__.__name__} write_registers {self._address=} {value=} ({self.latest_raw_state=}) {device_id=}")
        if self._data_type == ModbusClient.DATATYPE.UINT16 and isinstance(value, int) and 0 <= value <= 255:  # Unsigned 8-bit ints do not need encoding
            registers = [value]
        elif self._data_type == ModbusClient.DATATYPE.STRING:
            registers = modbus.convert_to_registers(str(value), self._data_type)
        else:
            registers = modbus.convert_to_registers(int(value), self._data_type)
        method = "write_register" if len(registers) == 1 else "write_registers"
        try:
            async with ModbusLockFactory.get(modbus).lock(max_wait):
                if Config.devices[self._plant_index].log_level == logging.DEBUG:
                    logging.debug(f"{self.__class__.__name__} {method}({self._address}, value={registers}, {device_id=}, {no_response_expected=}) [plant_index={self._plant_index}]")
                start = time.monotonic()
                if len(registers) == 1:
                    rr = await modbus.write_register(self._address, registers[0], device_id=device_id, no_response_expected=no_response_expected)
                else:
                    rr = await modbus.write_registers(self._address, registers, device_id=device_id, no_response_expected=no_response_expected)
                elapsed = time.monotonic() - start
                await Metrics.modbus_write(len(registers), elapsed)
            if Config.devices[self._plant_index].log_level == logging.DEBUG:
                logging.debug(f"{self.__class__.__name__} {method}({self._address}, value={registers}, {device_id=}, {no_response_expected=}) [plant_index={self._plant_index}] took {elapsed:.3f}s")
            result = self._check_register_response(rr, method)
            if result:
                self.force_publish = True
                await self.publish(mqtt, modbus)
            return result
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus write interrupted")
            result = False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus write failed to acquire lock within {max_wait}s")
            result = False
        except Exception as e:
            logging.error(f"{self.__class__.__name__} write_registers: {repr(e)}")
            await Metrics.modbus_write_error()
            raise

    def configure_mqtt_topics(self, device_id: str) -> None:
        base = super().configure_mqtt_topics(device_id)
        self["command_topic"] = f"{base}/set"
        return base

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source == self["command_topic"]:
            return await self._write_registers(modbus, value, mqtt)
        else:
            logging.warning(f"{self.__class__.__name__} Attempt to set_value({value}) from unknown topic {source}")
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
        payload_off: str = "off",
        payload_on: str = "on",
        name_off: str = "Power Off",
        name_on: str = "Power On",
        icon_off: str = "mdi:power-off",
        icon_on: str = "mdi:power-on",
        value_off: int = 0,
        value_on: int = 1,
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
        self._payloads = {"off": payload_off, "on": payload_on}
        self._names = {"off": name_off, "on": name_on}
        self._icons = {"off": icon_off, "on": icon_on}
        self._values = {"off": value_off, "on": value_on}

    def get_discovery_components(self) -> Dict[str, dict[str, Any]]:
        components = {}
        for action in ["On", "Off"]:  # Remove legacy entities first
            components[f"{self.unique_id}_{action}"] = {"p": "button"}
        for action in ["on", "off"]:
            config = {}
            for k, v in self.items():
                if v is not None:
                    if k == "name":
                        config[k] = self._names[action]
                    elif k == "object_id" or k == "unique_id":
                        config[k] = f"{v}_{self._payloads[action]}"
                    else:
                        config[k] = v
            config["icon"] = self._icons[action]
            config["payload_press"] = self._payloads[action]
            components[f"{self.unique_id}_{action}"] = config
        if self._debug_logging:
            logging.debug(f"{self.__class__.__name__} Discovered {components=}")
        return components

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if value == self._payloads["off"]:
            return await super().set_value(modbus, mqtt, self._values["off"], source, handler)
        elif value == self._payloads["on"]:
            return await super().set_value(modbus, mqtt, self._values["on"], source, handler)
        else:
            logging.warning(f"{self.__class__.__name__} Ignored attempt to set value to {value}: Must be either '{self._payloads['on']}' or '{self._payloads['off']}'")
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
        self._sanity.min_value = None
        self._sanity.max_value = None

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        state = await super().get_state(raw=raw, republish=republish, **kwargs)
        if isinstance(state, (float, int)):
            if state < self["min"]:
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} {state=} < {self['min']=} so adjusted")
                state = self["min"]
            elif state > self["max"]:
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} {state=} > {self['max']=} so adjusted")
                state = self["max"]
        return state

    async def set_value(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if value is not None:
            try:
                state = float(value)
                if self.gain != 1:
                    state = state * self.gain
                return await super().set_value(modbus, mqtt, state, source, handler)
            except Exception as e:
                logging.warning(f"{self.__class__.__name__} Attempt to set value to {value} FAILED: {repr(e)}")
        else:
            logging.warning(f"{self.__class__.__name__} Ignored attempt to set None value to {value}")
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
        alarm_type: str,
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
            scan_interval=Config.devices[plant_index].scan_interval.realtime if plant_index < len(Config.devices) else 5,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
        )
        self.alarm_type = alarm_type

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
        elif value is None or value == 0 or (isinstance(value, list) and sum(value) == 0):
            return self.NO_ALARM
        else:
            if isinstance(value, list) and len(value) == 2 and value[0] == 0 and value[1] != 0:
                logging.warning(f"{self.__class__.__name__} Converting '{value}' to {value[1]} for {self.alarm_type} alarm bit decoding")
                value = value[1]
            active_alarms = []
            try:
                for bit_position in range(16):
                    if value & (1 << bit_position):
                        description = self.decode_alarm_bit(bit_position)
                        if description:
                            active_alarms.append(description)
                        else:
                            active_alarms.append(f"Unknown (bit{bit_position}∈{value})")
                            logging.warning(f"{self.__class__.__name__} Unknown {self.alarm_type} alarm bit {bit_position} set in value {value}")
            except TypeError as e:
                logging.warning(f"{self.__class__.__name__} Failed to decode {self.alarm_type} alarm bits from '{value}': {e}")
            if not active_alarms:
                return f"Unknown Alarm {value}"
            else:
                alarms = ", ".join(active_alarms)
                if Config.home_assistant.enabled:
                    max_length = 255 if not ("max_length" in kwargs and isinstance(kwargs["max_length"], int) and int(kwargs["max_length"]) > 0) else int(kwargs["max_length"])
                    if len(alarms) > max_length:
                        alarms = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", alarms)).strip()
                        if len(alarms) > max_length:
                            alarms = alarms[: (max_length - 3)] + "..."
                return alarms


class Alarm1Sensor(AlarmSensor):
    """Superclass of all Alarm 1 definitions. Alarms have the same configuration in the both the Power Plant and the Hybrid Inverter."""

    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int):
        super().__init__(name, object_id, plant_index, device_address, address, "PCS")

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
        super().__init__(name, object_id, plant_index, device_address, address, "PCS")

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
        super().__init__(name, object_id, plant_index, device_address, address, "ESS")
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
        super().__init__(name, object_id, plant_index, device_address, address, "GW")
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
        super().__init__(name, object_id, plant_index, device_address, address, "EVDC")
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
        device_addresses = set([a._device_address for a in alarms])
        first_address = min([a._address for a in alarms])
        last_address = max([a._address + a._count - 1 for a in alarms])
        count = sum([a._count for a in alarms])
        assert len(device_addresses) == 1, f"{self.__class__.__name__} Combined alarms must have the same device address ({device_addresses})"
        assert (last_address - first_address + 1) == count, f"{self.__class__.__name__} Combined alarms must have contiguous address ranges ({[a._address for a in alarms]})"
        ReadableSensorMixin.__init__(self, scan_interval=10)
        self["enabled_by_default"] = True
        self._alarms = list(alarms)
        self._address = min([a._address for a in alarms])
        self._device_address = device_addresses.pop()
        self._scan_interval = min([a._scan_interval for a in alarms])
        self._count = count
        self._input_type = alarms[0]._input_type
        self._data_type = alarms[0]._data_type

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
            return self._apply_gain_and_precision(self._states[-1][1], raw)
        else:
            result = AlarmSensor.NO_ALARM
            for alarm in self._alarms:
                state = await alarm.get_state(raw=False, republish=False, max_length=sys.maxsize, **kwargs)
                if state != AlarmSensor.NO_ALARM:
                    if result == AlarmSensor.NO_ALARM:
                        result = state
                    else:
                        result = ", ".join([result, state])
                        if len(result) > 255 and Config.home_assistant.enabled:
                            result = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", result)).strip()
                            if len(result) > 255:
                                result = result[:252] + "..."
            self.set_state(result)
            return self._apply_gain_and_precision(self._states[-1][1], raw)


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
            scan_interval=Config.devices[plant_index].scan_interval.high if plant_index < len(Config.devices) else 10,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:power-settings",
            gain=None,
            precision=None,
        )
        self["enabled_by_default"] = True
        self["options"] = [
            "Standby",  # 0
            "Normal",  # 1
            "Fault",  # 2
            "Power-Off",  # 3
            None,  # 4
            None,  # 5
            None,  # 6
            "Environmental Abnormality",  # 7
        ]

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
        elif 0 <= value <= (len(self["options"]) - 1) and self["options"][value] is not None:
            return self["options"][value]
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
        unit: str,
        device_class: DeviceClass,
        state_class: StateClass,
        icon: str,
        gain: float,
        precision: int,
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

    def get_attributes(self) -> dict[str, Any]:
        attributes = super().get_attributes()
        attributes["reset_topic"] = self._reset_topic
        attributes["reset_unit"] = self.unit
        return attributes


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
        icon="mdi:home-lightning-bolt",
        gain=1000,
        precision=2,
    ):
        super().__init__(name, unique_id, object_id, source, unit=unit, device_class=device_class, state_class=state_class, icon=icon, gain=gain, precision=precision)
        self._current_total: float = 0.0
        self._persistent_state_file = Path(Config.persistent_state_path, f"{self.unique_id}.state")
        if self._persistent_state_file.is_file():
            with self._persistent_state_file.open("r") as f:
                try:
                    content = f.read()
                    if content is not None and content != "None":
                        self._current_total = float(content)
                        logging.debug(f"{self.__class__.__name__} Loaded current state from {self._persistent_state_file} ({self._current_total})")
                except ValueError as error:
                    logging.warning(f"{self.__class__.__name__} Failed to read {self._persistent_state_file}: {error}")
        else:
            logging.debug(f"{self.__class__.__name__} Persistent state file {self._persistent_state_file} not found")
        self.set_latest_state(self._current_total)

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self.observable_topics():
            new_total = (value if value is float else float(value)) * self.gain
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({new_total=})")
            await self._persist_current_total(new_total)
            self._current_total = new_total
            self.set_latest_state(self._current_total)
            self.force_publish = True
            return True
        else:
            return False

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        elif len(values) < 2:
            return False  # Need at least two points to calculate

        # Calculate time difference in hours
        interval_hours = sensor.latest_interval / 3600
        if interval_hours < 0:
            logging.warning(f"{self.__class__.__name__} negative interval IGNORED ({sensor.latest_interval=})")
            return False

        # Convert negative power readings to zero
        previous = max(0.0, values[-2][1])
        current = max(0.0, values[-1][1])
        # Calculate the area under the power curve using the trapezoidal rule
        # Area = 0.5 * (sum of parallel sides) * height
        # Here, parallel sides are power readings, and height is time difference.
        increase = 0.5 * (previous + current) * interval_hours
        new_total = self._current_total + increase

        if new_total < self._current_total and self.state_class == StateClass.TOTAL_INCREASING:
            logging.debug(f"{self.__class__.__name__} negative increase IGNORED ({self._current_total=} {previous=} {current=} {increase=} {new_total=} {sensor.latest_interval=:.2f}s)")
            return False
        else:
            asyncio.run_coroutine_threadsafe(self._persist_current_total(new_total), asyncio.get_running_loop())
            self._current_total = new_total
            self.set_latest_state(self._current_total)
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
    ):
        super().__init__(
            name, unique_id, object_id, source, unit=source.unit, device_class=source.device_class, state_class=source["state_class"], icon=source["icon"], gain=source.gain, precision=source.precision
        )
        self._state_at_midnight_lock = asyncio.Lock()
        self._state_at_midnight: float = None
        self._persistent_state_file = Path(Config.persistent_state_path, f"{source.unique_id}.atmidnight")
        if self._persistent_state_file.is_file():
            fmt = time.localtime(self._persistent_state_file.stat().st_mtime)
            now = time.localtime()
            if fmt.tm_year == now.tm_year and fmt.tm_mon == now.tm_mon and fmt.tm_mday == now.tm_mday:
                with self._persistent_state_file.open("r") as f:
                    try:
                        content = f.read()
                        if content is not None and content != "None":
                            value = float(content)
                            if value <= 0.0:
                                logging.debug(f"{self.__class__.__name__} Ignored negative last midnight state from {self._persistent_state_file} ({value})")
                                self._persistent_state_file.unlink()
                            else:
                                self._state_at_midnight = value
                                logging.debug(f"{self.__class__.__name__} Loaded last midnight state from {self._persistent_state_file} ({self._state_at_midnight})")
                    except ValueError as error:
                        logging.warning(f"Sensor {self.__class__.__name__} Failed to read {self._persistent_state_file}: {error}")
                        self._persistent_state_file.unlink()
            else:
                logging.debug(f"{self.__class__.__name__} Ignored last midnight state file {self._persistent_state_file} because it is stale ({fmt})")
                self._persistent_state_file.unlink(missing_ok=True)
        else:
            logging.debug(f"{self.__class__.__name__} Persistent state file {self._persistent_state_file} not found")

    async def notify(self, modbus: ModbusClient, mqtt: MqttClient, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self.observable_topics():
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} notified of updated state {value} {self.unit}")
            self._state_now = (value if value is float else float(value)) * self.gain
            updated_midnight_state = self._source.latest_raw_state - self._state_now
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} {self._source.latest_raw_state=} (from {self._source.unique_id}) {self._state_now=} {updated_midnight_state=}")
            await self._update_state_at_midnight(updated_midnight_state)
            self.set_latest_state(self._state_now)
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({self._state_now=})")
            self.force_publish = True
            return True
        else:
            return False

    async def publish(self, mqtt: MqttClient, modbus: ModbusClient, republish: bool = False) -> None:
        if not self._persistent_state_file.is_file():
            await self._update_state_at_midnight(self._state_at_midnight)
        return await super().publish(mqtt, modbus, republish)

    def set_source_values(self, sensor: ModbusSensor, values: list) -> bool:
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False

        now_state = values[-1][1]

        if len(values) > 1:
            was = time.localtime(values[-2][0])
            now = time.localtime(values[-1][0])
            if was.tm_year != now.tm_year or was.tm_mon != now.tm_mon or was.tm_mday != now.tm_mday:
                asyncio.run_coroutine_threadsafe(self._update_state_at_midnight(now_state), asyncio.get_running_loop())

        if not self._state_at_midnight:
            self._state_at_midnight = now_state

        self._state_now = now_state - self._state_at_midnight
        self.set_latest_state(self._state_now)

    async def _update_state_at_midnight(self, midnight_state: float) -> None:
        if midnight_state is not None:
            async with self._state_at_midnight_lock:
                with self._persistent_state_file.open("w") as f:
                    f.write(str(midnight_state))
                self._state_at_midnight = midnight_state


class PVPowerSensor:
    """Marker class"""

    pass
