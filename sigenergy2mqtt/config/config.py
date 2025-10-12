from . import const
from . import version
from .auto_discovery import scan as auto_discovery_scan
from .home_assistant_config import HomeAssistantConfiguration
from .modbus_config import DeviceConfig
from .mqtt_config import MqttConfiguration
from .pvoutput_config import CONSUMPTION, IMPORTED, PVOutputConfiguration
from .validation import check_bool, check_host, check_float, check_int, check_int_list, check_log_level, check_port, check_string
from pathlib import Path
from ruamel.yaml import YAML
from typing import List
import logging
import os


class Config:
    origin = {"name": "sigenergy2mqtt", "sw": version.__version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}

    clean: bool = False
    log_level: int = logging.WARNING

    devices: List[DeviceConfig] = []
    home_assistant: HomeAssistantConfiguration = HomeAssistantConfiguration()
    mqtt: MqttConfiguration = MqttConfiguration()
    pvoutput: PVOutputConfiguration = PVOutputConfiguration()
    sensor_debug_logging: bool = False
    sensor_overrides: dict = {}

    sanity_check_default_kw: float = 100.0
    metrics_enabled: bool = True

    persistent_state_path: str = "."

    _source: str = None

    @staticmethod
    def get_modbus_log_level() -> int:
        return min([device.log_level for device in Config.devices])

    @staticmethod
    def set_modbus_log_level(level: int) -> None:
        for device in Config.devices:
            device.log_level = level

    @staticmethod
    def load(filename: str) -> None:
        logging.info(f"Loading configuration from {filename}...")
        Config._source = filename
        Config.reload()

    @staticmethod
    def reload() -> None:
        overrides = {
            "home-assistant": {},
            "mqtt": {},
            "modbus": [{"smart-port": {"mqtt": [{}], "module": {}}}],
            "pvoutput": {},
            "sensor-overrides": {},
        }

        if Config._source:
            _yaml = YAML(typ="safe", pure=True)
            with open(Config._source, "r") as f:
                data = _yaml.load(f)
            Config._configure(data)

        auto_discovery = os.getenv(const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY)
        auto_discovery_cache = Path(Config.persistent_state_path, "auto-discovery.yaml")
        auto_discovered = None
        if auto_discovery == "force" or (auto_discovery == "once" and not auto_discovery_cache.is_file()):
            port = int(os.getenv(const.SIGENERGY2MQTT_MODBUS_PORT, "502"))
            logging.info(f"Auto-discovery required, scanning for Sigenergy devices ({port=})...")
            auto_discovered = auto_discovery_scan(port)
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
                        case const.SIGENERGY2MQTT_LOG_LEVEL:
                            overrides["log-level"] = check_log_level(os.environ[key], key)
                        case const.SIGENERGY2MQTT_DEBUG_SENSOR:
                            overrides["sensor-overrides"][check_string(os.environ[key], key, allow_empty=False, allow_none=False)] = {"debug-logging": True}
                            overrides["log-level"] = logging.DEBUG
                        case const.SIGENERGY2MQTT_SANITY_CHECK_DEFAULT_KW:
                            overrides["sanity-check-default-kw"] = check_float(os.environ[key], key, allow_none=False, min=0)
                        case const.SIGENERGY2MQTT_NO_METRICS:
                            overrides["no-metrics"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_ENABLED:
                            overrides["home-assistant"]["enabled"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX:
                            overrides["home-assistant"]["entity-id-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX:
                            overrides["home-assistant"]["device-name-prefix"] = check_string(os.environ[key], key)
                        case const.SIGENERGY2MQTT_HASS_DISCOVERY_ONLY:
                            overrides["home-assistant"]["discovery-only"] = check_bool(os.environ[key], key)
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
                        case const.SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE | const.SIGENERGY2MQTT_MODBUS_INVERTER_DEVICE_ID:
                            overrides["modbus"][0]["inverters"] = check_int_list([int(device_id) for device_id in os.environ[key].split(",")], key)
                        case const.SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE | const.SIGENERGY2MQTT_MODBUS_ACCHARGER_DEVICE_ID:
                            overrides["modbus"][0]["ac-chargers"] = check_int_list([int(device_id) for device_id in os.environ[key].split(",")], key)
                        case const.SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE | const.SIGENERGY2MQTT_MODBUS_DCCHARGER_DEVICE_ID:
                            overrides["modbus"][0]["dc-chargers"] = check_int_list([int(device_id) for device_id in os.environ[key].split(",")], key)
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
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_LOW:
                            overrides["modbus"][0]["scan-interval-low"] = check_int(os.environ[key], key, min=300)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["scan-interval-low"] = overrides["modbus"][0]["scan-interval-low"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_MEDIUM:
                            overrides["modbus"][0]["scan-interval-medium"] = check_int(os.environ[key], key, min=30)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["scan-interval-medium"] = overrides["modbus"][0]["scan-interval-medium"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_HIGH:
                            overrides["modbus"][0]["scan-interval-high"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
                                    device["scan-interval-high"] = overrides["modbus"][0]["scan-interval-high"]
                        case const.SIGENERGY2MQTT_SCAN_INTERVAL_REALTIME:
                            overrides["modbus"][0]["scan-interval-realtime"] = check_int(os.environ[key], key, min=1)
                            if auto_discovered:
                                for device in auto_discovered:
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
                        case const.SIGENERGY2MQTT_MQTT_TLS:
                            overrides["mqtt"]["tls"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_MQTT_TLS_INSECURE:
                            overrides["mqtt"]["tls-insecure"] = check_bool(os.environ[key], key)
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
                        case const.SIGENERGY2MQTT_PVOUTPUT_UPDATE_DEBUG_LOGGING:
                            overrides["pvoutput"]["update-debug-logging"] = check_bool(os.environ[key], key)
                        case const.SIGENERGY2MQTT_PVOUTPUT_API_KEY:
                            overrides["pvoutput"]["api-key"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False, hex_chars_only=True)
                        case const.SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID:
                            overrides["pvoutput"]["system-id"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False)
                        case const.SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION:
                            overrides["pvoutput"]["consumption"] = check_string(os.environ[key], key, "false", "true", CONSUMPTION, IMPORTED, allow_empty=False, allow_none=False)
                        case const.SIGENERGY2MQTT_PVOUTPUT_INTERVAL:
                            pass  # Deprecated
                        case const.SIGENERGY2MQTT_PVOUTPUT_TEMP_TOPIC:
                            overrides["pvoutput"]["temperature-topic"] = check_string(os.environ[key], key, allow_none=False, allow_empty=False)
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
                        case const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY:
                            pass  # Handled above
                        case _:
                            logging.warning(f"UNKNOWN env/cli override: {key} = {'******' if 'PASSWORD' in key or 'API_KEY' in key else value}")
                except Exception as e:
                    raise Exception(f"{repr(e)} when processing override '{key}'")

        Config._configure(overrides, True)

        if auto_discovered:
            if isinstance(auto_discovered, list):
                for device in auto_discovered:
                    updated = False
                    for defined in Config.devices:
                        if (defined.host == device.get("host") or defined.host == "") and defined.port == device.get("port"):
                            if defined.host == "":
                                defined.host = device.get("host")
                                defined.port = device.get("port")
                                logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                            else:
                                logging.info(f"Auto-discovered found configured Modbus device: {device.get('host')}:{device.get('port')}, updating with discovered device IDs")
                            defined.configure(device, override=True, auto_discovered=True)
                            updated = True
                            break
                    if not updated:
                        logging.info(f"Auto-discovery found new Modbus device: {device.get('host')}:{device.get('port')}")
                        new_device = DeviceConfig()
                        new_device.configure(device, override=True, auto_discovered=True)
                        Config.devices.append(new_device)
            else:
                raise ValueError("Auto-discovery results must be a list of modbus device configurations")

        if len(Config.devices) == 0:
            raise ValueError("No Modbus devices configured")

    @staticmethod
    def _configure(data: dict, override: bool = False) -> None:
        for name in data.keys():
            match name:
                case "home-assistant":
                    Config.home_assistant.configure(data[name], override)
                case "log-level":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: log-level = {data[name]}")
                    Config.log_level = check_log_level(data[name], name)
                case "sanity-check-default-kw":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: sanity-check-default-kw = {data[name]}")
                    Config.sanity_check_default_kw = check_float(data[name], name, allow_none=False, min=0)
                case "no-metrics":
                    logging.debug(f"Applying {'override from env/cli' if override else 'configuration'}: no-metrics = {data[name]}")
                    Config.metrics_enabled = not check_bool(data[name], name)
                case "mqtt":
                    Config.mqtt.configure(data[name], override)
                case "modbus":
                    if isinstance(data[name], list):
                        index = 0
                        for config in data[name]:
                            if isinstance(config, dict):
                                if len(Config.devices) <= index:
                                    device = DeviceConfig()
                                    Config.devices.append(device)
                                else:
                                    device = Config.devices[index]
                                device.configure(config, override)
                            index += 1
                    else:
                        raise ValueError("modbus configuration element must contain a list of Sigenergy hosts")
                case "pvoutput":
                    Config.pvoutput.configure(data[name], override)
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
                                        Config.sensor_overrides[sensor][p] = check_string(
                                            v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, starts_with="mdi:"
                                        )
                                    case "max-failures":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=True, min=1)
                                    case "max-failures-retry-interval":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0)
                                    case "precision":
                                        Config.sensor_overrides[sensor][p] = check_int(v, f"Error processing configuration sensor-overrides: {sensor}.{p} = {v} -", allow_none=False, min=0, max=6)
                                    case "publishable":
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
