import logging
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.config.modbus_config import ModbusConfiguration  # noqa: F401


class TestConfigStaticMethods:
    """Tests for Config static helper methods."""

    def test_get_modbus_log_level_single_device(self):
        """Test get_modbus_log_level with one device."""
        with patch.object(Config, "modbus", []):
            device = MagicMock()
            device.log_level = logging.DEBUG
            Config.modbus.append(device)

            level = Config.get_modbus_log_level()

            assert level == logging.DEBUG

    def test_get_modbus_log_level_multiple_devices(self):
        """Test get_modbus_log_level returns minimum level."""
        with patch.object(Config, "modbus", []):
            device1 = MagicMock()
            device1.log_level = logging.INFO
            device2 = MagicMock()
            device2.log_level = logging.DEBUG
            device3 = MagicMock()
            device3.log_level = logging.WARNING

            Config.modbus = [device1, device2, device3]

            level = Config.get_modbus_log_level()

            # Should return minimum (DEBUG=10 < INFO=20 < WARNING=30)
            assert level == logging.DEBUG

    def test_set_modbus_log_level(self):
        """Test set_modbus_log_level sets all devices."""
        device1 = MagicMock()
        device1.log_level = logging.WARNING
        device2 = MagicMock()
        device2.log_level = logging.ERROR

        Config.modbus = [device1, device2]

        Config.set_modbus_log_level(logging.INFO)

        assert device1.log_level == logging.INFO
        assert device2.log_level == logging.INFO

    def test_version(self):
        """Test version method returns version string."""
        version = Config.version()

        assert isinstance(version, str)
        assert len(version) > 0

    def test_origin_dict(self):
        """Test origin dictionary is properly configured."""
        assert "name" in Config.origin
        assert Config.origin["name"] == "sigenergy2mqtt"
        assert "sw" in Config.origin
        assert "url" in Config.origin
        assert "github.com" in Config.origin["url"]


class TestConfigDefaults:
    """Tests for Config default values."""

    def test_default_clean(self):
        """Test default clean flag."""
        assert isinstance(Config.clean, bool)
        assert Config.clean is False

    def test_default_log_level(self):
        """Test default log level."""
        assert Config.log_level == logging.WARNING

    def test_default_metrics_enabled(self):
        """Test default metrics enabled flag."""
        assert Config.metrics_enabled is True

    def test_default_sensor_debug_logging(self):
        """Test default sensor debug logging flag."""
        assert Config.sensor_debug_logging is False

    def test_default_sanity_check_kw(self):
        """Test default sanity check value."""
        assert Config.sanity_check_default_kw == 500.0

    @pytest.mark.no_persistent_state_mock
    def test_default_persistent_state_path(self):
        """Test default persistent state path."""
        # It might be "." or an absolute path depending on environment access
        path = Config.persistent_state_path
        assert str(path) == "." or (hasattr(path, "is_absolute") and path.is_absolute())

    def test_default_ems_mode_check(self):
        """Test default ems_mode_check flag."""
        assert Config.ems_mode_check is True


class TestConfigConfiguration:
    """Tests for Config._configure method."""

    def test_configure_log_level(self):
        """Test configuring log level."""
        with patch("sigenergy2mqtt.config.config.check_log_level") as mock_check:
            mock_check.return_value = logging.INFO
            Config._configure({"log-level": "INFO"})
            assert Config.log_level == logging.INFO
            mock_check.assert_called_once_with("INFO", "log-level")

    def test_configure_consumption(self):
        """Test configuring consumption method."""
        Config._configure({"consumption": "total"})
        from sigenergy2mqtt.common import ConsumptionMethod

        assert Config.consumption == ConsumptionMethod.TOTAL

    def test_configure_sanity_check_kw(self):
        """Test configuring sanity check kW."""
        Config._configure({"sanity-check-default-kw": 100.0})
        assert Config.sanity_check_default_kw == 100.0

    def test_configure_no_metrics(self):
        """Test configuring no-metrics."""
        Config._configure({"no-metrics": True})
        assert Config.metrics_enabled is False
        Config._configure({"no-metrics": False})
        assert Config.metrics_enabled is True

    def test_configure_ems_mode_check(self):
        """Test configuring ems_mode_check."""
        Config._configure({"no-ems-mode-check": True})
        assert Config.ems_mode_check is False
        Config._configure({"no-ems-mode-check": False})
        assert Config.ems_mode_check is True

    def test_configure_locale_invalid_fallback(self, caplog):
        """Test configuring an invalid locale falls back to default."""
        Config.reset()
        from sigenergy2mqtt import i18n

        with patch("sigenergy2mqtt.i18n.get_available_locales", return_value=["en", "fr"]):
            with patch("sigenergy2mqtt.i18n.get_default_locale", return_value="en"):
                with caplog.at_level(logging.WARNING):
                    Config._configure({"locale": "de"})
                    assert Config.locale == "en"
                    assert "Invalid locale 'de' for locale, falling back to 'en'" in caplog.text


class TestConfigReload:
    """Tests for Config.reload method."""

    @patch("sigenergy2mqtt.config.config.os.getenv")
    @patch("sigenergy2mqtt.config.config.os.environ", {})
    def test_reload_with_env_overrides(self, mock_getenv):
        """Test reload with environment variable overrides."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_LOG_LEVEL

        # Mock SIGENERGY2MQTT_LOG_LEVEL env var
        with patch.dict("os.environ", {SIGENERGY2MQTT_LOG_LEVEL: "DEBUG"}):
            Config.reload()
            assert Config.log_level == logging.DEBUG

    @patch("sigenergy2mqtt.config.config.os.getenv")
    @patch("sigenergy2mqtt.config.config.os.environ", {})
    def test_reload_with_no_ems_mode_check_env(self, mock_getenv):
        """Test reload with SIGENERGY2MQTT_NO_EMS_MODE_CHECK environment variable."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_NO_EMS_MODE_CHECK

        with patch.dict("os.environ", {SIGENERGY2MQTT_NO_EMS_MODE_CHECK: "true"}):
            Config.reload()
            assert Config.ems_mode_check is False

    @patch("sigenergy2mqtt.config.config.os.environ", {})
    def test_reload_with_locale_env_invalid_fallback(self, caplog):
        """Test reload with invalid locale environment variable."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_LOCALE

        with patch.dict("os.environ", {SIGENERGY2MQTT_LOCALE: "de"}):
            with patch("sigenergy2mqtt.i18n.get_available_locales", return_value=["en", "fr"]):
                with patch("sigenergy2mqtt.i18n.get_default_locale", return_value="en"):
                    with caplog.at_level(logging.WARNING):
                        Config.reload()
                        assert Config.locale == "en"
                        assert "Invalid locale 'de' for SIGENERGY2MQTT_LOCALE, falling back to 'en'" in caplog.text

    @patch("sigenergy2mqtt.config.config.auto_discovery_scan")
    @patch("sigenergy2mqtt.config.config.os.getenv")
    def test_reload_with_auto_discovery_force(self, mock_getenv, mock_scan):
        """Test reload with auto-discovery forced."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY

        mock_getenv.side_effect = lambda k, default=None: "force" if k == SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY else default
        mock_scan.return_value = [{"host": "1.2.3.4", "port": 502}]

        # We need to mock open to avoid writing discovery cache
        with patch("builtins.open", MagicMock()):
            with patch("sigenergy2mqtt.config.config.Path.is_file", return_value=False):
                Config.reload()

        mock_scan.assert_called_once()

    def test_devices_list_exists(self):
        """Test devices list exists and is a list."""
        assert isinstance(Config.modbus, list)

    def test_sensor_overrides_dict_exists(self):
        """Test sensor overrides dict exists."""
        assert isinstance(Config.sensor_overrides, dict)


class TestConfigHomeAssistant:
    """Tests for Config.home_assistant configuration."""

    def test_home_assistant_exists(self):
        """Test home_assistant configuration object exists."""
        assert Config.home_assistant is not None

    def test_home_assistant_unique_id_prefix(self):
        """Test default unique_id_prefix."""
        # Default should exist
        assert hasattr(Config.home_assistant, "unique_id_prefix")

    def test_home_assistant_entity_id_prefix(self):
        """Test default entity_id_prefix."""
        assert hasattr(Config.home_assistant, "entity_id_prefix")


class TestConfigMqtt:
    """Tests for Config.mqtt configuration."""

    def test_mqtt_exists(self):
        """Test mqtt configuration object exists."""
        assert Config.mqtt is not None

    def test_mqtt_has_broker(self):
        """Test mqtt has broker attribute."""
        assert hasattr(Config.mqtt, "broker")

    def test_mqtt_has_port(self):
        """Test mqtt has port attribute."""
        assert hasattr(Config.mqtt, "port")


class TestConfigPvOutput:
    """Tests for Config.pvoutput configuration."""

    def test_pvoutput_exists(self):
        """Test pvoutput configuration object exists."""
        assert Config.pvoutput is not None

    def test_pvoutput_has_enabled(self):
        """Test pvoutput has enabled attribute."""
        assert hasattr(Config.pvoutput, "enabled")
