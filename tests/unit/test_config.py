import logging
import os
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401
from pydantic import ValidationError

from sigenergy2mqtt.config import Config, active_config
from sigenergy2mqtt.config.config import _swap_active_config
from sigenergy2mqtt.config.settings import ModbusConfig, Settings


class TestConfigStaticMethods:
    """Tests for Config static helper methods."""

    def test_get_modbus_log_level_single_device(self):
        """Test get_modbus_log_level with one device."""
        original_modbus = list(active_config.modbus)
        try:
            device = MagicMock()
            device.log_level = logging.DEBUG
            active_config.modbus.clear()
            active_config.modbus.append(device)

            level = active_config.get_modbus_log_level()

            assert level == logging.DEBUG
        finally:
            active_config.modbus.clear()
            active_config.modbus.extend(original_modbus)

    def test_get_modbus_log_level_multiple_devices(self):
        """Test get_modbus_log_level returns minimum level."""
        original_modbus = list(active_config.modbus)
        try:
            device1 = MagicMock()
            device1.log_level = logging.INFO
            device2 = MagicMock()
            device2.log_level = logging.DEBUG
            device3 = MagicMock()
            device3.log_level = logging.WARNING

            active_config.modbus.clear()
            active_config.modbus.extend([device1, device2, device3])

            level = active_config.get_modbus_log_level()

            # Should return minimum (DEBUG=10 < INFO=20 < WARNING=30)
            assert level == logging.DEBUG
        finally:
            active_config.modbus.clear()
            active_config.modbus.extend(original_modbus)

    def test_set_modbus_log_level(self):
        """Test set_modbus_log_level sets all devices."""
        with _swap_active_config(Config()) as cfg:
            device1 = MagicMock()
            device1.log_level = logging.WARNING
            device2 = MagicMock()
            device2.log_level = logging.ERROR

            cfg._settings = MagicMock()
            cfg._settings.modbus = [device1, device2]

            cfg.set_modbus_log_level(logging.INFO)

            assert device1.log_level == logging.INFO
            assert device2.log_level == logging.INFO

    def test_version(self):
        """Test version method returns version string."""
        version = active_config.version

        assert isinstance(version, str)
        assert len(version) > 0

    def test_origin_dict(self):
        """Test origin dictionary is properly configured."""
        assert "name" in active_config.origin
        assert active_config.origin["name"] == "sigenergy2mqtt"
        assert "sw" in active_config.origin
        assert "url" in active_config.origin
        assert "github.com" in active_config.origin["url"]


class TestConfigDefaults:
    """Tests for Config default values."""

    def test_default_clean(self):
        """Test default clean flag."""
        assert isinstance(active_config.clean, bool)
        assert active_config.clean is False

    def test_default_log_level(self):
        """Test default log level."""
        assert active_config.log_level == logging.WARNING

    def test_default_metrics_enabled(self):
        """Test default metrics enabled flag."""
        assert active_config.metrics_enabled is True

    def test_default_sensor_debug_logging(self):
        """Test default sensor debug logging flag."""
        assert active_config.sensor_debug_logging is False

    def test_default_sanity_check_kw(self):
        """Test default sanity check value."""
        assert active_config.sanity_check_default_kw == 500.0

    @pytest.mark.no_persistent_state_mock
    def test_default_persistent_state_path(self):
        """Test default persistent state path."""
        # It might be "." or an absolute path depending on environment access
        path = active_config.persistent_state_path
        assert str(path) == "." or (hasattr(path, "is_absolute") and path.is_absolute())

    def test_default_ems_mode_check(self):
        """Test default ems_mode_check flag."""
        assert active_config.ems_mode_check is True

    def test_default_repeated_state_publish_interval(self):
        """Test default repeated_state_publish_interval."""
        assert active_config.repeated_state_publish_interval == 0


class TestConfigSettings:
    """Tests for Settings-based configuration via constructor."""

    def test_settings_log_level(self):
        """Test configuring log level via Settings."""
        s = Settings(log_level="INFO", modbus=[ModbusConfig(host="localhost")])
        assert s.log_level == logging.INFO

    def test_settings_consumption(self):
        """Test configuring consumption method via Settings."""
        from sigenergy2mqtt.common import ConsumptionMethod

        s = Settings(consumption="total", modbus=[ModbusConfig(host="localhost")])
        assert s.consumption == ConsumptionMethod.TOTAL

    def test_settings_consumption_default_when_omitted(self):
        """Test default consumption method when omitted from Settings."""
        from sigenergy2mqtt.common import ConsumptionMethod

        s = Settings(modbus=[ModbusConfig(host="localhost")])
        assert s.consumption == ConsumptionMethod.TOTAL

    def test_settings_sanity_check_kw(self):
        """Test configuring sanity check kW via Settings."""
        s = Settings(sanity_check_default_kw=100.0, modbus=[ModbusConfig(host="localhost")])
        assert s.sanity_check_default_kw == 100.0

    def test_settings_metrics_enabled(self):
        """Test configuring metrics_enabled via Settings."""
        s = Settings(metrics_enabled=False, modbus=[ModbusConfig(host="localhost")])
        assert s.metrics_enabled is False

        s2 = Settings(metrics_enabled=True, modbus=[ModbusConfig(host="localhost")])
        assert s2.metrics_enabled is True

    def test_settings_ems_mode_check(self):
        """Test configuring ems_mode_check via Settings."""
        s = Settings(ems_mode_check=False, modbus=[ModbusConfig(host="localhost", **{"read-write": True})])
        assert s.ems_mode_check is False

    def test_settings_repeated_state_publish_interval(self):
        """Test configuring repeated-state-publish-interval via Settings."""
        s = Settings(repeated_state_publish_interval=10, modbus=[ModbusConfig(host="localhost")])
        assert s.repeated_state_publish_interval == 10

    def test_settings_language_invalid_fallback(self, caplog):
        """Test that invalid language falls back to default."""
        with patch("sigenergy2mqtt.i18n.get_available_translations", return_value=["en", "fr"]):
            with patch("sigenergy2mqtt.i18n.get_default_language", return_value="en"):
                with caplog.at_level(logging.WARNING):
                    s = Settings(language="de", modbus=[ModbusConfig(host="localhost")])
                    assert s.language == "en"
                    assert "Invalid language 'de'" in caplog.text


class TestConfigReload:
    """Tests for active_config.reload method."""

    def test_reload_with_env_overrides(self):
        """Test reload with environment variable overrides."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_LOG_LEVEL, SIGENERGY2MQTT_MODBUS_HOST

        with _swap_active_config(Config()) as cfg:
            with patch.dict("os.environ", {SIGENERGY2MQTT_LOG_LEVEL: "DEBUG", SIGENERGY2MQTT_MODBUS_HOST: "localhost"}, clear=True):
                cfg.reload()
                assert cfg.log_level == logging.DEBUG

    def test_reload_with_no_ems_mode_check_env(self):
        """Test reload with SIGENERGY2MQTT_NO_EMS_MODE_CHECK environment variable."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_MODBUS_HOST, SIGENERGY2MQTT_NO_EMS_MODE_CHECK

        with _swap_active_config(Config()) as cfg:
            with patch.dict(
                "os.environ",
                {
                    SIGENERGY2MQTT_NO_EMS_MODE_CHECK: "true",
                    SIGENERGY2MQTT_MODBUS_HOST: "localhost",
                    # ems_mode_check=False requires read-write=True on all devices
                    "SIGENERGY2MQTT_MODBUS_READ_WRITE": "true",
                },
                clear=True,
            ):
                cfg.reload()
                assert cfg.ems_mode_check is False

    def test_reload_with_language_env_invalid_fallback(self, caplog):
        """Test reload with invalid language environment variable."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_LANGUAGE, SIGENERGY2MQTT_MODBUS_HOST

        with _swap_active_config(Config()) as cfg:
            with patch.dict("os.environ", {SIGENERGY2MQTT_LANGUAGE: "de", SIGENERGY2MQTT_MODBUS_HOST: "localhost"}, clear=True):
                with patch("sigenergy2mqtt.i18n.get_available_translations", return_value=["en", "fr"]):
                    with patch("sigenergy2mqtt.i18n.get_default_language", return_value="en"):
                        with caplog.at_level(logging.WARNING):
                            cfg.reload()
                            assert cfg.language == "en"
                            assert "Invalid language 'de'" in caplog.text

    @patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[{"host": "1.2.3.4", "port": 502}])
    @patch("sigenergy2mqtt.config.config.os.getenv")
    def test_reload_with_auto_discovery_force(self, mock_getenv, mock_run_auto_discovery):
        """Test reload with auto-discovery forced."""
        from sigenergy2mqtt.config.const import SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY

        with _swap_active_config(Config()) as cfg:
            mock_getenv.side_effect = lambda k, default=None: "force" if k == SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY else default

            # We need to mock open properly to avoid infinite loops in ruamel.yaml
            from unittest.mock import mock_open

            m = mock_open(read_data="- host: 1.2.3.4\n  port: 502\n")
            with patch("builtins.open", m):
                with patch("sigenergy2mqtt.config.config.Path.is_file", return_value=True):
                    cfg.reload()
            mock_run_auto_discovery.assert_called_once()

    @patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[{"host": "2.3.4.5", "port": 502}])
    def test_reload_triggers_auto_discovery_when_no_hosts_configured(self, mock_run_auto_discovery):
        """Test reload triggers auto-discovery if neither env nor YAML have modbus configured."""
        with _swap_active_config(Config()) as cfg:
            with patch.dict("os.environ", {}, clear=True):
                cfg.reload()
            mock_run_auto_discovery.assert_called_once()

    @patch("sigenergy2mqtt.config.config.Config._run_auto_discovery", return_value=[{"host": "2.3.4.5", "port": 502}])
    @patch("sigenergy2mqtt.config.sources.RuamelYamlSettingsSource.__call__", return_value={"modbus": [{"port": 502}]})
    def test_reload_triggers_auto_discovery_yaml_no_host(self, mock_yaml, mock_run_auto_discovery):
        """Test reload triggers auto-discovery if YAML possesses modbus array without a host."""
        with _swap_active_config(Config()) as cfg:
            with patch.dict("os.environ", {}, clear=True):
                with patch("sigenergy2mqtt.config.config.Path.exists", return_value=True):
                    cfg._source = "dummy.yaml"
                    try:
                        cfg.reload()
                    except ValidationError:
                        pass
            mock_run_auto_discovery.assert_called_once()

    def test_devices_list_exists(self):
        """Test devices list exists and is a list."""
        assert isinstance(active_config.modbus, list)

    def test_sensor_overrides_dict_exists(self):
        """Test sensor overrides dict exists."""
        assert isinstance(active_config.sensor_overrides, dict)


class TestConfigHomeAssistant:
    """Tests for active_config.home_assistant configuration."""

    def test_home_assistant_exists(self):
        """Test home_assistant configuration object exists."""
        assert active_config.home_assistant is not None

    def test_home_assistant_unique_id_prefix(self):
        """Test default unique_id_prefix."""
        # Default should exist
        assert hasattr(active_config.home_assistant, "unique_id_prefix")

    def test_home_assistant_entity_id_prefix(self):
        """Test default entity_id_prefix."""
        assert hasattr(active_config.home_assistant, "entity_id_prefix")

    def test_home_assistant_local_modbus_naming_validation(self):
        """Test validation fails when sigenergy_local_modbus_naming=True and entity_id_prefix is not 'sigen'."""
        from sigenergy2mqtt.config.config import ConfigurationError

        with pytest.raises(ConfigurationError, match="home-assistant.entity-id-prefix must be 'sigen'"):
            Settings(home_assistant={"sigenergy-local-modbus-naming": True, "entity-id-prefix": "other"}, modbus=[{"host": "localhost"}])


class TestConfigMqtt:
    """Tests for active_config.mqtt configuration."""

    def test_mqtt_exists(self):
        """Test mqtt configuration object exists."""
        assert active_config.mqtt is not None

    def test_mqtt_has_broker(self):
        """Test mqtt has broker attribute."""
        assert hasattr(active_config.mqtt, "broker")

    def test_mqtt_has_port(self):
        """Test mqtt has port attribute."""
        assert hasattr(active_config.mqtt, "port")


class TestConfigPvOutput:
    """Tests for active_config.pvoutput configuration."""

    def test_pvoutput_exists(self):
        """Test pvoutput configuration object exists."""
        assert active_config.pvoutput is not None

    def test_pvoutput_has_enabled(self):
        """Test pvoutput has enabled attribute."""
        assert hasattr(active_config.pvoutput, "enabled")


class TestConfigCoverageAugmentation:
    def test_init_persistent_state_exception(self):
        with patch("sigenergy2mqtt.config.config._create_persistent_state_path", side_effect=Exception("mocked error")):
            cfg = Config()
            assert str(cfg.persistent_state_path) == "."

    def test_getattr_settings_uninitialized(self):
        cfg = Config()
        cfg._settings = None
        with pytest.raises(AttributeError):
            _ = cfg.some_random_attribute

    def test_get_modbus_log_level_no_settings(self):
        cfg = Config()
        cfg._settings = None
        assert cfg.get_modbus_log_level() == logging.WARNING

    def test_get_modbus_log_level_no_modbus_devices(self):
        cfg = Config()
        cfg._settings = MagicMock()
        cfg._settings.modbus = []
        assert cfg.get_modbus_log_level() == logging.WARNING

    def test_set_modbus_log_level_no_settings(self):
        cfg = Config()
        cfg._settings = None
        with pytest.raises(AttributeError):
            cfg.set_modbus_log_level(logging.DEBUG)

    @patch("sigenergy2mqtt.config.config.asyncio.run")
    def test_run_auto_discovery_exception(self, mock_run):
        def side_effect(coro, **kwargs):
            if hasattr(coro, "close"):
                coro.close()
            raise Exception("Mocked Asyncio Error")

        mock_run.side_effect = side_effect
        cfg = Config()
        result = cfg._run_auto_discovery(502, 0.5, 0.25, 3)
        assert result == []
        # Ensure all captured coroutines are closed in case side_effect wasn't called (unlikely)
        for call in mock_run.call_args_list:
            c = call[0][0]
            if hasattr(c, "close"):
                c.close()

    @patch("sigenergy2mqtt.config.config.asyncio.get_running_loop")
    def test_run_auto_discovery_with_running_loop_success(self, mock_get_loop):
        # We simulate that a loop is running
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        with patch("sigenergy2mqtt.config.config.asyncio.run_coroutine_threadsafe") as mock_threadsafe:
            mock_future = MagicMock()
            mock_future.result.return_value = [{"host": "127.0.0.1", "port": 502}]
            mock_threadsafe.return_value = mock_future

            async def mock_scan_side_effect(*args, **kwargs):
                return []

            with patch("sigenergy2mqtt.config.config.auto_discovery_scan", side_effect=mock_scan_side_effect) as mock_scan:  # noqa: F841
                cfg = Config()
                result = cfg._run_auto_discovery(502, 0.5, 0.25, 3)
                assert result == [{"host": "127.0.0.1", "port": 502}]
                # Close all coroutines to avoid RuntimeWarning
                for call in mock_threadsafe.call_args_list:
                    coro = call[0][0]
                    if hasattr(coro, "close"):
                        coro.close()

    @patch("sigenergy2mqtt.config.config.asyncio.get_running_loop")
    def test_run_auto_discovery_with_running_loop_timeout(self, mock_get_loop):
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        with patch("sigenergy2mqtt.config.config.asyncio.run_coroutine_threadsafe") as mock_threadsafe:
            mock_future = MagicMock()
            mock_future.result.side_effect = TimeoutError("Timed out")
            mock_threadsafe.return_value = mock_future

            async def mock_scan_side_effect(*args, **kwargs):
                return []

            with patch("sigenergy2mqtt.config.config.auto_discovery_scan", side_effect=mock_scan_side_effect) as mock_scan:  # noqa: F841
                cfg = Config()
                result = cfg._run_auto_discovery(502, 0.5, 0.25, 3)
                assert result == []
                mock_future.cancel.assert_called_once()
                # Close all coroutines to avoid RuntimeWarning
                for call in mock_threadsafe.call_args_list:
                    coro = call[0][0]
                    if hasattr(coro, "close"):
                        coro.close()

    @patch("sigenergy2mqtt.config.config.asyncio.get_running_loop")
    def test_run_auto_discovery_with_running_loop_generic_exception(self, mock_get_loop):
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop

        with patch("sigenergy2mqtt.config.config.asyncio.run_coroutine_threadsafe") as mock_threadsafe:
            mock_future = MagicMock()
            mock_future.result.side_effect = Exception("Generic")
            mock_threadsafe.return_value = mock_future

            async def mock_scan_side_effect(*args, **kwargs):
                return []

            with patch("sigenergy2mqtt.config.config.auto_discovery_scan", side_effect=mock_scan_side_effect) as mock_scan:  # noqa: F841
                cfg = Config()
                result = cfg._run_auto_discovery(502, 0.5, 0.25, 3)
                assert result == []
                # Close all coroutines to avoid RuntimeWarning
                for call in mock_threadsafe.call_args_list:
                    coro = call[0][0]
                    if hasattr(coro, "close"):
                        coro.close()

    @patch("sigenergy2mqtt.config.config.time.time", return_value=1000000000.0)
    def test_clean_stale_files_unlink_exception(self, mock_time, tmp_path, caplog):
        from sigenergy2mqtt.config.config import _clean_stale_files

        # 1. Setup stale file
        stale_file = tmp_path / "stale.txt"
        stale_file.touch()
        os.utime(stale_file, (100.0, 100.0))

        # 2. Setup subdir (to be ignored)
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        # 3. Test PermissionError handling
        with patch("sigenergy2mqtt.config.config.Path.unlink", side_effect=PermissionError("Mock Permission Denied")):
            _clean_stale_files(tmp_path)
            assert "Failed to remove stale state file" in caplog.text
            assert "Mock Permission Denied" in caplog.text

        caplog.clear()  # Clear logs between checks

        # 4. Test OSError handling
        with patch("sigenergy2mqtt.config.config.Path.unlink", side_effect=OSError("Mock OS Error")):
            _clean_stale_files(tmp_path)
            assert "Failed to remove stale state file" in caplog.text
            assert "Mock OS Error" in caplog.text

    def test_setup_logging_tty(self):
        from sigenergy2mqtt.config.config import _setup_logging

        with patch("sigenergy2mqtt.config.config.os.isatty", return_value=True):
            _setup_logging()

    def test_config_proxy_methods(self):
        from sigenergy2mqtt.config.config import _ConfigProxy

        cfg = Config()
        proxy = _ConfigProxy(cfg)

        cfg.test_attr = "hello"
        assert proxy.test_attr == "hello"

        proxy.test_attr = "world"
        assert proxy.test_attr == "world"
        assert cfg.test_attr == "world"

        del proxy.test_attr
        assert not hasattr(cfg, "test_attr")

        assert repr(proxy).startswith("<ConfigProxy for")
        assert "load" in dir(proxy)

    def test_swap_active_config_no_proxy(self):
        import sigenergy2mqtt.config.config as conf_module
        from sigenergy2mqtt.config.config import _swap_active_config

        original = conf_module.active_config
        conf_module.active_config = Config()  # Not a proxy

        try:
            new_cfg = Config()
            with _swap_active_config(new_cfg) as yielded_cfg:
                assert yielded_cfg is new_cfg
                assert conf_module.active_config is new_cfg
        finally:
            conf_module.active_config = original

    @patch("sigenergy2mqtt.config.config.Config.reload")
    def test_load_config(self, mock_reload):
        cfg = Config()
        mock_reload.reset_mock()
        cfg.load("test_file.yaml")
        assert cfg._source == "test_file.yaml"
        mock_reload.assert_called_once()

    @patch("sigenergy2mqtt.config.config.Config.reload")
    def test_reset_config(self, mock_reload):
        cfg = Config()
        cfg._source = "test"
        cfg.reset()
        assert cfg._source is None
        assert isinstance(cfg._settings, Settings)

    def test_reload_with_exception_in_init(self):
        with patch("sigenergy2mqtt.config.config.Config.reload", side_effect=Exception("mock initialization error")):
            cfg = Config()
            assert cfg._source is None

    def test_setup_logging_level_from_env(self):
        from sigenergy2mqtt.config.config import _setup_logging

        with patch.dict("os.environ", {"SIGENERGY2MQTT_LOG_LEVEL": "DEBUG"}):
            _setup_logging()
            assert logging.getLogger().level == logging.DEBUG


class TestSampleConfig:
    """Tests for the sample configuration file."""

    def test_sample_yaml_validates(self):
        """Test that the sample configuration file validates against the Settings model."""
        sample_path = os.path.join("resources", "configuration", "sigenergy2mqtt.yaml")
        # Ensure the file exists
        assert os.path.exists(sample_path)

        # Loading the sample file should NOT raise a ValidationError
        # We use a swap to avoid affecting global state.
        s = Settings(yaml_file_arg=sample_path)

        # Verify specific fields from the sample (based on recent user edits)
        assert s.pvoutput.api_key == "cafefacefeeddeadbeef01234567890abcdeface"
        assert s.pvoutput.system_id == "testing"
        assert s.influxdb.enabled is True
        assert s.influxdb.username == "homeassistant"

        # Verify the negated flags were handled
        # The sample has 'no-ems-mode-check: false' and 'no-metrics: false'
        # These should be removed from the dict and ems_mode_check / metrics_enabled
        # should be set to True (since not val is True).
        assert s.ems_mode_check is True
        assert s.metrics_enabled is True


class TestConfigYamlString:
    def test_config_str_redacts_sensitive_by_default(self):
        with _swap_active_config(Config()) as cfg:
            cfg._settings = Settings(
                modbus=[ModbusConfig(host="localhost")],
                mqtt={"anonymous": False, "username": "user1", "password": "secretpwd"},
                pvoutput={"enabled": True, "api-key": "ABC123", "system-id": "12345"},
            )
            cfg.validate_show_credentials = False

            text = str(cfg)
            assert "[REDACTED]" in text
            assert "secretpwd" not in text
            assert "ABC123" not in text

    def test_config_str_shows_sensitive_when_enabled(self):
        with _swap_active_config(Config()) as cfg:
            cfg._settings = Settings(
                modbus=[ModbusConfig(host="localhost")],
                mqtt={"anonymous": False, "username": "user1", "password": "secretpwd"},
                pvoutput={"enabled": True, "api-key": "ABC123", "system-id": "12345"},
            )
            cfg.validate_show_credentials = True

            text = str(cfg)
            assert "secretpwd" in text
            assert "ABC123" in text
