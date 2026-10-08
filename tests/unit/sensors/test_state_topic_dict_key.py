"""Tests for the state_topic_dict_key property introduced in sensor.py.

Covers:
- Default initialisation to None
- Getter
- Setter validation (TypeError for non-str/None, AssertionError when STATE_TOPIC already set)
- Setter no-op when value unchanged (including debug-log branch)
- Setter sets value and logs when changed
- configure_mqtt_topics() builds STATE_TOPIC with/without state_topic_dict_key
- Dict-state publish strips the key suffix from state_topic before fanning out subtopics
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor
from sigenergy2mqtt.sensors.base.constants import DiscoveryKeys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return False


def _make_sensor(uid_suffix: str, debug: bool = False, **kwargs) -> ConcreteSensor:
    """Return a fresh ConcreteSensor with cleared ID registries."""
    uid = f"sigen_stdkey_{uid_suffix}"
    oid = f"sigen_stdkey_{uid_suffix}"

    cfg = Config()
    cfg.home_assistant.enabled = False
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"

    with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        s = ConcreteSensor(
            name="Test Sensor",
            unique_id=uid,
            object_id=oid,
            unit=UnitOfPower.WATT,
            device_class=DeviceClass.POWER,
            state_class=StateClass.MEASUREMENT,
            icon="mdi:solar-power",
            gain=1.0,
            precision=2,
            protocol_version=ProtocolVersion.V2_4,
            debug_logging=debug,
            **kwargs,
        )
    return s


def _mqtt_mock() -> MagicMock:
    m = MagicMock()
    m.publish.return_value.is_published.return_value = True
    return m


# ---------------------------------------------------------------------------
# 1. Initialisation
# ---------------------------------------------------------------------------


class TestStatTopicDictKeyInit:
    def test_default_value_is_none(self):
        """_state_topic_dict_key is None after __init__."""
        s = _make_sensor("init_none")
        assert s._state_topic_dict_key is None

    def test_getter_returns_none_by_default(self):
        """state_topic_dict_key property returns None before any assignment."""
        s = _make_sensor("getter_none")
        assert s.state_topic_dict_key is None


# ---------------------------------------------------------------------------
# 2. Setter - type validation
# ---------------------------------------------------------------------------


class TestStatTopicDictKeySetterTypeValidation:
    def test_set_to_valid_string(self):
        """Setting to a valid string stores the value."""
        s = _make_sensor("set_str")
        s.state_topic_dict_key = "power"
        assert s.state_topic_dict_key == "power"

    def test_set_to_none_is_allowed(self):
        """Setting to None is allowed (resets to default)."""
        s = _make_sensor("set_none2")
        s.state_topic_dict_key = None
        assert s.state_topic_dict_key is None

    def test_set_to_integer_raises_type_error(self):
        """Non-str, non-None values raise TypeError."""
        s = _make_sensor("set_int")
        with pytest.raises(TypeError, match="must be a string or None"):
            s.state_topic_dict_key = 42  # type: ignore[assignment]

    def test_set_to_list_raises_type_error(self):
        """A list value raises TypeError."""
        s = _make_sensor("set_list")
        with pytest.raises(TypeError, match="must be a string or None"):
            s.state_topic_dict_key = ["power"]  # type: ignore[assignment]

    def test_set_to_bool_raises_type_error(self):
        """bool is not str, so it raises TypeError."""
        s = _make_sensor("set_bool")
        with pytest.raises(TypeError, match="must be a string or None"):
            s.state_topic_dict_key = True  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 3. Setter - STATE_TOPIC already set guard
# ---------------------------------------------------------------------------


class TestStatTopicDictKeySetterStateTopicGuard:
    def test_raises_assertion_when_state_topic_already_set(self):
        """Setting state_topic_dict_key after STATE_TOPIC is in the dict raises AssertionError."""
        s = _make_sensor("guard_set")
        s[DiscoveryKeys.STATE_TOPIC] = "some/topic/state"
        with pytest.raises(AssertionError, match="cannot be set when STATE_TOPIC has already been set"):
            s.state_topic_dict_key = "power"

    def test_raises_assertion_after_configure_mqtt_topics(self):
        """Setting state_topic_dict_key after configure_mqtt_topics() raises AssertionError."""
        s = _make_sensor("guard_cfg")
        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            s.configure_mqtt_topics("device_001")
        with pytest.raises(AssertionError, match="cannot be set when STATE_TOPIC has already been set"):
            s.state_topic_dict_key = "power"


# ---------------------------------------------------------------------------
# 4. Setter - no-op when value unchanged
# ---------------------------------------------------------------------------


class TestStatTopicDictKeySetterNoOp:
    def test_setting_same_none_value_is_noop(self):
        """Setting to None when already None produces no change."""
        s = _make_sensor("noop_none")
        s.state_topic_dict_key = None
        assert s.state_topic_dict_key is None

    def test_setting_unchanged_none_with_debug_logs(self):
        """When value unchanged and debug_logging is True a debug message is emitted."""
        s = _make_sensor("noop_dbg", debug=True)
        # Default is None; setting None is a no-op that should trigger the debug branch
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.state_topic_dict_key = None
        mock_log.debug.assert_called()

    def test_setting_unchanged_string_with_debug_logs(self):
        """When string value unchanged and debug_logging is True a debug message is emitted."""
        s = _make_sensor("noop_str_dbg", debug=True)
        s.state_topic_dict_key = "power"
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.state_topic_dict_key = "power"
        mock_log.debug.assert_called()

    def test_setting_unchanged_string_without_debug_no_debug_log(self):
        """When value unchanged and debug_logging is False no debug call is made for the no-op."""
        s = _make_sensor("noop_nodebug", debug=False)
        s.state_topic_dict_key = "power"
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            mock_log.debug.reset_mock()
            s.state_topic_dict_key = "power"
        mock_log.debug.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Setter - value actually changes
# ---------------------------------------------------------------------------


class TestStatTopicDictKeySetterValueChanges:
    def test_setting_new_string_updates_value(self):
        """Setting a new string value updates _state_topic_dict_key."""
        s = _make_sensor("change_str")
        s.state_topic_dict_key = "power"
        assert s._state_topic_dict_key == "power"

    def test_setting_new_value_always_logs_debug(self):
        """When value changes, a debug message is always logged (regardless of debug_logging flag)."""
        s = _make_sensor("change_log", debug=False)
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.state_topic_dict_key = "energy"
        mock_log.debug.assert_called()

    def test_getter_reflects_new_value(self):
        """Property getter returns the updated value after assignment."""
        s = _make_sensor("change_getter")
        s.state_topic_dict_key = "temperature"
        assert s.state_topic_dict_key == "temperature"


# ---------------------------------------------------------------------------
# 6. configure_mqtt_topics() - STATE_TOPIC construction
# ---------------------------------------------------------------------------


class TestConfigureMqttTopicsStatTopicDictKey:
    def _cfg(self, enabled: bool = False) -> Config:
        cfg = Config()
        cfg.home_assistant.enabled = enabled
        cfg.home_assistant.use_simplified_topics = True
        cfg.home_assistant.discovery_prefix = "homeassistant"
        cfg.home_assistant.enabled_by_default = False
        return cfg

    def test_without_dict_key_state_topic_ends_with_state(self):
        """Without state_topic_dict_key the STATE_TOPIC suffix is '/state'."""
        s = _make_sensor("cfg_no_key")
        with _swap_active_config(self._cfg()):
            s.configure_mqtt_topics("dev_001")
        assert s.state_topic.endswith("/state")

    def test_with_dict_key_state_topic_ends_with_state_slash_key(self):
        """When state_topic_dict_key is set the STATE_TOPIC ends with '/state/<key>'."""
        s = _make_sensor("cfg_with_key")
        s.state_topic_dict_key = "power"
        with _swap_active_config(self._cfg()):
            s.configure_mqtt_topics("dev_001")
        assert s.state_topic.endswith("/state/power")

    def test_with_dict_key_state_topic_key_is_final_path_segment(self):
        """The key appears as the final path component of STATE_TOPIC, preceded by 'state'."""
        s = _make_sensor("cfg_key_segment")
        s.state_topic_dict_key = "energy_today"
        with _swap_active_config(self._cfg()):
            s.configure_mqtt_topics("dev_001")
        parts = s.state_topic.split("/")
        assert parts[-1] == "energy_today"
        assert parts[-2] == "state"


# ---------------------------------------------------------------------------
# 7. Dict-state publish - state_topic_dict_key strips the key suffix
# ---------------------------------------------------------------------------


class TestPublishDictStateStatTopicDictKey:
    def _sensor_with_dict_key(self, suffix: str, key: str, debug: bool = False) -> ConcreteSensor:
        """Create a sensor pre-configured with state_topic_dict_key and MQTT topics."""
        s = _make_sensor(suffix, debug=debug)
        s.state_topic_dict_key = key
        # Manually set STATE_TOPIC to simulate post-configure_mqtt_topics state;
        # it ends with /state/<key> as configure_mqtt_topics() would produce.
        s[DiscoveryKeys.STATE_TOPIC] = f"sigenergy2mqtt/dev_001/state/{key}"
        s[DiscoveryKeys.RAW_STATE_TOPIC] = "sigenergy2mqtt/dev_001/raw"
        s[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC] = "sigenergy2mqtt/dev_001/attributes"
        return s

    @pytest.mark.asyncio
    async def test_dict_state_published_to_correct_subtopics(self):
        """When state_topic_dict_key is set, dict keys are published as
        subtopics of state_topic with the key suffix stripped."""
        s = self._sensor_with_dict_key("pub_key_dict", "power")
        mqtt = _mqtt_mock()
        state = {"power": 1500.0, "reactive": 200.0}

        async def _update(**kw):
            s._states.append((time.time(), state))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)

        assert published is True
        published_topics = [call.args[0] for call in mqtt.publish.call_args_list]
        assert "sigenergy2mqtt/dev_001/state/power" in published_topics
        assert "sigenergy2mqtt/dev_001/state/reactive" in published_topics

    @pytest.mark.asyncio
    async def test_dict_state_strips_key_segment_from_base_topic(self):
        """The base topic for subtopic fan-out is derived via rsplit('/', 1)[0] on STATE_TOPIC."""
        s = self._sensor_with_dict_key("pub_strip", "energy")
        mqtt = _mqtt_mock()
        state = {"energy": 99.0, "other": 1.0}

        async def _update(**kw):
            s._states.append((time.time(), state))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            await s.publish(mqtt, None)

        # STATE_TOPIC = "sigenergy2mqtt/dev_001/state/energy"
        # rsplit("/", 1)[0] -> "sigenergy2mqtt/dev_001/state"
        # Each dict key is then appended -> ".../state/energy", ".../state/other"
        published_topics = [call.args[0] for call in mqtt.publish.call_args_list]
        assert "sigenergy2mqtt/dev_001/state/energy" in published_topics
        assert "sigenergy2mqtt/dev_001/state/other" in published_topics

    @pytest.mark.asyncio
    async def test_dict_state_without_dict_key_uses_original_state_topic(self):
        """When state_topic_dict_key is None (default) the topic is NOT modified before fan-out."""
        s = _make_sensor("pub_no_key")
        s[DiscoveryKeys.STATE_TOPIC] = "sigenergy2mqtt/dev_001/state"
        s[DiscoveryKeys.RAW_STATE_TOPIC] = "sigenergy2mqtt/dev_001/raw"
        s[DiscoveryKeys.JSON_ATTRIBUTES_TOPIC] = "sigenergy2mqtt/dev_001/attributes"
        mqtt = _mqtt_mock()
        state = {"a": 1.0, "b": 2.0}

        async def _update(**kw):
            s._states.append((time.time(), state))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            await s.publish(mqtt, None)

        published_topics = [call.args[0] for call in mqtt.publish.call_args_list]
        assert "sigenergy2mqtt/dev_001/state/a" in published_topics
        assert "sigenergy2mqtt/dev_001/state/b" in published_topics

    @pytest.mark.asyncio
    async def test_dict_state_with_dict_key_and_debug_logging(self):
        """Debug-logging path during dict-state publish is exercised with state_topic_dict_key."""
        s = self._sensor_with_dict_key("pub_key_dbg", "power", debug=True)
        mqtt = _mqtt_mock()
        state = {"power": 500.0}

        async def _update(**kw):
            s._states.append((time.time(), state))
            return True

        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log,
        ):
            published = await s.publish(mqtt, None)

        assert published is True
        mock_log.debug.assert_called()
