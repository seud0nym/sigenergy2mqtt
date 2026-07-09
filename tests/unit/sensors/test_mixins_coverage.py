import asyncio
import importlib
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
from pymodbus.pdu import ExceptionResponse

from sigenergy2mqtt.common import DeviceClass, InputType, Protocol
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import DiscoveryKeys
from sigenergy2mqtt.sensors.base.mixins import (
    ModbusSensorMixin,
    ObservableMixin,
    ReadableSensorMixin,
    WritableSensorMixin,
)
from sigenergy2mqtt.sensors.base.sensor import Sensor
from sigenergy2mqtt.sensors.base.writable import SwitchSensor, WriteOnlySensor


class DummyReadable(ReadableSensorMixin, Sensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("unique_id", "sigen_test_obj")
        kwargs.setdefault("object_id", "sigen_test_obj")
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("device_class", None)
        kwargs.setdefault("state_class", None)
        kwargs.setdefault("icon", None)
        kwargs.setdefault("gain", 1)
        kwargs.setdefault("precision", 0)
        kwargs.setdefault("protocol_version", Protocol.V2_9)
        kwargs.setdefault("data_type", ModbusDataType.UINT16)
        super().__init__(**kwargs)


class DummyModbus(ModbusSensorMixin, Sensor):
    def __init__(self, **kwargs):
        kwargs.setdefault("name", "test")
        kwargs.setdefault("object_id", "sigen_test_obj")
        kwargs.setdefault("unit", "V")
        kwargs.setdefault("device_class", None)
        kwargs.setdefault("state_class", None)
        kwargs.setdefault("icon", None)
        kwargs.setdefault("gain", 1)
        kwargs.setdefault("precision", 0)
        kwargs.setdefault("protocol_version", Protocol.V2_9)
        kwargs.setdefault("data_type", ModbusDataType.UINT16)
        super().__init__(**kwargs)


def test_readable_sensor_mixin_init_exceptions():
    with pytest.raises(ValueError, match="Missing required parameter 'scan_interval'"):
        DummyReadable()

    with pytest.raises(ValueError, match="scan_interval cannot be less than 1 second"):
        DummyReadable(scan_interval=0)


def test_readable_sensor_mixin_applicable_overrides(monkeypatch):
    r = DummyReadable(scan_interval=10)
    monkeypatch.setattr(r, "_matches_override_pattern", lambda x: False)
    # Line 80
    assert r._get_applicable_overrides("pattern") is None


def test_modbus_sensor_mixin_init_exceptions():
    # Line 117
    with pytest.raises(AssertionError, match="Invalid count 0"):
        DummyModbus(input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30000, count=0)


def test_modbus_sensor_mixin_check_register_response_fallthrough(monkeypatch):
    sensor = DummyModbus(input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30000, count=1)
    
    # Mock handle methods to not raise so we hit line 189
    monkeypatch.setattr(sensor, "_handle_illegal_function", lambda *a, **kw: None)
    
    rr = MagicMock()
    rr.isError.return_value = True
    rr.exception_code = 1
    # Hits line 189 (return False)
    assert sensor._check_register_response(rr, "test") is False


def test_modbus_sensor_mixin_debug_logging(caplog):
    caplog.set_level(logging.DEBUG)
    sensor = DummyModbus(input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30000, count=1)
    sensor.debug_logging = True
    
    # Line 198
    rr = ExceptionResponse(1)
    with pytest.raises(Exception):
        sensor._handle_illegal_function("test", rr)
    assert "Exception Response" in caplog.text or str(rr) in caplog.text
    caplog.clear()
    
    # Line 231
    rr = ExceptionResponse(3)
    with pytest.raises(Exception):
        sensor._handle_illegal_data_value("test", rr)
    assert "Exception Response" in caplog.text or str(rr) in caplog.text
    caplog.clear()
    
    # Line 241
    rr = ExceptionResponse(4)
    with pytest.raises(Exception):
        sensor._handle_slave_device_failure("test", rr)
    assert "Exception Response" in caplog.text or str(rr) in caplog.text


@pytest.mark.asyncio
async def test_observable_mixin_notify():
    class DummyObs(ObservableMixin):
        async def notify(self, modbus_client, mqtt_client, value, source, handler):
            # Line 277
            return await super().notify(modbus_client, mqtt_client, value, source, handler)
            
    d = DummyObs()
    await d.notify(None, None, 0, "", None)


class DummyWritable(WritableSensorMixin, DummyModbus):
    def __init__(self, **kwargs):
        kwargs.setdefault("data_type", ModbusDataType.UINT16)
        super().__init__(**kwargs)


def test_writable_sensor_mixin_command_topic():
    sensor = DummyWritable(input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30000, count=1)
    sensor[DiscoveryKeys.COMMAND_TOPIC] = "   "
    
    # Line 319
    with pytest.raises(RuntimeError, match="command topic is not defined"):
        _ = sensor.command_topic


def test_writable_sensor_mixin_raw2state_writeonly():
    sensor = WriteOnlySensor(
        name="test_wo",
        object_id="sigen_test_obj",
        plant_index=0,
        device_address=1,
        address=30000,
        protocol_version=Protocol.V2_9
    )
    sensor._values = {"off": "0", "on": "1"}
    sensor._names = {"off": "Disabled", "on": "Enabled"}
    # Lines 345-349
    assert sensor._raw2state("0") == "Disabled"
    assert sensor._raw2state("1") == "Enabled"
    assert sensor._raw2state("2") == "2"


def test_writable_sensor_mixin_raw2state_switch():
    sensor = SwitchSensor(
        availability_control_sensor=None,
        name="test_switch",
        object_id="sigen_test_obj",
        plant_index=0,
        device_address=1,
        address=30000,
        scan_interval=10,
        protocol_version=Protocol.V2_9,
        payload_off="OFF_VAL",
        payload_on="ON_VAL"
    )
    sensor[DiscoveryKeys.PAYLOAD_OFF] = "OFF_VAL"
    sensor[DiscoveryKeys.PAYLOAD_ON] = "ON_VAL"
    # Lines 353-355
    assert sensor._raw2state("OFF_VAL") == "Off"
    assert sensor._raw2state("ON_VAL") == "On"
    assert sensor._raw2state("OTHER") == "OTHER"


def test_mixins_importerror_handling():
    # Lines 28-29
    import sigenergy2mqtt.sensors.base.mixins as mixins
    
    # Force ImportError on reload
    original_import = __import__
    def failing_import(name, *args, **kwargs):
        if "_sigenergy_local_modbus_registers" in name:
            raise ImportError("Fake ImportError")
        return original_import(name, *args, **kwargs)
        
    with patch("builtins.__import__", side_effect=failing_import):
        importlib.reload(mixins)
        assert mixins.SIGENERGY_LOCAL_MODBUS_REGISTERS == {}
        
    # Restore
    importlib.reload(mixins)
