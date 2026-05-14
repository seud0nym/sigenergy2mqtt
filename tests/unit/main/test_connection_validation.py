from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as paho_mqtt
import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.main.main import (
    _validate_influxdb_connection,
    _validate_modbus_connections,
    _validate_mqtt_connection,
    _validate_pvoutput_connection,
    validate_connections,
)


@pytest.fixture
def mock_config_main():
    # We patch the underlying _settings of the active_config proxy
    with patch.object(active_config._config, "_settings", MagicMock()) as mock_s:
        mock_s.modbus = []
        mock_s.mqtt.broker = "localhost"
        mock_s.mqtt.port = 1883
        mock_s.mqtt.anonymous = True
        mock_s.mqtt.tls = False
        mock_s.mqtt.transport = "tcp"
        mock_s.mqtt.client_id_prefix = "sigen"
        mock_s.influxdb.enabled = True
        mock_s.influxdb.host = "localhost"
        mock_s.influxdb.port = 8086
        mock_s.influxdb.token = "tok"
        mock_s.influxdb.org = "org"
        mock_s.influxdb.write_timeout = 5.0
        mock_s.pvoutput.enabled = True
        mock_s.pvoutput.testing = False
        mock_s.pvoutput.api_key = "key"
        mock_s.pvoutput.system_id = "sys"
        yield active_config


@pytest.mark.asyncio
async def test_validate_modbus_connections_success(mock_config_main):
    mock_modbus = MagicMock()
    mock_modbus.host = "1.2.3.4"
    mock_modbus.port = 502
    mock_modbus.timeout = 1
    mock_modbus.retries = 1
    mock_config_main._config._settings.modbus = [mock_modbus]

    with patch("sigenergy2mqtt.main.main.ModbusClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = True
        await _validate_modbus_connections()
        mock_client.connect.assert_called()
        mock_client.close.assert_called()


@pytest.mark.asyncio
async def test_validate_modbus_connections_failure(mock_config_main):
    mock_modbus = MagicMock()
    mock_modbus.host = "1.2.3.4"
    mock_modbus.port = 502
    mock_config_main._config._settings.modbus = [mock_modbus]

    with patch("sigenergy2mqtt.main.main.ModbusClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock()
        mock_client.connected = False
        with pytest.raises(ConnectionError, match="Unable to connect"):
            await _validate_modbus_connections()


def test_validate_mqtt_connection_success(mock_config_main):
    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.is_connected.return_value = True
        mock_client.loop.return_value = paho_mqtt.MQTT_ERR_SUCCESS
        _validate_mqtt_connection(False)
        # Line 658-659: Exception in disconnect
        mock_client.disconnect.side_effect = Exception("boom")
        _validate_mqtt_connection(False)


def test_validate_mqtt_connection_tls_insecure(mock_config_main):
    mock_config_main._config._settings.mqtt.tls = True
    mock_config_main._config._settings.mqtt.tls_insecure = True
    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.is_connected.return_value = True
        mock_client.loop.return_value = paho_mqtt.MQTT_ERR_SUCCESS
        _validate_mqtt_connection(True)


def test_validate_mqtt_connection_timeout(mock_config_main):
    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.is_connected.return_value = False
        mock_client.loop.return_value = paho_mqtt.MQTT_ERR_SUCCESS
        with pytest.raises(TimeoutError, match="Timed out waiting"):
            _validate_mqtt_connection(False)


def test_validate_influxdb_connection_disabled(mock_config_main):
    # Line 674
    mock_config_main._config._settings.influxdb.enabled = False
    _validate_influxdb_connection(False)


def test_validate_influxdb_connection_v2_success(mock_config_main):
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.raise_for_status.return_value = None
        mock_get.return_value = mock_res
        _validate_influxdb_connection(True)  # Line 682
        _validate_influxdb_connection(False)  # Line 684


def test_validate_influxdb_connection_v1_success(mock_config_main):
    mock_config_main._config._settings.influxdb.token = None
    mock_config_main._config._settings.influxdb.username = "user"
    mock_config_main._config._settings.influxdb.password = "pass"
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_get.return_value = mock_res
        _validate_influxdb_connection(True)  # Line 689
        _validate_influxdb_connection(False)  # Line 691


def test_validate_pvoutput_connection_disabled(mock_config_main):
    # Line 713
    mock_config_main._config._settings.pvoutput.enabled = False
    _validate_pvoutput_connection(False)


def test_validate_pvoutput_connection_success(mock_config_main):
    with patch("requests.get") as mock_get:
        mock_res = MagicMock()
        mock_get.return_value = mock_res
        _validate_pvoutput_connection(True)  # Line 725
        _validate_pvoutput_connection(False)  # Line 727


def test_validate_pvoutput_connection_testing(mock_config_main):
    mock_config_main._config._settings.pvoutput.testing = True
    _validate_pvoutput_connection(False)


@pytest.mark.asyncio
async def test_validate_connections_all(mock_config_main):
    with patch("sigenergy2mqtt.main.main._validate_modbus_connections") as m1:
        with patch("sigenergy2mqtt.main.main._validate_mqtt_connection") as m3:
            with patch("sigenergy2mqtt.main.main._validate_influxdb_connection") as m4:
                with patch("sigenergy2mqtt.main.main._validate_pvoutput_connection") as m5:
                    await validate_connections(True)
                    m1.assert_called()
                    m3.assert_called()
                    m4.assert_called()
                    m5.assert_called()
