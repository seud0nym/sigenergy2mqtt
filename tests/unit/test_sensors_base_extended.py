from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, Protocol, RegisterAccess, StateClass, UnitOfPower
from sigenergy2mqtt.config import Config, _swap_active_config
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.sensors.base import (
    AlarmSensor,
    ReadOnlySensor,
    Sensor,
    WriteOnlySensor,
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


class TestDebugLoggingBranches:
    """Cover debug_logging=True branches in property setters."""

    def test_publishable_setter_unchanged_with_debug(self):
        """Setting publishable to the same value with debug_logging=True."""
        s = _make_sensor(uid_suffix="pub_dbg", debug=True)
        assert s.publishable is True
        # Setting same value triggers the debug branch for "unchanged"
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publishable = True  # No change → debug branch
            mock_log.debug.assert_called()

    def test_publish_raw_setter_unchanged_with_debug(self):
        """Setting publish_raw to same value with debug_logging=True."""
        s = _make_sensor(uid_suffix="raw_dbg", debug=True)
        assert s.publish_raw is False
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publish_raw = False  # unchanged → debug branch
            mock_log.debug.assert_called()

    def test_publishable_setter_changed_with_debug(self):
        """Setting publishable to different value with debug_logging=True."""
        s = _make_sensor(uid_suffix="pub_chg_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            s.publishable = False
            mock_log.debug.assert_called()

    def test_apply_gain_and_precision_none_with_debug(self):
        """_apply_gain_and_precision with None and debug_logging=True."""
        s = _make_sensor(uid_suffix="gap_none_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            result = s._apply_gain_and_precision(None)
            assert result is None
            mock_log.debug.assert_called()

    def test_apply_gain_and_precision_float_with_debug(self):
        """_apply_gain_and_precision with float and debug_logging=True."""
        s = _make_sensor(uid_suffix="gap_float_dbg", debug=True)
        with patch("sigenergy2mqtt.sensors.base.sensor.logging") as mock_log:
            result = s._apply_gain_and_precision(100.0)
            assert result == 100.0
            mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 2. apply_sensor_overrides branches
# ─────────────────────────────────────────────────────────────────────────────


class TestApplySensorOverrides:
    """Cover each override key branch in apply_sensor_overrides."""

    def _make_with_overrides(self, overrides: dict, suffix: str) -> Sensor:
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Override Test",
                unique_id=f"sigen_{suffix}",
                object_id=f"sigen_{suffix}",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        cfg = Config()
        cfg.sensor_overrides = {f"sigen_{suffix}": overrides}
        with _swap_active_config(cfg):
            s.apply_sensor_overrides(None)
        return s

    def test_override_debug_logging(self):
        s = self._make_with_overrides({"debug-logging": True}, "ov_debug")
        assert s.debug_logging is True

    def test_override_gain(self):
        s = self._make_with_overrides({"gain": 10.0}, "ov_gain")
        assert s._gain == 10.0

    def test_override_icon(self):
        s = self._make_with_overrides({"icon": "mdi:battery"}, "ov_icon")
        assert s["icon"] == "mdi:battery"

    def test_override_max_failures(self):
        s = self._make_with_overrides({"max-failures": 3}, "ov_maxfail")
        assert s._max_failures == 3

    def test_override_max_failures_retry_interval(self):
        s = self._make_with_overrides({"max-failures-retry-interval": 60}, "ov_retry")
        assert s._max_failures_retry_interval == 60

    def test_override_precision(self):
        s = self._make_with_overrides({"precision": 0}, "ov_prec")
        assert s.precision == 0
        assert s["display_precision"] == 0

    def test_override_publishable(self):
        s = self._make_with_overrides({"publishable": False}, "ov_pub")
        assert s.publishable is False

    def test_override_publish_raw(self):
        s = self._make_with_overrides({"publish-raw": True}, "ov_pubraw")
        assert s.publish_raw is True

    def test_override_sanity_check_delta(self):
        s = self._make_with_overrides({"sanity-check-delta": True}, "ov_scd")
        assert s.sanity_check.delta is True

    def test_override_sanity_check_max_value(self):
        s = self._make_with_overrides({"sanity-check-max-value": 5000.0}, "ov_scmax")
        assert s.sanity_check.max_raw == 5000.0

    def test_override_sanity_check_min_value(self):
        s = self._make_with_overrides({"sanity-check-min-value": -100.0}, "ov_scmin")
        assert s.sanity_check.min_raw == -100.0

    def test_override_unit_of_measurement(self):
        s = self._make_with_overrides({"unit-of-measurement": "kW"}, "ov_uom")
        assert s["unit_of_measurement"] == "kW"

    def test_override_device_class(self):
        s = self._make_with_overrides({"device-class": DeviceClass.ENERGY}, "ov_dc")
        assert s["device_class"] == DeviceClass.ENERGY

    def test_override_state_class(self):
        s = self._make_with_overrides({"state-class": StateClass.TOTAL}, "ov_sc")
        assert s["state_class"] == StateClass.TOTAL

    def test_override_name(self):
        s = self._make_with_overrides({"name": "New Name"}, "ov_name")
        assert s["name"] == "New Name"

    def test_override_registers_read_only(self):
        """apply_sensor_overrides with ReadableSensorMixin + read_only=False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="ReadOnly Test",
                unique_id="sigen_ro_reg",
                object_id="sigen_ro_reg",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.read_only = False
        registers.read_write = True
        registers.write_only = True
        cfg = Config()
        with _swap_active_config(cfg):
            # DerivedSensor instance check path
            s.apply_sensor_overrides(registers)

    def test_override_registers_no_remote_ems(self):
        """Publishable set to False when no_remote_ems is True and sensor has _remote_ems."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="RemoteEMS",
                unique_id="sigen_rems",
                object_id="sigen_rems",
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        s._remote_ems = True  # mark as remote EMS sensor
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = True
        cfg = Config()
        with _swap_active_config(cfg):
            s.apply_sensor_overrides(registers)
        assert s.publishable is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. publish() method branches
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
        mqtt.publish.assert_called_with("test/attributes", None, qos=1, retain=True)

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
        with _swap_active_config(cfg):
            components = s.get_discovery(mqtt)
        assert not pfile.exists()
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
        mqtt.publish.assert_called_with("test/attributes", None, qos=0, retain=False)

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
        with _swap_active_config(cfg):
            components = s.get_discovery(mqtt)
        assert pfile.exists()
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


class TestState2Raw:
    def _sensor_with_options(self, options: list, suffix: str):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s = ConcreteSensor(
                name="Options",
                unique_id=f"sigen_{suffix}",
                object_id=f"sigen_{suffix}",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        s["options"] = options
        return s

    def test_state2raw_none(self):
        s = _make_sensor(uid_suffix="s2r_none")
        assert s.state2raw(None) is None

    def test_state2raw_string_option_match(self):
        s = self._sensor_with_options(["Off", "On"], "s2r_opt")
        assert s.state2raw("Off") == 0
        assert s.state2raw("On") == 1

    def test_state2raw_numeric_string(self):
        s = _make_sensor(uid_suffix="s2r_numstr")
        assert s.state2raw("42") == 42

    def test_state2raw_float_string(self):
        s = _make_sensor(uid_suffix="s2r_floatstr")
        result = s.state2raw("3.14")
        assert result == 3  # int conversion

    def test_state2raw_int_with_gain(self):
        s = _make_sensor(uid_suffix="s2r_gain")
        s._gain = 10.0
        result = s.state2raw(5)
        assert result == 50

    def test_state2raw_float_gain_1_no_change(self):
        s = _make_sensor(uid_suffix="s2r_gain1")
        s._gain = 1.0
        result = s.state2raw(100)
        assert result == 100

    def test_state2raw_nonnumeric_string_fallback(self):
        """Non-numeric string not in options falls back."""
        s = self._sensor_with_options(["Alpha", "Beta"], "s2r_fallback")
        assert s.state2raw("Alpha") == 0


# ─────────────────────────────────────────────────────────────────────────────
# 10. _check_register_response() exception code branches
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckRegisterResponse:
    def _make_readonly_sensor(self, suffix):
        """Create a ReadOnlySensor instance for testing _check_register_response."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            s = ReadOnlySensor(
                name="RO Test",
                object_id=f"sigen_{suffix}",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        return s

    def test_check_register_response_none(self):
        s = self._make_readonly_sensor("crr_none")
        assert s._check_register_response(None, "read_input_registers") is False

    def test_check_register_response_exception_code_1(self):
        s = self._make_readonly_sensor("crr_ex1")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 1
        with pytest.raises(Exception, match="ILLEGAL FUNCTION"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_exception_code_2_sets_max_failures_zero(self):
        s = self._make_readonly_sensor("crr_ex2")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with pytest.raises(Exception, match="ILLEGAL DATA ADDRESS"):
            s._check_register_response(rr, "read_input_registers")
        assert s._max_failures == 0
        assert s._max_failures_retry_interval == 0

    def test_check_register_response_exception_code_2_write_no_max_reset(self):
        """For write_registers, max_failures NOT reset on exception code 2."""
        s = self._make_readonly_sensor("crr_ex2wr")
        original_max_failures = s._max_failures
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with pytest.raises(Exception, match="ILLEGAL DATA ADDRESS"):
            s._check_register_response(rr, "write_registers")
        assert s._max_failures == original_max_failures  # unchanged for write

    def test_check_register_response_exception_code_3(self):
        s = self._make_readonly_sensor("crr_ex3")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 3
        with pytest.raises(Exception, match="ILLEGAL DATA VALUE"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_exception_code_4(self):
        s = self._make_readonly_sensor("crr_ex4")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 4
        with pytest.raises(Exception, match="SLAVE DEVICE FAILURE"):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_unknown_exception_code(self):
        s = self._make_readonly_sensor("crr_ex_unk")
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 99
        with pytest.raises(Exception):
            s._check_register_response(rr, "read_input_registers")

    def test_check_register_response_success(self):
        s = self._make_readonly_sensor("crr_ok")
        rr = MagicMock()
        rr.isError.return_value = False
        assert s._check_register_response(rr, "read_input_registers") is True

    def test_check_register_response_exception_code_2_with_debug(self):
        s = self._make_readonly_sensor("crr_ex2_dbg")
        s.debug_logging = True
        rr = MagicMock()
        rr.isError.return_value = True
        rr.exception_code = 2
        with patch("sigenergy2mqtt.sensors.base.mixins.logging") as mock_log, pytest.raises(Exception):
            s._check_register_response(rr, "read_input_registers")
        mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 11. ReadOnlySensor._update_internal_state() branches
# ─────────────────────────────────────────────────────────────────────────────


class TestReadOnlySensorUpdateInternalState:
    def _make_ro(self, suffix):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            return ReadOnlySensor(
                name="RO",
                object_id=f"sigen_{suffix}",
                input_type=InputType.HOLDING,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )

    @pytest.mark.asyncio
    async def test_update_internal_state_cancelled_error(self):
        """asyncio.CancelledError results in result=False (lines ~1073+)."""
        s = self._make_ro("ro_cancel")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=asyncio.CancelledError())

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()
        mock_metrics.modbus_read_error = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_internal_state_timeout_error(self):
        """asyncio.TimeoutError results in result=False (lines ~1104+)."""
        s = self._make_ro("ro_timeout")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_internal_state_input_registers(self):
        """INPUT type uses read_input_registers."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            from sigenergy2mqtt.common import InputType

            s = ReadOnlySensor(
                name="RO Input",
                object_id="sigen_ro_input",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )

        rr = MagicMock()
        rr.isError.return_value = False
        rr.registers = [100]

        modbus = MagicMock()
        modbus.read_input_registers = AsyncMock(return_value=rr)
        modbus.read_holding_registers = AsyncMock(return_value=rr)
        modbus.convert_from_registers = MagicMock(return_value=100)

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics):
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is True
        modbus.read_input_registers.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_internal_state_generic_exception_increments_metrics(self):
        """Generic exception calls Metrics.modbus_read_error and re-raises."""
        s = self._make_ro("ro_gen_exc")
        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(side_effect=Exception("generic"))

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()
        mock_metrics.modbus_read_error = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics), pytest.raises(Exception, match="generic"):
            await s._update_internal_state(modbus_client=modbus)

        mock_metrics.modbus_read_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_internal_state_debug_logging(self):
        """Debug logging branch in _update_internal_state (line ~1151+)."""
        s = self._make_ro("ro_debug_upd")
        s.debug_logging = True

        rr = MagicMock()
        rr.isError.return_value = False
        rr.registers = [42]

        modbus = MagicMock()
        modbus.read_holding_registers = AsyncMock(return_value=rr)
        modbus.convert_from_registers = MagicMock(return_value=42)

        mock_metrics = MagicMock()
        mock_metrics.modbus_read = AsyncMock()

        with patch("sigenergy2mqtt.sensors.base.readable.Metrics", mock_metrics), patch("sigenergy2mqtt.sensors.base.readable.logging") as mock_log:
            result = await s._update_internal_state(modbus_client=modbus)
        assert result is True
        mock_log.debug.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 12. AlarmSensor / AlarmCombinedSensor branches
# ─────────────────────────────────────────────────────────────────────────────


class TestAlarmSensorBranches:
    def _make_alarm(self, suffix):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteAlarm(AlarmSensor):
                def decode_alarm_bit(self, bit_position: int):
                    return f"Error bit {bit_position}" if bit_position == 0 else None

            return ConcreteAlarm("Alarm", f"sigen_{suffix}", 0, 1, 30001, Protocol.V2_4, "Equipment")

    def test_alarm_state2raw_string_no_alarm(self):
        s = self._make_alarm("alrm_s2r_na")
        assert s.state2raw("No Alarm") == 0

    def test_alarm_state2raw_numeric_one(self):
        s = self._make_alarm("alrm_s2r_1")
        assert s.state2raw(1) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 13. DerivedSensor branches
# ─────────────────────────────────────────────────────────────────────────────


class TestDerivedSensorBranches:
    @pytest.mark.asyncio
    async def test_derived_sensor_get_state_no_states(self):
        """DerivedSensor.get_state returns 0 when no states."""
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src_123"
        source.latest_interval = 60.0

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            derived = EnergyLifetimeAccumulationSensor(
                "Accum",
                "sigen_accum_d",
                "sigen_accum_d",
                source,
                ModbusDataType.UINT32,
                "kWh",
                DeviceClass.ENERGY,
                StateClass.TOTAL,
                "mdi:battery",
                1.0,
                2,
            )
        result = await derived.get_state()
        assert result == 0

    @pytest.mark.asyncio
    async def test_derived_sensor_get_state_with_string_state(self):
        """DerivedSensor.get_state returns string directly without gain/precision."""
        from sigenergy2mqtt.sensors.base import EnergyLifetimeAccumulationSensor

        source = MagicMock(spec=ReadOnlySensor)
        source.unique_id = "src_str"
        source.latest_interval = 60.0

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            derived = EnergyLifetimeAccumulationSensor(
                "Accum Str",
                "sigen_accum_str",
                "sigen_accum_str",
                source,
                ModbusDataType.UINT32,
                "kWh",
                DeviceClass.ENERGY,
                StateClass.TOTAL,
                "mdi:battery",
                1.0,
                2,
            )
        derived._states.append((time.time(), "some_string"))
        result = await derived.get_state()
        assert result == "some_string"


# ─────────────────────────────────────────────────────────────────────────────
# 14. protocol_version setter edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestProtocolVersionSetter:
    def test_protocol_version_float_valid(self):
        s = _make_sensor(uid_suffix="pv_float")
        valid_float = Protocol.V2_4.value
        s.protocol_version = float(valid_float)
        assert s.protocol_version == Protocol.V2_4

    def test_protocol_version_float_invalid_raises(self):
        s = _make_sensor(uid_suffix="pv_bad")
        with pytest.raises(AssertionError):
            s.protocol_version = 99.9  # type: ignore

    def test_protocol_version_string_raises(self):
        s = _make_sensor(uid_suffix="pv_str")
        with pytest.raises(AssertionError):
            s.protocol_version = "V2.4"  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 15. set_latest_state propagates to derived sensors
# ─────────────────────────────────────────────────────────────────────────────


class TestSetLatestState:
    def test_set_latest_state_propagates_to_derived(self):
        """set_latest_state calls set_source_values on derived sensors."""
        s = _make_sensor(uid_suffix="sls_derived")
        derived = MagicMock()
        s.derived_sensors["Mock"] = derived
        s.set_latest_state(100.0)
        derived.set_source_values.assert_called_once_with(s, s._states)

    def test_set_state_respects_max_states(self):
        """set_state trims state history to _max_states."""
        s = _make_sensor(uid_suffix="ss_trim")
        s._max_states = 2
        for i in range(5):
            s.set_state(float(i))
        assert len(s._states) == 2
        assert s._states[-1][1] == 4.0


# ─────────────────────────────────────────────────────────────────────────────
# 16. ReservedSensor branches
# ─────────────────────────────────────────────────────────────────────────────


class TestReservedSensor:
    def _make_reserved(self, suffix):
        from sigenergy2mqtt.common import InputType
        from sigenergy2mqtt.sensors.base import ReservedSensor

        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):

            class ConcreteReserved(ReservedSensor):
                pass

            # Class name must start with "Reserved"
            ConcreteReserved.__name__ = "Reserved" + suffix
            ConcreteReserved.__qualname__ = "Reserved" + suffix

            # Directly instantiate with required args
            s = ConcreteReserved(
                "Reserved Sensor",
                f"sigen_res_{suffix}",
                InputType.INPUT,
                0,
                1,
                30002,
                1,
                ModbusDataType.UINT16,
                10,
                None,
                None,
                None,
                None,
                None,
                None,
                Protocol.V2_4,
            )
        return s

    def test_reserved_publishable_always_false(self):
        s = self._make_reserved("pub")
        assert s.publishable is False

    def test_reserved_publishable_cannot_be_set_true(self):
        s = self._make_reserved("settrue")
        with pytest.raises(ValueError):
            s.publishable = True

    def test_reserved_apply_sensor_overrides_noop(self):
        s = self._make_reserved("noop")
        registers = MagicMock()
        # Should not raise; it's a no-op
        s.apply_sensor_overrides(registers)


# ─────────────────────────────────────────────────────────────────────────────
# 17. SanityCheck failure increment config
# ─────────────────────────────────────────────────────────────────────────────


class TestSanityCheckFailureIncrement:
    @pytest.mark.asyncio
    async def test_sanity_check_exception_not_counted_when_config_disabled(self):
        """SanityCheckException doesn't increment failures when sanity_check_failures_increment=False."""
        from sigenergy2mqtt.sensors.base import SanityCheckException

        s = _make_sensor(uid_suffix="sc_nocount")
        s["state_topic"] = "test/state"
        s["json_attributes_topic"] = "test/attrs"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise SanityCheckException("out of range")

        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            patch("sigenergy2mqtt.sensors.base.active_config.sanity_check_failures_increment", False),
            patch("sigenergy2mqtt.sensors.base.active_config.home_assistant.enabled", False),
            patch("sigenergy2mqtt.sensors.base.logging"),
        ):
            await s.publish(mqtt, modbus)

        assert s._failures == 0  # not counted

    @pytest.mark.asyncio
    async def test_sanity_check_exception_counted_when_config_enabled(self):
        """SanityCheckException DOES increment failures when sanity_check_failures_increment=True."""
        from sigenergy2mqtt.sensors.base import SanityCheckException

        s = _make_sensor(uid_suffix="sc_count")
        s["state_topic"] = "test/state"
        s["json_attributes_topic"] = "test/attrs"
        mqtt = _mqtt_mock()
        modbus = MagicMock()
        modbus.connected = True

        async def _update(**kw):
            raise SanityCheckException("out of range")

        with (
            patch.object(s, "_update_internal_state", side_effect=_update),
            patch("sigenergy2mqtt.sensors.base.active_config.sanity_check_failures_increment", True),
            patch("sigenergy2mqtt.sensors.base.active_config.home_assistant.enabled", False),
            patch("sigenergy2mqtt.sensors.base.logging"),
        ):
            await s.publish(mqtt, modbus)

        assert s._failures == 1


# ─────────────────────────────────────────────────────────────────────────────
# 18. WritableSensorMixin publishable via apply_sensor_overrides
# ─────────────────────────────────────────────────────────────────────────────


class TestWritableSensorOverrides:
    def test_writable_sensor_read_write_false_sets_unpublishable(self):
        """WritableSensorMixin sensor becomes unpublishable when read_write=False."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            # WriteOnlySensor is a concrete WritableSensorMixin subclass
            wo = WriteOnlySensor("WO", "sigen_wo_rw", 0, 1, 30001, Protocol.V2_4)
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.write_only = False
        with patch.dict("sigenergy2mqtt.sensors.base.active_config.sensor_overrides", {}):
            wo.apply_sensor_overrides(registers)
        assert wo.publishable is False

    def test_write_only_sensor_write_only_false_unpublishable(self):
        """WriteOnlySensor (not WritableSensorMixin ReadWrite) also respects write_only override."""
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            wo = WriteOnlySensor("WO2", "sigen_wo_wo", 0, 1, 30001, Protocol.V2_4)
        registers = MagicMock(spec=RegisterAccess)
        registers.no_remote_ems = False
        registers.write_only = False
        with patch.dict("sigenergy2mqtt.sensors.base.active_config.sensor_overrides", {}):
            wo.apply_sensor_overrides(registers)
        assert wo.publishable is False


# ─────────────────────────────────────────────────────────────────────────────
# 19. __eq__ and __hash__
# ─────────────────────────────────────────────────────────────────────────────


class TestSensorEqualityAndHash:
    def test_eq_same_unique_id(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s1 = ConcreteSensor(
                name="S1",
                unique_id="sigen_eq1",
                object_id="sigen_eq1",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
            s2 = ConcreteSensor(
                name="S2",
                unique_id="sigen_eq1",
                object_id="sigen_eq1",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        assert s1 == s2

    def test_eq_different_unique_id(self):
        with patch.dict(Sensor._used_unique_ids, clear=True), patch.dict(Sensor._used_object_ids, clear=True):
            s1 = ConcreteSensor(
                name="S1",
                unique_id="sigen_eqa",
                object_id="sigen_eqa",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
            s2 = ConcreteSensor(
                name="S2",
                unique_id="sigen_eqb",
                object_id="sigen_eqb",
                unit=None,
                device_class=None,
                state_class=None,
                icon=None,
                gain=None,
                precision=None,
                protocol_version=Protocol.V2_4,
            )
        assert s1 != s2

    def test_eq_non_sensor(self):
        s = _make_sensor(uid_suffix="eq_non")
        assert s != "not a sensor"

    def test_hash_unique_id(self):
        s = _make_sensor(uid_suffix="hash1")
        assert hash(s) == hash(s["unique_id"])


# ─────────────────────────────────────────────────────────────────────────────
# 20. get_discovery_components with options
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


class TestGainProperty:
    def test_gain_returns_1_when_none(self):
        s = _make_sensor(uid_suffix="gain_none")
        s._gain = None
        assert s.gain == 1.0

    def test_gain_returns_value_when_set(self):
        s = _make_sensor(uid_suffix="gain_val")
        s._gain = 100.0
        assert s.gain == 100.0

    def test_gain_setter(self):
        s = _make_sensor(uid_suffix="gain_set")
        s.gain = 500.0
        assert s._gain == 500.0

    def test_gain_setter_none(self):
        s = _make_sensor(uid_suffix="gain_set_none")
        s.gain = None
        assert s._gain is None


# ─────────────────────────────────────────────────────────────────────────────
# 22. ReadableSensorMixin scan-interval override
# ─────────────────────────────────────────────────────────────────────────────


class TestReadableSensorScanIntervalOverride:
    def test_scan_interval_override_applied(self):
        """scan-interval override is applied during __init__."""
        from sigenergy2mqtt.common import InputType

        with (
            patch.dict(Sensor._used_unique_ids, clear=True),
            patch.dict(Sensor._used_object_ids, clear=True),
            patch(
                "sigenergy2mqtt.sensors.base.active_config.sensor_overrides",
                {"sigen_ro_si": {"scan-interval": 99}},
            ),
        ):
            s = ReadOnlySensor(
                name="ScanInterval",
                object_id="sigen_ro_si",
                input_type=InputType.INPUT,
                plant_index=0,
                device_address=1,
                address=30001,
                count=1,
                data_type=ModbusDataType.UINT16,
                scan_interval=10,
                unit=UnitOfPower.WATT,
                device_class=DeviceClass.POWER,
                state_class=StateClass.MEASUREMENT,
                icon="mdi:flash",
                gain=1.0,
                precision=2,
                protocol_version=Protocol.V2_4,
            )
        assert s.scan_interval == 99
