import os
import time
import asyncio
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.config.config import Config


@pytest.fixture(autouse=True)
def reset_env(tmp_path):
    Config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    Config.home_assistant.enabled = False
    yield


def test_state2raw_string_datatype():
    s = base.DerivedSensor(name="ds", unique_id="sigen_ds", object_id="sigen_ds_obj", data_type=ModbusDataType.STRING, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    assert s.state2raw("abc") == "abc"


def test_get_attributes_includes_comment_and_source():
    r = base.ReadOnlySensor(name="ro", object_id="sigen_ro3", input_type=base.InputType.INPUT, plant_index=0, device_address=1, address=30090, count=2, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    r[base.DiscoveryKeys.JSON_ATTRIBUTES_TOPIC] = "t"
    r[base.DiscoveryKeys.OBJECT_ID] = "sigen_ro3"
    r["comment"] = "a comment"
    attrs = r.get_attributes()
    assert "source" in attrs or base.SensorAttributeKeys.SOURCE in attrs


def test_get_base_topic_simplified_true():
    s = base.DerivedSensor(name="bt", unique_id="sigen_bt", object_id="sigen_bt_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    Config.home_assistant.enabled = True
    Config.home_assistant.use_simplified_topics = True
    t = s._get_base_topic("dev1")
    assert "sigenergy2mqtt/" in t or "homeassistant" not in t


def test_numeric_flatten_discovery_components():
    n = base.NumericSensor(None, name="nfl", object_id="sigen_nfl", input_type=base.InputType.HOLDING, plant_index=0, device_address=1, address=30100, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A, minimum=(1.0, 2.0), maximum=(10.0, 20.0))
    comps = n.get_discovery_components()
    v = comps[n.unique_id][base.DiscoveryKeys.MIN]
    assert isinstance(v, float) or isinstance(v, int)


def test_resettable_notify_persists_file(tmp_path):
    src = base.DerivedSensor(name="src2", unique_id="sigen_src2", object_id="sigen_src2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    r = base.ResettableAccumulationSensor(name="rsx", unique_id="sigen_rsx", object_id="sigen_rsx_obj", source=src, data_type=ModbusDataType.UINT32, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    # notify with value
    loop = asyncio.new_event_loop()
    loop.run_until_complete(r.notify(None, Mock(), 5.0, r._reset_topic, Mock()))
    loop.close()
    assert r._persistent_state_file.exists()


def test_energydaily_load_midnight_stale_file(tmp_path):
    src = base.DerivedSensor(name="src3", unique_id="sigen_src3", object_id="sigen_src3_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    # create stale file
    uid = str(src.unique_id)
    safe = base._sanitize_path_component(uid)
    pfile = tmp_path / f"{safe}.atmidnight"
    pfile.write_text("5.0")
    # set mtime to yesterday
    old = time.time() - (24 * 60 * 60)
    os.utime(pfile, (old, old))
    # create EnergyDailyAccumulationSensor which should remove stale file
    ed = base.EnergyDailyAccumulationSensor(name="ed", unique_id="sigen_ed", object_id="sigen_ed_obj", source=src)
    assert not pfile.exists()


def test_alarm_unknown_bit_decoding():
    class CustomAlarm(base.AlarmSensor):
        def __init__(self):
            super().__init__(name="ca", object_id="sigen_ca", plant_index=0, device_address=1, address=30110, protocol_version=base.Protocol.N_A, alarm_type="TEST")

        def decode_alarm_bit(self, bit_position: int):
            return None

    a = CustomAlarm()
    res = a._decode_alarm_bits(1 << 3, 8)
    assert any("Unknown" in s for s in res)
