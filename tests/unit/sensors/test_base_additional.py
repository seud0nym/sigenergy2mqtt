import asyncio
import time
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.common import PERCENTAGE, DeviceClass, InputType
from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors import base


@pytest.fixture(autouse=True)
def reset_sensor_base_test_env(tmp_path):
    active_config.persistent_state_path = tmp_path
    active_config.home_assistant.enabled = False
    active_config.home_assistant.use_simplified_topics = False
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


def test_publish_and_attributes():
    mqtt = Mock()
    mqtt.publish = Mock()

    s = base.DerivedSensor(name="d", unique_id="sigen_x", object_id="sigen_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    s.configure_mqtt_topics("dev1")
    s.set_latest_state(42)
    s.publish_attributes(mqtt, clean=False, extra=1)
    mqtt.publish.assert_called()


@pytest.mark.asyncio
async def test_publish_state_calls_mqtt():
    mqtt = Mock()
    mqtt.publish = Mock()

    s = base.DerivedSensor(name="d2", unique_id="sigen_y", object_id="sigen_obj2", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    s.configure_mqtt_topics("dev2")
    s.publish_raw = True
    s.set_latest_state(3)
    result = await s.publish(mqtt, None, republish=True)
    assert result is True
    assert mqtt.publish.called


def test_timestamp_sensor_conversion():
    ts = base.TimestampSensor(name="t", object_id="sigen_ts", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30010, scan_interval=1, protocol_version=base.Protocol.N_A)
    assert ts.state2raw("--") == 0
    now = int(time.time())
    ts.set_latest_state(now)
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(ts.get_state(raw=False, republish=True))
    assert isinstance(val, str) and val.endswith("+00:00")
    loop.close()


def test_select_options_and_indexing():
    sel = base.SelectSensor(None, name="sel", object_id="sigen_sel", plant_index=0, device_address=1, address=30020, scan_interval=1, options=["A", "B", "C"], protocol_version=base.Protocol.N_A)
    assert sel._get_option(1) == "B"
    assert sel._get_option_index("B") == 1
    assert sel._get_option_index(2) == 2
    with pytest.raises(ValueError):
        sel._get_option_index("Z")


def test_state2raw_and_gain():
    s = base.DerivedSensor(name="d3", unique_id="sigen_z", object_id="sigen_o", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=2, precision=0)
    s.set_state(3)
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
    n._states.append((time.time(), 150))
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(n.get_state(raw=False, republish=True))
    loop.close()
    assert val == 100.0 or val == 100


def test_alarm_decoding_and_truncate():
    a = base.Alarm1Sensor(name="a1", object_id="sigen_a_obj", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    bits = 1 << 2
    decoded = a._decode_alarm_bits(bits, bits)
    assert any("Over-temperature" in s or "Unknown" in s for s in decoded)
    active_config.home_assistant.enabled = True
    long_alarms = ", ".join([f"alarm{i}" for i in range(500)])
    out = a._truncate_alarms(long_alarms, None)
    assert isinstance(out, str)


def test_numeric_min_max_tuple_validation():
    with pytest.raises(AssertionError):
        base.NumericSensor(
            None,
            name="n",
            object_id="sigen_n",
            input_type=InputType.HOLDING,
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
            minimum=(0, 1),
            maximum=(0, 1, 2),
        )


def test_get_base_topic_variants():
    s = base.DerivedSensor(name="t", unique_id="sigen_topic", object_id="sigen_obj_topic", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    base_topic = s._get_base_topic("devx")
    assert base_topic.startswith("sigenergy2mqtt/")

    active_config.home_assistant.enabled = True
    active_config.home_assistant.use_simplified_topics = False
    active_config.home_assistant.discovery_prefix = "homeassistant"
    t2 = s._get_base_topic("devx")
    assert "homeassistant" in t2


def test_select_get_state_unknown_mode():
    sel = base.SelectSensor(None, name="selx", object_id="sigen_selx", plant_index=0, device_address=1, address=30020, scan_interval=1, options=["A", "B"], protocol_version=base.Protocol.N_A)
    sel.set_latest_state(0)
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(sel.get_state(raw=False, republish=True))
    loop.close()
    assert isinstance(val, str) and ("A" in val or "Unknown Mode" in val)


def test_switch_value_is_valid_and_set_value(monkeypatch):
    sw = base.SwitchSensor(None, name="sw", object_id="sigen_sw", plant_index=0, device_address=1, address=30021, scan_interval=1, protocol_version=base.Protocol.N_A)
    loop = asyncio.new_event_loop()
    res_invalid = loop.run_until_complete(sw.value_is_valid(None, 5))
    loop.close()
    assert res_invalid is False

    async def fake_write(self, modbus_client, raw_value, mqtt_client):
        return True

    monkeypatch.setattr(base.WritableSensorMixin, "_write_registers", fake_write)
    sw.configure_mqtt_topics("dev")
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(sw.set_value(Mock(), Mock(), 1, sw[base.DiscoveryKeys.COMMAND_TOPIC], Mock()))
    loop.close()
    assert res is True


def test_alarmcombined_get_state_combines_alarms():
    a1 = base.Alarm1Sensor("a1", "sigen_a1", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    a2 = base.Alarm2Sensor("a2", "sigen_a2", plant_index=0, device_address=1, address=30051, protocol_version=base.Protocol.N_A)
    a1.set_latest_state(1 << 2)
    a2.set_latest_state(1 << 1)

    comb = base.AlarmCombinedSensor("comb", "sigen_comb", "sigen_comb_obj", a1, a2)
    comb.configure_mqtt_topics("dev")
    comb.set_state("No Alarm")
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(comb.get_state(raw=False, republish=True))
    loop.close()
    assert isinstance(val, str)


def test_pv_power_notify_returns_true():
    p = base.PVPowerSensor()
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(p.notify(None, None, 1, "t", Mock()))
    loop.close()
    assert res is True
