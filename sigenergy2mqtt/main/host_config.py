import asyncio
from dataclasses import dataclass, field
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.sensors.base import Sensor


@dataclass
class DeviceIndex:
    index: int
    device: Device


@dataclass
class HostConfig:
    host: str
    port: int
    name: str = ""

    _devices: list[DeviceIndex] = field(default_factory=list)
    
    @property
    def description(self) -> str:
        return self.name if self.name and not self.name.isspace() else f"{self.host}:{self.port}"

    @property
    def devices(self) -> list[Device]:
        return [host.device for host in self._devices]

    def add_device(self, plant_index: int, device: Device) -> None:
        self._devices.append(DeviceIndex(plant_index, device))

    def offline(self) -> None:
        for config in self._devices:
            config.device.online = False

    def online(self, future: asyncio.Future) -> None:
        for config in self._devices:
            config.device.online = future

    def reload_config(self) -> None:
        for config in self._devices:
            device: Device = config.device
            sensor: Sensor = None
            for sensor in device.sensors.values():
                sensor.apply_sensor_overrides(device.registers)


class HostConfigFactory:
    _configs: dict[tuple[str, int], HostConfig] = {}

    @classmethod
    def get_config(self, host, port) -> HostConfig:
        key = (host, port)
        if key not in HostConfigFactory._configs:
            self._configs[key] = HostConfig(host, port)
        return self._configs[key]

    @classmethod
    def get_configs(self) -> list[HostConfig]:
        return list(self._configs.values())
