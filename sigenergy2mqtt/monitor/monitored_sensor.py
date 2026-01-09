import time
from dataclasses import dataclass


@dataclass
class MonitoredSensor:
    device_name: str
    sensor_name: str
    scan_interval: int
    last_seen: float = time.time()
    notified: bool = False

    @property
    def is_overdue(self) -> bool:
        return not self.notified and self.last_seen + (self.scan_interval * 2) < time.time()

    @property
    def name(self) -> str:
        return f"{self.device_name} - {self.sensor_name}"

    @property
    def overdue(self) -> float:
        return round(time.time() - self.last_seen, 2)
