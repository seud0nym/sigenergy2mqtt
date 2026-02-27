import json
from typing import cast
from unittest.mock import MagicMock

import pytest

from sigenergy2mqtt.common import InputType, Protocol, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.devices import Device, DeviceRegistry
from sigenergy2mqtt.modbus.types import ModbusDataType
from sigenergy2mqtt.sensors.base import AlarmSensor, EnergyDailyAccumulationSensor, ReadableSensorMixin, Sensor, TimestampSensor

SUPPORTED_DISCOVERY_KEYS = {
    "act_t",
    "act_tpl",
    "atype",
    "aux_cmd_t",
    "aux_stat_t",
    "aux_stat_tpl",
    "av_tones",
    "avty",
    "avty_mode",
    "avty_t",
    "avty_tpl",
    "away_mode_cmd_t",
    "away_mode_stat_t",
    "away_mode_stat_tpl",
    "b_tpl",
    "bri_cmd_t",
    "bri_cmd_tpl",
    "bri_scl",
    "bri_stat_t",
    "bri_tpl",
    "bri_val_tpl",
    "clr_temp_cmd_tpl",
    "clr_temp_cmd_t",
    "clr_temp_k",
    "clr_temp_stat_t",
    "clr_temp_tpl",
    "clr_temp_val_tpl",
    "clrm",
    "clrm_stat_t",
    "clrm_val_tpl",
    "cmd_off_tpl",
    "cmd_on_tpl",
    "cmd_t",
    "cmd_tpl",
    "cmps",
    "cod_arm_req",
    "cod_dis_req",
    "cod_trig_req",
    "cont_type",
    "curr_temp_t",
    "curr_temp_tpl",
    "def_ent_id",
    "dev",
    "dev_cla",
    "dir_cmd_t",
    "dir_cmd_tpl",
    "dir_stat_t",
    "dir_val_tpl",
    "dsp_prc",
    "e",
    "en",
    "ent_cat",
    "ent_pic",
    "evt_typ",
    "exp_aft",
    "fanspd_lst",
    "flsh",
    "flsh_tlng",
    "flsh_tsht",
    "fx_cmd_t",
    "fx_cmd_tpl",
    "fx_list",
    "fx_stat_t",
    "fx_tpl",
    "fx_val_tpl",
    "fan_mode_cmd_t",
    "fan_mode_cmd_tpl",
    "fan_mode_stat_t",
    "fan_mode_stat_tpl",
    "frc_upd",
    "g_tpl",
    "hs_cmd_t",
    "hs_cmd_tpl",
    "hs_stat_t",
    "hs_val_tpl",
    "ic",
    "img_e",
    "img_t",
    "init",
    "hum_cmd_t",
    "hum_cmd_tpl",
    "hum_stat_t",
    "hum_state_tpl",
    "json_attr",
    "json_attr_t",
    "json_attr_tpl",
    "l_ver_t",
    "l_ver_tpl",
    "lrst_t",
    "lrst_val_tpl",
    "max",
    "max_hum",
    "max_k",
    "max_mirs",
    "max_temp",
    "migr_discvry",
    "min",
    "min_hum",
    "min_k",
    "min_mirs",
    "min_temp",
    "mode",
    "mode_cmd_t",
    "mode_cmd_tpl",
    "mode_stat_t",
    "mode_stat_tpl",
    "modes",
    "name",
    "o",
    "off_dly",
    "on_cmd_type",
    "ops",
    "opt",
    "osc_cmd_t",
    "osc_cmd_tpl",
    "osc_stat_t",
    "osc_val_tpl",
    "p",
    "pct_cmd_t",
    "pct_cmd_tpl",
    "pct_stat_t",
    "pct_val_tpl",
    "pl",
    "pl_arm_away",
    "pl_arm_custom_b",
    "pl_arm_home",
    "pl_arm_nite",
    "pl_arm_vacation",
    "pl_avail",
    "pl_cln_sp",
    "pl_cls",
    "pl_dir_fwd",
    "pl_dir_rev",
    "pl_disarm",
    "pl_home",
    "pl_inst",
    "pl_loc",
    "pl_lock",
    "pl_not_avail",
    "pl_not_home",
    "pl_off",
    "pl_on",
    "pl_open",
    "pl_osc_off",
    "pl_osc_on",
    "pl_paus",
    "pl_prs",
    "pl_ret",
    "pl_rst",
    "pl_rst_hum",
    "pl_rst_mode",
    "pl_rst_pct",
    "pl_rst_pr_mode",
    "pl_stop",
    "pl_stop_tilt",
    "pl_stpa",
    "pl_strt",
    "pl_toff",
    "pl_ton",
    "pl_trig",
    "pl_unlk",
    "pos",
    "pos_clsd",
    "pos_open",
    "pr_mode_cmd_t",
    "pr_mode_cmd_tpl",
    "pr_mode_stat_t",
    "pr_mode_val_tpl",
    "pr_modes",
    "ptrn",
    "r_tpl",
    "rel_s",
    "rel_u",
    "ret",
    "rgb_cmd_t",
    "rgb_cmd_tpl",
    "rgb_stat_t",
    "rgb_val_tpl",
    "rgbw_cmd_t",
    "rgbw_cmd_tpl",
    "rgbw_stat_t",
    "rgbw_val_tpl",
    "rgbww_cmd_t",
    "rgbww_cmd_tpl",
    "rgbww_stat_t",
    "rgbww_val_tpl",
    "send_cmd_t",
    "send_if_off",
    "set_fan_spd_t",
    "set_pos_t",
    "set_pos_tpl",
    "pos_t",
    "pos_tpl",
    "spd_rng_min",
    "spd_rng_max",
    "src_type",
    "stat_cla",
    "stat_closing",
    "stat_clsd",
    "stat_jam",
    "stat_locked",
    "stat_locking",
    "stat_off",
    "stat_on",
    "stat_open",
    "stat_opening",
    "stat_stopped",
    "stat_unlocked",
    "stat_unlocking",
    "stat_t",
    "stat_tpl",
    "stat_val_tpl",
    "step",
    "stype",
    "sug_dsp_prc",
    "sup_clrm",
    "sup_dur",
    "sup_vol",
    "sup_feat",
    "swing_mode_cmd_t",
    "swing_mode_cmd_tpl",
    "swing_mode_stat_t",
    "swing_mode_stat_tpl",
    "t",
    "temp_cmd_t",
    "temp_cmd_tpl",
    "temp_hi_cmd_t",
    "temp_hi_cmd_tpl",
    "temp_hi_stat_t",
    "temp_hi_stat_tpl",
    "temp_lo_cmd_t",
    "temp_lo_cmd_tpl",
    "temp_lo_stat_t",
    "temp_lo_stat_tpl",
    "temp_stat_t",
    "temp_stat_tpl",
    "temp_unit",
    "tilt_clsd_val",
    "tilt_cmd_t",
    "tilt_cmd_tpl",
    "tilt_max",
    "tilt_min",
    "tilt_opnd_val",
    "tilt_opt",
    "tilt_status_t",
    "tilt_status_tpl",
    "tit",
    "trns",
    "uniq_id",
    "unit_of_meas",
    "url_t",
    "url_tpl",
    "val_tpl",
    "whit_cmd_t",
    "whit_scl",
    "xy_cmd_t",
    "xy_cmd_tpl",
    "xy_stat_t",
    "xy_val_tpl",
    # Full keys
    "action_topic",
    "action_template",
    "automation_type",
    "aux_command_topic",
    "aux_state_topic",
    "aux_state_template",
    "available_tones",
    "availability",
    "availability_mode",
    "availability_topic",
    "availability_template",
    "away_mode_command_topic",
    "away_mode_state_topic",
    "away_mode_state_template",
    "blue_template",
    "brightness_command_topic",
    "brightness_command_template",
    "brightness_scale",
    "brightness_state_topic",
    "brightness_template",
    "brightness_value_template",
    "color_temp_command_template",
    "color_temp_command_topic",
    "color_temp_kelvin",
    "color_temp_state_topic",
    "color_temp_template",
    "color_temp_value_template",
    "color_mode",
    "color_mode_state_topic",
    "color_mode_value_template",
    "command_off_template",
    "command_on_template",
    "command_topic",
    "command_template",
    "components",
    "code_arm_required",
    "code_disarm_required",
    "code_trigger_required",
    "content_type",
    "current_temperature_topic",
    "current_temperature_template",
    "default_entity_id",
    "device",
    "device_class",
    "direction_command_topic",
    "direction_command_template",
    "direction_state_topic",
    "direction_value_template",
    "display_precision",
    "encoding",
    "enabled_by_default",
    "entity_category",
    "entity_picture",
    "event_types",
    "expire_after",
    "fan_speed_list",
    "flash",
    "flash_time_long",
    "flash_time_short",
    "effect_command_topic",
    "effect_command_template",
    "effect_list",
    "effect_state_topic",
    "effect_template",
    "effect_value_template",
    "fan_mode_command_topic",
    "fan_mode_command_template",
    "fan_mode_state_topic",
    "fan_mode_state_template",
    "force_update",
    "green_template",
    "hs_command_topic",
    "hs_command_template",
    "hs_stat_topic",
    "hs_value_template",
    "icon",
    "image_encoding",
    "image_topic",
    "initial",
    "target_humidity_command_topic",
    "target_humidity_command_template",
    "target_humidity_state_topic",
    "target_humidity_state_template",
    "json_attributes",
    "json_attributes_topic",
    "json_attributes_template",
    "latest_version_topic",
    "latest_version_template",
    "last_reset_topic",
    "last_reset_value_template",
    "max",
    "max_humidity",
    "max_kelvin",
    "max_mireds",
    "max_temp",
    "migrate_discovery",
    "min",
    "min_humidity",
    "min_kelvin",
    "min_mireds",
    "min_temp",
    "mode",
    "mode_command_topic",
    "mode_command_template",
    "mode_state_topic",
    "mode_state_template",
    "modes",
    "name",
    "origin",
    "off_delay",
    "on_command_type",
    "options",
    "optimistic",
    "oscillation_command_topic",
    "oscillation_command_template",
    "oscillation_state_topic",
    "oscillation_value_template",
    "platform",
    "percentage_command_topic",
    "percentage_command_template",
    "percentage_state_topic",
    "percentage_value_template",
    "payload",
    "payload_arm_away",
    "payload_arm_custom_bypass",
    "payload_arm_home",
    "payload_arm_night",
    "payload_arm_vacation",
    "payload_available",
    "payload_clean_spot",
    "payload_close",
    "payload_direction_forward",
    "payload_direction_reverse",
    "payload_disarm",
    "payload_home",
    "payload_install",
    "payload_locate",
    "payload_lock",
    "payload_not_available",
    "payload_not_home",
    "payload_off",
    "payload_on",
    "payload_open",
    "payload_oscillation_off",
    "payload_oscillation_on",
    "payload_pause",
    "payload_press",
    "payload_return_to_base",
    "payload_reset",
    "payload_reset_humidity",
    "payload_reset_mode",
    "payload_reset_percentage",
    "payload_reset_preset_mode",
    "payload_stop",
    "payload_stop_tilt",
    "payload_start_pause",
    "payload_start",
    "payload_turn_off",
    "payload_turn_on",
    "payload_trigger",
    "payload_unlock",
    "reports_position",
    "position_closed",
    "position_open",
    "preset_mode_command_topic",
    "preset_mode_command_template",
    "preset_mode_state_topic",
    "preset_mode_value_template",
    "preset_modes",
    "pattern",
    "red_template",
    "release_summary",
    "release_url",
    "retain",
    "rgb_command_topic",
    "rgb_command_template",
    "rgb_state_topic",
    "rgb_value_template",
    "rgbw_command_topic",
    "rgbw_command_template",
    "rgbw_state_topic",
    "rgbw_val_template",
    "rgbww_command_topic",
    "rgbww_command_template",
    "rgbww_state_topic",
    "rgbww_value_template",
    "send_command_topic",
    "send_if_off",
    "set_fan_speed_topic",
    "set_position_topic",
    "set_position_template",
    "position_topic",
    "position_template",
    "speed_range_min",
    "speed_range_max",
    "source_type",
    "state_class",
    "state_closing",
    "state_closed",
    "state_jammed",
    "state_locked",
    "state_locking",
    "state_off",
    "state_on",
    "state_open",
    "state_opening",
    "state_stopped",
    "state_unlocked",
    "state_unlocking",
    "state_topic",
    "state_template",
    "state_value_template",
    "step",
    "subtype",
    "suggested_display_precision",
    "supported_color_modes",
    "support_duration",
    "support_volume_set",
    "supported_features",
    "swing_mode_command_topic",
    "swing_mode_command_template",
    "swing_mode_state_topic",
    "swing_mode_state_template",
    "topic",
    "temperature_command_topic",
    "temperature_command_template",
    "temperature_high_command_topic",
    "temperature_high_command_template",
    "temperature_high_state_topic",
    "temperature_high_state_template",
    "temperature_low_command_topic",
    "temperature_low_command_template",
    "temperature_low_state_topic",
    "temperature_low_state_template",
    "temperature_state_topic",
    "temperature_state_template",
    "temperature_unit",
    "tilt_closed_value",
    "tilt_command_topic",
    "tilt_command_template",
    "tilt_max",
    "tilt_min",
    "tilt_opened_value",
    "tilt_optimistic",
    "tilt_status_topic",
    "tilt_status_template",
    "title",
    "transition",
    "unique_id",
    "unit_of_measurement",
    "url_topic",
    "url_template",
    "value_template",
    "white_command_topic",
    "white_scale",
    "xy_command_topic",
    "xy_command_template",
    "xy_state_topic",
    "xy_val_template",
}

SUPPORTED_DEVICE_KEYS = {
    # Abbreviations
    "cu",
    "cns",
    "ids",
    "name",
    "mf",
    "mdl",
    "mdl_id",
    "hw",
    "sw",
    "sa",
    "sn",
    # Full keys
    "configuration_url",
    "connections",
    "identifiers",
    "name",
    "manufacturer",
    "model",
    "model_id",
    "hw_version",
    "sw_version",
    "suggested_area",
    "serial_number",
}


SUPPORTED_ORIGIN_KEYS = {"name", "sw", "url", "sw_version", "support_url"}


def assert_keys_valid(data, allowed_keys, context=""):
    """Helper to assert that all keys in a dictionary are in the allowed set."""
    if not isinstance(data, dict) or not data:
        return
    invalid_keys = [k for k in data.keys() if k not in allowed_keys]
    assert not invalid_keys, f"Invalid keys found in {context}: {invalid_keys}. Allowed keys: {allowed_keys}"


class DummySensor(ReadableSensorMixin):
    def __init__(self, name, unique_id, address):
        super().__init__(
            name=name, unique_id=unique_id, object_id=unique_id, unit=UnitOfPower.WATT, device_class="power", state_class=StateClass.MEASUREMENT, icon="mdi:flash", gain=1.0, precision=2, scan_interval=60
        )
        self.address = address
        self.count = 1
        self.device_address = 1
        self.input_type = InputType.HOLDING
        self.data_type = ModbusDataType.UINT16
        self._publishable = True
        # For discovery to work, these MUST be set or configured
        self["state_topic"] = f"state/{unique_id}"
        self["json_attributes_topic"] = f"state/{unique_id}/attr"

    async def _update_internal_state(self, **kwargs) -> bool:
        return False

    def configure_mqtt_topics(self, device_id):
        self["state_topic"] = f"state/{device_id}/{self.unique_id}"
        self["json_attributes_topic"] = f"state/{device_id}/{self.unique_id}/attr"
        return self["state_topic"]


@pytest.fixture
def mock_config(tmp_path):
    # Ensure logging level doesn't trigger discovery dump unless we want it
    import logging

    old_level = logging.getLogger().level

    cfg = Config()
    cfg.home_assistant.enabled = True
    cfg.home_assistant.discovery_prefix = "homeassistant"
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"
    cfg.home_assistant.use_simplified_topics = False
    cfg.home_assistant.device_name_prefix = ""
    cfg.home_assistant.enabled_by_default = True
    cfg.origin = {"name": "sigenergy2mqtt", "sw": "1.0", "url": "http://test"}
    cfg.persistent_state_path = tmp_path
    cfg.clean = False

    mock_device = MagicMock()
    mock_device.registers = None
    mock_device.scan_interval.realtime = 5
    cfg.modbus = [mock_device]

    cfg.sensor_overrides = {}
    cfg.sensor_debug_logging = False

    with _swap_active_config(cfg):
        yield cfg

    logging.getLogger().setLevel(old_level)
    DeviceRegistry._devices.clear()
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()


def get_discovery_payload(mqtt_mock):
    """Helper to extract discovery payload from mqtt mock."""
    for call in mqtt_mock.publish.call_args_list:
        topic = call[0][0] if call[0] else call[1].get("topic")
        if topic and topic.endswith("/config"):
            payload = call[0][1] if len(call[0]) > 1 else call[1].get("payload")
            if payload is not None:
                return topic, json.loads(payload)
    return None, None


def test_discovery_base_structure(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    sensor = DummySensor("TestSensor", "sigen_s1", 100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    topic, discovery = get_discovery_payload(mqtt_client)

    assert topic == "homeassistant/device/sigen_uid/config"
    assert "dev" in discovery
    assert "o" in discovery
    assert "cmps" in discovery

    assert discovery["dev"]["name"] == "TestDevice"
    assert "sigen_s1" in discovery["cmps"]
    comp = discovery["cmps"]["sigen_s1"]
    assert comp["platform"] == "sensor"
    assert comp["name"] == "TestSensor"


def test_energy_daily_accumulation_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    source = DummySensor("Power", "sigen_power", 100)
    dev._add_read_sensor(cast(Sensor, source))

    sensor = EnergyDailyAccumulationSensor("Daily Energy", "sigen_daily", "sigen_daily", source)
    dev._add_to_all_sensors(sensor)

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    key = "sigen_daily"
    assert key in discovery["cmps"]
    comp = discovery["cmps"][key]
    assert comp["device_class"] == "power"
    assert comp["state_class"] == "measurement"


def test_alarm_sensor_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)

    class ConcreteAlarm(AlarmSensor):
        def decode_alarm_bit(self, bit):
            return "Error"

    sensor = ConcreteAlarm("Alarm1", "sigen_alarm1", 0, 1, 30001, Protocol.V1_8, "Equipment")
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    expected_id = "sigen_0_001_30001"
    assert expected_id in discovery["cmps"]
    comp = discovery["cmps"][expected_id]
    assert comp["platform"] == "sensor"


def test_timestamp_sensor_discovery(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)

    # name, object_id, input_type, plant_index, device_address, address, scan_interval, protocol_version
    sensor = TimestampSensor("UpdateTime", "sigen_ts1", InputType.INPUT, 0, 1, 30005, 60, Protocol.V1_8)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)

    expected_id = "sigen_0_001_30005"
    assert expected_id in discovery["cmps"]
    comp = discovery["cmps"][expected_id]
    assert comp["entity_category"] == "diagnostic"
    assert comp["device_class"] == "timestamp"


def test_simplified_topics_discovery(mock_config):
    mock_config.home_assistant.use_simplified_topics = True

    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    sensor = DummySensor("TestSensor", "sigen_s1", 100)
    dev._add_read_sensor(cast(Sensor, sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    _, discovery = get_discovery_payload(mqtt_client)
    comp = discovery["cmps"]["sigen_s1"]

    assert "sigen_s1" in comp["state_topic"]


def test_discovery_keys_validity(mock_config):
    dev = Device("TestDevice", 0, "sigen_uid", "Sigenergy", "SigenStor", Protocol.V1_8)
    sensor = DummySensor("TestSensor", "sigen_s1", 100)
    dev._add_read_sensor(cast(Sensor, sensor))

    # Add various types of sensors to ensure mixed discovery content
    source = DummySensor("Power", "sigen_power", 101)
    dev._add_read_sensor(cast(Sensor, source))
    energy_sensor = EnergyDailyAccumulationSensor("Daily Energy", "sigen_daily", "sigen_daily", source)
    dev._add_to_all_sensors(energy_sensor)
    ts_sensor = TimestampSensor("UpdateTime", "sigen_ts1", InputType.INPUT, 0, 1, 30005, 60, Protocol.V1_8)
    dev._add_read_sensor(cast(Sensor, ts_sensor))

    mqtt_client = MagicMock()
    dev.publish_discovery(mqtt_client)

    topic, discovery = get_discovery_payload(mqtt_client)

    # Validate main discovery keys
    assert_keys_valid(discovery, SUPPORTED_DISCOVERY_KEYS, "main discovery")

    # Validate device keys
    if "dev" in discovery:
        assert_keys_valid(discovery["dev"], SUPPORTED_DEVICE_KEYS, "device (dev)")
    if "device" in discovery:
        assert_keys_valid(discovery["device"], SUPPORTED_DEVICE_KEYS, "device (device)")

    # Validate origin keys
    if "o" in discovery:
        assert_keys_valid(discovery["o"], SUPPORTED_ORIGIN_KEYS, "origin (o)")
    if "origin" in discovery:
        assert_keys_valid(discovery["origin"], SUPPORTED_ORIGIN_KEYS, "origin (origin)")

    # Validate components
    if "cmps" in discovery:
        for comp_id, comp_config in discovery["cmps"].items():
            assert_keys_valid(comp_config, SUPPORTED_DISCOVERY_KEYS, f"component {comp_id}")
            if "avty" in comp_config:  # availability
                avty = comp_config["avty"]
                if isinstance(avty, list):
                    for item in avty:
                        assert_keys_valid(item, SUPPORTED_DISCOVERY_KEYS | {"topic", "t"}, f"availability item in {comp_id}")
                else:
                    assert_keys_valid(avty, SUPPORTED_DISCOVERY_KEYS | {"topic", "t"}, f"availability in {comp_id}")
