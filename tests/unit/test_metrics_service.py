from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.config import Config, Protocol
from sigenergy2mqtt.metrics.metrics import Metrics
from sigenergy2mqtt.metrics.metrics_service import MetricsService
from sigenergy2mqtt.sensors.const import PERCENTAGE


@pytest.fixture
def mock_mqtt_client():
    return MagicMock(spec=mqtt.Client)


class TestMetricsService:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Backup original config
        original_enabled = Config.home_assistant.enabled
        original_discovery_prefix = Config.home_assistant.discovery_prefix
        original_unique_id_prefix = Config.home_assistant.unique_id_prefix
        original_device_name_prefix = Config.home_assistant.device_name_prefix
        original_devices = list(Config.devices)
        original_started = Metrics._started

        # Set test config
        Config.home_assistant.enabled = True
        Config.home_assistant.discovery_prefix = "homeassistant"
        Config.home_assistant.unique_id_prefix = "test_prefix"
        Config.home_assistant.device_name_prefix = ""
        Config.devices = []
        Metrics._started = 0.0

        yield

        # Restore original config
        Config.home_assistant.enabled = original_enabled
        Config.home_assistant.discovery_prefix = original_discovery_prefix
        Config.home_assistant.unique_id_prefix = original_unique_id_prefix
        Config.home_assistant.device_name_prefix = original_device_name_prefix
        Config.devices = original_devices
        Metrics._started = original_started

    def test_init(self):
        service = MetricsService(Protocol.V2_4)
        assert service.name == "Sigenergy Metrics"
        assert service.unique_id == "test_prefix_metrics"
        assert len(service.read_sensors) > 0

    def test_sensors_added(self):
        service = MetricsService(Protocol.V2_4)
        sensors = service.read_sensors

        # Verify key sensors are present
        assert "test_prefix_modbus_cache_hit_percentage" in sensors
        assert "test_prefix_modbus_reads_sec" in sensors
        assert "test_prefix_modbus_read_errors" in sensors
        assert "test_prefix_modbus_locks" in sensors
        assert "test_prefix_started" in sensors
        assert "test_prefix_modbus_protocol" in sensors

    def test_sensor_config(self):
        service = MetricsService(Protocol.V2_4)
        sensor = service.read_sensors["test_prefix_modbus_cache_hit_percentage"]

        assert sensor.name == "Modbus Cache Hits"
        assert sensor.unit == PERCENTAGE
        assert sensor["icon"] == "mdi:percent"
        assert sensor.state_topic == "sigenergy2mqtt/metrics/modbus_cache_hit_percentage"

    def test_update_workflow(self):
        service = MetricsService(Protocol.V2_4)

        # Mock Metrics values
        Metrics.sigenergy2mqtt_modbus_reads = 100
        Metrics._started = 1000.0

        with patch("time.monotonic", return_value=1010.0):  # 10 seconds elapsed
            reads_sensor = service.read_sensors["test_prefix_modbus_reads_sec"]
            # Trigger update manually or simulate check
            # For ReadableSensorMixin we rely on _update_internal_state

            # This requires async run if we follow normal pattern, but let's test the update logic directly

            import asyncio

            async def run_update():
                await reads_sensor._update_internal_state()

            asyncio.run(run_update())

            assert reads_sensor.latest_raw_state == 10.0  # 100 reads / 10 sec

    def test_lock_sensor(self):
        service = MetricsService(Protocol.V2_4)
        with patch("sigenergy2mqtt.modbus.lock_factory.ModbusLockFactory.get_waiter_count", return_value=5):
            lock_sensor = service.read_sensors["test_prefix_modbus_locks"]

            import asyncio

            asyncio.run(lock_sensor._update_internal_state())

            assert lock_sensor.latest_raw_state == 5

    def test_topics_structure(self):
        service = MetricsService(Protocol.V2_4)

        # Check a few specific topics to ensure they match old format
        # existing: sigenergy2mqtt/metrics/modbus_protocol

        errors_sensor = service.read_sensors["test_prefix_modbus_read_errors"]
        assert errors_sensor.state_topic == "sigenergy2mqtt/metrics/modbus_read_errors"

        proto_sensor = service.read_sensors["test_prefix_modbus_protocol"]
        assert proto_sensor.state_topic == "sigenergy2mqtt/metrics/modbus_protocol"
