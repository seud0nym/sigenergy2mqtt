from .device_config import DeviceConfig
from .home_assistant_config import HomeAssistantConfiguration
from .mqtt_config import MqttConfiguration
from .pvoutput_config import PVOutputConfiguration
from .validation import check_bool, check_int, check_log_level, check_string
from ruamel.yaml import YAML
from typing import List
import logging

__version__ = "2025.5.8"

class Config:
    origin = {"name": "sigenergy2mqtt", "sw": __version__, "url": "https://github.com/seud0nym/sigenergy2mqtt"}

    home_assistant = HomeAssistantConfiguration()
    mqtt = MqttConfiguration()
    devices: List[DeviceConfig] = []
    pvoutput = PVOutputConfiguration()
    sensor_debug_logging: bool = False
    sensor_overrides: dict = {}

    clean: bool = False
    log_level: int = logging.WARNING

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
        Config._source = filename
        Config.reload()

    @staticmethod
    def reload() -> None:
        _yaml = YAML(typ="safe", pure=True)
        with open(Config._source, "r") as f:
            data = _yaml.load(f)

        for name in data.keys():
            match name:
                case "home-assistant":
                    Config.home_assistant.configure(data[name])
                case "log-level":
                    Config.log_level = check_log_level(data[name], name)
                case "mqtt":
                    Config.mqtt.configure(data[name])
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
                                device.configure(config)
                            index += 1
                    else:
                        raise ValueError("modbus configuration element must contain a list of Sigenergy hosts")
                case "pvoutput":
                    Config.pvoutput.configure(data[name])
                case "sensor-debug-logging":
                    Config.sensor_debug_logging = check_bool(data[name], name)
                case "sensor-overrides":
                    if isinstance(data[name], dict):
                        for sensor, settings in data[name].items():
                            Config.sensor_overrides[sensor] = {}
                            for p, v in settings.items():
                                if (
                                    (p == "debug-logging" and check_bool(v, f"Error processing {sensor} override {p} = {v} -") == v)
                                    or (p == "gain" and check_int(v, f"Error processing {sensor} override {p} = {v} -", allow_none=True, min=1) == v)
                                    or (p == "icon" and check_string(v, f"Error processing {sensor} override {p} = {v} -", allow_none=False, starts_with="mdi:") == v)
                                    or (p == "max-failures" and check_int(v, f"Error processing {sensor} override {p} = {v} -", allow_none=True, min=1) == v)
                                    or (p == "max-failures-retry-interval" and check_int(v, f"Error processing {sensor} override {p} = {v} -", allow_none=False, min=30) == v)
                                    or (p == "precision" and check_int(v, f"Error processing {sensor} override {p} = {v} -", allow_none=False, min=0, max=6) == v)
                                    or (p == "publishable" and check_bool(v, f"Error processing {sensor} override {p} = {v} -") == v)
                                    or (p == "scan-interval" and check_int(v, f"Error processing {sensor} override {p} = {v} -", allow_none=False, min=1) == v)
                                    or (p == "unit-of-measurement" and check_string(v, f"Error processing {sensor} override {p} = {v} -", allow_none=False) == v)
                                ):
                                    logging.debug(f"Applying {sensor} override: {p} = {v}")
                                    Config.sensor_overrides[sensor][p] = v
                                else:
                                    raise ValueError(f"Error processing {sensor} override {p} = {v} - property is not known or not overridable")
                    elif data[name] is not None:
                        raise ValueError("sensor-overrides configuration elements must contain a list of classnames, each followed by options and their values")
                case _:
                    raise ValueError(f"Configuration contains unknown element '{name}'")

        if len(Config.devices) == 0:
            raise ValueError("No modbus devices found in configuration file.")
