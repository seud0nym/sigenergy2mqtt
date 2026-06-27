import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest
import paho.mqtt.client as paho_mqtt

from sigenergy2mqtt.main import main as main_mod
from sigenergy2mqtt.config import active_config, Config
from sigenergy2mqtt.common import Protocol


@pytest.fixture(autouse=True)
def clean_config():
    """Ensure active_config is set up correctly."""
    from sigenergy2mqtt.config import _swap_active_config
    cfg = Config()
    _swap_active_config(cfg)
    yield
    _swap_active_config(Config())


# ---------------------------------------------------------------------------
# _setup_pss
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_pss_normal():
    mock_device = MagicMock()
    mock_device.pss = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    mock_config = MagicMock()
    mock_pss = MagicMock()
    mock_plant = MagicMock()
    
    with patch("sigenergy2mqtt.main.main.make_pss", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main.validate_publishable_sensors", new_callable=AsyncMock) as mock_validate:
        mock_make.return_value = mock_pss
        
        res = await main_mod._setup_pss(
            plant_index=0,
            device=mock_device,
            plant=mock_plant,
            seen_serial_numbers=set(),
            modbus_client=MagicMock(),
            config=mock_config,
            protocol_version=Protocol.V2_9,
            sequence_start=0,
            total_count=1,
        )
        
        assert res == 1
        mock_config.add_device.assert_called_once_with(mock_pss)
        mock_validate.assert_called_once()

@pytest.mark.asyncio
async def test_setup_pss_exception_grid_outage(caplog):
    mock_device = MagicMock()
    mock_device.pss = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    with patch("sigenergy2mqtt.main.main.make_pss", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main._is_grid_outage", new_callable=AsyncMock) as mock_outage, \
         patch("sigenergy2mqtt.main.main._schedule_restart_on_grid_restore") as mock_schedule:
        
        mock_make.side_effect = Exception("Outage error")
        mock_outage.return_value = True
        
        res = await main_mod._setup_pss(
            0, mock_device, MagicMock(), set(), MagicMock(), MagicMock(), Protocol.V2_9, 0, 1
        )
        
        assert res == 1
        mock_schedule.assert_called_once()
        assert "initialization failed during grid outage" in caplog.text

@pytest.mark.asyncio
async def test_setup_pss_exception_normal(caplog):
    mock_device = MagicMock()
    mock_device.pss = [1]
    mock_device.host = "127.0.0.1"
    mock_device.port = 502
    
    with patch("sigenergy2mqtt.main.main.make_pss", new_callable=AsyncMock) as mock_make, \
         patch("sigenergy2mqtt.main.main._is_grid_outage", new_callable=AsyncMock) as mock_outage:
        
        mock_make.side_effect = Exception("Other error")
        mock_outage.return_value = False
        
        res = await main_mod._setup_pss(
            0, mock_device, MagicMock(), set(), MagicMock(), MagicMock(), Protocol.V2_9, 0, 1
        )
        
        assert res == 1
        assert "Failed to initialize PSS device at address 1" in caplog.text


# ---------------------------------------------------------------------------
# _is_grid_outage failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_grid_outage_exception(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    with patch("sigenergy2mqtt.main.main.GridStatus") as mock_gs:
        instance = mock_gs.return_value
        instance.get_state = AsyncMock(side_effect=Exception("mocked get_state exception"))
        
        assert await main_mod._is_grid_outage(0, MagicMock()) is None
        assert "Unable to probe GridStatus for outage detection" in caplog.text

@pytest.mark.asyncio
async def test_is_grid_outage_none_returned():
    with patch("sigenergy2mqtt.main.main.GridStatus") as mock_gs:
        instance = mock_gs.return_value
        instance.get_state = AsyncMock(return_value=None)
        
        assert await main_mod._is_grid_outage(0, MagicMock()) is None

@pytest.mark.asyncio
async def test_is_grid_outage_type_error(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    with patch("sigenergy2mqtt.main.main.GridStatus") as mock_gs:
        instance = mock_gs.return_value
        instance.get_state = AsyncMock(return_value="not_an_int")
        
        assert await main_mod._is_grid_outage(0, MagicMock()) is None
        assert "Unexpected GridStatus raw value for outage detection: not_an_int" in caplog.text


# ---------------------------------------------------------------------------
# _watch_grid_restore_and_request_restart and _schedule_restart_on_grid_restore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watch_grid_restore_cancelled():
    with patch("sigenergy2mqtt.main.main.ModbusClient", autospec=True) as mock_mc:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_mc.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        
        with patch("sigenergy2mqtt.main.main._is_grid_outage", new_callable=AsyncMock) as mock_outage, \
             patch("asyncio.sleep", side_effect=asyncio.CancelledError):
            mock_outage.return_value = True # Still in outage
            
            # Pretend key was added to set
            key = ("host", 502, 0)
            main_mod._GRID_RESTORE_WATCH_TASKS.add(key)
            
            with pytest.raises(asyncio.CancelledError):
                await main_mod._watch_grid_restore_and_request_restart("host", 502, 1.0, 1, 0)
            
            assert key not in main_mod._GRID_RESTORE_WATCH_TASKS

def test_schedule_restart_on_grid_restore_already_watched():
    mock_device = MagicMock()
    mock_device.host = "host2"
    mock_device.port = 502
    
    key = ("host2", 502, 0)
    main_mod._GRID_RESTORE_WATCH_TASKS.add(key)
    
    with patch("asyncio.create_task") as mock_create:
        main_mod._schedule_restart_on_grid_restore(mock_device, 0)
        mock_create.assert_not_called()
    
    main_mod._GRID_RESTORE_WATCH_TASKS.remove(key)


# ---------------------------------------------------------------------------
# _validate_modbus_connections
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_modbus_connections_missing_host(caplog):
    mock_modbus = MagicMock()
    mock_modbus.host = ""
    
    with patch("sigenergy2mqtt.config.active_config.modbus", [mock_modbus]):
        await main_mod._validate_modbus_connections()
        assert "Unable to validate Modbus connection for device #0, host is not set" in caplog.text


# ---------------------------------------------------------------------------
# _validate_mqtt_connection
# ---------------------------------------------------------------------------

def test_validate_mqtt_connection_show_credentials_and_rc_fail(caplog):
    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Make loop simulate rc error on first try
        mock_client.loop.return_value = paho_mqtt.MQTT_ERR_PROTOCOL
        mock_client.is_connected.return_value = False
        
        active_config.mqtt.anonymous = False
        active_config.mqtt.username = "my_user"
        active_config.mqtt.password = "my_pass"
        active_config.mqtt.broker = "broker"
        active_config.mqtt.port = 1883
        active_config.mqtt.tls = False
        
        with pytest.raises(ConnectionError, match="MQTT broker connection failed with rc="):
            main_mod._validate_mqtt_connection(show_credentials=True)
            
        assert "Validating MQTT connection to mqtt://broker:1883 with username='my_user' password='my_pass'" in caplog.text

def test_validate_mqtt_connection_hide_credentials_and_rc_fail(caplog):
    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.loop.return_value = paho_mqtt.MQTT_ERR_PROTOCOL
        mock_client.is_connected.return_value = False
        
        active_config.mqtt.anonymous = False
        active_config.mqtt.username = "my_user"
        active_config.mqtt.password = "my_pass"
        
        with pytest.raises(ConnectionError):
            main_mod._validate_mqtt_connection(show_credentials=False)
            
        assert "password='[REDACTED]'" in caplog.text


# ---------------------------------------------------------------------------
# validate_publishable_sensors and caching
# ---------------------------------------------------------------------------

def test_is_valid_validation_cache_payload():
    assert main_mod._is_valid_validation_cache_payload("invalid json") is False
    assert main_mod._is_valid_validation_cache_payload('{"cache_version": 1}') is False # missing fields

@pytest.mark.asyncio
async def test_validate_publishable_sensors_clean_mode():
    active_config.clean = True
    await main_mod.validate_publishable_sensors(MagicMock(), MagicMock())
    active_config.clean = False # Reset for other tests

@pytest.mark.asyncio
async def test_validate_publishable_sensors_read_exceptions(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    mock_sensor_1 = MagicMock(spec=main_mod.ModbusSensorMixin)
    mock_sensor_1.address = 100
    mock_sensor_1.count = 1
    mock_sensor_1.device_address = 1
    mock_sensor_1.input_type = 4
    mock_sensor_1.publishable = True
    mock_sensor_1.state_count = 0
    mock_sensor_1.log_identity = "Sensor1"
    mock_sensor_1.alarms = [mock_sensor_1] # Pretend it's not combined for simplicity, wait no it checks isinstance(sensor, AlarmCombinedSensor)
    # mock_sensor_1 is not AlarmCombinedSensor
    
    mock_sensor_2 = MagicMock(spec=main_mod.ModbusSensorMixin)
    mock_sensor_2.address = 200
    mock_sensor_2.count = 1
    mock_sensor_2.device_address = 1
    mock_sensor_2.input_type = 4
    mock_sensor_2.publishable = True
    mock_sensor_2.state_count = 0
    mock_sensor_2.log_identity = "Sensor2"
    
    mock_device = MagicMock()
    mock_device.get_all_sensors.return_value = {"s1": mock_sensor_1, "s2": mock_sensor_2}
    mock_device.log_identity = "TestDevice"
    
    with patch("sigenergy2mqtt.main.main.state_store.load", new_callable=AsyncMock) as mock_load, \
         patch("sigenergy2mqtt.main.main.read_registers", new_callable=AsyncMock) as mock_rr:
        
        mock_load.return_value = None # No cache
        
        # First read throws transient error
        # Second read throws exception with "0x02 ILLEGAL DATA ADDRESS"
        def mock_read_registers(client, addr, count, daddr, itype):
            if addr == mock_sensor_1.address:
                raise Exception("Transient network error")
            else:
                raise Exception("0x02 ILLEGAL DATA ADDRESS")
        
        mock_rr.side_effect = mock_read_registers
        
        await main_mod.validate_publishable_sensors(MagicMock(), mock_device)
        
        assert "Validation read failed: Transient network error" in caplog.text
        assert "Validation detected illegal address: 0x02 ILLEGAL DATA ADDRESS" in caplog.text
        assert "Validation scan not cached because one or more sensor reads failed" in caplog.text
