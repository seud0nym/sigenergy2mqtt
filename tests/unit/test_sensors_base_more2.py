import os
import time
import asyncio
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.sensors.const import InputType
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.config.config import Config


@pytest.fixture(autouse=True)
def reset_env(tmp_path):
    Config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    Config.home_assistant.enabled = False
    yield


def test_cleanup_persistent_publish_state_file():
    s = base.DerivedSensor(name="c", unique_id="sigen_c", object_id="sigen_c_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    # create file
    s._persistent_publish_state_file.parent.mkdir(parents=True, exist_ok=True)
    s._persistent_publish_state_file.write_text("0")
    assert s._persistent_publish_state_file.exists()
    s._cleanup_persistent_state_file()
    assert not s._persistent_publish_state_file.exists()


def test_handle_unpublishable_discovery_creates_and_clears():
    mqtt = Mock()
    s = base.DerivedSensor(name="d", unique_id="sigen_d", object_id="sigen_d_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("dev")

    # Case: no persistent file -> should create minimal discovery to remove entity
    s.publishable = False
    comps = s.get_discovery(mqtt)
    assert comps
    # persistent file should exist now
    assert s._persistent_publish_state_file.exists()

    # Case: persistent file exists -> get_discovery should return empty dict
    comps2 = s.get_discovery(mqtt)
    assert comps2 == {}


def test_modbus_exception_handlers_raise():
    s = base.ReadOnlySensor(name="r", object_id="sigen_ro2", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30011, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    for code in (base.ModbusSensorMixin.ExceptionCode.ILLEGAL_DATA_VALUE, base.ModbusSensorMixin.ExceptionCode.SLAVE_DEVICE_FAILURE, 99):
        rr = Mock()
        rr.isError.return_value = True
        rr.exception_code = code
        with pytest.raises(Exception):
            s._check_register_response(rr, "read")


def test_writable_raw2state_option_and_numeric():
    w = base.ReadWriteSensor(None, name="rw", object_id="sigen_rw", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30020, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)
    # options behavior
    w[base.DiscoveryKeys.OPTIONS] = ["Zero", "One"]
    assert w._raw2state(1) == "One"
    # numeric behavior
    assert isinstance(w._raw2state(5), (int, float))


def test_numeric_tuple_range_constrain():
    n = base.NumericSensor(None, name="numt", object_id="sigen_numt", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30040, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=1, protocol_version=base.Protocol.N_A, minimum=(0.0, 10.0), maximum=(5.0, 20.0))
    # set a state outside positive tuple range and ensure constraint
    # directly append a state bypassing sanity check
    n._states.append((time.time(), 100))
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(n.get_state(raw=False, republish=True))
    loop.close()
    assert isinstance(val, float)


def test_resettable_persist_load(tmp_path):
    src = base.DerivedSensor(name="src", unique_id="sigen_src", object_id="sigen_src_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    uid = str(src.unique_id)
    safe = base._sanitize_path_component(uid)
    pfile = tmp_path / f"{safe}.state"
    pfile.write_text("12.34")
    # create sensor that will load persisted state
    r = base.ResettableAccumulationSensor(name="rs", unique_id="sigen_rs2", object_id="sigen_rs2_obj", source=src, data_type=ModbusDataType.UINT32, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    # persistent file should be read and value set
    assert isinstance(r._current_total, float)
