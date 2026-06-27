import logging
from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.common import ConsumptionMethod
from sigenergy2mqtt.config import Config


@pytest.fixture
def clean_config():
    """Fixture that provides an uninitialized Config object."""
    cfg = Config()
    cfg._settings = None
    return cfg


def test_property_setters_raise_attribute_error_when_uninitialized(clean_config):
    """Test that property setters raise AttributeError when settings are not initialized."""
    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.log_level = logging.DEBUG

    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.language = "es"

    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.consumption = ConsumptionMethod.CALCULATED

    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.persistence_debug = True

    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.modbus = []

    with pytest.raises(AttributeError, match="settings not initialised"):
        clean_config.sensor_overrides = {}


def test_property_setters_update_settings(clean_config):
    """Test that property setters update settings when initialized."""
    from sigenergy2mqtt.config.settings import Settings, PersistenceConfig
    
    clean_config._settings = Settings()

    clean_config.log_level = logging.DEBUG
    assert clean_config._settings.log_level == logging.DEBUG

    clean_config.language = "es"
    assert clean_config._settings.language == "es"

    clean_config.consumption = ConsumptionMethod.CALCULATED
    assert clean_config._settings.consumption == ConsumptionMethod.CALCULATED

    clean_config.persistence_debug = True
    assert clean_config._settings.persistence.debug is True

    mock_modbus = ["test"]
    clean_config.modbus = mock_modbus
    assert clean_config._settings.modbus == mock_modbus

    mock_overrides = {"sensor": "override"}
    clean_config.sensor_overrides = mock_overrides
    assert clean_config._settings.sensor_overrides == mock_overrides


def test_property_deleters(clean_config):
    """Test that property deleters do nothing (pass) without error."""
    # Should not raise any exceptions
    del clean_config.log_level
    del clean_config.language
    del clean_config.consumption
    del clean_config.persistence_debug
    del clean_config.modbus
    del clean_config.sensor_overrides
