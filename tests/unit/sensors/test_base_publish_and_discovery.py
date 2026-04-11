from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, Protocol, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.sensors.base import (
    Sensor,
)

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

    with _swap_active_config(cfg):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
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
                protocol_version=Protocol.V2_4,
                debug_logging=debug,
                **kwargs,
            )
    return s


def _mqtt_mock():
    m = MagicMock()
    m.publish = MagicMock()
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

    @pytest.mark.asyncio
    async def test_publish_with_debug_skips_none_state(self):
        """Cover debug branch when state is None and force_publish is False."""
        s = self._sensor_with_topics("pub_none_dbg", debug=True)
        mqtt = _mqtt_mock()
        cfg = Config()
        with _swap_active_config(cfg):
            with patch("sigenergy2mqtt.sensors.base.sensor.logging"):
                published = await s.publish(mqtt, None)
        assert published is False

    @pytest.mark.asyncio
    async def test_publish_resets_failures_on_success(self):
        """Cover failure reset branch."""
        s = self._sensor_with_topics("pub_reset")
        s._failures = 5
        mqtt = _mqtt_mock()

        async def _update(**kw):
            s._states.append((time.time(), 42.0))
            return True

        with patch.object(s, "_update_internal_state", side_effect=_update):
            published = await s.publish(mqtt, None)
        assert published is True
        assert s._failures == 0

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
    async def test_publish_exception_increments_failures(self):
        """Cover failure counting in exception handler."""
        s = self._sensor_with_topics("pub_exc")
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise RuntimeError("Modbus error")

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

        with patch.object(s, "_update_internal_state", side_effect=_update):
            with pytest.raises(RuntimeError):
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
            raise RuntimeError("error")

        cfg = Config()
        cfg.home_assistant.enabled = False
        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            _swap_active_config(cfg),
            patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log,
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
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
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
    async def test_publish_failure_with_ha_enabled_publishes_attributes(self):
        """publish_attributes is called on failure when HA enabled."""
        s = self._sensor_with_topics("pub_ha_attr")
        s["json_attributes_topic"] = "test/attributes"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise RuntimeError("ha test error")

        cfg = Config()
        cfg.home_assistant.enabled = True
        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            _swap_active_config(cfg),
            patch.object(s, "publish_attributes") as mock_pub_attrs,
        ):
            await s.publish(mqtt, modbus)
        mock_pub_attrs.assert_called_once()

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
            raise RuntimeError("retry interval test")

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
        mqtt.publish.assert_called_with("test/attributes", b"", qos=0, retain=True)

    def test_publish_attributes_clean_with_debug(self):
        """clean=True with debug_logging=True covers debug branch."""
        s = self._sensor_with_attrs("pa_clean_dbg", debug=True)
        mqtt = _mqtt_mock()
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
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
        with _swap_active_config(cfg):
            with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
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
                protocol_version=Protocol.V2_4,
            )
        cfg = Config()
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            attrs = s.get_attributes()
        assert "unit-of-measurement" not in attrs

    def test_get_attributes_protocol_na_omits_since_protocol(self):
        """Protocol.N_A omits since-protocol from attributes."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="NA Protocol",
                unique_id="sigen_na_proto",
                object_id="sigen_na_proto",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.N_A,
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
        pfile = tmp_path / "test.publishable"
        pfile.write_text("0")
        s._persistent_publish_state_file = pfile
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
        s._persistent_publish_state_file = tmp_path / "gd_unpub.publishable"
        mqtt = _mqtt_mock()
        cfg = Config()
        cfg.clean = False
        cfg.home_assistant.enabled = False
        with _swap_active_config(cfg):
            s.get_discovery(mqtt)
        mqtt.publish.assert_called_with("test/attributes", b"", qos=0, retain=False)

    def test_get_discovery_clean_mode_clears_all(self, tmp_path):
        """In clean mode, components dict is empty."""
        s = self._sensor_with_topics("gd_clean")
        s._publishable = False
        s._persistent_publish_state_file = tmp_path / "gd_clean.publishable"
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
        pfile = tmp_path / "gd_persist.publishable"
        s._persistent_publish_state_file = pfile
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
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
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
                protocol_version=Protocol.V2_4,
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
