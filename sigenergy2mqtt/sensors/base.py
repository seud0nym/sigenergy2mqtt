from __future__ import annotations

import abc
import asyncio
import datetime
import html
import json
import logging
import re
import sys
import time
from concurrent.futures import Future
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Iterable, cast

import paho.mqtt.client as mqtt
from pymodbus.pdu import ExceptionResponse, ModbusPDU

from sigenergy2mqtt.common import HybridInverter, Protocol, PVInverter, RegisterAccess
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.i18n import _t
from sigenergy2mqtt.modbus.types import ModbusClientType, ModbusDataType

if TYPE_CHECKING:
    from sigenergy2mqtt.mqtt import MqttHandler

from .const import PERCENTAGE, DeviceClass, InputType, StateClass, UnitOfEnergy
from .sanity_check import SanityCheck, SanityCheckException


# Provide a small runtime proxy for ModbusLockFactory so other modules/tests
# can patch `sigenergy2mqtt.sensors.base.ModbusLockFactory.get` without
# importing the full modbus package at module import time.
class _ModbusLockFactoryProxy:
    @staticmethod
    def get(modbus):
        from sigenergy2mqtt.modbus import ModbusLockFactory as _Real

        return _Real.get(modbus)

    @staticmethod
    def get_waiter_count() -> int:
        from sigenergy2mqtt.modbus import ModbusLockFactory as _Real

        return _Real.get_waiter_count()


ModbusLockFactory = _ModbusLockFactoryProxy


# Expose a module-level `Metrics` binding. Prefer a `Metrics` attribute if the
# metrics package provides one, otherwise expose the module object. This lets
# tests either patch `sigenergy2mqtt.sensors.base.Metrics` or replace the
# `sigenergy2mqtt.metrics.metrics` module in `sys.modules` with a mock
# (the latter often provides functions at module scope instead of a class).
import importlib as _importlib  # noqa: E402

try:
    _metrics_module = _importlib.import_module("sigenergy2mqtt.metrics.metrics")
    Metrics = getattr(_metrics_module, "Metrics", _metrics_module)
except Exception:
    Metrics: Any = None


class SensorDebuggingMixin:
    def __init__(self, **kwargs):
        self.debug_logging: bool = Config.sensor_debug_logging
        super().__init__(**kwargs)


class Sensor(SensorDebuggingMixin, dict[str, str | int | bool | float | list[str] | list[dict[str, str]] | tuple[float] | DeviceClass | StateClass | None], metaclass=abc.ABCMeta):
    _used_object_ids = {}
    _used_unique_ids = {}

    def __hash__(self) -> int:  # pyright: ignore[reportIncompatibleVariableOverride]
        return hash(self["unique_id"])

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sensor):
            return self["unique_id"] == other["unique_id"]
        return False

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol = Protocol.V2_4,
        **kwargs,
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
        assert isinstance(protocol_version, Protocol), f"{self.__class__.__name__} protocol_version '{protocol_version}' is invalid"

        super().__init__()

        self._used_unique_ids[unique_id] = self.__class__.__name__
        self._used_object_ids[object_id] = self.__class__.__name__

        self._protocol_version = protocol_version

        self["platform"] = "sensor"
        self["name"] = _t(f"{self.__class__.__name__}.name", name)
        self["object_id"] = object_id
        self["unique_id"] = unique_id
        self["device_class"] = device_class
        self["icon"] = icon
        self["state_class"] = state_class
        self["unit_of_measurement"] = unit
        self["display_precision"] = precision
        self["enabled_by_default"] = Config.home_assistant.enabled_by_default

        self._gain: float | None = gain

        self._derived_sensors: dict[str, "DerivedSensor"] = {}

        self._attributes_published: bool = False
        self._publish_raw: bool = False
        self._publishable: bool = True
        self._persistent_publish_state_file: Path = Path(Config.persistent_state_path, f"{unique_id}.publishable")

        self._states: list[tuple[float, Any]] = []
        self._max_states: int = 2

        self._failures: int = 0
        self._max_failures: int = 10
        self._max_failures_retry_interval: int = 0
        self._next_retry: float | None = None

        self._qos: int = 0
        self._retain: bool = False

        self.force_publish: bool = False
        self.name: str = name
        self.object_id: str = object_id
        self.parent_device: Any = None
        self.precision: int | None = precision
        self.sleeper_task: asyncio.Task[None] | None = None
        self.state_class: StateClass | None = state_class
        self.unit: str | None = unit
        self.unique_id: str = unique_id

        self.sanity_check: SanityCheck = SanityCheck(
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            gain=gain,
            precision=precision,
            data_type=getattr(self, "data_type", None),
            delta=False if any(v in self.__class__.__name__ for v in ["Available", "Rated", "Adjustment", "Limit "]) else None,
        )
        if any(v in self.__class__.__name__ for v in ["Available", "Rated", "Adjustment", "Limit "]):
            assert self.sanity_check.delta is False

    # region Properties
    @property
    def device_class(self) -> DeviceClass:
        return cast(DeviceClass, self["device_class"])

    @property
    def gain(self) -> float:
        return 1.0 if self._gain is None else self._gain

    @gain.setter
    def gain(self, value: float | None):
        self._gain = value

    @property
    def latest_interval(self) -> float | None:
        return None if len(self._states) < 2 else self._states[-1][0] - self._states[-2][0]

    @property
    def latest_raw_state(self) -> float | int | str | None:
        return None if len(self._states) == 0 else self._states[-1][1]

    @latest_raw_state.setter
    def latest_raw_state(self, value: float | int | str):
        latest = self._states.pop()
        self._states.append((latest[0], value))

    @property
    def latest_time(self) -> float:
        return 0 if len(self._states) == 0 else self._states[-1][0]

    @property
    def protocol_version(self) -> Protocol:
        return self._protocol_version if self._protocol_version else Protocol.N_A

    @protocol_version.setter
    def protocol_version(self, protocol_version: Protocol | float):
        isProtocol = isinstance(protocol_version, Protocol)
        assert isProtocol or (isinstance(protocol_version, float) and protocol_version in [p.value for p in Protocol]), f"{self.__class__.__name__} protocol_version '{protocol_version}' is invalid"
        if isProtocol:
            self._protocol_version = cast(Protocol, protocol_version)
        else:
            protocol = {p.value: p for p in Protocol}.get(protocol_version)
            if protocol is None:
                raise ValueError(f"{self.__class__.__name__} protocol_version '{protocol_version}' is invalid")
            self._protocol_version = protocol

    @property
    def publishable(self) -> bool:
        return self._publishable

    @publishable.setter
    def publishable(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError(f"{self.__class__.__name__}.publishable must be a bool")
        if self._publishable == value:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__}.publishable unchanged ({value})")
        else:
            self._publishable = value
            logging.debug(f"{self.__class__.__name__}.publishable set to {value}")

    @property
    def publish_raw(self) -> bool:
        return self._publish_raw

    @publish_raw.setter
    def publish_raw(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError(f"{self.__class__.__name__}.publish_raw must be a bool")
        if self._publish_raw == value:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__}.publish_raw unchanged ({value})")
        else:
            self._publish_raw = value
            logging.debug(f"{self.__class__.__name__}.publish_raw set to {value}")

    @property
    def raw_state_topic(self) -> str:
        return cast(str, self["raw_state_topic"])

    @property
    def state_topic(self) -> str:
        return cast(str, self["state_topic"])

    # endregion

    # region Methods
    def _apply_gain_and_precision(self, state: float | int | None, raw: bool = False) -> float | int | None:
        if state is None:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Skipped applying gain={self.gain} and precision={self.precision} to {state=}")
        elif isinstance(state, (float, int)) and not raw:
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Applying gain={self.gain} and precision={self.precision} to {state=}")
            if self.gain is not None:
                state /= self.gain
            if isinstance(state, float) and self.precision is not None:
                state = round(state, self.precision)
                if self.precision == 0:
                    state = int(cast(float, state))
        return state

    def _get_applicable_overrides(self, identifier: str) -> dict | None:
        if re.search(identifier, self.__class__.__name__) or re.search(identifier, self.object_id) or re.search(identifier, self.unique_id):
            return Config.sensor_overrides[identifier]
        return None

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
        self._derived_sensors[sensor.__class__.__name__] = sensor

    def apply_sensor_overrides(self, registers: RegisterAccess | None):
        for identifier in Config.sensor_overrides.keys():
            overrides = self._get_applicable_overrides(identifier)
            if overrides:
                if "debug-logging" in overrides and self.debug_logging != overrides["debug-logging"]:
                    self.debug_logging = overrides["debug-logging"]
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
                if "precision" in overrides and self.precision != overrides["precision"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'precision' override ({overrides['precision']})")
                    self.precision = overrides["precision"]
                    self["display_precision"] = self.precision
                if "publishable" in overrides and self.publishable != overrides["publishable"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'publishable' override ({overrides['publishable']})")
                    self.publishable = overrides["publishable"]
                if "publish-raw" in overrides and self.publish_raw != overrides["publish-raw"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'publish-raw' override ({overrides['publish-raw']})")
                    self.publish_raw = overrides["publish-raw"]
                if "sanity-check-delta" in overrides and self.sanity_check.delta != overrides["sanity-check-delta"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-delta' override ({overrides['sanity-check-delta']})")
                    self.sanity_check.delta = overrides["sanity-check-delta"]
                if "sanity-check-max-value" in overrides and self.sanity_check.max_raw != overrides["sanity-check-max-value"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-max-value' override ({overrides['sanity-check-max-value']})")
                    self.sanity_check.max_raw = overrides["sanity-check-max-value"]
                if "sanity-check-min-value" in overrides and self.sanity_check.min_raw != overrides["sanity-check-min-value"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'sanity-check-min-value' override ({overrides['sanity-check-min-value']})")
                    self.sanity_check.min_raw = overrides["sanity-check-min-value"]
                if "unit-of-measurement" in overrides and self["unit_of_measurement"] != overrides["unit-of-measurement"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'unit-of-measurement' override ({overrides['unit-of-measurement']})")
                    self["unit_of_measurement"] = overrides["unit-of-measurement"]
                if "device-class" in overrides and self["device_class"] != overrides["device-class"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'device-class' override ({overrides['device-class']})")
                    self["device_class"] = overrides["device-class"]
                if "state-class" in overrides and self["state_class"] != overrides["state-class"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'state-class' override ({overrides['state-class']})")
                    self["state_class"] = overrides["state-class"]
                if "name" in overrides and self["name"] != overrides["name"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'name' override ({overrides['name']})")
                    self["name"] = overrides["name"]
        if self.publishable and registers:
            if registers.no_remote_ems and (getattr(self, "_remote_ems", None) is not None or getattr(self, "address", None) == 40029):
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
        self["raw_state_topic"] = f"{base}/raw"
        self["json_attributes_topic"] = f"{base}/attributes"
        if Config.home_assistant.enabled:
            self["availability_mode"] = "all"
            self["availability"] = [{"topic": f"{Config.home_assistant.discovery_prefix}/device/{device_id}/availability"}]
        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Configured MQTT topics ({Config.home_assistant.enabled=} {Config.home_assistant.use_simplified_topics=})")
            for key in ("state_topic", "raw_state_topic", "json_attributes_topic", "availability"):
                if key in self:
                    logging.debug(f"{self.__class__.__name__} >>> {key}={self[key]})")
        return base

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes: dict[str, float | int | str] = {}
        if not Config.home_assistant.enabled:
            attributes["name"] = self.name
            if self.unit:
                attributes["unit-of-measurement"] = self.unit
        attributes["sensor-class"] = self.__class__.__name__
        if self.protocol_version and self.protocol_version != Protocol.N_A:
            attributes["since-protocol"] = f"V{self.protocol_version.value}"
        if self._gain:
            attributes["gain"] = self._gain
        if isinstance(self, ReadableSensorMixin):
            attributes["scan-interval"] = self.scan_interval
        if isinstance(self, WritableSensorMixin):
            attributes["update-topic"] = self.command_topic
        return attributes

    def get_discovery(self, mqtt_client: mqtt.Client) -> dict[str, dict[str, Any]]:
        assert "state_topic" in self, f"{self.__class__.__name__} MQTT topics are not configured?"
        if self.debug_logging:
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
                mqtt_client.publish(cast(str, self["json_attributes_topic"]), None, qos=0, retain=False)  # Clear retained messages
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed any retained messages in topic {self['json_attributes_topic']}")
            if self._persistent_publish_state_file.exists() or Config.clean:
                components = {}
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery ({self._persistent_publish_state_file} exists and {Config.clean=})")
            else:
                for id in components.keys():
                    components[id] = {"p": self["platform"]}
                with self._persistent_publish_state_file.open("w") as f:
                    f.write("0")
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} unpublished - removed all discovery except {components} ({self._persistent_publish_state_file} exists and {Config.clean=})")
        return components

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components = dict((k, v) for k, v in self.items() if v is not None)
        if "options" in self:
            components["options"] = [_t(f"{self.__class__.__name__}.options.{i}", x) for i, x in enumerate(cast(list[str], self["options"])) if x is not None and x != ""]
        return {self.unique_id: dict(components)}

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        state: float | int | str | None = None
        if republish and len(self._states) > 0:
            state = self._states[-1][1]
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Republishing previous state ({state=} retrieved={time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self._states[-1][0]))})")
        else:
            result = await self._update_internal_state(**kwargs)
            if result:
                state = self._states[-1][1]
        return state if raw or isinstance(state, str) else self._apply_gain_and_precision(state, raw)

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool = False) -> bool:
        published: bool = False
        now = time.time()
        if self._failures < self._max_failures or (self._next_retry and self._next_retry <= now):
            try:
                if self.publishable:
                    state = await self.get_state(modbus_client=modbus_client, raw=False, republish=republish)
                    if state is None and not self.force_publish:
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} Publishing SKIPPED: State is None?")
                    else:
                        if self._failures > 0:
                            logging.info(f"{self.__class__.__name__} Resetting failure count from {self._failures} to 0 because valid state acquired ({state=})")
                            self._failures = 0
                            self._next_retry = None
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} Publishing {state=} to topic {self['state_topic']}")
                        mqtt_client.publish(cast(str, self["state_topic"]), f"{state}", self._qos, self._retain)
                        published = True
                        if self.publish_raw:
                            if self.debug_logging:
                                logging.debug(f"{self.__class__.__name__} Publishing raw state={self.latest_raw_state} to topic {self['raw_state_topic']}")
                            mqtt_client.publish(cast(str, self["raw_state_topic"]), f"{self.latest_raw_state}", self._qos, self._retain)
                for sensor in self._derived_sensors.values():
                    await sensor.publish(mqtt_client, modbus_client, republish=republish)
            except Exception as e:
                logging.warning(f"{self.__class__.__name__} Publishing SKIPPED: Failed to get state ({repr(e)})")
                if modbus_client and modbus_client.connected:
                    if isinstance(e, SanityCheckException) and not Config.sanity_check_failures_increment:
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} SanityCheck failure ignored for failure counting ({self._failures} failures)")
                    else:
                        self._failures += 1
                        self._next_retry = (
                            None if self._failures < self._max_failures or self._max_failures_retry_interval == 0 else (now + (self._max_failures_retry_interval * max(1, self._failures - self._max_failures)))
                        )
                        if self.debug_logging:
                            logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=}")
                else:
                    raise
                if Config.home_assistant.enabled:
                    self.publish_attributes(mqtt_client, clean=False, failures=self._failures, exception=f"{repr(e)}")
                if self._failures >= self._max_failures:
                    next = "restart" if self._next_retry is None else time.strftime("%c", time.localtime(self._next_retry))
                    affected = [s.__class__.__name__ for s in self._derived_sensors.values()]
                    logging.warning(f"{self.__class__.__name__} Publishing DISABLED until {next} ({self._failures} failures >= {self._max_failures}) Affected derived sensors={','.join(affected)}")
            finally:
                self.force_publish = False
        elif self.debug_logging:
            logging.debug(f"{self.__class__.__name__} {self._failures=} {self._max_failures=} {self._next_retry=} {now=}")
        return published

    def publish_attributes(self, mqtt_client: mqtt.Client, clean: bool = False, **kwargs) -> None:
        if not self._attributes_published or clean:
            if clean:
                if self.debug_logging:
                    logging.debug(f"{self.name} cleaning attributes")
                mqtt_client.publish(cast(str, self["json_attributes_topic"]), None, qos=1, retain=True)  # Clear retained messages
            elif self.publishable:
                attributes = {key: html.unescape(value) if isinstance(value, str) else value for key, value in self.get_attributes().items()}
                for k, v in kwargs.items():
                    attributes[k] = v
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} Publishing {attributes=}")
                mqtt_client.publish(cast(str, self["json_attributes_topic"]), json.dumps(attributes, indent=4), qos=2, retain=True)
                self._attributes_published = True
                self.force_publish = False
        for sensor in self._derived_sensors.values():
            sensor.publish_attributes(mqtt_client, clean=clean)

    def set_latest_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> None:  # Updates the latest state of this sensor, and passes the updated state to any derived sensors.
        self.set_state(state)
        for sensor in self._derived_sensors.values():
            sensor.set_source_values(self, self._states)

    def set_state(self, state: int | float | str | list[bool] | list[int] | list[float]) -> None:  # Updates the latest state of this sensor, WITHOUT passing the updated state to any derived sensors.
        if isinstance(state, str) or (isinstance(state, (int, float)) and self.sanity_check.is_sane(state, self._states)):
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} Acquired raw {state=}")
            self._states.append((time.time(), state))
            if len(self._states) > self._max_states:
                self._states = self._states[-self._max_states :]

    def state2raw(self, state: float | int | str) -> float | int | str | None:
        if state is None:
            return None
        elif isinstance(state, str):
            if isinstance(self, TypedSensorMixin) and self.data_type == ModbusDataType.STRING:
                return state
            elif "options" in self and state in cast(list[str], self["options"]):
                return cast(list[str], self["options"]).index(state)
            try:
                value = float(state) if "." in state else int(state)
            except ValueError:
                value = state
        else:
            value = state
        if isinstance(value, (float, int)):
            if self.gain is not None and self.gain != 1:
                value *= self.gain
        return int(value)

    # endregion


class TypedSensorMixin:
    def __init__(self, **kwargs):
        assert "data_type" in kwargs, "Missing required parameter: data_type"
        if kwargs["data_type"] not in ModbusDataType:
            raise AssertionError(f"Invalid data type {kwargs['data_type']}")
        self.data_type = kwargs["data_type"]
        super().__init__(**kwargs)


class DerivedSensor(TypedSensorMixin, Sensor):
    def __init__(self, **kwargs):
        if "protocol_version" not in kwargs:
            kwargs["protocol_version"] = Protocol.N_A
        super().__init__(**kwargs)
        self["enabled_by_default"] = True

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        return False

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        if len(self._states) == 0:
            return 0
        else:
            return self._states[-1][1] if isinstance(self._states[-1][1], str) else self._apply_gain_and_precision(self._states[-1][1], raw)

    @abc.abstractmethod
    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        """Applies the values from the source Sensor to this DerivedSensor.

        Args:
            sensor:     The Sensor that contributes to this DerivedSensor.
            values:     The list of current values to update this sensor.
        """
        pass


class ReadableSensorMixin(Sensor):
    def __init__(self, **kwargs):
        assert "scan_interval" in kwargs, "Missing required parameter: scan_interval"
        assert isinstance(kwargs["scan_interval"], int), "scan_interval must be an int"
        assert kwargs["scan_interval"] is not None and kwargs["scan_interval"] >= 1, "scan_interval cannot be less than 1 second"
        self.scan_interval = kwargs["scan_interval"]
        super().__init__(**kwargs)
        for identifier in Config.sensor_overrides.keys():
            overrides = super()._get_applicable_overrides(identifier)
            if overrides:
                if "scan-interval" in overrides and self.scan_interval != overrides["scan-interval"]:
                    logging.debug(f"{self.__class__.__name__} Applying {identifier} 'scan-interval' override ({overrides['scan-interval']})")
                    self.scan_interval = overrides["scan-interval"]


class ModbusSensorMixin(SensorDebuggingMixin):
    def __init__(self, input_type: InputType, plant_index: int, device_address: int, address: int, count: int, unique_id_override: str | None = None, **kwargs):
        assert device_address is not None and 1 <= device_address <= 247, f"Invalid device address {device_address}"
        assert address >= 30000, f"Invalid address {address}"
        assert count > 0, f"Invalid count {count}"

        kwargs["unique_id"] = self.unique_id = unique_id_override if unique_id_override is not None else f"{Config.home_assistant.unique_id_prefix}_{plant_index}_{device_address:03d}_{address}"

        super().__init__(**kwargs)

        self.address = address
        self.count = count
        self.device_address = device_address
        self.input_type = input_type
        self.plant_index = plant_index

    def _check_register_response(self, rr: ModbusPDU | None, source: str) -> bool:
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
                    if source != "write_registers":
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
        else:
            return True


class ReadOnlySensor(TypedSensorMixin, ReadableSensorMixin, ModbusSensorMixin, Sensor):
    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        unique_id_override: str | None = None,
    ):
        super().__init__(
            name=name,
            object_id=object_id,
            input_type=input_type,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=count,
            data_type=data_type,
            scan_interval=scan_interval,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
            protocol_version=protocol_version,
            unique_id_override=unique_id_override,
        )

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        assert "modbus_client" in kwargs, f"{self.__class__.__name__} Required argument 'modbus_client' not supplied"
        result = False
        modbus_client: ModbusClientType = kwargs["modbus_client"]

        if self.debug_logging:
            logging.debug(
                f"{self.__class__.__name__} read_{self.input_type}_registers({self.address}, count={self.count}, device_id={self.device_address}) plant_index={self.plant_index} interval={self.scan_interval}s actual={None if len(self._states) == 0 else str(round(time.time() - self._states[-1][0], 2)) + 's'}"
            )

        try:
            start = time.monotonic()
            if self.input_type == InputType.HOLDING:
                rr = await modbus_client.read_holding_registers(self.address, count=self.count, device_id=self.device_address, trace=self.debug_logging)
            elif self.input_type == InputType.INPUT:
                rr = await modbus_client.read_input_registers(self.address, count=self.count, device_id=self.device_address, trace=self.debug_logging)
            else:
                logging.error(f"{self.__class__.__name__} Unknown input type '{self.input_type}'")
                raise Exception(f"Unknown input type '{self.input_type}'")
            elapsed = time.monotonic() - start
            # use module-level `Metrics` (set at import time) so tests can
            # patch either the module or the `Metrics` name.
            await Metrics.modbus_read(self.count, elapsed)
            result = self._check_register_response(rr, f"read_{self.input_type}_registers")
            if result and rr:
                self.set_latest_state(modbus_client.convert_from_registers(rr.registers, self.data_type))  # pyright: ignore[reportArgumentType]
            if self.debug_logging:
                logging.debug(
                    f"{self.__class__.__name__} read_{self.input_type}_registers({self.address}, count={self.count}, device_id={self.device_address}) plant_index={self.plant_index} interval={self.scan_interval}s actual={None if len(self._states) == 0 else str(round(time.time() - self._states[-1][0], 2)) + 's'} elapsed={(elapsed / 1000):.2f}ms {result=}"
                )
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus read interrupted")
            result = False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus read failed to acquire lock within {self.scan_interval}s")
            result = False
        except Exception:
            # use module-level `Metrics` (set at import time) so tests can
            # patch either the module or the `Metrics` name.
            await Metrics.modbus_read_error()
            raise

        return result

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        source_key = "ReadOnlySensor.attributes.source" if self.count == 1 else "ReadOnlySensor.attributes.source_range"
        source_default = f"Modbus Register {self.address}" if self.count == 1 else f"Modbus Registers {self.address}-{self.address + self.count - 1}"
        attributes["source"] = _t(source_key, source_default).format(address=self.address, start=self.address, end=self.address + self.count - 1)
        if "comment" in self:
            attributes["comment"] = _t(f"{self.__class__.__name__}.comment", cast(str, self["comment"]))
        return attributes


class AvailabilityMixin(Sensor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ReservedSensor(ReadOnlySensor):
    def __init__(
        self,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        unique_id_override: str | None = None,
        availability_control_sensor: AvailabilityMixin | None = None,
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
            protocol_version,
            unique_id_override=unique_id_override,
        )
        assert self.__class__.__name__.startswith("Reserved"), f"{self.__class__.__name__} class name does not start with 'Reserved'"
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
        scan_interval: int,
        protocol_version: Protocol,
    ):
        super().__init__(
            name,
            object_id,
            input_type,
            plant_index,
            device_address,
            address,
            2,  # count
            ModbusDataType.UINT32,
            scan_interval,
            unit=None,
            device_class=DeviceClass.TIMESTAMP,
            state_class=None,
            icon="mdi:calendar-clock",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
        )
        self["entity_category"] = "diagnostic"

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = cast(float, await super().get_state(raw=raw, republish=republish, **kwargs))
        if raw:
            return value
        elif value is None or value == 0:
            return None
        else:
            dt_object = datetime.datetime.fromtimestamp(value, datetime.timezone.utc)
            return dt_object.isoformat()

    def state2raw(self, state) -> float | int | str:
        if isinstance(state, (float, int)):
            return int(state)
        else:
            return int(datetime.datetime.fromisoformat(state).timestamp())


class ObservableMixin(abc.ABC):
    @abc.abstractmethod
    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        pass

    def observable_topics(self) -> set[str]:
        return set()


class SubstituteMixin(abc.ABC):
    @abc.abstractmethod
    def fallback(self, source: str):
        pass

    @abc.abstractmethod
    def failover(self, smartport_sensor: Sensor) -> bool:
        pass


class WritableSensorMixin(TypedSensorMixin, ModbusSensorMixin, Sensor):
    @property
    def command_topic(self) -> str:
        topic: str = cast(str, self["command_topic"])
        assert topic and not topic.isspace(), f"{self.__class__.__name__} command topic is not defined"
        return topic

    def _raw2state(self, raw_value: float | int | str) -> float | int | str:
        if isinstance(raw_value, str):
            return raw_value
        if "options" in self and isinstance(raw_value, int):
            return cast(list[str], self["options"])[raw_value]
        if isinstance(self, WriteOnlySensor) and isinstance(raw_value, str):
            return self._names["off"] if self._values["off"] == raw_value else self._names["on"] if self._values["on"] == raw_value else raw_value
        if isinstance(self, SwitchSensor) and isinstance(raw_value, str):
            return "Off" if self["payload_off"] == raw_value else "On" if self["payload_on"] == raw_value else raw_value
        if isinstance(raw_value, (float, int)):
            state = self._apply_gain_and_precision(raw_value)
            if state is not None:
                return state
        return raw_value

    async def _write_registers(self, modbus_client: ModbusClientType, raw_value: float | int | str, mqtt_client: mqtt.Client) -> bool:
        max_wait = 2
        device_id = self.device_address
        no_response_expected = False
        logging.info(f"{self.__class__.__name__} _write_registers value={self._raw2state(raw_value)} (raw={raw_value} latest_raw_state={self.latest_raw_state} address={self.address} {device_id=})")
        if self.data_type == ModbusDataType.UINT16 and isinstance(raw_value, int) and 0 <= raw_value <= 255:  # Unsigned 8-bit ints do not need encoding
            registers = [raw_value]
        elif self.data_type == ModbusDataType.STRING:
            registers = modbus_client.convert_to_registers(str(raw_value), self.data_type)
        else:
            registers = modbus_client.convert_to_registers(int(raw_value), self.data_type)
        method = "write_register" if len(registers) == 1 else "write_registers"
        self.force_publish = True
        try:
            start = time.monotonic()
            async with ModbusLockFactory.get(modbus_client).lock(max_wait):
                if len(registers) == 1:
                    rr = await modbus_client.write_register(self.address, registers[0], device_id=device_id, no_response_expected=no_response_expected)
                else:
                    rr = await modbus_client.write_registers(self.address, registers, device_id=device_id, no_response_expected=no_response_expected)
            elapsed = time.monotonic() - start
            # use module-level `Metrics` (set at import time) so tests can
            # patch either the module or the `Metrics` name.
            await Metrics.modbus_write(len(registers), elapsed)
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} {method}({self.address}, value={registers}, {device_id=}, {no_response_expected=}) [plant_index={self.plant_index}] took {elapsed:.3f}s")
            result = self._check_register_response(rr, method)
            return result
        except asyncio.CancelledError:
            logging.warning(f"{self.__class__.__name__} Modbus write interrupted")
            return False
        except asyncio.TimeoutError:
            logging.warning(f"{self.__class__.__name__} Modbus write failed to acquire lock within {max_wait}s")
            return False
        except Exception as e:
            logging.error(f"{self.__class__.__name__} write_registers: {repr(e)}")
            # use module-level `Metrics` (set at import time) so tests can
            # patch either the module or the `Metrics` name.
            await Metrics.modbus_write_error()
            raise

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        self["command_topic"] = f"{base}/set"
        return base

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        assert modbus_client is not None, "ModbusClient cannot be None"
        try:
            if not await self.value_is_valid(modbus_client, value):
                return False
        except Exception as e:
            logging.error(f"{self.__class__.__name__} value_is_valid check of value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) FAILED: {repr(e)}")
            raise
        if source == self["command_topic"]:
            return await self._write_registers(modbus_client, value, mqtt_client)
        else:
            logging.error(f"{self.__class__.__name__} Attempt to set value '{value if isinstance(value, str) else self._apply_gain_and_precision(value)}' (raw={value}) from unknown topic {source}")
            return False

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        return True


class WriteOnlySensor(WritableSensorMixin, Sensor):
    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
        payload_off: str = "off",
        payload_on: str = "on",
        name_off: str = "Power Off",
        name_on: str = "Power On",
        icon_off: str = "mdi:power-off",
        icon_on: str = "mdi:power-on",
        value_off: int = 0,
        value_on: int = 1,
        **kwargs,
    ):
        super().__init__(
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            unit=None,
            device_class=None,
            state_class=None,
            icon=None,
            gain=None,
            precision=None,
            protocol_version=protocol_version,
            **kwargs,
        )
        assert icon_on is not None and icon_on.startswith("mdi:"), f"{self.__class__.__name__} on icon {icon_on} does not start with 'mdi:'"
        assert icon_off is not None and icon_off.startswith("mdi:"), f"{self.__class__.__name__} off icon {icon_off} does not start with 'mdi:'"
        self["platform"] = "button"
        self["enabled_by_default"] = True
        self._payloads = {"off": payload_off, "on": payload_on}
        self._names = {"off": name_off, "on": name_on}
        self._icons = {"off": icon_off, "on": icon_on}
        self._values = {"off": value_off, "on": value_on}

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        return False

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components: dict[str, Any] = {}
        for action in ["On", "Off"]:  # Remove legacy entities first
            components[f"{self.unique_id}_{action}"] = {"p": "button"}
        for action in ["on", "off"]:
            config: dict[str, Any] = {}
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
        if self.debug_logging:
            logging.debug(f"{self.__class__.__name__} Discovered {components=}")
        return components

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        return await super().set_value(modbus_client, mqtt_client, self._values["off"] if self._payloads["off"] == value else self._values["on"] if self._payloads["on"] else value, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        if raw_value not in (self._values["off"], self._values["on"]):
            logging.error(f"{self.__class__.__name__} Invalid value '{raw_value}': Must be either '{self._payloads['on']}' or '{self._payloads['off']}'")
            return False
        return True


class ReadWriteSensor(WritableSensorMixin, ReadOnlySensor):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
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
            protocol_version,
        )
        assert availability_control_sensor is None or isinstance(availability_control_sensor, AvailabilityMixin), f"{self.__class__.__name__} availability_control_sensor is not an instance of AvailabilityMixin"
        self._availability_control_sensor = availability_control_sensor
        self["enabled_by_default"] = True

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        if self._availability_control_sensor is not None and Config.home_assistant.enabled:
            assert self._availability_control_sensor.state_topic and not self._availability_control_sensor.state_topic.isspace(), "RemoteEMS state_topic has not been configured"
            cast(list[dict[str, float | int | str]], self["availability"]).append({"topic": self._availability_control_sensor.state_topic, "payload_available": 1, "payload_not_available": 0})
        return base


class NumericSensor(ReadWriteSensor):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        input_type: InputType,
        plant_index: int,
        device_address: int,
        address: int,
        count: int,
        data_type: ModbusDataType,
        scan_interval: int,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
        protocol_version: Protocol,
        minimum: float | tuple[float, float] | None = None,
        maximum: float | tuple[float, float] | None = None,
    ):
        super().__init__(
            availability_control_sensor,
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
            protocol_version,
        )
        assert (
            minimum is None
            or maximum is None
            or (isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum < maximum)
            or (
                isinstance(minimum, (tuple))
                and isinstance(maximum, (tuple))
                and len(minimum) == len(maximum)
                and all(isinstance(mn, (int, float)) and isinstance(mx, (int, float)) and mn < mx for mn, mx in zip(minimum, maximum))
            )
        ), f"{self.__class__.__name__} Invalid min/max values: {minimum}/{maximum}"
        self["platform"] = "number"
        if minimum is None and maximum is None and unit == PERCENTAGE:
            self["min"] = 0.0
            self["max"] = 100.0
        if minimum is not None:  # Must NOT be raw value, and *may* be a tuple of display values!
            self["min"] = float(minimum) if isinstance(minimum, (float, int)) else cast(tuple, minimum) if isinstance(minimum, tuple) else minimum
        elif minimum is None and maximum is not None:
            self["min"] = 0.0 if isinstance(maximum, float) else 0
        if maximum is not None:  # Must NOT be raw value, and *may* be a tuple of display values!
            self["max"] = float(maximum) if isinstance(maximum, (float, int)) else cast(tuple, maximum) if isinstance(maximum, tuple) else maximum
        self["mode"] = "slider" if (unit == PERCENTAGE and not Config.home_assistant.edit_percentage_with_box) else "box"
        self["step"] = 1 if precision is None else 10**-precision
        if "min" in self and isinstance(self["min"], (int, float)):
            self.sanity_check.min_raw = int(self["min"] * gain) if gain else int(self["min"])  # pyright: ignore[reportArgumentType, reportOperatorIssue]
        elif "min" in self and isinstance(self["min"], tuple):
            min_val = min(self["min"])  # pyright: ignore[reportArgumentType]
            self.sanity_check.min_raw = int(min_val * gain) if gain else int(min_val)  # pyright: ignore[reportOperatorIssue]

        if "max" in self and isinstance(self["max"], (int, float)):
            self.sanity_check.max_raw = int(self["max"] * gain) if gain else int(self["max"])  # pyright: ignore[reportArgumentType, reportOperatorIssue]
        elif "max" in self and isinstance(self["max"], tuple):
            max_val = max(self["max"])  # pyright: ignore[reportArgumentType]
            self.sanity_check.max_raw = int(max_val * gain) if gain else int(max_val)  # pyright: ignore[reportOperatorIssue]

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
        components = super().get_discovery_components()
        if "min" in self and isinstance(components[self.unique_id]["min"], (tuple, list)):
            components[self.unique_id]["min"] = min(cast(Iterable[float], self["min"]))
        if "max" in self and isinstance(components[self.unique_id]["max"], (tuple, list)):
            components[self.unique_id]["max"] = max(cast(Iterable[float], self["max"]))
        return components

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        state = await super().get_state(raw=raw, republish=republish, **kwargs)
        if isinstance(state, (float, int)):
            value = float(state) if not raw else cast(float, self._apply_gain_and_precision(state))
            if "min" in self and isinstance(self["min"], float) and value < cast(float, self["min"]):
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} value={state} < minimum={self['min']}")
                value = state
                state = cast(float, self["min"]) if not raw else cast(float, self["min"]) * self.gain
            elif "max" in self and isinstance(self["max"], float) and value > cast(float, self["max"]):
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} value={state} > maximum={self['max']}")
                value = state
                state = cast(float, self["max"]) if not raw else cast(float, self["max"]) * self.gain
            elif "min" in self and isinstance(self["min"], tuple) and value < 0 and not min(self["min"]) <= value <= max(self["min"]):  # pyright: ignore[reportOperatorIssue, reportArgumentType]
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} value={state} not in range {self['min']}")
                value = state
                state = min(self["min"]) if not raw else min(self["min"]) * self.gain  # pyright: ignore[reportOperatorIssue, reportArgumentType]
            elif "max" in self and isinstance(self["max"], tuple) and value > 0 and not min(self["max"]) <= value <= max(self["max"]):  # pyright: ignore[reportOperatorIssue, reportArgumentType]
                if self.debug_logging:
                    logging.debug(f"{self.__class__.__name__} value={state} > not in range {self['max']}")
                value = state
                state = max(self["max"]) if not raw else max(self["max"]) * self.gain  # pyright: ignore[reportOperatorIssue, reportArgumentType]
            if value != state and self.debug_logging:
                logging.debug(f"{self.__class__.__name__} {value=} adjusted to {state=}")
        return state

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if value is not None:
            try:
                state = float(value)
                if self.gain != 1:
                    state = state * self.gain  # Convert to raw value before validating and writing
            except Exception as e:
                logging.warning(f"{self.__class__.__name__} Attempt to set value to '{value}' FAILED: {repr(e)}")
                return False
            return await super().set_value(modbus_client, mqtt_client, state, source, handler)
        else:
            logging.warning(f"{self.__class__.__name__} Ignored attempt to set value to *None*")
        return False

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        try:
            value = cast(float, self._apply_gain_and_precision(float(raw_value)))  # Make NOT raw
            if isinstance(self["min"], float) and value < cast(float, self["min"]):
                logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Less than minimum of {self['min']}")
                return False
            elif isinstance(self["max"], float) and value > cast(float, self["max"]):
                logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Greater than maximum of {self['max']}")
                return False
            elif isinstance(self["min"], tuple) and value < 0 and not min(self["min"]) <= value <= max(self["min"]):  # pyright: ignore[reportOperatorIssue, reportArgumentType]
                logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Not in range {self['min']}")
                return False
            elif isinstance(self["max"], tuple) and value > 0 and not min(self["max"]) <= value <= max(self["max"]):  # pyright: ignore[reportOperatorIssue, reportArgumentType]
                logging.error(f"{self.name} invalid value '{value}' (raw={raw_value}): Not in range {self['max']}")
                return False
            return True
        except ValueError:
            logging.error(f"{self.name} invalid value '{raw_value}': Not a number")
            return False


class SelectSensor(ReadWriteSensor):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        scan_interval: int,
        options: list[str],
        protocol_version: Protocol,
    ):
        assert options is not None and isinstance(options, list) and len(options) > 0 and not any(o for o in options if not isinstance(o, str)), "options must be a non-empty list of strings"
        super().__init__(
            availability_control_sensor=availability_control_sensor,
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=scan_interval,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:list-status",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
        )
        assert all([isinstance(o, str) for o in options]), "options must be a non-empty list of strings"
        self["platform"] = "select"
        self["options"] = options
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(options) - 1

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)) and 0 <= value <= (len(cast(list[str], self["options"])) - 1):
            return cast(list[str], self["options"])[int(value)]
        else:
            return f"Unknown Mode: {value}"

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        try:
            index = int(value)
        except ValueError:
            index = cast(list[str], self["options"]).index(str(value))
        return await super().set_value(modbus_client, mqtt_client, index, source, handler)

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        try:
            index = cast(list[str], self["options"]).index(str(raw_value))
            option = cast(list[str], self["options"])[index]
            if len(option.strip()) == 0 or option is None:
                logging.error(f"{self.name} invalid value '{raw_value}': Empty option?")
                return False
            else:
                return True
        except ValueError:
            try:
                index = int(raw_value)
                if 0 <= index < len(cast(list[str], self["options"])):
                    option = cast(list[str], self["options"])[index]
                    if len(option.strip()) == 0 or option is None:
                        logging.error(f"{self.name} invalid value '{raw_value}': Empty option?")
                        return False
                    else:
                        return True
            except ValueError:
                pass
        logging.error(f"{self.name} invalid value '{raw_value}': Not a valid option or index")
        return False


class SwitchSensor(ReadWriteSensor):
    def __init__(
        self,
        availability_control_sensor: AvailabilityMixin | None,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        scan_interval: int,
        protocol_version: Protocol,
    ):
        super().__init__(
            availability_control_sensor=availability_control_sensor,
            name=name,
            object_id=object_id,
            input_type=InputType.HOLDING,
            plant_index=plant_index,
            device_address=device_address,
            address=address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=scan_interval,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:toggle-switch",
            gain=None,
            precision=0,
            protocol_version=protocol_version,
        )
        self["platform"] = "switch"
        self["payload_off"] = 0
        self["payload_on"] = 1
        self["state_off"] = 0
        self["state_on"] = 1
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = 1

    async def set_value(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        try:
            return await super().set_value(modbus_client, mqtt_client, int(value), source, handler)
        except ValueError as e:
            logging.error(f"{self.__class__.__name__} value_is_valid check of value '{value}' FAILED: {repr(e)}")
            raise

    async def value_is_valid(self, modbus_client: ModbusClientType | None, raw_value: float | int | str) -> bool:
        if raw_value not in (self["payload_off"], self["payload_on"]):
            logging.error(f"{self.__class__.__name__} Failed to write value '{raw_value}': Must be either '{self['payload_off']}' or '{self['payload_on']}'")
            return False
        return True


class AlarmSensor(ReadOnlySensor, metaclass=abc.ABCMeta):
    NO_ALARM: Final = "No Alarm"

    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
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
            data_type=ModbusDataType.UINT16,
            scan_interval=Config.modbus[plant_index].scan_interval.realtime if plant_index < len(Config.modbus) else 5,
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
        )
        self.alarm_type = alarm_type

    @abc.abstractmethod
    def decode_alarm_bit(self, bit_position: int) -> str | None:
        """Decodes the alarm bit.

        Args:
            bit_position:     The set bit in the alarm register value.

        Returns:
            The alarm description or None if not found.
        """
        pass

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None or value == 0 or (isinstance(value, list) and sum(cast(list[int], value)) == 0) or value == 65535:
            return _t("AlarmSensor.no_alarm", self.NO_ALARM)
        else:
            if isinstance(value, list) and len(value) == 2 and value[0] == 0 and value[1] != 0:
                logging.warning(f"{self.__class__.__name__} Converting '{value}' to {value[1]} for {self.alarm_type} alarm bit decoding")
                alarm = int(value[1])
            else:
                alarm = int(value)
            active_alarms = []
            try:
                for bit_position in range(16):
                    if alarm & (1 << bit_position):
                        description = self.decode_alarm_bit(bit_position)
                        if description:
                            active_alarms.append(_t(f"{self.__class__.__name__}.alarm.{bit_position}", description))
                        else:
                            active_alarms.append(_t("AlarmSensor.unknown_alarm", "Unknown (bit{bit}∈{value})").format(bit=bit_position, value=value))
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

    def state2raw(self, state):
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


class Alarm1Sensor(AlarmSensor):
    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
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
    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "PCS")

    def decode_alarm_bit(self, bit_position: int) -> str | None:
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
    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "ESS")
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
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
    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
    ):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "GW")
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
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
    def __init__(self, name: str, object_id: str, plant_index: int, device_address: int, address: int, protocol_version: Protocol):
        super().__init__(name, object_id, plant_index, device_address, address, protocol_version, "EVDC")
        self["enabled_by_default"] = True

    def decode_alarm_bit(self, bit_position: int) -> str | None:
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


class AlarmCombinedSensor(ReadableSensorMixin, Sensor, HybridInverter, PVInverter):
    def __init__(self, name: str, unique_id: str, object_id: str, *alarms: AlarmSensor):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            scan_interval=min([a.scan_interval for a in alarms]),
            unit=None,
            device_class=None,
            state_class=None,
            icon="mdi:flash-triangle",
            gain=None,
            precision=None,
            protocol_version=Protocol.N_A,
        )
        device_addresses = set([a.device_address for a in alarms])
        first_address = min([a.address for a in alarms])
        last_address = max([a.address + a.count - 1 for a in alarms])
        count = sum([a.count for a in alarms])
        assert len(device_addresses) == 1, f"{self.__class__.__name__} Combined alarms must have the same device address ({device_addresses})"
        assert (last_address - first_address + 1) == count, f"{self.__class__.__name__} Combined alarms must have contiguous address ranges ({[a.address for a in alarms]})"
        self["enabled_by_default"] = True
        self.alarms = list(alarms)
        self.address = min([a.address for a in alarms])
        self.device_address = device_addresses.pop()
        self.count = count
        self.input_type = InputType.INPUT
        self.data_type = ModbusDataType.UINT16

    @property
    def protocol_version(self) -> Protocol:
        protocol = super().protocol_version
        for alarm in self.alarms:
            if alarm.protocol_version > protocol:
                protocol = alarm.protocol_version
        return protocol

    @protocol_version.setter
    def protocol_version(self, protocol_version: Protocol | float):
        raise NotImplementedError("protocol_version is read-only")

    async def _update_internal_state(self, **kwargs) -> bool | Exception | ExceptionResponse:
        return True

    def configure_mqtt_topics(self, device_id: str) -> str:
        base = super().configure_mqtt_topics(device_id)
        for alarm in self.alarms:
            alarm.configure_mqtt_topics(device_id)
        return base

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        if republish and len(self._states) > 0:
            return self._apply_gain_and_precision(self._states[-1][1], raw) if isinstance(self._states[-1][1], (float, int)) else self._states[-1][1]
        else:
            no_alarm = _t("AlarmSensor.no_alarm", AlarmSensor.NO_ALARM)
            result: str = no_alarm
            for alarm in [a for a in self.alarms if a.publishable]:
                state = cast(str, await alarm.get_state(raw=False, republish=False, max_length=sys.maxsize, **kwargs))
                if state != no_alarm:
                    if result == no_alarm:
                        result = state
                    else:
                        result = ", ".join([result, state])
                        if len(result) > 255 and Config.home_assistant.enabled:
                            result = re.sub(r"\s+", " ", re.sub(r"[0-9:_]", "", result)).strip()
                            if len(result) > 255:
                                result = result[:252] + "..."
            self.set_state(result)
            return result

    def state2raw(self, state):
        if state == AlarmSensor.NO_ALARM:
            return 0
        return super().state2raw(state)


class RunningStateSensor(ReadOnlySensor):
    def __init__(
        self,
        name: str,
        object_id: str,
        plant_index: int,
        device_address: int,
        address: int,
        protocol_version: Protocol,
    ):
        super().__init__(
            name,
            object_id,
            InputType.INPUT,
            plant_index,
            device_address,
            address,
            count=1,
            data_type=ModbusDataType.UINT16,
            scan_interval=Config.modbus[plant_index].scan_interval.high if plant_index < len(Config.modbus) else 10,
            unit=None,
            device_class=DeviceClass.ENUM,
            state_class=None,
            icon="mdi:power-settings",
            gain=None,
            precision=None,
            protocol_version=protocol_version,
        )
        self["enabled_by_default"] = True
        self["options"] = [
            "Standby",  # 0
            "Normal",  # 1
            "Fault",  # 2
            "Power-Off",  # 3
            "",  # 4
            "",  # 5
            "",  # 6
            "Environmental Abnormality",  # 7
        ]
        self.sanity_check.min_raw = 0
        self.sanity_check.max_raw = len(cast(list[str], self["options"])) - 1  # pyrefly: ignore

    async def get_state(self, raw: bool = False, republish: bool = False, **kwargs) -> float | int | str | None:
        value = await super().get_state(raw=raw, republish=republish, **kwargs)
        if raw:
            return value
        elif value is None:
            return None
        elif isinstance(value, (float, int)) and 0 <= value <= (len(cast(list[str], self["options"])) - 1):
            return cast(list[str], self["options"])[int(value)]
        else:
            return f"Unknown State code: {value}"


class ResettableAccumulationSensor(ObservableMixin, DerivedSensor):
    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        data_type: ModbusDataType,
        unit: str | None,
        device_class: DeviceClass | None,
        state_class: StateClass | None,
        icon: str | None,
        gain: float | None,
        precision: int | None,
    ):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            data_type=data_type,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
        )
        self._source = source
        self._reset_topic = f"sigenergy2mqtt/{self['object_id']}/reset"
        self._current_total_lock = asyncio.Lock()
        self._current_total: float = 0.0
        uid = str(self.unique_id)
        if uid.startswith("<MagicMock"):
            uid = "mock_uid"
        self._persistent_state_file = Path(Config.persistent_state_path, f"{uid}.state")
        if self._persistent_state_file.is_file():
            with self._persistent_state_file.open("r") as f:
                try:
                    content = f.read()
                    if content is not None and content != "None":
                        self._current_total = float(content)
                        logging.debug(f"{self.__class__.__name__} Loaded current state from {self._persistent_state_file} ({self._current_total})")
                except ValueError as error:
                    logging.warning(f"{self.__class__.__name__} Failed to read {self._persistent_state_file}: {error}")
        self.set_latest_state(self._current_total)

    def get_discovery_components(self) -> dict[str, dict[str, Any]]:
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
            "step": 10 ** -(self.precision if self.precision else 0),
            "enabled_by_default": self.publishable,
        }
        components: dict[str, dict[str, Any]] = super().get_discovery_components()
        components[updater["unique_id"]] = updater
        return components

    def observable_topics(self) -> set[str]:
        topics = super().observable_topics()
        topics.add(self._reset_topic)
        return topics

    def get_attributes(self) -> dict[str, float | int | str]:
        attributes = super().get_attributes()
        attributes["reset_topic"] = self._reset_topic
        if self.unit:
            attributes["reset_unit"] = self.unit
        return attributes

    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self.observable_topics():
            new_total = (value if value is float else float(value)) * self.gain
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({new_total=})")
            if new_total != self._current_total:
                await self._persist_current_total(new_total)
            self._current_total = new_total
            self.set_latest_state(self._current_total)
            self.force_publish = True
            return True
        else:
            return False

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False
        elif len(values) < 2:
            return False  # Need at least two points to calculate

        # Calculate time difference in hours
        interval_hours = sensor.latest_interval / 3600 if sensor.latest_interval else 0
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
            if new_total != self._current_total:
                try:
                    asyncio.get_running_loop().create_task(self._persist_current_total(new_total))
                except RuntimeError:
                    asyncio.run_coroutine_threadsafe(self._persist_current_total(new_total), asyncio.get_event_loop())
            self._current_total = new_total
            self.set_latest_state(self._current_total)
            return True

    async def _persist_current_total(self, new_total: float) -> None:
        async with self._current_total_lock:
            with self._persistent_state_file.open("w") as f:
                f.write(str(new_total))


class EnergyLifetimeAccumulationSensor(ResettableAccumulationSensor):
    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: Sensor,
        data_type=None,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=DeviceClass.ENERGY,
        state_class=StateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt",
        gain=1000,
        precision=2,
    ):
        if data_type is None:
            data_type = ModbusDataType.UINT32
        super().__init__(
            name,
            unique_id,
            object_id,
            source,
            data_type=data_type,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            icon=icon,
            gain=gain,
            precision=precision,
        )


class EnergyDailyAccumulationSensor(ResettableAccumulationSensor):
    futures: set[Future] = set()

    def __init__(
        self,
        name: str,
        unique_id: str,
        object_id: str,
        source: ReadOnlySensor | DerivedSensor,
    ):
        super().__init__(
            name=name,
            unique_id=unique_id,
            object_id=object_id,
            source=source,
            data_type=source.data_type,
            unit=source.unit,
            device_class=source.device_class,
            state_class=source.state_class,
            icon=cast(str, source["icon"]),
            gain=source.gain,
            precision=source.precision,
        )
        self._state_at_midnight_lock = asyncio.Lock()
        self._state_at_midnight: float | None = None
        uid = str(source.unique_id)
        if uid.startswith("<MagicMock"):
            uid = "mock_uid_atmidnight"
        self._persistent_state_file = Path(Config.persistent_state_path, f"{uid}.atmidnight")
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

    async def notify(self, modbus_client: ModbusClientType | None, mqtt_client: mqtt.Client, value: float | int | str, source: str, handler: MqttHandler) -> bool:
        if source in self.observable_topics():
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} notified of updated state {value} {self.unit}")
            self._state_now = (value if value is float else float(value)) * self.gain
            updated_midnight_state = self._source.latest_raw_state - self._state_now if isinstance(self._source.latest_raw_state, (float, int)) and self._source.latest_raw_state else self._state_now
            if self.debug_logging:
                logging.debug(f"{self.__class__.__name__} {self._source.latest_raw_state=} (from {self._source.unique_id}) {self._state_now=} {updated_midnight_state=}")
            await self._update_state_at_midnight(updated_midnight_state)
            self.set_latest_state(self._state_now)
            logging.info(f"{self.__class__.__name__} reset to {value} {self.unit} ({self._state_now=})")
            self.force_publish = True
            return True
        else:
            return False

    async def publish(self, mqtt_client: mqtt.Client, modbus_client: ModbusClientType | None, republish: bool = False) -> bool:
        if not self._persistent_state_file.is_file():
            await self._update_state_at_midnight(self._state_at_midnight)
        return await super().publish(mqtt_client, modbus_client, republish)

    def set_source_values(self, sensor: Sensor, values: list) -> bool:
        if sensor is not self._source:
            logging.warning(f"Attempt to call {self.__class__.__name__}.set_source_values from {sensor.__class__.__name__}")
            return False

        now_state = values[-1][1]

        if len(values) > 1:
            was = time.localtime(values[-2][0])
            now = time.localtime(values[-1][0])
            if was.tm_year != now.tm_year or was.tm_mon != now.tm_mon or was.tm_mday != now.tm_mday:
                try:
                    asyncio.get_running_loop().create_task(self._update_state_at_midnight(now_state))
                except RuntimeError:
                    asyncio.run_coroutine_threadsafe(self._update_state_at_midnight(now_state), asyncio.get_event_loop())
                self._states.clear()
                self._state_at_midnight = now_state

        if not self._state_at_midnight:
            self._state_at_midnight = now_state

        self._state_now = now_state - self._state_at_midnight
        self.set_latest_state(self._state_now)
        return True

    async def _update_state_at_midnight(self, midnight_state: float | None) -> None:
        if midnight_state is not None:
            async with self._state_at_midnight_lock:
                with self._persistent_state_file.open("w") as f:
                    f.write(str(midnight_state))
                self._state_at_midnight = midnight_state


class PVPowerSensor:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
