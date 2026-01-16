"""Comprehensive test coverage for sigenergy2mqtt/devices/smartport/enphase.py"""

import asyncio
import logging
import os
import time
import xml.etree.ElementTree as xml
from typing import Any, cast
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
import requests

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.smartport.enphase import (
    EnphaseCurrent,
    EnphaseDailyPVEnergy,
    EnphaseFrequency,
    EnphaseLifetimePVEnergy,
    EnphasePowerFactor,
    EnphasePVPower,
    EnphaseReactivePower,
    EnphaseVoltage,
    SmartPort,
)
from sigenergy2mqtt.sensors.base import Sensor

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Set up minimal Config mock for EnphasePVPower initialization."""
    orig_modbus = Config.modbus

    class SI:
        realtime = 5

    class D:
        scan_interval = SI()
        registers = None

    Config.modbus = [D()]
    yield
    Config.modbus = orig_modbus


@pytest.fixture
def pv_power_sensor(mock_config, tmp_path, monkeypatch):
    """Create an EnphasePVPower sensor with mocked config."""
    monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
    return EnphasePVPower(0, "TEST123", "192.168.1.100", "user@example.com", "password123")


def make_values(val_dict):
    """Create a values list with the given dictionary as the solar data."""
    return [(time.time(), 0, val_dict)]


# =============================================================================
# EnphasePVPower Tests
# =============================================================================


class TestEnphasePVPowerInit:
    """Tests for EnphasePVPower.__init__"""

    def test_init_creates_sensor_with_correct_attributes(self, mock_config, tmp_path, monkeypatch):
        """Test that EnphasePVPower initializes with correct attributes."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        sensor = EnphasePVPower(0, "SN123", "host", "user", "pass")

        assert sensor._serial_number == "SN123"
        assert sensor._host == "host"
        assert sensor._username == "user"
        assert sensor._password == "pass"
        assert sensor._token == ""
        assert sensor._failover_initiated is False
        assert sensor._max_failures == 5
        assert sensor._max_failures_retry_interval == 30
        assert sensor["enabled_by_default"] is True

    def test_init_with_debug_logging(self, mock_config, tmp_path, monkeypatch):
        """Test debug logging setup during init."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        monkeypatch.setattr(Config, "log_level", logging.DEBUG)

        sensor = EnphasePVPower(0, "SN123", "host", "user", "pass")
        sensor.debug_logging = False  # simulate condition on line 49

        # The sensor should still be created successfully
        assert sensor._serial_number == "SN123"


class TestEnphasePVPowerGetAttributes:
    """Tests for EnphasePVPower.get_attributes"""

    def test_get_attributes_includes_source(self, pv_power_sensor):
        """Test that get_attributes includes the 'source' key."""
        attrs = pv_power_sensor.get_attributes()
        assert "source" in attrs
        assert attrs["source"] == "Enphase Envoy API"


class TestEnphasePVPowerGetToken:
    """Tests for EnphasePVPower.get_token"""

    def test_get_token_returns_cached_token(self, pv_power_sensor):
        """Test that cached token is returned when available."""
        pv_power_sensor._token = "cached_token_123"

        token = pv_power_sensor.get_token()

        assert token == "cached_token_123"

    def test_get_token_loads_from_file(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test loading token from file when not cached."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        token_file.write_text("file_token_456")

        pv_power_sensor._token = ""
        token = pv_power_sensor.get_token()

        assert token == "file_token_456"
        assert pv_power_sensor._token == "file_token_456"

    def test_get_token_generates_new_token(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test generating a new token when none cached or in file."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = ""

        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "new_generated_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [mock_login_response, mock_token_response]
            token = pv_power_sensor.get_token()

        assert token == "new_generated_token"
        assert pv_power_sensor._token == "new_generated_token"

        # Verify token was saved to file
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        assert token_file.exists()
        assert token_file.read_text() == "new_generated_token"

    def test_get_token_reauthenticate_forces_new_token(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test that reauthenticate=True forces new token generation."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "old_cached_token"

        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "reauthenticated_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [mock_login_response, mock_token_response]
            token = pv_power_sensor.get_token(reauthenticate=True)

        assert token == "reauthenticated_token"

    def test_load_token_handles_empty_file(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test loading token from an empty file returns empty string."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        token_file.write_text("")

        pv_power_sensor._token = ""

        # Need to generate new token since file is empty
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "new_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [mock_login_response, mock_token_response]
            token = pv_power_sensor.get_token()

        assert token == "new_token"


class TestEnphasePVPowerUpdateInternalState:
    """Tests for EnphasePVPower._update_internal_state"""

    @pytest.mark.asyncio
    async def test_update_internal_state_success(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test successful API response updates state."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = [{"activePower": 2500.5, "actEnergyDlvd": 1000}]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            result = await pv_power_sensor._update_internal_state()

        assert result is True
        assert pv_power_sensor._states[-1][1] == 2500.5

    @pytest.mark.asyncio
    async def test_update_internal_state_clamps_negative_power(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test that negative power values are clamped to 0."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = [{"activePower": -100, "actEnergyDlvd": 1000}]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            result = await pv_power_sensor._update_internal_state()

        assert result is True
        assert pv_power_sensor._states[-1][1] == 0.0

    @pytest.mark.asyncio
    async def test_update_internal_state_401_reauthenticates(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test 401 response triggers reauthentication."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "expired_token"

        mock_401_response = MagicMock()
        mock_401_response.status_code = 401
        mock_401_response.__enter__ = lambda s: s
        mock_401_response.__exit__ = lambda s, *args: None

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.elapsed.total_seconds.return_value = 0.5
        mock_success_response.json.return_value = [{"activePower": 1000, "actEnergyDlvd": 500}]
        mock_success_response.__enter__ = lambda s: s
        mock_success_response.__exit__ = lambda s, *args: None

        # Mock token generation
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "new_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        call_count = [0]

        def mock_get(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_401_response
            return mock_success_response

        with patch("requests.get", side_effect=mock_get):
            with patch("requests.post", side_effect=[mock_login_response, mock_token_response]):
                result = await pv_power_sensor._update_internal_state()

        assert result is True

    @pytest.mark.asyncio
    async def test_update_internal_state_non_200_raises(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test non-200 response raises exception."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(Exception, match="Failed to connect"):
                await pv_power_sensor._update_internal_state()

    @pytest.mark.asyncio
    async def test_update_internal_state_json_error(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test JSON parsing error is handled."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(ValueError, match="Invalid JSON"):
                await pv_power_sensor._update_internal_state()

    @pytest.mark.asyncio
    async def test_update_internal_state_request_exception_failover(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test request exception triggers failover after max failures."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"
        pv_power_sensor._failures = 4  # one less than max
        pv_power_sensor._failover_initiated = False

        # Add a mock TotalPVPower derived sensor with failover method
        mock_derived = MagicMock()
        mock_derived.failover.return_value = True
        pv_power_sensor._derived_sensors["TotalPVPower"] = mock_derived

        with patch("requests.get", side_effect=requests.exceptions.RequestException("Network error")):
            result = await pv_power_sensor._update_internal_state()

        mock_derived.failover.assert_called_once_with(pv_power_sensor)

    @pytest.mark.asyncio
    async def test_update_internal_state_request_exception_no_failover(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test request exception without TotalPVPower returns True after max failures."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"
        pv_power_sensor._failures = 4  # one less than max
        pv_power_sensor._failover_initiated = False
        pv_power_sensor._derived_sensors = {}  # No TotalPVPower

        with patch("requests.get", side_effect=requests.exceptions.RequestException("Network error")):
            result = await pv_power_sensor._update_internal_state()

        assert result is True

    @pytest.mark.asyncio
    async def test_update_internal_state_request_exception_reraises_before_max(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test request exception re-raises before max failures."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"
        pv_power_sensor._failures = 0  # Well below max
        pv_power_sensor._failover_initiated = False

        with patch("requests.get", side_effect=requests.exceptions.RequestException("Network error")):
            with pytest.raises(requests.exceptions.RequestException):
                await pv_power_sensor._update_internal_state()


# =============================================================================
# Derived Sensor get_attributes Tests
# =============================================================================


class TestDerivedSensorGetAttributes:
    """Tests for get_attributes methods on derived sensors."""

    def test_enphase_lifetime_get_attributes(self):
        """Test EnphaseLifetimePVEnergy.get_attributes includes source."""
        sensor = EnphaseLifetimePVEnergy(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_daily_get_attributes(self, mock_config, tmp_path, monkeypatch):
        """Test EnphaseDailyPVEnergy.get_attributes includes source."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        lifetime = EnphaseLifetimePVEnergy(0, "SN123")
        sensor = EnphaseDailyPVEnergy(0, "SN123", lifetime)
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_current_get_attributes(self):
        """Test EnphaseCurrent.get_attributes includes source."""
        sensor = EnphaseCurrent(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_frequency_get_attributes(self):
        """Test EnphaseFrequency.get_attributes includes source."""
        sensor = EnphaseFrequency(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_power_factor_get_attributes(self):
        """Test EnphasePowerFactor.get_attributes includes source."""
        sensor = EnphasePowerFactor(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_reactive_power_get_attributes(self):
        """Test EnphaseReactivePower.get_attributes includes source."""
        sensor = EnphaseReactivePower(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"

    def test_enphase_voltage_get_attributes(self):
        """Test EnphaseVoltage.get_attributes includes source."""
        sensor = EnphaseVoltage(0, "SN123")
        attrs = sensor.get_attributes()
        assert attrs["source"] == "Enphase Envoy API when EnphasePVPower derived"


# =============================================================================
# SmartPort Device Tests
# =============================================================================


class TestSmartPort:
    """Tests for SmartPort device initialization."""

    def test_get_text_with_element(self):
        """Test _get_text returns element text when present."""
        root = xml.fromstring("<root><device><sn>123456</sn></device></root>")
        result = SmartPort._get_text(root, "./device/sn")
        assert result == "123456"

    def test_get_text_missing_element(self):
        """Test _get_text returns empty string when element missing."""
        root = xml.fromstring("<root><device></device></root>")
        result = SmartPort._get_text(root, "./device/sn")
        assert result == ""

    def test_get_text_empty_element(self):
        """Test _get_text returns empty string when element has no text."""
        root = xml.fromstring("<root><device><sn></sn></device></root>")
        result = SmartPort._get_text(root, "./device/sn")
        assert result == ""

    def test_smartport_testing_mode(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort initialization in testing mode."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = True
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        smartport = SmartPort(0, MockModuleConfig())

        assert smartport["sn"] == "123456789012"
        assert "Envoy-S" in str(smartport["mdl_id"])

    def test_smartport_normal_init_success(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort initialization with mocked HTTP response."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = False
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <envoy_info>
            <device>
                <sn>ABC123456789</sn>
                <pn>Envoy-S-Metered</pn>
                <software>D7.1.2</software>
            </device>
        </envoy_info>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__enter__ = lambda s: s
        mock_session.__exit__ = lambda s, *args: None

        with patch("requests.Session", return_value=mock_session):
            smartport = SmartPort(0, MockModuleConfig())

        assert smartport["sn"] == "ABC123456789"

    def test_smartport_unsupported_firmware_raises(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort raises on unsupported firmware."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = False
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <envoy_info>
            <device>
                <sn>ABC123</sn>
                <pn>Envoy-S</pn>
                <software>D5.0.0</software>
            </device>
        </envoy_info>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__enter__ = lambda s: s
        mock_session.__exit__ = lambda s, *args: None

        with patch("requests.Session", return_value=mock_session):
            with pytest.raises(AssertionError, match="Unsupported Enphase Envoy firmware"):
                SmartPort(0, MockModuleConfig())

    def test_smartport_retries_on_connection_error(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort retries on connection errors."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        # Speed up test by patching sleep
        monkeypatch.setattr("sigenergy2mqtt.devices.smartport.enphase.sleep", lambda x: None)

        class MockModuleConfig:
            testing = False
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_session.__enter__ = lambda s: s
        mock_session.__exit__ = lambda s, *args: None

        with patch("requests.Session", return_value=mock_session):
            with pytest.raises(Exception, match="Unable to initialise.*after 3 attempts"):
                SmartPort(0, MockModuleConfig())

        # Should have been called 3 times (retries)
        assert mock_session.get.call_count == 3

    def test_smartport_retries_on_non_200_response(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort retries on non-200 responses."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        monkeypatch.setattr("sigenergy2mqtt.devices.smartport.enphase.sleep", lambda x: None)

        class MockModuleConfig:
            testing = False
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__enter__ = lambda s: s
        mock_session.__exit__ = lambda s, *args: None

        with patch("requests.Session", return_value=mock_session):
            with pytest.raises(Exception, match="Unable to initialise.*after 3 attempts"):
                SmartPort(0, MockModuleConfig())

    def test_smartport_d8_firmware_supported(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort supports D8 firmware."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = False
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <envoy_info>
            <device>
                <sn>XYZ789</sn>
                <pn>IQ-Envoy</pn>
                <software>D8.2.1</software>
            </device>
        </envoy_info>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = xml_response.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__enter__ = lambda s: s
        mock_session.__exit__ = lambda s, *args: None

        with patch("requests.Session", return_value=mock_session):
            smartport = SmartPort(0, MockModuleConfig())

        assert smartport["sn"] == "XYZ789"

    def test_smartport_plant_index_naming(self, mock_config, tmp_path, monkeypatch):
        """Test SmartPort name varies with plant_index."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = True
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        smartport0 = SmartPort(0, MockModuleConfig())
        smartport1 = SmartPort(1, MockModuleConfig())

        assert "Smart-Port" in smartport0["name"]
        assert "Plant 2" in smartport1["name"] or "Smart-Port" in smartport1["name"]


# =============================================================================
# Additional Tests for Missing Coverage
# =============================================================================


class TestDerivedSensorSetSourceValuesWrongSensor:
    """Tests for set_source_values rejection with wrong sensor types."""

    def test_enphase_current_rejects_wrong_sensor(self):
        """Test EnphaseCurrent.set_source_values rejects non-EnphasePVPower."""
        sensor = EnphaseCurrent(0, "SN123")

        class WrongSensor:
            pass

        result = sensor.set_source_values(cast(Sensor, WrongSensor()), make_values({"current": 10}))
        assert result is False

    def test_enphase_frequency_rejects_wrong_sensor(self):
        """Test EnphaseFrequency.set_source_values rejects non-EnphasePVPower."""
        sensor = EnphaseFrequency(0, "SN123")

        class WrongSensor:
            pass

        result = sensor.set_source_values(cast(Sensor, WrongSensor()), make_values({"freq": 50}))
        assert result is False

    def test_enphase_power_factor_rejects_wrong_sensor(self):
        """Test EnphasePowerFactor.set_source_values rejects non-EnphasePVPower."""
        sensor = EnphasePowerFactor(0, "SN123")

        class WrongSensor:
            pass

        result = sensor.set_source_values(cast(Sensor, WrongSensor()), make_values({"pwrFactor": 0.9}))
        assert result is False

    def test_enphase_reactive_power_rejects_wrong_sensor(self):
        """Test EnphaseReactivePower.set_source_values rejects non-EnphasePVPower."""
        sensor = EnphaseReactivePower(0, "SN123")

        class WrongSensor:
            pass

        result = sensor.set_source_values(cast(Sensor, WrongSensor()), make_values({"reactivePower": 100}))
        assert result is False

    def test_enphase_voltage_rejects_wrong_sensor(self):
        """Test EnphaseVoltage.set_source_values rejects non-EnphasePVPower."""
        sensor = EnphaseVoltage(0, "SN123")

        class WrongSensor:
            pass

        result = sensor.set_source_values(cast(Sensor, WrongSensor()), make_values({"voltage": 240}))
        assert result is False


class TestDebugLogging:
    """Tests for debug logging branches."""

    @pytest.mark.asyncio
    async def test_update_internal_state_with_debug_logging(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test _update_internal_state with debug_logging enabled."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"
        pv_power_sensor.debug_logging = True

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = [{"activePower": 1500, "actEnergyDlvd": 2000}]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            result = await pv_power_sensor._update_internal_state()

        assert result is True

    def test_get_token_with_debug_logging_cached(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test get_token debug logging with cached token."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "cached_token"
        pv_power_sensor.debug_logging = True

        token = pv_power_sensor.get_token()

        assert token == "cached_token"

    def test_get_token_with_debug_logging_from_file(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test get_token debug logging when loading from file."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        token_file.write_text("file_token")

        pv_power_sensor._token = ""
        pv_power_sensor.debug_logging = True

        token = pv_power_sensor.get_token()

        assert token == "file_token"

    def test_get_token_with_debug_logging_empty_file(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test get_token debug logging when file exists but is empty."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        token_file.write_text("")

        pv_power_sensor._token = ""
        pv_power_sensor.debug_logging = True

        # Need to generate new token
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "new_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [mock_login_response, mock_token_response]
            token = pv_power_sensor.get_token()

        assert token == "new_token"

    def test_get_token_with_debug_logging_generate_new(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test get_token debug logging when generating new token."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = ""
        pv_power_sensor.debug_logging = True

        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "generated_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [mock_login_response, mock_token_response]
            token = pv_power_sensor.get_token()

        assert token == "generated_token"


class TestTokenFileErrors:
    """Tests for token file error handling."""

    def test_load_token_handles_read_exception(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test loading token handles read errors gracefully."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        token_file = tmp_path / f"{pv_power_sensor.unique_id}.token"
        token_file.write_text("some_token")

        pv_power_sensor._token = ""

        # Create a mock file that raises on read
        class FailingFile:
            def read(self):
                raise IOError("Read error")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        original_open = open

        def mock_open_func(path, *args, **kwargs):
            if str(path).endswith(".token") and "r" in str(args):
                return FailingFile()
            return original_open(path, *args, **kwargs)

        # Need to generate new token since file read fails
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__ = lambda s: s
        mock_login_response.__exit__ = lambda s, *args: None

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "fallback_token"
        mock_token_response.__enter__ = lambda s: s
        mock_token_response.__exit__ = lambda s, *args: None

        with patch("builtins.open", mock_open_func):
            with patch("requests.post") as mock_post:
                mock_post.side_effect = [mock_login_response, mock_token_response]
                token = pv_power_sensor.get_token()

        # Should have generated new token due to read failure
        assert token == "fallback_token"


class TestSmartPortInitFromEnphaseInfo:
    """Tests for SmartPort._init_from_enphase_info."""

    def test_init_from_enphase_info_returns_none(self, mock_config, tmp_path, monkeypatch):
        """Test _init_from_enphase_info returns None, None, None."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))

        class MockModuleConfig:
            testing = True
            host = "192.168.1.100"
            username = "user@example.com"
            password = "password123"

        smartport = SmartPort(0, MockModuleConfig())
        result = smartport._init_from_enphase_info(MockModuleConfig())

        assert result == (None, None, None)


class TestExceptionHandling:
    """Tests for exception handling in _update_internal_state."""

    @pytest.mark.asyncio
    async def test_update_internal_state_generic_exception(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test generic exception in JSON processing."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        # Return malformed data that causes exception after JSON parsing
        mock_response.json.return_value = [{}]  # Missing 'activePower' key
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(KeyError):
                await pv_power_sensor._update_internal_state()


class TestSaveTokenErrors:
    """Tests for save_token error handling."""

    def test_save_token_handles_write_exception(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test save_token handles write errors gracefully."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor.debug_logging = True

        # Mock open to fail on write
        mock_file = MagicMock()
        mock_file.write.side_effect = IOError("Write error")
        mock_file.__enter__.return_value = mock_file

        # Mock login and token responses
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.text = '{"session_id": "sess123"}'
        mock_login_response.__enter__.return_value = mock_login_response

        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.text = "new_token"
        mock_token_response.__enter__.return_value = mock_token_response

        with patch("requests.post", side_effect=[mock_login_response, mock_token_response]):
            with patch("builtins.open", return_value=mock_file):
                # This should log an error but not raise
                pv_power_sensor.get_token(reauthenticate=True)

        mock_file.write.assert_called_once()


class TestDerivedSensorTriggering:
    """Tests that derived sensors are correctly triggered."""

    @pytest.mark.asyncio
    async def test_update_internal_state_calls_set_source_values(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test that _update_internal_state calls set_source_values on derived sensors."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        # Mock a derived sensor
        mock_derived = MagicMock()
        pv_power_sensor.add_derived_sensor(mock_derived)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = [{"activePower": 100, "actEnergyDlvd": 1000}]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            await pv_power_sensor._update_internal_state()

        mock_derived.set_source_values.assert_called_once()


class TestDerivedSensorValueIntegration:
    """Integration style tests for derived sensor value updates."""

    @pytest.mark.asyncio
    async def test_derived_sensors_update_values(self, pv_power_sensor, tmp_path, monkeypatch):
        """Test that derived sensors update their state correctly from main sensor data."""
        monkeypatch.setattr(Config, "persistent_state_path", str(tmp_path))
        pv_power_sensor._token = "valid_token"

        # Instantiate and attach detailed sensors
        lifetime = EnphaseLifetimePVEnergy(0, "SN123")
        daily = EnphaseDailyPVEnergy(0, "SN123", lifetime)
        current = EnphaseCurrent(0, "SN123")
        freq = EnphaseFrequency(0, "SN123")
        pf = EnphasePowerFactor(0, "SN123")
        reactive = EnphaseReactivePower(0, "SN123")
        voltage = EnphaseVoltage(0, "SN123")

        pv_power_sensor.add_derived_sensor(lifetime)
        # daily is derived from lifetime, not directly from pv_power
        # pv_power_sensor.add_derived_sensor(daily)
        pv_power_sensor.add_derived_sensor(current)
        pv_power_sensor.add_derived_sensor(freq)
        pv_power_sensor.add_derived_sensor(pf)
        pv_power_sensor.add_derived_sensor(reactive)
        pv_power_sensor.add_derived_sensor(voltage)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.json.return_value = [{"activePower": 2500, "actEnergyDlvd": 123456, "current": 10.5, "freq": 50.1, "pwrFactor": 0.95, "reactivePower": 150, "voltage": 230.5}]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("requests.get", return_value=mock_response):
            await pv_power_sensor._update_internal_state()

        # Verify derived sensor states
        assert lifetime.latest_raw_state == 123456
        assert current.latest_raw_state == 10.5
        assert freq.latest_raw_state == 50.1
        assert pf.latest_raw_state == 0.95
        assert reactive.latest_raw_state == 150
        assert voltage.latest_raw_state == 230.5
