from unittest.mock import AsyncMock

from sigenergy2mqtt.common import Protocol
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.const import DeviceClass, StateClass


class ConcreteSensor(Sensor):
    """Concrete implementation of Sensor for testing since Sensor is abstract."""

    async def _update_internal_state(self, **kwargs):
        return True


class DummySensor(Sensor):
    """Another concrete implementation of Sensor for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _update_internal_state(self, **kwargs):
        return True


def make_test_sensor(unique_suffix: str = "1") -> ConcreteSensor:
    """Helper to create a ConcreteSensor with consistent defaults."""
    # Respect configured prefixes
    prefix_u = Config.home_assistant.unique_id_prefix
    prefix_o = Config.home_assistant.entity_id_prefix
    unique_id = f"{prefix_u}_test_{unique_suffix}"
    object_id = f"{prefix_o}_test_{unique_suffix}"
    return ConcreteSensor(
        name="Test",
        unique_id=unique_id,
        object_id=object_id,
        unit="W",
        device_class=DeviceClass.POWER,
        state_class=StateClass.MEASUREMENT,
        icon="mdi:power",
        gain=1.0,
        precision=2,
        protocol_version=Protocol.V2_4,
    )


class MockResponse:
    """Reusable mock for HTTP responses."""

    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self.json_data = json_data or {}

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"HTTP Error: {self.status_code}")
