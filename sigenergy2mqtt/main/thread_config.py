from dataclasses import dataclass, field
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.sensors.base import Sensor
import asyncio
import ipaddress


@dataclass
class DeviceIndex:
    index: int
    device: Device


@dataclass
class ThreadConfig:
    host: str
    port: int
    timeout: float = 1.0
    retries: int = 3
    name: str = ""

    _devices: list[DeviceIndex] = field(default_factory=list)

    @property
    def description(self) -> str:
        return self.name if self.name and not self.name.isspace() else f"modbus://{self.host}:{self.port}"

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


class ThreadConfigFactory:
    _configs: dict[tuple[str, int], ThreadConfig] = {}

    @classmethod
    def get_config(self, host: str, port: int, timeout: float = 1.0, retries: int = 3) -> ThreadConfig:
        key = (host, port)
        if key not in ThreadConfigFactory._configs:
            try:
                ipaddress.IPv4Address(host)
                octets = host.split(".")
                hostname = "".join(f"{int(octet):02X}" for octet in octets)
            except ipaddress.AddressValueError:
                hostname = host
            self._configs[key] = ThreadConfig(host, port, timeout, retries, name=f"Modbus@{hostname}" if port == 502 else f"Modbus@{hostname}:{port:02X}")
        return self._configs[key]

    @classmethod
    def get_configs(self) -> list[ThreadConfig]:
        return list(self._configs.values())
