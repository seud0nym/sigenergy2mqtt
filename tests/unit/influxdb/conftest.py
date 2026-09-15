"""Shared test doubles and fixtures for the InfluxDB test suites."""

from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.influxdb.hass_history_sync import HassHistorySync
from sigenergy2mqtt.influxdb.service import InfluxService


class FakeResponse:
    """Minimal, requests-compatible response used by InfluxDB tests."""

    def __init__(self, status_code, json_data=None, text="", content=b""):
        self.status_code = status_code
        self.text = text
        self.content = content
        self._json_data = json_data

    def json(self):
        return self._json_data


@pytest.fixture
def disabled_influx_config():
    """Temporarily install a complete, disabled InfluxDB configuration."""
    config = MagicMock()
    config.enabled = False
    config.max_retries = 3
    config.pool_connections = 100
    config.pool_maxsize = 100
    config.batch_size = 100
    config.flush_interval = 1.0
    config.query_interval = 0.1
    config.sync_chunk_size = 100
    config.max_sync_workers = 5
    config.default_measurement = "state"
    config.load_hass_history = False

    with patch.object(active_config, "influxdb", config):
        yield config


@pytest.fixture
def disabled_influx_service(disabled_influx_config):
    """Create an InfluxService without attempting InfluxDB initialisation."""
    yield InfluxService(plant_index=0)


@pytest.fixture
def disabled_hass_history_sync(disabled_influx_config):
    """Create a HassHistorySync without attempting InfluxDB initialisation."""
    yield HassHistorySync(plant_index=0)


@pytest.fixture
def service(disabled_influx_service):
    """Short fixture name used by the helper-focused unit tests."""
    yield disabled_influx_service
