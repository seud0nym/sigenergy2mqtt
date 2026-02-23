"""Coverage tests for ModbusConfig pydantic model."""

import logging

import pytest
from pydantic import ValidationError

from sigenergy2mqtt.config.settings import ModbusConfig, SmartPortConfig, SmartPortModule


def test_modbus_config_empty_host_raises():
    """ModbusConfig with empty host must raise validation error."""
    with pytest.raises(ValidationError, match="modbus entry must have a host"):
        ModbusConfig(host="")


def test_modbus_config_all_fields():
    """Set all fields via constructor and verify."""
    config = ModbusConfig(
        host="1.2.3.4",
        port=505,
        log_level="DEBUG",
        disable_chunking=True,
        retries=10,
        timeout=5.0,
        ac_chargers=[1, 2],
        dc_chargers=[3, 4],
        inverters=[5, 6],
        **{
            "no-remote-ems": True,
            "read-only": True,
            "read-write": True,
            "write-only": True,
            "scan-interval-low": 1000,
            "scan-interval-medium": 100,
            "scan-interval-high": 10,
            "scan-interval-realtime": 1,
        },
    )
    assert config.host == "1.2.3.4"
    assert config.port == 505
    assert config.log_level == logging.DEBUG
    assert config.scan_interval.low == 1000
    assert config.disable_chunking is True
    assert config.retries == 10
    assert config.timeout == 5.0
    assert config.ac_chargers == [1, 2]
    assert config.dc_chargers == [3, 4]
    assert config.inverters == [5, 6]
    assert config.registers.no_remote_ems is True
    assert config.registers.read_only is True
    assert config.registers.read_write is True
    assert config.registers.write_only is True
    assert config.scan_interval.medium == 100
    assert config.scan_interval.high == 10
    assert config.scan_interval.realtime == 1


def test_modbus_config_default_inverter():
    """Default to [1] when no devices specified."""
    config = ModbusConfig(host="h")
    assert config.inverters == [1]


def test_modbus_config_smartport():
    """SmartPortConfig can be set as nested field."""
    config = ModbusConfig(
        host="h",
        smartport=SmartPortConfig(
            enabled=True,
            module=SmartPortModule(name="enphase"),
        ),
    )
    assert config.smartport.enabled is True
    assert config.smartport.module.name == "enphase"


def test_modbus_config_alias_keys():
    """Test that alias keys (YAML kebab-case) work for flat register/scan fields."""
    config = ModbusConfig(
        **{
            "host": "1.2.3.4",
            "no-remote-ems": True,
            "scan-interval-low": 999,
        }
    )
    assert config.registers.no_remote_ems is True
    assert config.scan_interval.low == 999
