import asyncio
import time
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, InputType
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors import base


@pytest.fixture(autouse=True)
def clear_usage_ids(tmp_path, monkeypatch):
    # Ensure persistent path is temporary
    active_config.persistent_state_path = tmp_path
    # Reset class-level registries to avoid test interference
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    yield


def test_sanitize_path_component():
    s = "a/..\\b\n\r\t\0"
    out = base._sanitize_path_component(s)
    assert "/" not in out and ".." not in out and "\\" not in out


def test_latest_state_and_interval():
    s = base.ReservedSensor(
        name="r",
        object_id="sigen_obj",
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

    assert s.publishable is False
    s.set_state(5)
    time.sleep(0.01)
    s.set_state(7)
    assert s.latest_raw_state == 7
    assert s.latest_interval is not None


def test_publish_and_attributes(tmp_path):
    mqtt = Mock()
    mqtt.publish = Mock()

    s = base.DerivedSensor(name="d", unique_id="sigen_x", object_id="sigen_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    # configure topics
    s.configure_mqtt_topics("dev1")
    s.set_latest_state(42)
    # publish attributes
    s.publish_attributes(mqtt, clean=False, extra=1)
    mqtt.publish.assert_called()


@pytest.mark.asyncio
async def test_publish_state_calls_mqtt(tmp_path):
    mqtt = Mock()
    mqtt.publish = Mock()

    s = base.DerivedSensor(name="d2", unique_id="sigen_y", object_id="sigen_obj2", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    s.configure_mqtt_topics("dev2")
    s.publish_raw = True
    s.set_latest_state(3)
    # should publish
    result = await s.publish(mqtt, None, republish=True)
    assert result is True
    assert mqtt.publish.called


def test_timestamp_sensor_conversion():
    ts = base.TimestampSensor(name="t", object_id="sigen_ts", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30010, scan_interval=1, protocol_version=base.Protocol.N_A)
    # raw
    assert ts.state2raw("--") == 0
    now = int(time.time())
    ts.set_latest_state(now)
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(ts.get_state(raw=False, republish=True))
    assert isinstance(val, str) and val.endswith("+00:00")
    loop.close()


def test_select_options_and_indexing():
    sel = base.SelectSensor(None, name="sel", object_id="sigen_sel", plant_index=0, device_address=1, address=30020, scan_interval=1, options=["A", "B", "C"], protocol_version=base.Protocol.N_A)
    # get option by index
    assert sel._get_option(1) == "B"
    assert sel._get_option_index("B") == 1
    assert sel._get_option_index(2) == 2
    with pytest.raises(ValueError):
        sel._get_option_index("Z")


def test_state2raw_and_gain():
    s = base.DerivedSensor(name="d3", unique_id="sigen_z", object_id="sigen_o", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=2, precision=0)
    s.set_state(3)
    # when precision 0 and gain set, state2raw multiplies by gain
    assert s.state2raw(3) == 6


def test_writeonly_get_discovery_components():
    w = base.WriteOnlySensor(name="w", object_id="sigen_btn", plant_index=0, device_address=1, address=30030, protocol_version=base.Protocol.N_A)
    comps = w.get_discovery_components()
    assert any(k.endswith("_on") for k in comps.keys())


def test_numeric_min_max_behavior():
    n = base.NumericSensor(
        None,
        name="num",
        object_id="sigen_num",
        input_type=InputType.HOLDING,
        plant_index=0,
        device_address=1,
        address=30040,
        count=1,
        data_type=ModbusDataType.UINT16,
        scan_interval=1,
        unit=PERCENTAGE,
        device_class=DeviceClass.ENERGY,
        state_class=None,
        icon="mdi:test",
        gain=1,
        precision=0,
        protocol_version=base.Protocol.N_A,
        minimum=0.0,
        maximum=100.0,
    )
    # bypass sanity check by appending directly
    n._states.append((time.time(), 150))
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(n.get_state(raw=False, republish=True))
    loop.close()
    assert val == 100.0 or val == 100


def test_alarm_decoding_and_truncate(monkeypatch):
    a = base.Alarm1Sensor(name="a1", object_id="sigen_a_obj", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    # single bit set
    bits = 1 << 2
    decoded = a._decode_alarm_bits(bits, bits)
    assert any("Over-temperature" in s or "Unknown" in s for s in decoded)
    # test truncate when home assistant enabled
    active_config.home_assistant.enabled = True
    long_alarms = ", ".join([f"alarm{i}" for i in range(500)])
    out = a._truncate_alarms(long_alarms, None)
    assert isinstance(out, str)
    active_config.home_assistant.enabled = False
