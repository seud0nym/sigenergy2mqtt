from __future__ import annotations

import json
import logging
import time
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pymodbus import ModbusException

from sigenergy2mqtt.cloud.exceptions import CloudControlUnavailableError
from sigenergy2mqtt.common import DeviceClass, ProtocolVersion, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import Sensor, WriteOnlySensor

# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class ConcreteSensor(Sensor):
    async def _update_internal_state(self, **kwargs):
        return False


def _make_sensor(name="Test", uid_suffix="x", debug=False, **kwargs):
    """Create a fresh ConcreteSensor with cleared ID registries."""
    uid = f"sigen_{uid_suffix}"
    oid = f"sigen_{uid_suffix}"

    cfg = Config()
    cfg.home_assistant.enabled = False
    cfg.home_assistant.unique_id_prefix = "sigen"
    cfg.home_assistant.entity_id_prefix = "sigen"

    with _swap_active_config(cfg), patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
        s = ConcreteSensor(
            name=name,
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


def _mqtt_mock():
    m = MagicMock()
    m.publish.return_value.is_published.return_value = True
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. Debug-logging branches in property setters
# ─────────────────────────────────────────────────────────────────────────────


class TestPublishMethod:
    """Test the publish() method's various branches."""

    def _sensor_with_topics(self, suffix, debug=False):
        s = _make_sensor(uid_suffix=suffix, debug=debug)
        s["state_topic"] = "test/state"
        s["raw_state_topic"] = "test/raw"
        s["json_attributes_topic"] = "test/attributes"
        return s

    def test_configure_mqtt_topics_adds_sensor_availability_for_home_assistant(self):
        s = self._sensor_with_topics("sensor_availability_discovery")
        cfg = Config()
        cfg.home_assistant.enabled = True
        cfg.home_assistant.discovery_prefix = "homeassistant"

        with _swap_active_config(cfg):
            s.configure_mqtt_topics("device_1")

        assert s.availability_topic is not None
        assert s.availability_topic.endswith("/availability")
        availability = cast(list[dict[str, str]], s["availability"])
        assert {item["topic"] for item in availability} == {
            "homeassistant/device/device_1/availability",
            s.availability_topic,
        }

    def test_write_only_sensor_uses_device_availability_only(self):
        cfg = Config()
        cfg.home_assistant.enabled = True

        with (
            _swap_active_config(cfg),
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
        ):
            sensor = WriteOnlySensor("Button", "sigen_button_availability", 0, 1, 30001, ProtocolVersion.V2_4)
            sensor.configure_mqtt_topics("device_1")

        assert sensor.availability_topic is None
        assert sensor["availability"] == [{"topic": "homeassistant/device/device_1/availability"}]

    def test_publish_availability_uses_retained_qos_one_message(self):
        s = self._sensor_with_topics("sensor_availability_publish")
        mqtt = _mqtt_mock()
        s.availability_topic = "device_1/sensor/state/availability"

        s.publish_availability(mqtt, "offline")

        mqtt.publish.assert_called_once_with(s.availability_topic, "offline", qos=1, retain=True)

    @pytest.mark.asyncio
    async def test_publish_with_debug_skips_none_state(self):
        """Cover debug branch when state is None and force_publish is False."""
        s = self._sensor_with_topics("pub_none_dbg", debug=True)
        mqtt = _mqtt_mock()
        cfg = Config()
        with _swap_active_config(cfg), patch("sigenergy2mqtt.sensors.base.sensor.logger"):
            published = await s.publish(mqtt, None)
        assert published is False

    @pytest.mark.asyncio
    async def test_publish_skips_none_state_even_if_force_publish_true(self, caplog: pytest.LogCaptureFixture):
        """Cover debug branch when state is None and force_publish is True.
        It should still skip publishing rather than warning about NoneType."""
        s = self._sensor_with_topics("pub_none_force", debug=False)
        s.force_publish = True
        mqtt = _mqtt_mock()
        cfg = Config()
        with _swap_active_config(cfg), caplog.at_level(logging.WARNING):
            caplog.clear()
            published = await s.publish(mqtt, None)
            assert published is False
            assert not any(r for r in caplog.records if r.levelname == "WARNING" and "Unsupported state type" in r.message)

    @pytest.mark.asyncio
    async def test_publish_resets_failures_on_success(self):
        """Cover failure reset branch."""
        s = self._sensor_with_topics("pub_reset")
        s.availability_topic = "test/state/availability"
        s._failures = 5
        mqtt = _mqtt_mock()

        async def _update(**kw):
            s._states.append((time.time(), 42.0))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)
        assert published is True
        assert s._failures == 0
        mqtt.publish.assert_any_call("test/state/availability", "online", qos=1, retain=True)

    @pytest.mark.asyncio
    async def test_successful_suppressed_read_restores_online_availability(self):
        s = self._sensor_with_topics("pub_suppressed_recovery")
        s.set_state(42.0)
        s.availability_topic = "test/availability"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _failed_update(**kw):
            raise ModbusException("read failed")

        async def _unchanged_update(**kw):
            s.mark_successful_read()
            return s.set_latest_state(42.0)

        cfg = Config()
        cfg.home_assistant.enabled = True
        cfg.repeated_state_publish_interval = -1
        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_failed_update):
            assert await s.publish(mqtt, modbus) is False

        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_unchanged_update):
            assert await s.publish(mqtt, modbus) is False

        availability_payloads = [call.args[1] for call in mqtt.publish.call_args_list if call.args[0] == "test/availability"]
        assert availability_payloads == ["offline", "online"]
        assert all(call.args[0] != "test/state" for call in mqtt.publish.call_args_list)

    @pytest.mark.asyncio
    async def test_successful_suppressed_read_is_current_after_a_failed_read(self):
        s = self._sensor_with_topics("pub_suppressed_current")
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _failed_update(**kw):
            raise ModbusException("read failed")

        async def _unchanged_update(**kw):
            s.mark_successful_read()
            return s.set_latest_state(42.0)

        cfg = Config()
        cfg.repeated_state_publish_interval = -1
        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_unchanged_update):
            await s.publish(mqtt, modbus)
        assert s.is_read_current(60.0) is True

        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_failed_update):
            assert await s.publish(mqtt, modbus) is False
        assert s._failures == 1
        assert s.is_read_current(60.0) is False

        # The unchanged value is not published, so the failure count is not
        # reset, but the read itself succeeded and the state is current again.
        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_unchanged_update):
            assert await s.publish(mqtt, modbus) is False
        assert s._failures == 1
        assert s.is_read_current(60.0) is True

    @pytest.mark.asyncio
    async def test_sanity_check_failure_makes_read_not_current(self):
        from sigenergy2mqtt.sensors.base import SanityCheckException

        s = self._sensor_with_topics("pub_sanity_current")
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _insane_update(**kw):
            s.mark_successful_read()  # registers were read before the value was rejected
            raise SanityCheckException("out of range")

        with patch.object(s, "_update_internal_state", side_effect=_insane_update):
            assert await s.publish(mqtt, modbus) is False
        assert s.is_read_current(60.0) is False

    @pytest.mark.asyncio
    async def test_publish_with_publish_raw_enabled(self):
        """Cover the publish_raw branch."""
        s = self._sensor_with_topics("pub_raw_en")
        s._publish_raw = True
        mqtt = _mqtt_mock()

        async def _update(**kw):
            s._states.append((time.time(), 100.0))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)
        assert published is True
        # Both state and raw should be published
        assert mqtt.publish.call_count >= 2

    @pytest.mark.asyncio
    async def test_publish_dict_uses_key_subtopics_and_json_raw_state(self):
        s = self._sensor_with_topics("pub_dict")
        s._publish_raw = True
        mqtt = _mqtt_mock()
        raw_state = {"power": 100.126, "status": "online"}

        async def _update(**kw):
            s._states.append((time.time(), raw_state))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)

        assert published is True
        assert mqtt.publish.call_count == 3
        state_calls = {call.args[0]: call.args[1] for call in mqtt.publish.call_args_list[:2]}
        assert state_calls == {"test/state/power": "100.126", "test/state/status": "online"}
        raw_call = mqtt.publish.call_args_list[2]
        assert raw_call.args[0] == "test/raw"
        assert json.loads(raw_call.args[1]) == raw_state

    @pytest.mark.asyncio
    async def test_publish_rejects_unsupported_state_type(self, caplog):
        s = self._sensor_with_topics("pub_unsupported")
        mqtt = _mqtt_mock()

        async def _update(**kw):
            s._states.append((time.time(), [1, 2, 3]))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)

        assert published is False
        mqtt.publish.assert_not_called()
        assert "Unsupported state type list" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_exception_increments_failures(self):
        """Cover failure counting in exception handler."""
        s = self._sensor_with_topics("pub_exc")
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise ModbusException("Modbus error")

        cfg = Config()
        cfg.home_assistant.enabled = False
        with patch.object(s, "_update_internal_state", side_effect=_update), _swap_active_config(cfg):
            await s.publish(mqtt, modbus)
        assert s._failures == 1

    @pytest.mark.asyncio
    async def test_publish_exception_raises_when_not_connected(self):
        """Exception re-raised when modbus not connected."""
        s = self._sensor_with_topics("pub_exc_nc")
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = False

        async def _update(**kw):
            raise RuntimeError("connection lost")

        with patch.object(s, "_update_internal_state", side_effect=_update), pytest.raises(RuntimeError):
            await s.publish(mqtt, modbus)

    @pytest.mark.asyncio
    async def test_publish_max_failures_triggers_warning(self):
        """Cover the max-failures warning path."""
        s = self._sensor_with_topics("pub_maxfail")
        s._max_failures = 2
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise ModbusException("error")

        cfg = Config()
        cfg.home_assistant.enabled = False
        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            _swap_active_config(cfg),
            patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log,
        ):
            await s.publish(mqtt, modbus)
            await s.publish(mqtt, modbus)
            # After 2 failures reaching max, warning should be logged
            warning_calls = [str(c) for c in mock_log.warning.call_args_list]
            assert any("DISABLED" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_publish_skips_when_max_failures_exceeded(self):
        """No publish attempt when failures >= max_failures and no retry due (line ~781+)."""
        s = self._sensor_with_topics("pub_skip_maxfail", debug=True)
        s._failures = 20
        s._max_failures = 10
        s._next_retry = None
        mqtt = _mqtt_mock()
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            published = await s.publish(mqtt, None)
        assert published is False
        mock_log.debug.assert_called()  # hits the elif debug branch

    @pytest.mark.asyncio
    async def test_publish_retries_after_retry_time(self):
        """Retry occurs when _next_retry <= now."""
        s = self._sensor_with_topics("pub_retry")
        s._failures = 15
        s._max_failures = 10
        s._next_retry = time.time() - 1  # in the past

        mqtt = _mqtt_mock()

        async def _update(**kw):
            s._states.append((time.time(), 55.0))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)
        assert published is True
        assert s._failures == 0  # reset on success

    @pytest.mark.asyncio
    async def test_publish_failure_with_ha_enabled_publishes_offline_availability(self):
        """A publish failure marks the sensor offline without publishing exception attributes."""
        s = self._sensor_with_topics("pub_ha_attr")
        s["json_attributes_topic"] = "test/attributes"
        s.availability_topic = "test/availability"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise ModbusException("ha test error")

        cfg = Config()
        cfg.home_assistant.enabled = True
        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            _swap_active_config(cfg),
            patch.object(s, "publish_attributes") as mock_pub_attrs,
        ):
            await s.publish(mqtt, modbus)
        mock_pub_attrs.assert_not_called()
        mqtt.publish.assert_any_call("test/availability", "offline", qos=1, retain=True)

    @pytest.mark.asyncio
    async def test_cloud_unavailable_marks_offline_and_propagates(self):
        s = self._sensor_with_topics("pub_cloud_unavailable")
        s.availability_topic = "test/availability"
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.home_assistant.enabled = True

        async def _cloud_failure(**kw):
            raise CloudControlUnavailableError("cloud offline")

        with _swap_active_config(cfg), patch.object(s, "_update_internal_state", side_effect=_cloud_failure), pytest.raises(CloudControlUnavailableError, match="cloud offline"):
            await s.publish(mqtt, MagicMock())

        mqtt.publish.assert_called_once_with("test/availability", "offline", qos=1, retain=True)

    @pytest.mark.asyncio
    async def test_republish_forces_online_availability(self):
        s = self._sensor_with_topics("pub_force_availability")
        s.set_state(42.0)
        s.availability_topic = "test/availability"
        s.availability_state = "online"
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.home_assistant.enabled = True

        with _swap_active_config(cfg):
            assert await s.publish(mqtt, None, republish=True) is True

        mqtt.publish.assert_any_call("test/availability", "online", qos=1, retain=True)

    @pytest.mark.asyncio
    async def test_publish_retry_interval_calculated(self):
        """_next_retry is set when max_failures_retry_interval > 0."""
        s = self._sensor_with_topics("pub_retry_interval")
        s._max_failures = 2
        s._max_failures_retry_interval = 30
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise ModbusException("retry interval test")

        cfg = Config()
        cfg.home_assistant.enabled = False
        with patch.object(s, "_update_internal_state", side_effect=_update), _swap_active_config(cfg):
            await s.publish(mqtt, modbus)
            await s.publish(mqtt, modbus)
        # After hitting max_failures with retry_interval set, _next_retry should be set
        assert s._next_retry is not None


# ─────────────────────────────────────────────────────────────────────────────
# 4. publish_attributes() branches
# ─────────────────────────────────────────────────────────────────────────────


class TestPublishAttributes:
    def _sensor_with_attrs(self, suffix, debug=False):
        s = _make_sensor(uid_suffix=suffix, debug=debug)
        s["json_attributes_topic"] = "test/attributes"
        return s

    def test_publish_attributes_clean_clears_retained(self):
        """clean=True publishes None to clear retained messages."""
        s = self._sensor_with_attrs("pa_clean")
        mqtt = _mqtt_mock()
        s.publish_attributes(mqtt, clean=True)
        mqtt.publish.assert_called_with("test/attributes", b"", qos=1, retain=True)

    def test_publish_attributes_clean_with_debug(self):
        """clean=True with debug_logging=True covers debug branch."""
        s = self._sensor_with_attrs("pa_clean_dbg", debug=True)
        mqtt = _mqtt_mock()
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.publish_attributes(mqtt, clean=True)
        mock_log.debug.assert_called()

    def test_publish_attributes_not_published_again_when_already_published(self):
        """Already-published attributes are not re-published (no clean)."""
        s = self._sensor_with_attrs("pa_skip")
        mqtt = _mqtt_mock()
        # First publish
        s.publish_attributes(mqtt)
        assert s._attributes_published is True
        # Second publish without clean should skip
        mqtt.publish.reset_mock()
        s.publish_attributes(mqtt)
        mqtt.publish.assert_not_called()

    def test_publish_attributes_publishes_extra_kwargs(self):
        """Additional kwargs are included in published attributes."""
        s = self._sensor_with_attrs("pa_kwargs")
        mqtt = _mqtt_mock()
        s.publish_attributes(mqtt, failures=3, exception="RuntimeError('x')")
        call_args = mqtt.publish.call_args
        import json

        payload = json.loads(call_args[0][1])
        assert payload["failures"] == 3

    def test_publish_attributes_unpublishable_sensor_skips(self):
        """Unpublishable sensor doesn't publish attributes."""
        s = self._sensor_with_attrs("pa_unpub")
        s._publishable = False
        mqtt = _mqtt_mock()
        s.publish_attributes(mqtt)
        mqtt.publish.assert_not_called()

    def test_publish_attributes_propagates_to_derived(self):
        """publish_attributes propagates to derived sensors."""
        s = self._sensor_with_attrs("pa_derived")
        derived = MagicMock()
        s.derived_sensors["Mock"] = derived
        mqtt = _mqtt_mock()
        s.publish_attributes(mqtt, clean=True)
        derived.publish_attributes.assert_called_once_with(mqtt, clean=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. configure_mqtt_topics() branches
# ─────────────────────────────────────────────────────────────────────────────


class TestConfigureMqttTopics:
    def test_simplified_topics(self):
        """Cover simplified topics path."""
        s = _make_sensor(uid_suffix="simplified")
        from sigenergy2mqtt.config import _swap_active_config

        cfg = Config()
        cfg.home_assistant.enabled = True
        cfg.home_assistant.use_simplified_topics = True
        cfg.home_assistant.discovery_prefix = "homeassistant"
        cfg.home_assistant.enabled_by_default = False
        with _swap_active_config(cfg):
            base = s.configure_mqtt_topics("test_device")
        assert base == "sigenergy2mqtt/sigen_simplified"

    def test_ha_disabled_topics(self):
        """Cover path when HA is not enabled."""
        s = _make_sensor(uid_suffix="ha_off")
        cfg = Config()
        cfg.home_assistant.enabled = False
        cfg.home_assistant.use_simplified_topics = False
        cfg.home_assistant.discovery_prefix = "homeassistant"
        cfg.home_assistant.enabled_by_default = False
        with _swap_active_config(cfg):
            base = s.configure_mqtt_topics("test_device")
        assert "availability" not in s
        assert base == "sigenergy2mqtt/sigen_ha_off"

    def test_ha_enabled_no_simplified_with_debug(self):
        """Debug branch in configure_mqtt_topics (line ~620+)."""
        s = _make_sensor(uid_suffix="cfg_dbg", debug=True)
        cfg = Config()
        cfg.home_assistant.enabled = True
        cfg.home_assistant.use_simplified_topics = False
        cfg.home_assistant.discovery_prefix = "homeassistant"
        cfg.home_assistant.enabled_by_default = False
        with _swap_active_config(cfg), patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            s.configure_mqtt_topics("test_device")
        mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_attributes() branches
# ─────────────────────────────────────────────────────────────────────────────


class TestGetAttributes:
    def test_get_attributes_ha_disabled_includes_name_and_unit(self):
        """When HA disabled, name and unit included in attributes."""
        s = _make_sensor(uid_suffix="ga_ha_off")
        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            attrs = s.get_attributes()
        assert "name" in attrs
        assert "unit-of-measurement" in attrs

    def test_get_attributes_no_unit_ha_disabled(self):
        """When HA disabled and unit is None, unit-of-measurement omitted."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="No Unit",
                unique_id="sigen_no_unit",
                object_id="sigen_no_unit",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=ProtocolVersion.V2_4,
            )
        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            attrs = s.get_attributes()
        assert "unit-of-measurement" not in attrs

    def test_get_attributes_protocol_na_omits_since_protocol(self):
        """ProtocolVersion.N_A omits since-protocol from attributes."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="NA ProtocolVersion",
                unique_id="sigen_na_proto",
                object_id="sigen_na_proto",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=ProtocolVersion.N_A,
            )
        attrs = s.get_attributes()
        assert "since-protocol" not in attrs

    def test_get_attributes_with_gain(self):
        """Gain is included in attributes when set."""
        s = _make_sensor(uid_suffix="ga_gain")
        s._gain = 1000.0
        attrs = s.get_attributes()
        assert attrs.get("gain") == 1000.0


# ─────────────────────────────────────────────────────────────────────────────
# 7. get_discovery() branches
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDiscovery:
    def _sensor_with_topics(self, suffix):
        s = _make_sensor(uid_suffix=suffix)
        s["state_topic"] = "test/state"
        s["raw_state_topic"] = "test/raw"
        s["json_attributes_topic"] = "test/attributes"
        return s

    def test_get_discovery_publishable_removes_persistent_file(self, tmp_path):
        """When publishable and file exists, it's removed."""
        s = self._sensor_with_topics("gd_pub")
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.clean = False
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg), patch("sigenergy2mqtt.sensors.base.sensor.state_store") as mock_ss:
            components = s.get_discovery(mqtt)
        mock_ss.delete_sync.assert_called_once()
        assert len(components) > 0

    def test_get_discovery_unpublishable_clears_attributes(self, tmp_path):
        """When not publishable, attributes topic cleared."""
        s = self._sensor_with_topics("gd_unpub")
        s._publishable = False
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.clean = False
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            s.get_discovery(mqtt)
        mqtt.publish.assert_called_with("test/attributes", b"", qos=1, retain=True)

    def test_get_discovery_clean_mode_clears_all(self, tmp_path):
        """In clean mode, components dict is empty."""
        s = self._sensor_with_topics("gd_clean")
        s._publishable = False
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.clean = True
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            components = s.get_discovery(mqtt)
        assert components == {}

    def test_get_discovery_unpublishable_writes_persistent_file(self, tmp_path):
        """When unpublishable and file does not exist, file is written."""
        s = self._sensor_with_topics("gd_persist")
        s._publishable = False
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.clean = False
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg), patch("sigenergy2mqtt.sensors.base.sensor.state_store") as mock_ss:
            mock_ss.load_sync.return_value = None
            components = s.get_discovery(mqtt)
        mock_ss.save_sync.assert_called_once()
        # Components should have minimal platform entry
        for v in components.values():
            assert "p" in v


# ─────────────────────────────────────────────────────────────────────────────
# 8. get_state() with republish=True
# ─────────────────────────────────────────────────────────────────────────────


class TestGetStateRepublish:
    @pytest.mark.asyncio
    async def test_get_state_republish_returns_cached_state(self):
        """republish=True returns cached state without calling _update_internal_state."""
        s = _make_sensor(uid_suffix="gs_repub")
        s._states.append((time.time(), 75.0))
        called = []

        async def _update(**kw):
            called.append(True)
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            result = await s.get_state(republish=True)
        assert result == 75.0
        assert not called  # _update_internal_state should NOT have been called

    @pytest.mark.asyncio
    async def test_get_state_republish_with_debug_logs(self):
        """republish debug branch."""
        s = _make_sensor(uid_suffix="gs_repub_dbg", debug=True)
        s._states.append((time.time(), 42.0))
        with patch("sigenergy2mqtt.sensors.base.sensor.logger") as mock_log:
            await s.get_state(republish=True)
        mock_log.debug.assert_called()

    @pytest.mark.asyncio
    async def test_get_state_no_republish_no_states_returns_none(self):
        """When not republish and _update_internal_state returns False, state is None."""
        s = _make_sensor(uid_suffix="gs_none")
        result = await s.get_state(republish=False)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 9. state2raw() edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestGetDiscoveryComponents:
    def test_options_are_translated(self):
        """Options list is properly translated in get_discovery_components."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Opts",
                unique_id="sigen_gdc_opts",
                object_id="sigen_gdc_opts",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=ProtocolVersion.V2_4,
            )
        s["options"] = ["Option A", "Option B", ""]  # empty string should be filtered
        components = s.get_discovery_components()
        sensor_cfg = components[s.unique_id]
        assert "options" in sensor_cfg
        # Empty option filtered out
        assert "" not in sensor_cfg["options"]
        assert len(sensor_cfg["options"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 21. gain property edge cases
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Outage-aware logging of read failures
# ─────────────────────────────────────────────────────────────────────────────


class TestPublishDuringOutage:
    def _sensor(self, suffix):
        s = _make_sensor(uid_suffix=suffix)
        s["state_topic"] = "test/state"
        s["raw_state_topic"] = "test/raw"
        s["json_attributes_topic"] = "test/attributes"
        return s

    def _modbus(self, tracker):
        modbus = MagicMock()
        modbus.connected = True
        modbus.outage = tracker
        return modbus

    @pytest.mark.asyncio
    async def test_failure_during_outage_is_demoted_and_recovery_is_quiet(self, caplog):
        from sigenergy2mqtt.common.outage import OutageTracker

        s = self._sensor("outage_quiet")
        tracker = OutageTracker("modbus://h:502")
        tracker.failure(ModbusException("No response received"))
        modbus = self._modbus(tracker)
        mqtt = _mqtt_mock()

        async def _fail(**kw):
            raise ModbusException("No response received")

        async def _ok(**kw):
            s._states.append((time.time(), 42.0))
            return True

        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg), caplog.at_level(logging.DEBUG):
            with patch.object(s, "_update_internal_state", side_effect=_fail):
                await s.publish(mqtt, modbus)
            assert s._failures == 1
            tracker.success()
            with patch.object(s, "_update_internal_state", side_effect=_ok):
                await s.publish(mqtt, modbus)
        assert s._failures == 0

        skipped = [r for r in caplog.records if "Publishing SKIPPED" in r.getMessage()]
        reset = [r for r in caplog.records if "Resetting failure count" in r.getMessage()]
        assert skipped and all(r.levelno == logging.DEBUG for r in skipped)
        assert reset and all(r.levelno == logging.DEBUG for r in reset)

    @pytest.mark.asyncio
    async def test_failure_without_outage_still_warns(self, caplog):
        from sigenergy2mqtt.common.outage import OutageTracker

        s = self._sensor("outage_none")
        modbus = self._modbus(OutageTracker("modbus://h:502"))
        mqtt = _mqtt_mock()

        async def _fail(**kw):
            raise ModbusException("Illegal data address")

        async def _ok(**kw):
            s._states.append((time.time(), 42.0))
            return True

        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg), caplog.at_level(logging.DEBUG):
            with patch.object(s, "_update_internal_state", side_effect=_fail):
                await s.publish(mqtt, modbus)
            with patch.object(s, "_update_internal_state", side_effect=_ok):
                await s.publish(mqtt, modbus)

        skipped = [r for r in caplog.records if "Publishing SKIPPED" in r.getMessage()]
        reset = [r for r in caplog.records if "Resetting failure count" in r.getMessage()]
        assert [r.levelno for r in skipped] == [logging.WARNING]
        assert [r.levelno for r in reset] == [logging.INFO]
