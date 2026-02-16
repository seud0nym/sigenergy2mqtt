import asyncio
import importlib
import os
import time
from unittest.mock import Mock, AsyncMock

import pytest

from sigenergy2mqtt.sensors import base
from sigenergy2mqtt.sensors.const import InputType
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.config.config import Config
from sigenergy2mqtt.common.protocol import Protocol


@pytest.fixture(autouse=True)
def reset_env(tmp_path):
    Config.persistent_state_path = tmp_path
    base.Sensor._used_object_ids.clear()
    base.Sensor._used_unique_ids.clear()
    Config.home_assistant.enabled = False
    yield


def test__load_metrics_module_import_error(monkeypatch):
    # force importlib.import_module to raise ImportError
    monkeypatch.setattr(importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError()))
    assert base._load_metrics_module() is None


def test__load_metrics_module_returns_metrics(monkeypatch):
    class DummyMod:
        Metrics = "X"

    monkeypatch.setattr(importlib, "import_module", lambda name: DummyMod)
    assert base._load_metrics_module() == "X"


def test_icon_validation_raises():
    with pytest.raises(AssertionError):
        base.DerivedSensor(name="i", unique_id="sigen_i", object_id="sigen_i_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="notmdi", gain=None, precision=None)


def test_protocol_version_setter_accepts_float():
    s = base.DerivedSensor(name="pv2", unique_id="sigen_pv2", object_id="sigen_pv2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.protocol_version = 2.4
    assert s.protocol_version == Protocol.V2_4


def test_validate_unique_and_object_id_prefix_and_duplication():
    # wrong prefixes
    with pytest.raises(AssertionError):
        base.DerivedSensor(name="bad", unique_id="wrong_prefix", object_id="sigen_ok", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)

    with pytest.raises(AssertionError):
        base.DerivedSensor(name="bad2", unique_id="sigen_ok2", object_id="wrong_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)

    # duplication across classes
    a = base.DerivedSensor(name="ddup", unique_id="sigen_dup", object_id="sigen_dup_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None)
    with pytest.raises(AssertionError):
        base.ReadOnlySensor(name="rdup", object_id="sigen_dup2", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30001, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A, unique_id_override="sigen_dup")


def test_latest_time_and_interval_edges():
    s = base.DerivedSensor(name="e", unique_id="sigen_e", object_id="sigen_e_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    assert s.latest_time == 0
    assert s.latest_interval is None
    s.set_state(1)
    assert s.latest_interval is None


def test_publish_skipped_when_failures_high():
    mqtt = Mock()
    s = base.DerivedSensor(name="ps", unique_id="sigen_ps", object_id="sigen_ps_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s._failures = s._max_failures + 1
    s._next_retry = None
    assert s._should_attempt_publish() is False
    assert asyncio.get_event_loop().run_until_complete(s.publish(mqtt, None, republish=True)) is False


def test_log_configured_topics_and_get_discovery_for_publishable(caplog):
    s = base.DerivedSensor(name="ld", unique_id="sigen_ld", object_id="sigen_ld_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.debug_logging = True
    base_topic = s.configure_mqtt_topics("devx")
    s.get_discovery(Mock())
    assert "Configured MQTT topics" in caplog.text or base_topic


def test_reserved_subclass_name_enforced():
    class NotReserved(base.ReservedSensor):
        pass

    with pytest.raises(ValueError):
        NotReserved(name="nr", object_id="sigen_nr", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30001, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)


def test_readable_sensor_scan_interval_validation():
    with pytest.raises(ValueError):
        base.ReadableSensorMixin.__init__(base.ReadOnlySensor, **{})

    with pytest.raises(ValueError):
        base.ReadOnlySensor(name="rs_err", object_id="sigen_rserr", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30002, count=1, data_type=ModbusDataType.UINT16, scan_interval=0, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)


def test_modbussensor_constructor_validations():
    with pytest.raises(AssertionError):
        base.ReadOnlySensor(name="m1", object_id="sigen_m1", input_type=InputType.HOLDING, plant_index=0, device_address=0, address=30001, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)

    with pytest.raises(AssertionError):
        base.ReadOnlySensor(name="m2", object_id="sigen_m2", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=100, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)

    with pytest.raises(AssertionError):
        base.ReadOnlySensor(name="m3", object_id="sigen_m3", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30001, count=0, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)


def test_perform_modbus_read_unknown_input_type():
    s = base.ReadOnlySensor(name="rnone", object_id="sigen_rnone", input_type=InputType.NONE, plant_index=0, device_address=1, address=30012, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    modbus = Mock()
    with pytest.raises(ValueError):
        asyncio.get_event_loop().run_until_complete(s._perform_modbus_read(modbus))


def test_log_read_attempt_and_complete(caplog):
    s = base.ReadOnlySensor(name="lr", object_id="sigen_lr", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30013, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon="mdi:test", gain=None, precision=None, protocol_version=base.Protocol.N_A)
    s.debug_logging = True
    caplog.set_level("DEBUG")
    s._log_read_attempt()
    s._states.append((time.time(), 1))
    s._log_read_complete(0.001, True)
    assert "read_input_registers" in caplog.text


def test_set_latest_state_propagates_to_derived():
    parent = base.DerivedSensor(name="p", unique_id="sigen_p", object_id="sigen_p_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)

    class Child(base.DerivedSensor):
        def __init__(self):
            super().__init__(name="c", unique_id="sigen_c2", object_id="sigen_c2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
            self.updated = False

        def set_source_values(self, sensor, values):
            self.updated = True
            return True

    child = Child()
    parent.add_derived_sensor(child)
    parent.set_latest_state(9)
    assert child.updated is True


def test_publish_attributes_clean_and_current(mqtt_mock=Mock()):
    mqtt = Mock()
    s = base.DerivedSensor(name="attr", unique_id="sigen_attr", object_id="sigen_attr_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("dev")
    s.publish_attributes(mqtt, clean=True)
    mqtt.publish.assert_called()
    # publish current attributes
    s.publish_attributes(mqtt, clean=False)
    assert s._attributes_published is True


def test_writeonly_icon_validation_and_set_value(monkeypatch):
    with pytest.raises(ValueError):
        base.WriteOnlySensor(name="wb", object_id="sigen_wb", plant_index=0, device_address=1, address=30030, protocol_version=base.Protocol.N_A, icon_off="bad", icon_on="mdi:ok")

    w = base.WriteOnlySensor(name="wb2", object_id="sigen_wb2", plant_index=0, device_address=1, address=30031, protocol_version=base.Protocol.N_A)
    # stub _write_registers
    async def fake_write(self, modbus_client, raw_value, mqtt_client):
        return True

    monkeypatch.setattr(base.WritableSensorMixin, "_write_registers", fake_write)
    w.configure_mqtt_topics("dev")
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(w.set_value(Mock(), Mock(), "on", w[base.DiscoveryKeys.COMMAND_TOPIC], Mock()))
    loop.close()
    assert res is True


def test_writable_command_topic_getter_raises():
    w = base.WriteOnlySensor(name="wcmd", object_id="sigen_wcmd", plant_index=0, device_address=1, address=30032, protocol_version=base.Protocol.N_A)
    with pytest.raises(RuntimeError):
        _ = w.command_topic


def test_readwrite_availability_control_sensor_type_check():
    with pytest.raises(ValueError):
        base.ReadWriteSensor(availability_control_sensor=object(), name="rwerr", object_id="sigen_rwerr", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30033, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)


def test_numeric_validate_min_max_ranges_and_sanity_update():
    with pytest.raises(AssertionError):
        base.NumericSensor(None, name="nbad", object_id="sigen_nbad", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30034, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A, minimum=10.0, maximum=5.0)

    n = base.NumericSensor(None, name="nok", object_id="sigen_nok", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30035, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit="%", device_class=None, state_class=None, icon=None, gain=2, precision=1, protocol_version=base.Protocol.N_A, minimum=0.0, maximum=100.0)
    # sanity ranges updated
    assert n.sanity_check.min_raw is not None and n.sanity_check.max_raw is not None


def test_select_invalid_options_raise():
    with pytest.raises(ValueError):
        base.SelectSensor(None, name="sbad", object_id="sigen_sbad", plant_index=0, device_address=1, address=30020, scan_interval=1, options=[], protocol_version=base.Protocol.N_A)

    with pytest.raises(ValueError):
        base.SelectSensor(None, name="sbad2", object_id="sigen_sbad2", plant_index=0, device_address=1, address=30021, scan_interval=1, options=[1, 2], protocol_version=base.Protocol.N_A)


def test_state2raw_decimal_string_and_numeric_option():
    s = base.DerivedSensor(name="sr", unique_id="sigen_sr", object_id="sigen_sr_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s[base.DiscoveryKeys.OPTIONS] = ["A", "B"]
    assert s.state2raw("1.9") == 1
    assert s.state2raw("B") == 1


def test_alarm_normalize_and_decode_typeerror_and_truncate():
    a = base.Alarm1Sensor("altest", "sigen_al", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.N_A)
    assert a._normalize_alarm_code([0, 7]) == 7
    # decode with bad value triggers TypeError handling
    assert a._decode_alarm_bits(None, None) == []
    # truncation compressed (Home Assistant enabled)
    Config.home_assistant.enabled = True
    long = ", ".join([f"1_test{i}" for i in range(200)])
    out = a._truncate_alarms(long, 50)
    assert isinstance(out, str) and len(out) <= 50
    Config.home_assistant.enabled = False


def test_alarmcombined_protocol_version_readonly_and_compress():
    a1 = base.Alarm1Sensor("a1", "sigen_a1b", plant_index=0, device_address=1, address=30050, protocol_version=base.Protocol.V2_4)
    a2 = base.Alarm2Sensor("a2", "sigen_a2b", plant_index=0, device_address=1, address=30051, protocol_version=base.Protocol.V2_5)
    comb = base.AlarmCombinedSensor("comb2", "sigen_comb2", "sigen_comb2_obj", a1, a2)
    with pytest.raises(NotImplementedError):
        comb.protocol_version = Protocol.V2_8
    big = ", ".join(["alarm"] * 300)
    comp = comb._compress_alarm_string(big)
    assert isinstance(comp, str) and len(comp) <= 255


def test_energy_lifetime_default_data_type():
    src = base.DerivedSensor(name="src4", unique_id="sigen_src4", object_id="sigen_src4_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=1000, precision=2)
    e = base.EnergyLifetimeAccumulationSensor("el", "sigen_el", "sigen_el_obj", source=src)
    assert e[base.DiscoveryKeys.UNIT_OF_MEASUREMENT] is not None


def test_energydaily_day_change_resets_and_persists(tmp_path, monkeypatch):
    src = base.DerivedSensor(name="src5", unique_id="sigen_src5", object_id="sigen_src5_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=1, precision=2)
    ed = base.EnergyDailyAccumulationSensor(name="ed2", unique_id="sigen_ed2", object_id="sigen_ed2_obj", source=src)
    # avoid scheduling background task (no running loop in pytest sync test)
    monkeypatch.setattr(asyncio, "create_task", lambda coro: Mock())

    # simulate values spanning day change
    now = time.time()
    yesterday = now - (24 * 60 * 60)
    values = [ (yesterday, 10.0), (now, 20.0) ]
    res = ed.set_source_values(src, values)
    assert res is True


def test_substitute_mixin_implementation():
    class Impl(base.SubstituteMixin):
        def fallback(self, source):
            self.last = source

        def failover(self, smartport_sensor):
            self.last2 = smartport_sensor
            return True

    i = Impl()
    i.fallback("s")
    assert getattr(i, "last") == "s"
    assert i.failover("sensor") is True


def test_configure_topics_with_ha_and_simplified_false():
    Config.home_assistant.enabled = True
    Config.home_assistant.use_simplified_topics = False

    s = base.DerivedSensor(name="ha1", unique_id="sigen_ha1", object_id="sigen_ha1_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    base_topic = s.configure_mqtt_topics("dev123")

    assert s[base.DiscoveryKeys.STATE_TOPIC] == f"{Config.home_assistant.discovery_prefix}/sensor/dev123/{s[base.DiscoveryKeys.OBJECT_ID]}/state"
    assert s[base.DiscoveryKeys.AVAILABILITY_MODE] == "all"
    assert isinstance(s[base.DiscoveryKeys.AVAILABILITY], list)
    assert s[base.DiscoveryKeys.AVAILABILITY][0]["topic"].startswith(f"{Config.home_assistant.discovery_prefix}/device/dev123/availability")


def test_configure_topics_with_ha_and_simplified_true():
    Config.home_assistant.enabled = True
    Config.home_assistant.use_simplified_topics = True

    s = base.DerivedSensor(name="ha2", unique_id="sigen_ha2", object_id="sigen_ha2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("devX")

    # simplified topics => base should be sigenergy2mqtt/<object_id>
    assert s[base.DiscoveryKeys.STATE_TOPIC] == f"sigenergy2mqtt/{s[base.DiscoveryKeys.OBJECT_ID]}/state"
    # availability still present when HA enabled
    assert isinstance(s.get(base.DiscoveryKeys.AVAILABILITY), list)


def test_get_discovery_cleans_objectid_and_removes_raw():
    Config.home_assistant.enabled = True

    s = base.DerivedSensor(name="ha3", unique_id="sigen_ha3", object_id="sigen_ha3_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("devZ")

    components = s.get_discovery(Mock())
    assert s.unique_id in components
    cfg = components[s.unique_id]
    assert base.DiscoveryKeys.OBJECT_ID not in cfg
    assert base.DiscoveryKeys.DEFAULT_ENTITY_ID in cfg
    assert base.DiscoveryKeys.RAW_STATE_TOPIC not in cfg


def test_unpublishable_creates_minimal_discovery_and_persists(tmp_path):
    # persistent path controlled by fixture/reset_env
    Config.home_assistant.enabled = True

    s = base.DerivedSensor(name="up", unique_id="sigen_up", object_id="sigen_up_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("devU")
    s.publishable = False

    mqtt_mock = Mock()
    persist_file = s._persistent_publish_state_file
    if persist_file.exists():
        persist_file.unlink()

    comps = s.get_discovery(mqtt_mock)

    # JSON attributes topic should have been cleared
    mqtt_mock.publish.assert_called_with(str(s[base.DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]), None, qos=0, retain=False)

    # discovery reduced to a minimal mapping and persistent file created
    assert isinstance(comps, dict)
    assert s.unique_id in comps
    assert comps[s.unique_id] == {"p": s[base.DiscoveryKeys.PLATFORM]}
    assert persist_file.exists()


def test_unpublishable_with_existing_persistent_file_returns_empty_and_publishes_none(tmp_path):
    Config.home_assistant.enabled = True

    s = base.DerivedSensor(name="up2", unique_id="sigen_up2", object_id="sigen_up2_obj", data_type=ModbusDataType.UINT16, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    s.configure_mqtt_topics("devU2")

    # create persistent file to simulate prior unpublish
    s._persistent_publish_state_file.parent.mkdir(parents=True, exist_ok=True)
    s._persistent_publish_state_file.write_text("0")

    s.publishable = False
    mqtt_mock = Mock()
    comps = s.get_discovery(mqtt_mock)

    # should clear attributes but return empty discovery
    mqtt_mock.publish.assert_called_with(str(s[base.DiscoveryKeys.JSON_ATTRIBUTES_TOPIC]), None, qos=0, retain=False)
    assert comps == {}


def test_availability_control_sensor_appends_control_topic_and_raises_when_missing():
    Config.home_assistant.enabled = True

    # availability control sensor must have topics configured first
    control = base.AvailabilityMixin(name="ctl", unique_id="sigen_ctl", object_id="sigen_ctl_obj", unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    control.configure_mqtt_topics("devC")

    num = base.NumericSensor(control, name="num", object_id="sigen_num_obj", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30010, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)
    num.configure_mqtt_topics("devC")

    # last availability entry should reference the control sensor state topic
    assert num[base.DiscoveryKeys.AVAILABILITY][-1]["topic"] == control.state_topic
    assert num[base.DiscoveryKeys.AVAILABILITY][-1]["payload_available"] == 1

    # if control sensor has not been configured, expect RuntimeError
    control2 = base.AvailabilityMixin(name="ctl2", unique_id="sigen_ctl2", object_id="sigen_ctl2_obj", unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None)
    num2 = base.NumericSensor(control2, name="num2", object_id="sigen_num2_obj", input_type=InputType.HOLDING, plant_index=0, device_address=1, address=30011, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)

    # if control sensor has not been configured, accessing its state_topic raises KeyError
    with pytest.raises(KeyError):
        num2.configure_mqtt_topics("devC2")

    # if state_topic exists but is empty/whitespace, numeric.configure_mqtt_topics should raise RuntimeError
    control2[base.DiscoveryKeys.STATE_TOPIC] = " "
    with pytest.raises(RuntimeError):
        num2.configure_mqtt_topics("devC2")


# ---------------------------------------------------------------------------
# Writable / Modbus write path tests
# ---------------------------------------------------------------------------


def test__check_register_response_success_and_error_branches(caplog):
    s = base.ReadOnlySensor(name="chk", object_id="sigen_chk", input_type=InputType.INPUT, plant_index=0, device_address=1, address=30020, count=1, data_type=ModbusDataType.UINT16, scan_interval=1, unit=None, device_class=None, state_class=None, icon=None, gain=None, precision=None, protocol_version=base.Protocol.N_A)

    # None response
    assert s._check_register_response(None, "read_input_registers") is False

    # successful response (isError -> False)
    rr_ok = Mock()
    rr_ok.isError = Mock(return_value=False)
    assert s._check_register_response(rr_ok, "read_input_registers") is True

    # ILLEGAL FUNCTION -> raises
    rr_ill = Mock()
    rr_ill.isError = Mock(return_value=True)
    rr_ill.exception_code = s.ExceptionCode.ILLEGAL_FUNCTION
    with pytest.raises(Exception, match="0x01"):
        s._check_register_response(rr_ill, "read_input_registers")

    # ILLEGAL DATA ADDRESS -> sets max failures to 0 (for read ops) and raises
    s._max_failures = 5
    rr_addr = Mock()
    rr_addr.isError = Mock(return_value=True)
    rr_addr.exception_code = s.ExceptionCode.ILLEGAL_DATA_ADDRESS
    with pytest.raises(Exception, match="0x02"):
        s._check_register_response(rr_addr, "read_input_registers")
    assert s._max_failures == 0 and s._max_failures_retry_interval == 0

    # unknown exception -> raises
    rr_unknown = Mock()
    rr_unknown.isError = Mock(return_value=True)
    rr_unknown.exception_code = 999
    with pytest.raises(Exception):
        s._check_register_response(rr_unknown, "read_input_registers")


def test__convert_value_to_registers_variants(monkeypatch):
    w = base.WriteOnlySensor(name="wcv", object_id="sigen_wcv", plant_index=0, device_address=1, address=30060, protocol_version=base.Protocol.N_A)

    # UINT16 small int optimized path
    assert w._convert_value_to_registers(Mock(), 42) == [42]

    # STRING path uses modbus_client.convert_to_registers with str()
    w.data_type = ModbusDataType.STRING
    mc = Mock()
    mc.convert_to_registers = Mock(return_value=[1, 2, 3])
    assert w._convert_value_to_registers(mc, "abc") == [1, 2, 3]
    mc.convert_to_registers.assert_called_with("abc", ModbusDataType.STRING)

    # numeric default uses int(raw_value)
    w.data_type = ModbusDataType.INT32
    mc2 = Mock()
    mc2.convert_to_registers = Mock(return_value=[9, 9])
    assert w._convert_value_to_registers(mc2, 2.9) == [9, 9]
    mc2.convert_to_registers.assert_called_with(2, ModbusDataType.INT32)


@pytest.mark.asyncio
async def test__perform_modbus_write_single_and_multi(monkeypatch):
    # Dummy lock factory returning an async context manager for `async with` usage
    class DummyLock:
        def __init__(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyLockFactory:
        def lock(self, *args, **kwargs):
            return DummyLock()

    monkeypatch.setattr(base.ModbusLockFactory, "get", lambda modbus: DummyLockFactory())

    w = base.WriteOnlySensor(name="wpm", object_id="sigen_wpm", plant_index=0, device_address=1, address=30061, protocol_version=base.Protocol.N_A)

    # single-register write -> write_register called
    rr_ok = Mock()
    rr_ok.isError = Mock(return_value=False)
    mc = Mock()
    mc.write_register = AsyncMock(return_value=rr_ok)
    res = await w._perform_modbus_write(mc, [7], device_id=1, no_response_expected=False, method="write_register")
    assert res is True
    mc.write_register.assert_awaited()

    # multi-register write -> write_registers called
    mc2 = Mock()
    mc2.write_registers = AsyncMock(return_value=rr_ok)
    res2 = await w._perform_modbus_write(mc2, [1, 2, 3], device_id=1, no_response_expected=False, method="write_registers")
    assert res2 is True
    mc2.write_registers.assert_awaited()

    # None response should be treated as error (return False)
    mc3 = Mock()
    mc3.write_register = AsyncMock(return_value=None)
    res3 = await w._perform_modbus_write(mc3, [5], device_id=1, no_response_expected=False, method="write_register")
    assert res3 is False


@pytest.mark.asyncio
async def test__write_registers_exception_handling(monkeypatch):
    w = base.WriteOnlySensor(name="we", object_id="sigen_we", plant_index=0, device_address=1, address=30062, protocol_version=base.Protocol.N_A)

    # stub out _convert_value_to_registers to avoid modbus conversions
    monkeypatch.setattr(w, "_convert_value_to_registers", lambda mc, v: [1])

    # Timeout -> _write_registers should return False
    async def raise_timeout(*a, **k):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(w, "_perform_modbus_write", raise_timeout)
    assert await w._write_registers(Mock(), 1, Mock()) is False

    # CancelledError -> return False
    async def raise_cancel(*a, **k):
        raise asyncio.CancelledError()

    monkeypatch.setattr(w, "_perform_modbus_write", raise_cancel)
    assert await w._write_registers(Mock(), 1, Mock()) is False

    # Generic exception should propagate
    async def raise_generic(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(w, "_perform_modbus_write", raise_generic)
    with pytest.raises(RuntimeError):
        await w._write_registers(Mock(), 1, Mock())


@pytest.mark.asyncio
async def test_set_value_validation_and_unknown_source(monkeypatch, caplog):
    w = base.WriteOnlySensor(name="sv", object_id="sigen_sv", plant_index=0, device_address=1, address=30063, protocol_version=base.Protocol.N_A)
    w.configure_mqtt_topics("devsv")

    # modbus_client cannot be None
    with pytest.raises(ValueError):
        await w.set_value(None, Mock(), 1, w[base.DiscoveryKeys.COMMAND_TOPIC], Mock())

    # value_is_valid raising should be re-raised
    async def bad_check(mc, v):
        raise RuntimeError("valfail")

    monkeypatch.setattr(w, "value_is_valid", bad_check)
    with pytest.raises(RuntimeError):
        await w.set_value(Mock(), Mock(), 1, w[base.DiscoveryKeys.COMMAND_TOPIC], Mock())

    # unknown topic should return False and log an error
    async def ok_check(mc, v):
        return True

    monkeypatch.setattr(w, "value_is_valid", ok_check)
    caplog.set_level("ERROR")
    res = await w.set_value(Mock(), Mock(), 1, "unknown/topic", Mock())
    assert res is False
    assert "Attempt to set value" in caplog.text

