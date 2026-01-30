import logging

import pytest

from sigenergy2mqtt.config.influxdb_config import InfluxDBConfiguration


class TestInfluxDBConfigCoverage:
    def test_default_values(self):
        config = InfluxDBConfiguration()
        assert config.enabled is False
        assert config.host == "127.0.0.1"
        assert config.port == 8086
        assert config.database == "sigenergy"

    def test_configure_enabled(self):
        config = InfluxDBConfiguration()
        data = {"enabled": True}
        config.configure(data)
        assert config.enabled is True

    def test_configure_all_fields(self):
        config = InfluxDBConfiguration()
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
        }
        config.configure(data)

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

    def test_configure_invalid_port(self):
        config = InfluxDBConfiguration()
        config.enabled = True
        data = {"port": 70000}  # Out of range
        with pytest.raises(ValueError, match="less than or equal to 65535"):
            config.configure(data)

    def test_configure_invalid_include(self):
        config = InfluxDBConfiguration()
        config.enabled = True
        data = {"include": "not_a_list"}
        with pytest.raises(ValueError, match="must be a list"):
            config.configure(data)

    def test_configure_invalid_exclude(self):
        config = InfluxDBConfiguration()
        config.enabled = True
        data = {"exclude": "not_a_list"}
        with pytest.raises(ValueError, match="must be a list"):
            config.configure(data)

    def test_configure_unknown_option(self):
        config = InfluxDBConfiguration()
        config.enabled = True
        data = {"unknown_key": "some_value"}
        with pytest.raises(ValueError, match="unknown option"):
            config.configure(data)

    def test_configure_not_a_dict(self):
        config = InfluxDBConfiguration()
        with pytest.raises(ValueError, match="must contain options"):
            config.configure("not_a_dict")

    def test_configure_logs_password_hidden(self, caplog):
        config = InfluxDBConfiguration()
        config.enabled = True
        data = {"password": "secret_password"}
        with caplog.at_level(logging.DEBUG):
            config.configure(data)

        assert "influxdb.password = ******" in caplog.text

    def test_configure_override_log(self, caplog):
        config = InfluxDBConfiguration()
        data = {"enabled": True}
        with caplog.at_level(logging.DEBUG):
            config.configure(data, override=True)

        assert "Applying override from env/cli" in caplog.text
