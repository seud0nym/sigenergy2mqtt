import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import ConsumptionMethod

from . import const, version
from .auto_discovery import scan as auto_discovery_scan
from .home_assistant_config import HomeAssistantConfiguration
from .influxdb_config import InfluxDBConfiguration
from .modbus_config import ModbusConfiguration
from .mqtt_config import MqttConfiguration
from .pvoutput_config import ConsumptionSource, PVOutputConfiguration, VoltageSource
from .validation import check_bool, check_float, check_host, check_int, check_int_list, check_log_level, check_port, check_string, check_string_list


class DualMethod:
    """Descriptor that identifies if a method is called on a class or an instance.

    If called on the class, it delegates to the 'active_config' singleton.
    If called on an instance, it uses that instance.
    """

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__
        self.name = func.__name__

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Check if the attribute has been patched on the instance specifically
        if self.name in instance.__dict__:
            return instance.__dict__[self.name]

        return self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        # Check if the attribute has been patched on active_config specifically
        if self.name in active_config.__dict__:
            return active_config.__dict__[self.name](*args, **kwargs)

        return self.func(active_config, *args, **kwargs)


class ConfigMeta(type):
    """Metaclass to support backward compatibility for class-level access."""

    def __getattr__(cls, name):
        return getattr(active_config, name)

    def __setattr__(cls, name, value):
        if name == "_initializing_singleton" or name.startswith("__"):
            type.__setattr__(cls, name, value)
            return

        if hasattr(value, "__get__"):
            type.__setattr__(cls, name, value)
            return

        try:
            setattr(active_config, name, value)
        except (AttributeError, NameError):
            type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        try:
            delattr(active_config, name)
        except (AttributeError, NameError):
            pass

        try:
            type.__delattr__(cls, name)
        except AttributeError:
            pass


class Config(metaclass=ConfigMeta):
    _initializing_singleton = True
    # Remove class-level attributes to let ConfigMeta.__getattr__ handle them
    # but keep type hints for IDEs
    origin: dict[str, str]

    clean: bool
    consumption: ConsumptionMethod
    ems_mode_check: bool
    log_level: int
    metrics_enabled: bool

    language: str

    sanity_check_default_kw: float
    sanity_check_failures_increment: bool

    modbus: list[ModbusConfiguration]
    home_assistant: HomeAssistantConfiguration
    influxdb: InfluxDBConfiguration
    mqtt: MqttConfiguration
    pvoutput: PVOutputConfiguration

    sensor_debug_logging: bool
    sensor_overrides: dict[str, dict[str, bool | int | float | str | list[int] | Any | None]]

    persistent_state_path: Path

    _source: str | None

    def __init__(self):
        self._apply_defaults()

    @DualMethod
    def reset(self):
        self._apply_defaults()

    def _apply_defaults(self):
        self.origin = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}

        self.clean = False
        self.consumption = ConsumptionMethod.TOTAL
        self.ems_mode_check = True
        self.log_level = logging.WARNING
        self.metrics_enabled = True

        self.language = i18n.get_default_language()

        self.sanity_check_default_kw = 500.0
        self.sanity_check_failures_increment = False

        self.modbus = []
        self.home_assistant = HomeAssistantConfiguration()
        self.influxdb = InfluxDBConfiguration()
        self.mqtt = MqttConfiguration()
        self.pvoutput = PVOutputConfiguration()

        self.sensor_debug_logging = False
        self.sensor_overrides = {}
        self._source = None

        self.persistent_state_path = Path(".")

    @DualMethod
    def validate(self) -> None:
        if len(self.modbus) == 0:
            raise ValueError("At least one Modbus device must be configured")

        for device in self.modbus:
            device.validate()

            if not self.ems_mode_check:
                if device.registers.no_remote_ems:
                    raise ValueError("When ems_mode_check is disabled, no_remote_ems must be False")
                if not device.registers.read_write:
                    raise ValueError("When ems_mode_check is disabled, read_write must be True")

        self.mqtt.validate()
        self.home_assistant.validate()
        self.pvoutput.validate()

    @DualMethod
    def get_modbus_log_level(self) -> int:
        if not self.modbus:
            return logging.WARNING
        return min([device.log_level for device in self.modbus])

    @DualMethod
    def set_modbus_log_level(self, level: int) -> None:
        for device in self.modbus:
            device.log_level = level

    @DualMethod
    def load(self, filename: str) -> None:
        logging.info(f"Loading configuration from {filename}...")
        self._source = filename
        self.reload()

    @DualMethod
    def reload(self) -> None:
        overrides: dict[str, Any] = {
            "home-assistant": {},
            "mqtt": {},
            "modbus": [{"smart-port": {"mqtt": [{}], "module": {}}}],
            "influxdb": {},
            "pvoutput": {},
            "sensor-overrides": {},
        }

        if self._source:
            _yaml = YAML(typ="safe", pure=True)
            with open(self._source, "r") as f:
                data = _yaml.load(f)
            if data:
                self._configure(data)
            else:
                logging.warning(f"Ignored configuration file {self._source} because it contains no keys?")

        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(self.persistent_state_path, "auto-discovery.yaml")
        auto_discovered = None
        if auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file()):
            port = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, "502"))
            ping_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, "0.5"))
            modbus_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, "0.25"))
            modbus_retries = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, "0"))
            logging.info(f"Auto-discovery required, scanning for Sigenergy devices ({port=} {ping_timeout=} {modbus_timeout=} {modbus_retries=})...")
            auto_discovered = auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries)
            if len(auto_discovered) > 0:
                with open(auto_discovery_cache, "w") as f:
                    _yaml = YAML(typ="safe", pure=True)
                    _yaml.dump(auto_discovered, f)
        elif auto_discovery == "once" and auto_discovery_cache.is_file():
            logging.info("Auto-discovery already completed, using cached results.")
            with open(auto_discovery_cache, "r") as f:
                auto_discovered = YAML(typ="safe", pure=True).load(f)

        self._load_from_env(overrides, auto_discovered)
        self._configure(overrides, True)

        i18n.load(self.language)

        if auto_discovered:
            self._apply_auto_discovery(auto_discovered)

    def _load_from_env(self, overrides: dict[str, Any], auto_discovered: Any = None):
        for key, value in os.environ.items():
            if key.startswith("SIGENERGY2MQTT_") and key != "SIGENERGY2MQTT_CONFIG" and value is not None and value != "None":
                logging.debug(f"Found env/cli override: {key} = {'[REDACTED]' if 'PASSWORD' in key or 'API_KEY' in key else value}")
                try:
                    self._process_env_key(key, value, overrides, auto_discovered)
                except Exception as e:
                    raise Exception(f"{repr(e)} when processing override '{key}'")

    def _process_env_key(self, key: str, value: str, overrides: dict[str, Any], auto_discovered: Any):
        match key:
            case const.SIGENERGY2MQTT_CONSUMPTION:
                overrides["consumption"] = ConsumptionMethod(
                    cast(
                        str,
                        check_string(
                            value,
                            key,
                            ConsumptionMethod.CALCULATED.value,
                            ConsumptionMethod.TOTAL.value,
                            ConsumptionMethod.GENERAL.value,
                            allow_empty=False,
                            allow_none=False,
                        ),
                    ),
                )
            case const.SIGENERGY2MQTT_DEBUG_SENSOR:
                overrides["sensor-overrides"][check_string(value, key, allow_empty=False, allow_none=False)] = {"debug-logging": True}
                overrides["log-level"] = logging.DEBUG
            case const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX:
                overrides["home-assistant"]["device-name-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX:
                overrides["home-assistant"]["discovery-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX:
                overrides["home-assistant"]["edit-pct-box"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_HASS_ENABLED:
                overrides["home-assistant"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX:
                overrides["home-assistant"]["entity-id-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX:
                overrides["home-assistant"]["unique-id-prefix"] = check_string(value, key)
            case const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS:
                overrides["home-assistant"]["use-simplified-topics"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_BUCKET:
                overrides["influxdb"]["bucket"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_DATABASE:
                overrides["influxdb"]["database"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_INFLUX_DEFAULT_MEASUREMENT:
                overrides["influxdb"]["default-measurement"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_INFLUX_LOAD_HASS_HISTORY:
                overrides["influxdb"]["load-hass-history"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_ENABLED:
                overrides["influxdb"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_INFLUX_EXCLUDE:
                overrides["influxdb"]["exclude"] = check_string_list(value, key)
            case const.SIGENERGY2MQTT_INFLUX_HOST:
                overrides["influxdb"]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_INFLUX_INCLUDE:
                overrides["influxdb"]["include"] = check_string_list(value, key)
            case const.SIGENERGY2MQTT_INFLUX_LOG_LEVEL:
                overrides["influxdb"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_INFLUX_ORG:
                overrides["influxdb"]["org"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_PASSWORD:
                overrides["influxdb"]["password"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_PORT:
                overrides["influxdb"]["port"] = check_int(value, key, min=1, max=65535)
            case const.SIGENERGY2MQTT_INFLUX_TOKEN:
                overrides["influxdb"]["token"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_INFLUX_USERNAME:
                overrides["influxdb"]["username"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_LANGUAGE:
                try:
                    overrides["language"] = check_string(value, key, *i18n.get_available_translations(), allow_empty=False, allow_none=False)
                except ValueError:
                    default = i18n.get_default_language()
                    logging.warning(f"Invalid language '{value}' for {key}, falling back to '{default}'")
                    overrides["language"] = default
            case const.SIGENERGY2MQTT_LOG_LEVEL:
                overrides["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID:
                overrides["modbus"][0]["ac-chargers"] = check_int_list(value, key)
            case (
                const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT
                | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES
            ):
                pass  # Handled above
            case const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID:
                overrides["modbus"][0]["dc-chargers"] = check_int_list(value, key)
            case const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING:
                overrides["modbus"][0]["disable-chunking"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MODBUS_HOST:
                overrides["modbus"][0]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID:
                overrides["modbus"][0]["inverters"] = check_int_list(value, key)
            case const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL:
                overrides["modbus"][0]["log-level"] = check_log_level(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["log-level"] = overrides["modbus"][0]["log-level"]
            case const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS:
                overrides["modbus"][0]["no-remote-ems"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["no-remote-ems"] = overrides["modbus"][0]["no-remote-ems"]
            case const.SIGENERGY2MQTT_MODBUS_PORT:
                overrides["modbus"][0]["port"] = check_port(value, key)
            case const.SIGENERGY2MQTT_MODBUS_READ_ONLY:
                overrides["modbus"][0]["read-only"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["read-only"] = overrides["modbus"][0]["read-only"]
            case const.SIGENERGY2MQTT_MODBUS_READ_WRITE:
                overrides["modbus"][0]["read-write"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["read-write"] = overrides["modbus"][0]["read-write"]
            case const.SIGENERGY2MQTT_MODBUS_RETRIES:
                overrides["modbus"][0]["retries"] = check_int(value, key, min=0)
            case const.SIGENERGY2MQTT_MODBUS_TIMEOUT:
                overrides["modbus"][0]["timeout"] = check_float(value, key, min=0.25)
            case const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY:
                overrides["modbus"][0]["write-only"] = check_bool(value, key)
                if auto_discovered:
                    for device in auto_discovered:
                        device["write-only"] = overrides["modbus"][0]["write-only"]
            case const.SIGENERGY2MQTT_MQTT_ANONYMOUS:
                overrides["mqtt"]["anonymous"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_BROKER:
                overrides["mqtt"]["broker"] = check_host(value, key)
            case const.SIGENERGY2MQTT_MQTT_KEEPALIVE:
                overrides["mqtt"]["keepalive"] = check_int(value, key, min=1)
            case const.SIGENERGY2MQTT_MQTT_LOG_LEVEL:
                overrides["mqtt"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_MQTT_PASSWORD:
                overrides["mqtt"]["password"] = value
            case const.SIGENERGY2MQTT_MQTT_PORT:
                overrides["mqtt"]["port"] = check_port(value, key)
            case const.SIGENERGY2MQTT_MQTT_TLS:
                overrides["mqtt"]["tls"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_TLS_INSECURE:
                overrides["mqtt"]["tls-insecure"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_MQTT_TRANSPORT:
                overrides["mqtt"]["transport"] = check_string(value, key, "tcp", "websockets", allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_MQTT_USERNAME:
                overrides["mqtt"]["username"] = value
            case const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK:
                overrides["no-ems-mode-check"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_NO_METRICS:
                overrides["no-metrics"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_API_KEY:
                overrides["pvoutput"]["api-key"] = check_string(value, key, allow_none=False, allow_empty=False, hex_chars_only=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING:
                overrides["pvoutput"]["calc-debug-logging"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION:
                overrides["pvoutput"]["consumption"] = check_string(
                    value,
                    key,
                    "false",
                    "true",
                    ConsumptionSource.CONSUMPTION.value,
                    ConsumptionSource.IMPORTED.value,
                    ConsumptionSource.NET_OF_BATTERY.value,
                    allow_empty=False,
                    allow_none=False,
                )
            case const.SIGENERGY2MQTT_PVOUTPUT_ENABLED:
                overrides["pvoutput"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS:
                overrides["pvoutput"]["exports"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10:
                overrides["pvoutput"]["v10"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11:
                overrides["pvoutput"]["v11"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12:
                overrides["pvoutput"]["v12"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7:
                overrides["pvoutput"]["v7"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8:
                overrides["pvoutput"]["v8"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9:
                overrides["pvoutput"]["v9"] = check_string(value, key, allow_none=True, allow_empty=True)
            case const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS:
                overrides["pvoutput"]["imports"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL:
                overrides["pvoutput"]["log-level"] = check_log_level(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR:
                overrides["pvoutput"]["output-hour"] = check_int(value, key, min=-1, max=23)
            case const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON:
                overrides["pvoutput"]["time-periods"] = json.loads(value)
            case const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID:
                overrides["pvoutput"]["system-id"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC:
                overrides["pvoutput"]["temperature-topic"] = check_string(value, key, allow_none=False, allow_empty=False)
            case const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING:
                overrides["pvoutput"]["update-debug-logging"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE:
                overrides["pvoutput"]["voltage"] = check_string(value, key, *[v.value for v in VoltageSource])
            case const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW:
                overrides["sanity-check-default-kw"] = check_float(value, key, allow_none=False, min=0)
            case const.SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT:
                overrides["sanity-check-failures-increment"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH:
                overrides["modbus"][0]["scan-interval-high"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-high"]:
                            device["scan-interval-high"] = overrides["modbus"][0]["scan-interval-high"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW:
                overrides["modbus"][0]["scan-interval-low"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-low"]:
                            device["scan-interval-low"] = overrides["modbus"][0]["scan-interval-low"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM:
                overrides["modbus"][0]["scan-interval-medium"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-medium"]:
                            device["scan-interval-medium"] = overrides["modbus"][0]["scan-interval-medium"]
            case const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME:
                overrides["modbus"][0]["scan-interval-realtime"] = check_int(value, key, min=1)
                if auto_discovered:
                    for device in auto_discovered:
                        if overrides["modbus"][0]["scan-interval-realtime"]:
                            device["scan-interval-realtime"] = overrides["modbus"][0]["scan-interval-realtime"]
            case const.SIGENERGY2MQTT_SMARTPORT_ENABLED:
                overrides["modbus"][0]["smart-port"]["enabled"] = check_bool(value, key)
            case const.SIGENERGY2MQTT_SMARTPORT_HOST:
                overrides["modbus"][0]["smart-port"]["module"]["host"] = check_host(value, key)
            case const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME:
                overrides["modbus"][0]["smart-port"]["module"]["name"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN:
                overrides["modbus"][0]["smart-port"]["mqtt"][0]["gain"] = check_int(value, key, allow_none=True, min=1)
            case const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC:
                overrides["modbus"][0]["smart-port"]["mqtt"][0]["topic"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_PASSWORD:
                overrides["modbus"][0]["smart-port"]["module"]["password"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_PV_POWER:
                overrides["modbus"][0]["smart-port"]["module"]["pv-power"] = value
            case const.SIGENERGY2MQTT_SMARTPORT_USERNAME:
                overrides["modbus"][0]["smart-port"]["module"]["username"] = value
            case _:
                logging.warning(f"UNKNOWN env/cli override: {key} = {'******' if 'PASSWORD' in key or 'API_KEY' in key else value}")

    def _apply_auto_discovery(self, auto_discovered: Any):
        if isinstance(auto_discovered, list):
            for device in auto_discovered:
                updated = False
                for defined in self.modbus:
                    if (defined.host == device.get("host") or defined.host == "") and defined.port == device.get("port"):
                        if defined.host == "":
                            defined.host = cast(str, device.get("host"))
                            defined.port = cast(int, device.get("port"))
                            logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                        else:
                            logging.info(f"Auto-discovered found configured Modbus device: {device.get('host')}:{device.get('port')}, updating with discovered device IDs")
                        defined.configure(device, override=True, auto_discovered=True)
                        updated = True
                        break
                if not updated:
                    logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                    new_device = ModbusConfiguration()
                    new_device.configure(device, override=True, auto_discovered=True)
                    self.modbus.append(new_device)

    @DualMethod
    def version(self) -> str:
        return version.__version__

    @DualMethod
    def _configure(self, data: dict, override: bool = False) -> None:
        for name in data.keys() if data else {}:
            match name:
                case "consumption":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: consumption = {data[name]}")
                    self.consumption = ConsumptionMethod(
                        cast(
                            str,
                            check_string(
                                data[name],
                                name,
                                ConsumptionMethod.CALCULATED.value,
                                ConsumptionMethod.TOTAL.value,
                                ConsumptionMethod.GENERAL.value,
                                allow_empty=False,
                                allow_none=False,
                            ),
                        )
                    )
                case "language":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: language = {data[name]}")
                    try:
                        self.language = cast(str, check_string(data[name], name, *i18n.get_available_translations(), allow_empty=False, allow_none=False))
                    except ValueError:
                        default = i18n.get_default_language()
                        logging.warning(f"Invalid language '{data[name]}' for {name}, falling back to '{default}'")
                        self.language = default
                case "home-assistant":
                    self.home_assistant.configure(data[name], override)
                case "log-level":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: log-level = {data[name]}")
                    self.log_level = check_log_level(data[name], name)
                case "mqtt":
                    self.mqtt.configure(data[name], override)
                case "modbus":
                    if isinstance(data[name], list):
                        index = 0
                        for config in data[name]:
                            if isinstance(config, dict):
                                if len(self.modbus) <= index:
                                    device = ModbusConfiguration()
                                    self.modbus.append(device)
                                else:
                                    device = self.modbus[index]
                                device.configure(config, override)
                            index += 1
                    else:
                        raise ValueError("modbus configuration element must contain a list of Sigenergy hosts")
                case "no-ems-mode-check":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: no-ems-mode-check = {data[name]}")
                    self.ems_mode_check = not check_bool(data[name], name)
                case "no-metrics":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: no-metrics = {data[name]}")
                    self.metrics_enabled = not check_bool(data[name], name)
                case "pvoutput":
                    self.pvoutput.configure(data[name], override)
                case "influxdb":
                    self.influxdb.configure(data[name], override)
                case "sanity-check-default-kw":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sanity-check-default-kw = {data[name]}")
                    self.sanity_check_default_kw = cast(float, check_float(data[name], name, allow_none=False, min=0))
                case "sanity-check-failures-increment":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sanity-check-failures-increment = {data[name]}")
                    self.sanity_check_failures_increment = check_bool(data[name], name)
                case "sensor-debug-logging":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sensor-debug-logging = {data[name]}")
                    self.sensor_debug_logging = check_bool(data[name], name)
                case "sensor-overrides":
                    if isinstance(data[name], dict):
                        for sensor, settings in data[name].items():
                            self.sensor_overrides[sensor] = {}
                            for p, v in settings.items():
                                logging.debug(f"Applying configuration sensor-overrides: {sensor}.{p} = {v}")
                                match p:
                                    case "debug-logging":
                                        self.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "gain":
                                        self.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=True, min=1)
                                    case "icon":
                                        self.sensor_overrides[sensor][p] = check_string(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, starts_with="mdi:")
                                    case "max-failures":
                                        self.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=True, min=1)
                                    case "max-failures-retry-interval":
                                        self.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0)
                                    case "precision":
                                        self.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0, max=6)
                                    case "publishable":
                                        self.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "publish-raw":
                                        self.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "scan-interval":
                                        self.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=1)
                                    case "sanity-check-max-value":
                                        self.sensor_overrides[sensor][p] = check_float(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case "sanity-check-min-value":
                                        self.sensor_overrides[sensor][p] = check_float(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case "sanity-check-delta":
                                        self.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "unit-of-measurement":
                                        self.sensor_overrides[sensor][p] = check_string(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case _:
                                        raise ValueError(f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} - property is not known or not overridable")
                    elif data[name] is not None:
                        raise ValueError("sensor-overrides configuration elements must contain a list of class names, each followed by options and their values")
                case _:
                    raise ValueError(f"Configuration contains unknown element '{name}'")

    @classmethod
    def apply_cli_to_env(cls, variable: str, value: str) -> None:
        was = os.getenv(variable)
        if value is not None:
            if str(value) != was:
                os.environ[variable] = str(value)
                if was is not None:
                    logging.debug(f"Environment variable '{variable}' overridden from command line: set to '{'[REDACTED]' if 'PASSWORD' in variable or 'API_KEY' in variable else value}' (was '{was}')")
        else:
            if was is not None:
                os.environ[variable] = ""
                logging.debug(f"Environment variable '{variable}' overridden from command line: cleared (was '{was}')")
            else:
                logging.debug(f"Environment variable '{variable}' not set")

    @classmethod
    def system_initialize(cls):
        """Perform system-level initialization (logging, folders)."""
        # Logging setup
        if os.isatty(sys.stdout.fileno()):
            logging.basicConfig(format="{asctime} {levelname:<8} sigenergy2mqtt:{module:.<15.15}{lineno:04d} {message}", level=logging.INFO, style="{")
        else:
            cgroup = Path("/proc/self/cgroup")
            if Path("/.dockerenv").is_file() or (cgroup.is_file() and "docker" in cgroup.read_text()):
                logging.basicConfig(format="{asctime} {levelname:<8} {module:.<15.15}{lineno:04d} {message}", level=logging.INFO, style="{")
            else:
                logging.basicConfig(format="{levelname:<8} {module:.<15.15}{lineno:04d} {message}", level=logging.INFO, style="{")

        logger = logging.getLogger("root")
        logger.info(f"Release {version.__version__} (Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")

        # Version check
        min_version = (3, 12)
        if sys.version_info < min_version:
            logging.critical(f"Python {min_version[0]}.{min_version[1]} or higher is required!")
            sys.exit(1)

        # Persistent state path
        found_path = None
        for storage_base_path in ["/data/", "/var/lib/", str(Path.home()), "/tmp/"]:
            if os.path.isdir(storage_base_path) and os.access(storage_base_path, os.W_OK):
                path = Path(storage_base_path, "sigenergy2mqtt")
                if not path.is_dir():
                    logging.info(f"Persistent state folder '{path}' created")
                    path.mkdir()
                else:
                    logging.debug(f"Persistent state folder '{path}' already exists")
                found_path = path.resolve()
                break

        if not found_path:
            logging.critical("Unable to create persistent state folder!")
            sys.exit(1)

        # Stale file cleanup
        threshold_time = time.time() - (7 * 86400)
        for file in found_path.iterdir():
            if (
                file.is_file()
                and file.stat().st_mtime < threshold_time
                and not file.name == ".current-version"
                and not file.name.endswith(".yaml")
                and not file.name.endswith(".publishable")
                and not file.name.endswith(".token")
            ):
                logging.info(f"Removing stale state file: {file} (last modified: {time.ctime(file.stat().st_mtime)})")
                file.unlink()

        return found_path


# Global instance for compatibility
active_config = Config()
Config.persistent_state_path = Path(".")  # Initial default
