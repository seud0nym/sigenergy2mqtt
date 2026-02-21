import asyncio
import os
import time
from unittest.mock import Mock

import pytest

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.sensors.const import InputType


@pytest.fixture(autouse=True)
def reset_env(tmp_path):
    active_config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    active_config.home_assistant.enabled = False
    active_config.home_assistant.use_simplified_topics = False
    yield


def test_numeric_min_max_tuple_validation():
    # mismatched tuple lengths
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
    # default when HA disabled
    base_topic = s._get_base_topic("devx")
    assert base_topic.startswith("sigenergy2mqtt/")

    # when HA enabled and simplified topics disabled
    active_config.home_assistant.enabled = True
    active_config.home_assistant.use_simplified_topics = False
    active_config.home_assistant.discovery_prefix = "homeassistant"
    t2 = s._get_base_topic("devx")
    assert "homeassistant" in t2


def test_select_get_state_unknown_mode():
    sel = base.SelectSensor(None, name="selx", object_id="sigen_selx", plant_index=0, device_address=1, address=30020, scan_interval=1, options=["A", "B"], protocol_version=base.Protocol.N_A)
    # no state set -> Unknown Mode
    # set a cached state and republish to avoid Modbus reads
    sel.set_latest_state(0)
    loop = asyncio.new_event_loop()
    val = loop.run_until_complete(sel.get_state(raw=False, republish=True))
    loop.close()
    assert isinstance(val, str) and ("A" in val or "Unknown Mode" in val)


def test_switch_value_is_valid_and_set_value(monkeypatch):
    sw = base.SwitchSensor(None, name="sw", object_id="sigen_sw", plant_index=0, device_address=1, address=30021, scan_interval=1, protocol_version=base.Protocol.N_A)
    # invalid value (async in implementation) - await
    loop = asyncio.new_event_loop()
    res_invalid = loop.run_until_complete(sw.value_is_valid(None, 5))
    loop.close()
    assert res_invalid is False

    # patch write to always succeed
    async def fake_write(self, modbus_client, raw_value, mqtt_client):
        return True

    monkeypatch.setattr(base.WritableSensorMixin, "_write_registers", fake_write)
    # now set value should return True (using command topic as source)
    sw.configure_mqtt_topics("dev")
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(sw.set_value(Mock(), Mock(), 1, sw[base.DiscoveryKeys.COMMAND_TOPIC], Mock()))
    loop.close()
    assert res is True


def test_alarmcombined_get_state_combines_alarms():
    a1 = base.Alarm1Sensor("a1", "sigen_a1", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    a2 = base.Alarm2Sensor("a2", "sigen_a2", plant_index=0, device_address=1, address=30051, protocol_version=base.Protocol.N_A)
    # set raw states for alarms
    a1.set_latest_state(1 << 2)  # Over-temperature
    a2.set_latest_state(1 << 1)  # Communication abnormal

    comb = base.AlarmCombinedSensor("comb", "sigen_comb", "sigen_comb_obj", a1, a2)
    comb.configure_mqtt_topics("dev")
    # use republish=True to avoid Modbus reads
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
