import json
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from ruamel.yaml import YAML

from sigenergy2mqtt import i18n
from sigenergy2mqtt.common import ConsumptionMethod

from . import const, version
from .auto_discovery import scan as auto_discovery_scan
from .home_assistant_config import HomeAssistantConfiguration
from .modbus_config import ModbusConfiguration
from .mqtt_config import MqttConfiguration
from .pvoutput_config import ConsumptionSource, PVOutputConfiguration, VoltageSource
from .validation import check_bool, check_float, check_host, check_int, check_int_list, check_log_level, check_port, check_string


class Config:
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
    mqtt: MqttConfiguration
    pvoutput: PVOutputConfiguration

    sensor_debug_logging: bool
    sensor_overrides: dict[str, dict[str, bool | int | float | str | list[int] | ModuleType | None]]

    persistent_state_path: Path

    _source: str | None

    @classmethod
    def _apply_defaults(cls):
        cls.origin = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}

        cls.clean = False
        cls.consumption = ConsumptionMethod.TOTAL
        cls.ems_mode_check = True
        cls.log_level = logging.WARNING
        cls.metrics_enabled = True

        cls.language = i18n.get_default_language()

        cls.sanity_check_default_kw = 500.0
        cls.sanity_check_failures_increment = False

        cls.modbus = []
        cls.home_assistant = HomeAssistantConfiguration()
        cls.mqtt = MqttConfiguration()
        cls.pvoutput = PVOutputConfiguration()

        cls.sensor_debug_logging = False
        cls.sensor_overrides = {}

        cls.persistent_state_path = Path(".")

        cls._source = None

    @classmethod
    def reset(cls):
        cls._apply_defaults()

    @classmethod
    def validate(cls) -> None:
        if len(cls.modbus) == 0:
            raise ValueError("At least one Modbus device must be configured")

        for device in cls.modbus:
            device.validate()

            if not cls.ems_mode_check:
                if device.registers.no_remote_ems:
                    raise ValueError("When ems_mode_check is disabled, no_remote_ems must be False")
                if not device.registers.read_write:
                    raise ValueError("When ems_mode_check is disabled, read_write must be True")

        cls.mqtt.validate()
        cls.home_assistant.validate()
        cls.pvoutput.validate()

    @classmethod
    def get_modbus_log_level(cls) -> int:
        return min([device.log_level for device in cls.modbus])

    @classmethod
    def set_modbus_log_level(cls, level: int) -> None:
        for device in cls.modbus:
            device.log_level = level

    @classmethod
    def load(cls, filename: str) -> None:
        logging.info(f"Loading configuration from {filename}...")
        cls._source = filename
        cls.reload()

    @classmethod
    def reload(cls) -> None:
        overrides: dict[str, Any] = {
            "home-assistant": {},
            "mqtt": {},
            "modbus": [{"smart-port": {"mqtt": [{}], "module": {}}}],
            "pvoutput": {},
            "sensor-overrides": {},
        }

        if cls._source:
            _yaml = YAML(typ="safe", pure=True)
            with open(cls._source, "r") as f:
                data = _yaml.load(f)
            if data:
                cls._configure(data)
            else:
                logging.warning(f"Ignored configuration file {cls._source} because it contains no keys?")

        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(cls.persistent_state_path, "auto-discovery.yaml")
        auto_discovered = None
        if auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file()):
            port = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, "502"))
            ping_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT, "0.5"))
            modbus_timeout = float(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT, "0.25"))
            modbus_retries = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES, "0"))
            logging.info(f"Auto-discovery required, scanning for Sigenergy devices ({port=} {ping_timeout=} {modbus_timeout=} {modbus_timeout=})...")
            auto_discovered = auto_discovery_scan(port, ping_timeout, modbus_timeout, modbus_retries)
            if len(auto_discovered) > 0:
                with open(auto_discovery_cache, "w") as f:
                    _yaml = YAML(typ="safe", pure=True)
                    _yaml.dump(auto_discovered, f)
        elif auto_discovery == "once" and auto_discovery_cache.is_file():
            logging.info("Auto-discovery already completed, using cached results.")
            with open(auto_discovery_cache, "r") as f:
                auto_discovered = YAML(typ="safe", pure=True).load(f)

        for key, value in os.environ.items():
            if key.startswith("SIGENERGY2MQTT_") and key != "SIGENERGY2MQTT_CONFIG" and value is not None and value != "None":
                logging.debug(f"Found env/cli override: {key} = {'[REDACTED]' if 'PASSWORD' in key or 'API_KEY' in key else value}")
                try:
                    match key:
                        case const.SIGENERGY2MQTT_CONSUMPTION:
                            overrides["consumption"] = ConsumptionMethod(
                                cast(
                                    str,
                                    check_string(
                                        os.environ[key],
                                        key,
                                        ConsumptionMethod.CALCULATED.value,
                                        ConsumptionMethod.TOTAL.value,
                                        ConsumptionMethod.GENERAL.value,
                                        allow_empty=False,
                                        allow_none=False,
                                    ),
                                ),
                            )
                        case const.SIGENERGY2MQTT_LOG_LEVEL:
                            overrides["log-level"] = check_log_level(os.environ[key], key)
                        case const.SIGENERGY2MQTT_DEBUG_SENSOR:
                            overrides["sensor-overrides"][check_string(os.environ[key], key, allow_empty=False, allow_none=False)] = {"debug-logging": True}
                            overrides["log-level"] = logging.DEBUG
                        case const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW:
                            overrides["sanity-check-default-kw"] = check_float(os.environ[key], key, allow_none=False, min=0)
                        case const.SIGENERGY2MQTT_SANITY_CHECK_FAILURES_INCREMENT:
                            overrides["sanity-check-failures-increment"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_LANGUAGE:
                            try:
                                overrides["language"] = check_string(os.environ[key], key, *i18n.get_available_translations(), allow_empty=False, allow_none=False)
                            except ValueError:
                                default = i18n.get_default_language()
                                logging.warning(f"Invalid language '{os.environ[key]}' for {key}, falling back to '{default}'")
                                overrides["language"] = default
                        case const.SIGENERGY2MQTT_NO_EMS_MODE_CHECK:
                            overrides["no-ems-mode-check"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_NO_METRICS:
                            overrides["no-metrics"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_ENABLED:
                            overrides["home-assistant"]["enabled"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_EDIT_PCT_BOX:
                            overrides["home-assistant"]["edit-pct-box"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX:
                            overrides["home-assistant"]["entity-id-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX:
                            overrides["home-assistant"]["device-name-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX:
                            overrides["home-assistant"]["discovery-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX:
                            overrides["home-assistant"]["unique-id-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_USE_SIMPLIFIED_TOPICS:
                            overrides["home-assistant"]["use-simplified-topics"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_HOST:
                            overrides["modbus"][0]["host"] = check_host(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_PORT:
                            overrides["modbus"][0]["port"] = check_port(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_LOG_LEVEL:
                            overrides["modbus"][0]["log-level"] = check_log_level(os.environ[key], key)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["log-level"] = overrides["modbus"][0]["log-level"]
                        case const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID:
                            overrides["modbus"][0]["inverters"] = check_int_list(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID:
                            overrides["modbus"][0]["ac-chargers"] = check_int_list(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID:
                            overrides["modbus"][0]["dc-chargers"] = check_int_list(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_NO_REMOTE_EMS:
                            overrides["modbus"][0]["no-remote-ems"] = check_bool(os.environ[key], key)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["no-remote-ems"] = overrides["modbus"][0]["no-remote-ems"]
                        case const.SIGENERGY2MQTT_MODBUS_READ_ONLY:
                            overrides["modbus"][0]["read-only"] = check_bool(os.environ[key], key)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["read-only"] = overrides["modbus"][0]["read-only"]
                        case const.SIGENERGY2MQTT_MODBUS_READ_WRITE:
                            overrides["modbus"][0]["read-write"] = check_bool(os.environ[key], key)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["read-write"] = overrides["modbus"][0]["read-write"]
                        case const.SIGENERGY2MQTT_MODBUS_WRITE_ONLY:
                            overrides["modbus"][0]["write-only"] = check_bool(os.environ[key], key)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["write-only"] = overrides["modbus"][0]["write-only"]
                        case const.SIGENERGY2MQTT_MODBUS_DISABLE_CHUNKING:
                            overrides["modbus"][0]["disable-chunking"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MODBUS_RETRIES:
                            overrides["modbus"][0]["retries"] = check_int(os.environ[key], key, min=0)
                        case const.SIGENERGY2MQTT_MODBUS_TIMEOUT:
                            overrides["modbus"][0]["timeout"] = check_float(os.environ[key], key, min=0.25)
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW:
                            overrides["modbus"][0]["scan-interval-low"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
                                    if overrides["modbus"][0]["scan-interval-low"]:
                                        device["scan-interval-low"] = overrides["modbus"][0]["scan-interval-low"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM:
                            overrides["modbus"][0]["scan-interval-medium"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
                                    if overrides["modbus"][0]["scan-interval-medium"]:
                                        device["scan-interval-medium"] = overrides["modbus"][0]["scan-interval-medium"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH:
                            overrides["modbus"][0]["scan-interval-high"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
                                    if overrides["modbus"][0]["scan-interval-high"]:
                                        device["scan-interval-high"] = overrides["modbus"][0]["scan-interval-high"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME:
                            overrides["modbus"][0]["scan-interval-realtime"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
                                    if overrides["modbus"][0]["scan-interval-realtime"]:
                                        device["scan-interval-realtime"] = overrides["modbus"][0]["scan-interval-realtime"]
                        case const.SIGENERGY2MQTT_SMARTPORT_ENABLED:
                            overrides["modbus"][0]["smart-port"]["enabled"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_SMARTPORT_MODULE_NAME:
                            overrides["modbus"][0]["smart-port"]["module"]["name"] = os.environ[key]
                        case const.SIGENERGY2MQTT_SMARTPORT_HOST:
                            overrides["modbus"][0]["smart-port"]["module"]["host"] = check_host(os.environ[key], key)
                        case const.SIGENERGY2MQTT_SMARTPORT_USERNAME:
                            overrides["modbus"][0]["smart-port"]["module"]["username"] = os.environ[key]
                        case const.SIGENERGY2MQTT_SMARTPORT_PASSWORD:
                            overrides["modbus"][0]["smart-port"]["module"]["password"] = os.environ[key]
                        case const.SIGENERGY2MQTT_SMARTPORT_PV_POWER:
                            overrides["modbus"][0]["smart-port"]["module"]["pv-power"] = os.environ[key]
                        case const.SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC:
                            overrides["modbus"][0]["smart-port"]["mqtt"][0]["topic"] = os.environ[key]
                        case const.SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN:
                            overrides["modbus"][0]["smart-port"]["mqtt"][0]["gain"] = check_int(os.environ[key], key, allow_none=True, min=1)
                        case const.SIGENERGY2MQTT_MQTT_BROKER:
                            overrides["mqtt"]["broker"] = check_host(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_PORT:
                            overrides["mqtt"]["port"] = check_port(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_KEEPALIVE:
                            overrides["mqtt"]["keepalive"] = check_int(os.environ[key], key, min=1)
                        case const.SIGENERGY2MQTT_MQTT_TLS:
                            overrides["mqtt"]["tls"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_TLS_INSECURE:
                            overrides["mqtt"]["tls-insecure"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_TRANSPORT:
                            overrides["mqtt"]["transport"] = check_string(os.environ[key], key, "tcp", "websockets", allow_none=False, allow_empty=False)
                        case const.SIGENERGY2MQTT_MQTT_ANONYMOUS:
                            overrides["mqtt"]["anonymous"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_LOG_LEVEL:
                            overrides["mqtt"]["log-level"] = check_log_level(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_USERNAME:
                            overrides["mqtt"]["username"] = os.environ[key]
                        case const.SIGENERGY2MQTT_MQTT_PASSWORD:
                            overrides["mqtt"]["password"] = os.environ[key]
                        case const.SIGENERGY2MQTT_PVOUTPUT_ENABLED:
                            overrides["pvoutput"]["enabled"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXPORTS:
                            overrides["pvoutput"]["exports"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_IMPORTS:
                            overrides["pvoutput"]["imports"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL:
                            overrides["pvoutput"]["log-level"] = check_log_level(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_OUTPUT_HOUR:
                            overrides["pvoutput"]["output-hour"] = check_int(os.environ[key], key, min=-1, max=23)
                        case const.SIGENERGY2MQTT_PVOUTPUT_PERIODS_JSON:
                            overrides["pvoutput"]["time-periods"] = json.loads(os.environ[key])
                        case const.SIGENERGY2MQTT_PVOUTPUT_CALC_DEBUG_LOGGING:
                            overrides["pvoutput"]["calc-debug-logging"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING:
                            overrides["pvoutput"]["update-debug-logging"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_API_KEY:
                            overrides["pvoutput"]["api-key"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False, hex_chars_only=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID:
                            overrides["pvoutput"]["system-id"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False)
                        case const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION:
                            overrides["pvoutput"]["consumption"] = check_string(
                                os.environ[key],
                                key,
                                "false",
                                "true",
                                ConsumptionSource.CONSUMPTION.value,
                                ConsumptionSource.IMPORTED.value,
                                ConsumptionSource.NET_OF_BATTERY.value,
                                allow_empty=False,
                                allow_none=False,
                            )
                        case const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC:
                            overrides["pvoutput"]["temperature-topic"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False)
                        case const.SIGENERGY2MQTT_PVOUTPUT_VOLTAGE:
                            overrides["pvoutput"]["voltage"] = check_string(os.environ[key], key, *[v.value for v in VoltageSource])
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V7:
                            overrides["pvoutput"]["v7"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V8:
                            overrides["pvoutput"]["v8"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V9:
                            overrides["pvoutput"]["v9"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V10:
                            overrides["pvoutput"]["v10"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V11:
                            overrides["pvoutput"]["v11"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_EXT_V12:
                            overrides["pvoutput"]["v12"] = check_string(os.environ[key], key, allow_none=True, allow_empty=True)
                        case (
                            const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY
                            | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT
                            | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_TIMEOUT
                            | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_RETRIES
                        ):
                            pass  # Handled above
                        case _:
                            logging.warning(f"UNKNOWN env/cli override: {key} = {'******' if 'PASSWORD' in key or 'API_KEY' in key else value}")
                except Exception as e:
                    raise Exception(f"{repr(e)} when processing override '{key}'")

        cls._configure(overrides, True)

        i18n.load(cls.language)

        if auto_discovered:
            if isinstance(auto_discovered, list):
                for device in auto_discovered:
                    updated = False
                    for defined in cls.modbus:
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
                        cls.modbus.append(new_device)
            else:
                raise ValueError("Auto-discovery results must be a list of modbus device configurations")

    @staticmethod
    def version() -> str:
        return version.__version__

    @staticmethod
    def _configure(data: dict, override: bool = False) -> None:
        for name in data.keys() if data else {}:
            match name:
                case "consumption":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: consumption = {data[name]}")
                    Config.consumption = ConsumptionMethod(
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
                        Config.language = cast(str, check_string(data[name], name, *i18n.get_available_translations(), allow_empty=False, allow_none=False))
                    except ValueError:
                        default = i18n.get_default_language()
                        logging.warning(f"Invalid language '{data[name]}' for {name}, falling back to '{default}'")
                        Config.language = default
                case "home-assistant":
                    Config.home_assistant.configure(data[name], override)
                case "log-level":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: log-level = {data[name]}")
                    Config.log_level = check_log_level(data[name], name)
                case "mqtt":
                    Config.mqtt.configure(data[name], override)
                case "modbus":
                    if isinstance(data[name], list):
                        index = 0
                        for config in data[name]:
                            if isinstance(config, dict):
                                if len(Config.modbus) <= index:
                                    device = ModbusConfiguration()
                                    Config.modbus.append(device)
                                else:
                                    device = Config.modbus[index]
                                device.configure(config, override)
                            index += 1
                    else:
                        raise ValueError("modbus configuration element must contain a list of Sigenergy hosts")
                case "no-ems-mode-check":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: no-ems-mode-check = {data[name]}")
                    Config.ems_mode_check = not check_bool(data[name], name)
                case "no-metrics":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: no-metrics = {data[name]}")
                    Config.metrics_enabled = not check_bool(data[name], name)
                case "pvoutput":
                    Config.pvoutput.configure(data[name], override)
                case "sanity-check-default-kw":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sanity-check-default-kw = {data[name]}")
                    Config.sanity_check_default_kw = cast(float, check_float(data[name], name, allow_none=False, min=0))
                case "sanity-check-failures-increment":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sanity-check-failures-increment = {data[name]}")
                    Config.sanity_check_failures_increment = check_bool(data[name], name)
                case "sensor-debug-logging":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sensor-debug-logging = {data[name]}")
                    Config.sensor_debug_logging = check_bool(data[name], name)
                case "sensor-overrides":
                    if isinstance(data[name], dict):
                        for sensor, settings in data[name].items():
                            Config.sensor_overrides[sensor] = {}
                            for p, v in settings.items():
                                logging.debug(f"Applying configuration sensor-overrides: {sensor}.{p} = {v}")
                                match p:
                                    case "debug-logging":
                                        Config.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "gain":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=True, min=1)
                                    case "icon":
                                        Config.sensor_overrides[sensor][p] = check_string(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, starts_with="mdi:")
                                    case "max-failures":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=True, min=1)
                                    case "max-failures-retry-interval":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0)
                                    case "precision":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0, max=6)
                                    case "publishable":
                                        Config.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "publish-raw":
                                        Config.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "scan-interval":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=1)
                                    case "sanity-check-max-value":
                                        Config.sensor_overrides[sensor][p] = check_float(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case "sanity-check-min-value":
                                        Config.sensor_overrides[sensor][p] = check_float(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case "sanity-check-delta":
                                        Config.sensor_overrides[sensor][p] = check_bool(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -")
                                    case "unit-of-measurement":
                                        Config.sensor_overrides[sensor][p] = check_string(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False)
                                    case _:
                                        raise ValueError(f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} - property is not known or not overridable")
                    elif data[name] is not None:
                        raise ValueError("sensor-overrides configuration elements must contain a list of class names, each followed by options and their values")
                case _:
                    raise ValueError(f"Configuration contains unknown element '{name}'")


Config._apply_defaults()
