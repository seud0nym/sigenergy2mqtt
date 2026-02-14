import logging
from unittest.mock import ANY, patch

import pytest

from sigenergy2mqtt.config.modbus_config import ModbusConfiguration


def test_modbus_config_exhaustive():
    m = ModbusConfiguration()

    # Line 41: host must be provided
    m.host = ""
    with pytest.raises(ValueError, match="modbus.host must be provided"):
        m.validate()

    # Line 93: must be a dict
    with pytest.raises(ValueError, match="must contain options and their values"):
        m.configure("not a dict")

    # Line 89: unknown option
    with pytest.raises(ValueError, match="contains unknown option 'unknown'"):
        m.configure({"unknown": 1})

    # Hit all cases in configure()
    config = {
        "host": "1.2.3.4",
        "port": 505,
        "log-level": "DEBUG",
        "no-remote-ems": True,
        "read-only": True,
        "read-write": True,
        "write-only": True,
        "disable-chunking": True,
        "retries": 10,
        "timeout": 5.0,
        "ac-chargers": [1, 2],
        "dc-chargers": [3, 4],
        "inverters": [5, 6],
        "scan-interval-low": 1000,
        "scan-interval-medium": 100,
        "scan-interval-high": 10,
        "scan-interval-realtime": 1,
    }
    m.configure(config)
    m.validate()
    assert m.host == "1.2.3.4"
    assert m.port == 505
    assert m.log_level == logging.DEBUG
    assert m.scan_interval.low == 1000

    # Lines 47-48: auto_discovered logging
    with patch("sigenergy2mqtt.config.modbus_config.logging.info") as mock_info:
        m.configure({"host": "2.3.4.5"}, auto_discovered=True)
        # Check if info was called (line 48)
        mock_info.assert_called()

    # Line 50: auto_discovered INFO log
    with patch("sigenergy2mqtt.config.modbus_config.logging.log") as mock_log:
        m.configure({"retries": 1}, auto_discovered=True)
        mock_log.assert_called_with(logging.INFO, ANY)

    # Lines 90-91: default inverter 1 if empty
    m2 = ModbusConfiguration()
    m2.inverters = []
    m2.configure({"host": "h"})
    assert m2.inverters == [1]

    # Smart port configuration (line 79)
    with patch.object(m.smartport, "configure") as mock_smart:
        m.configure({"smart-port": {"enabled": True}})
        mock_smart.assert_called()
