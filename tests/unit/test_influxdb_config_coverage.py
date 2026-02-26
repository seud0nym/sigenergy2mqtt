import logging

import pytest
from pydantic import ValidationError

from sigenergy2mqtt.config.settings import InfluxDbConfig


class TestInfluxDBConfigCoverage:
    def test_default_values(self):
        config = InfluxDbConfig()
        assert config.enabled is False
        assert config.host == "127.0.0.1"
        assert config.port == 8086
        assert config.database == "sigenergy"
        assert config.default_measurement == "state"
        assert config.load_hass_history is False

    def test_configure_enabled(self):
        data = {"enabled": True, "token": "test_token", "org": "test_org"}
        config = InfluxDbConfig(**data)
        assert config.enabled is True

    def test_configure_all_fields(self):
        data = {
            "enabled": True,
            "host": "192.168.1.100",
            "port": 8087,
            "database": "test_db",
            "token": "my_token",
            "org": "my_org",
            "bucket": "my_bucket",
            "username": "user",
            "password": "pass",
            "include": ["sensor1", "sensor2"],
            "exclude": ["sensor3"],
            "log-level": "DEBUG",
            "default-measurement": "power",
            "load-hass-history": True,
        }
        config = InfluxDbConfig(**data)

        assert config.enabled is True
        assert config.host == "192.168.1.100"
        assert config.port == 8087
        assert config.database == "test_db"
        assert config.token == "my_token"
        assert config.org == "my_org"
        assert config.bucket == "my_bucket"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.include == ["sensor1", "sensor2"]
        assert config.exclude == ["sensor3"]
        assert config.log_level == logging.DEBUG
        assert config.default_measurement == "power"
        assert config.load_hass_history is True

    def test_configure_invalid_port(self):
        data = {"enabled": True, "port": 70000}  # Out of range
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            InfluxDbConfig(**data)

    def test_configure_invalid_include(self):
        data = {"enabled": True, "include": "not_a_list"}
        with pytest.raises(ValidationError, match="Input should be a valid list|input must be a list"):
            InfluxDbConfig(**data)

    def test_configure_invalid_exclude(self):
        data = {"enabled": True, "exclude": "not_a_list"}
        with pytest.raises(ValidationError, match="Input should be a valid list|input must be a list"):
            InfluxDbConfig(**data)

    def test_configure_invalid_default_measurement(self):
        data = {"enabled": True, "token": "dummy", "org": "dummy", "default-measurement": ""}
        with pytest.raises(ValidationError, match="least 1 character"):
            InfluxDbConfig(**data)

    def test_configure_missing_credentials(self):
        """Test that configuration fails when no valid credentials are provided."""
        data = {"enabled": True, "host": "localhost"}
        with pytest.raises(ValidationError, match="v2 credentials.*or v1 credentials"):
            InfluxDbConfig(**data)

    def test_configure_partial_v2_credentials(self):
        """Test that configuration fails with only token but missing org."""
        data = {"enabled": True, "token": "test_token"}
        with pytest.raises(ValidationError, match="v2 credentials.*or v1 credentials"):
            InfluxDbConfig(**data)

    def test_configure_partial_v1_credentials(self):
        """Test that configuration fails with only username but missing password."""
        data = {"enabled": True, "username": "test_user"}
        with pytest.raises(ValidationError, match="v2 credentials.*or v1 credentials"):
            InfluxDbConfig(**data)

    def test_configure_v1_credentials_valid(self):
        """Test that v1 credentials (username + password) are accepted."""
        data = {"enabled": True, "username": "test_user", "password": "test_pass"}
        config = InfluxDbConfig(**data)
        assert config.username == "test_user"
        assert config.password == "test_pass"

    def test_configure_v2_credentials_valid(self):
        """Test that v2 credentials (token + org) are accepted."""
        data = {"enabled": True, "token": "test_token", "org": "test_org"}
        config = InfluxDbConfig(**data)
        assert config.token == "test_token"
        assert config.org == "test_org"

    def test_configure_password_as_token(self):
        """Test that password is treated as token when no username or token specified."""
        data = {"enabled": True, "password": "my_api_token", "org": "test_org"}
        config = InfluxDbConfig(**data)
        assert config.token == "my_api_token"
        assert config.password == ""
        assert config.org == "test_org"
