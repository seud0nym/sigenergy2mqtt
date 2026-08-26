import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.config.sensors import (
    ApplicationLogLevel,
    DiagnosticsLogLevel,
    InfluxDBLogLevel,
    PVOutputLogLevel,
)
from sigenergy2mqtt.config.service import SettingsService


@pytest.fixture
def config():
    with _swap_active_config(Config()) as cfg:
        yield cfg


def test_optional_settings_follow_integration_configuration(config):
    config.diagnostics.enabled = True
    config.influxdb.enabled = True
    config.pvoutput.enabled = True

    service = SettingsService()

    assert isinstance(service.sensors["sigenergy2mqtt_config_log_level"], ApplicationLogLevel)
    assert any(isinstance(sensor, DiagnosticsLogLevel) for sensor in service.sensors.values())
    assert any(isinstance(sensor, InfluxDBLogLevel) for sensor in service.sensors.values())
    assert any(isinstance(sensor, PVOutputLogLevel) for sensor in service.sensors.values())


def test_optional_settings_are_omitted_when_integrations_are_disabled(config):
    config.diagnostics.enabled = False
    config.influxdb.enabled = False
    config.pvoutput.enabled = False

    service = SettingsService()

    assert not any(isinstance(sensor, DiagnosticsLogLevel) for sensor in service.sensors.values())
    assert not any(isinstance(sensor, InfluxDBLogLevel) for sensor in service.sensors.values())
    assert not any(isinstance(sensor, PVOutputLogLevel) for sensor in service.sensors.values())


@pytest.mark.asyncio
async def test_application_log_level_write_updates_config_and_logger(config):
    sensor = ApplicationLogLevel()
    sensor.configure_mqtt_topics("test-device")

    with patch.object(logging.getLogger("sigenergy2mqtt"), "setLevel") as set_level:
        assert await sensor.set_value(None, MagicMock(), "DEBUG", sensor.command_topic, MagicMock()) is True

    assert config.log_level == logging.DEBUG
    set_level.assert_called_once_with(logging.DEBUG)
