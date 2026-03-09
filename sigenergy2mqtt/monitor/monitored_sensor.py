"""Data model for MQTT topic monitoring state."""

import time
from dataclasses import dataclass, field

from sigenergy2mqtt.config import active_config


@dataclass
class MonitoredSensor:
    """Represents runtime monitoring details for a single MQTT sensor topic.

    Args:
        device_name: Human-readable name of the device publishing the sensor.
        sensor_name: Human-readable name of the sensor.
        scan_interval: Expected publish interval in seconds for the sensor.
        last_seen: Unix timestamp of the last observed MQTT update.
        notified: Whether an overdue warning has already been logged.
    """

    device_name: str
    sensor_name: str
    scan_interval: int
    last_seen: float = field(default_factory=time.time)
    notified: bool = False

    @property
    def is_overdue(self) -> bool:
        """Return whether the sensor is overdue for an update."""

        repeated_interval = active_config.repeated_state_publish_interval
        if repeated_interval < 0:
            # Repeated states are never republished when unchanged, so the
            # monitor cannot infer staleness from missing messages.
            return False

        expected_publish_interval = self.scan_interval
        if repeated_interval > 0:
            expected_publish_interval = max(expected_publish_interval, repeated_interval)

        return not self.notified and self.last_seen + (expected_publish_interval * 3) < time.time()

    @property
    def name(self) -> str:
        """Return a combined display name in ``<device> - <sensor>`` format."""

        return f"{self.device_name} - {self.sensor_name}"

    @property
    def overdue(self) -> float:
        """Return the number of seconds since the last update was observed."""

        return round(time.time() - self.last_seen, 2)
