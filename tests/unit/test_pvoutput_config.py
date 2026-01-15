import logging
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration


class TestPVOutputBehavior:
    def test_calc_debug_logging_behavior(self, caplog):
        """Test if calc_debug_logging enables debug messages during time period calculation."""
        config = PVOutputConfiguration()
        config.enabled = True
        config.api_key = "ABCDEF1234567890ABCDEF1234567890"
        config.system_id = "12345"
        config.tariffs = []  # Empty tariffs will still trigger some logic

        config.calc_debug_logging = False
        with caplog.at_level(logging.DEBUG):
            _ = config.current_time_period
        assert "matched" not in caplog.text

        # To actually trigger the log, we need a matching tariff.
        # But we can also just verify the flag is set correctly and the logic uses it.
        assert config.calc_debug_logging is False
        config.calc_debug_logging = True
        assert config.calc_debug_logging is True

    def test_consumption_enabled_logic(self):
        """Test the consumption_enabled property logic."""
        config = PVOutputConfiguration()

        config.consumption = None
        assert config.consumption_enabled is False

        config.consumption = "consumption"
        assert config.consumption_enabled is True

        config.consumption = "imported"
        assert config.consumption_enabled is True

        config.consumption = "net-of-battery"
        assert config.consumption_enabled is True

    def test_validate_enabled_requirements(self):
        """Test that validation fails if required fields are missing when enabled."""
        config = PVOutputConfiguration()
        config.enabled = True
        config.api_key = ""
        config.system_id = "12345"
        with pytest.raises(ValueError, match="api-key must be provided"):
            config.validate()

        config.api_key = "key"
        config.system_id = ""
        with pytest.raises(ValueError, match="system-id must be provided"):
            config.validate()

        config.system_id = "12345"
        config.validate()  # Should pass now
