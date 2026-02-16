import asyncio
import time
from collections import deque
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.sensors.const import InputType
from sigenergy2mqtt.sensors.sanity_check import SanityCheckException


@pytest.fixture(autouse=True)
def reset_config_and_ids(tmp_path):
    Config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    Config.home_assistant.enabled = False
    yield


def make_readonly_sensor():
    return base.ReadOnlySensor(
        name="r",
        object_id="sigen_ro",
        input_type=InputType.INPUT,
        plant_index=0,
        device_address=1,
        address=30001,
        count=1,
        data_type=ModbusDataType.UINT16,
        scan_interval=1,
        unit=None,
        device_class=None,
        state_class=None,
        icon="mdi:test",
        gain=None,
        precision=None,
        protocol_version=base.Protocol.N_A,
    )


# duplicate coverage exists in `test_sensors_base_coverage.py` — consolidated there

def test_check_register_response_success():
    s = make_readonly_sensor()
    rr = Mock()
    rr.isError.return_value = False
    # not an ExceptionResponse
    assert s._check_register_response(rr, "read") is True


def test_check_register_response_illegal_function_raises():
    s = make_readonly_sensor()
    rr = Mock()
    rr.isError.return_value = True
    rr.exception_code = base.ModbusSensorMixin.ExceptionCode.ILLEGAL_FUNCTION
    with pytest.raises(Exception) as ei:
        s._check_register_response(rr, "read")
    assert "ILLEGAL FUNCTION" in str(ei.value)


def test_check_register_response_illegal_data_address_adjusts():
    s = make_readonly_sensor()
    rr = Mock()
    rr.isError.return_value = True
    rr.exception_code = base.ModbusSensorMixin.ExceptionCode.ILLEGAL_DATA_ADDRESS
    with pytest.raises(Exception):
        s._check_register_response(rr, "read")
    assert s._max_failures == 0


def test_apply_overrides_and_device_overrides():
    s = base.DerivedSensor(name="dov", unique_id="sigen_override", object_id="sigen_o2", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=1, precision=None)
    # create overrides that match class name
    Config.sensor_overrides = {"DerivedSensor": {"debug-logging": True, "gain": 5, "publishable": False, "precision": 2}}
    # registers - simulate read_only True
    regs = Mock()
    regs.no_remote_ems = False
    regs.read_only = True
    s.apply_sensor_overrides(regs)
    assert s.debug_logging is True
    assert s.gain == 5
    assert s.publishable is False
    assert s.precision == 2


def test_convert_value_to_registers_string_calls_modbus_client():
    w = base.WriteOnlySensor(name="w2", object_id="sigen_btn2", plant_index=0, device_address=1, address=30030, protocol_version=base.Protocol.N_A)
    w.data_type = ModbusDataType.STRING
    mock_modbus = Mock()
    mock_modbus.convert_to_registers.return_value = [1, 2, 3]
    regs = w._convert_value_to_registers(mock_modbus, "abc")
    assert regs == [1, 2, 3]
    mock_modbus.convert_to_registers.assert_called()


def test_sensor_equality_and_hash():
    a = base.DerivedSensor(name="a", unique_id="sigen_eq1", object_id="sigen_obj_eq", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    b = base.DerivedSensor(name="b", unique_id="sigen_eq1", object_id="sigen_obj_eq2", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    assert a == b
    assert hash(a) == hash(b)


def test_alarm_is_no_alarm_cases():
    a = base.Alarm1Sensor(name="al", object_id="sigen_alarm", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    assert a._is_no_alarm(None)
    assert a._is_no_alarm(0)
    assert a._is_no_alarm(65535)
    assert a._is_no_alarm([0, 0])


def test_alarmcombined_invalid_args_raises():
    a1 = base.Alarm1Sensor("a1", "sigen_a1", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    a2 = base.Alarm1Sensor("a2", "sigen_a2", plant_index=0, device_address=2, address=30051, protocol_version=base.Protocol.N_A)
    with pytest.raises(ValueError):
        base.AlarmCombinedSensor("comb", "sigen_comb", "sigen_comb_obj", a1, a2)


def test_resettable_accumulation_negative_interval():
    src = Mock()
    src.latest_interval = -5
    r = base.ResettableAccumulationSensor(name="rs", unique_id="sigen_rs", object_id="sigen_rs_o", source=src, data_type=ModbusDataType.UINT32, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    # call set_source_values with wrong sensor object
    res = r.set_source_values(Mock(), deque := [])
    assert res is False


def test_typed_sensor_mixin_requires_data_type():
    class Dummy(base.TypedSensorMixin, base.Sensor):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    with pytest.raises(AssertionError):
        Dummy(name="d", unique_id="sigen_dt", object_id="sigen_dt_obj", unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)


def test_protocol_version_setter_invalid_float():
    s = base.DerivedSensor(name="pv", unique_id="sigen_pv", object_id="sigen_pv_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    with pytest.raises(AssertionError):
        s.protocol_version = 99.9


def test_get_discovery_requires_configured_topics():
    mqtt = Mock()
    s = base.DerivedSensor(name="dd", unique_id="sigen_dd", object_id="sigen_dd_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    with pytest.raises(RuntimeError):
        s.get_discovery(mqtt)


def test_publishable_and_publish_raw_setter_type_enforcement():
    s = base.DerivedSensor(name="dd2", unique_id="sigen_dd2", object_id="sigen_dd2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    with pytest.raises(ValueError):
        s.publishable = "true"
    with pytest.raises(ValueError):
        s.publish_raw = "false"


@pytest.mark.asyncio
async def test_perform_modbus_read_and_write(monkeypatch):
    # prepare dummy lock factory
    class DummyLock:
        def __init__(self, *_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyFactory:
        def lock(self, *_):
            return DummyLock()

    class DummyContainer:
        @staticmethod
        def get(_):
            return DummyFactory()

    monkeypatch.setattr(base, "ModbusLockFactory", DummyContainer)

    # prepare modbus client for read
    modbus = Mock()
    async def read_input_registers(addr, count, device_id, trace):
        rr = Mock()
        rr.isError.return_value = False
        rr.registers = [123]
        return rr

    modbus.read_input_registers = read_input_registers
    modbus.convert_from_registers = Mock(return_value=123)

    s = make_readonly_sensor()
    ok = await s._perform_modbus_read(modbus)
    assert ok is True
    assert s.latest_raw_state == 123

    # write
    w = base.WriteOnlySensor(name="w3", object_id="sigen_btn3", plant_index=0, device_address=1, address=30060, protocol_version=base.Protocol.N_A)
    async def write_registers(addr, registers, device_id, no_response_expected=False):
        rr = Mock()
        rr.isError.return_value = False
        return rr

    modbus.write_registers = write_registers
    regs = [1, 2]
    ok2 = await w._perform_modbus_write(modbus, regs, device_id=1, no_response_expected=False, method="write_regs")
    assert ok2 is True


def test_handle_publish_error_and_failure_count(monkeypatch):
    mqtt = Mock()
    mqtt.publish = Mock()
    s = base.DerivedSensor(name="hd", unique_id="sigen_hd", object_id="sigen_hd_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)

    # case no modbus -> should raise
    with pytest.raises(Exception):
        s._handle_publish_error(mqtt, None, Exception("boom"))

    # case with modbus connected increments failures and publishes attributes
    modbus = Mock()
    modbus.connected = True
    Config.home_assistant.enabled = True
    s.configure_mqtt_topics("dev")
    s._failures = 0
    res = s._handle_publish_error(mqtt, modbus, Exception("err"))
    assert res is False
    assert s._failures >= 1


def test_update_failure_count_sanity_check_ignored():
    s = base.DerivedSensor(name="ufc", unique_id="sigen_ufc", object_id="sigen_ufc_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s._failures = 0
    # sanity check exception should not increment when config says so
    Config.sanity_check_failures_increment = False
    s._update_failure_count(SanityCheckException("nope"))
    assert s._failures == 0


def test_apply_gain_and_precision_behavior():
    s = base.DerivedSensor(name="g", unique_id="sigen_g", object_id="sigen_g_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=2, precision=1)
    out = s._apply_gain_and_precision(5.0)
    assert abs(out - 2.5) < 1e-6
    s.precision = 0
    out2 = s._apply_gain_and_precision(4.0)
    assert isinstance(out2, int)


def test_state2raw_option_string():
    sel = base.SelectSensor(None, name="sel2", object_id="sigen_sel2", plant_index=0, device_address=1, address=30070, scan_interval=1, options=["A","B","C"], protocol_version=base.Protocol.N_A)
    assert sel.state2raw("B") == 1


def test_reserved_sensor_publishable_setter_raises():
    r = base.ReservedSensor(name="rs2", object_id="sigen_rs2", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30080, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    with pytest.raises(ValueError):
        r.publishable = True
