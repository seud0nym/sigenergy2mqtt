import asyncio
import json
import logging
import time
from collections import deque
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigenergy2mqtt.common import DeviceClass, Protocol, StateClass
from sigenergy2mqtt.config.models.persistence import PersistenceConfig
from sigenergy2mqtt.modbus import ModbusDataType
from sigenergy2mqtt.persistence import state_store
from sigenergy2mqtt.sensors.base.accumulation import (
    EnergyDailyAccumulationSensor,
    EnergyLifetimeAccumulationSensor,
    ResettableAccumulationSensor,
)
from sigenergy2mqtt.sensors.base.constants import DiscoveryKeys, SensorAttributeKeys
from sigenergy2mqtt.sensors.base.sensor import Sensor


@pytest.fixture(autouse=True)
def mock_config(tmp_path):
    # Clear class-level tracking to avoid "already used" errors
    Sensor._used_unique_ids.clear()
    Sensor._used_object_ids.clear()

    with (
        patch("sigenergy2mqtt.config.active_config.persistent_state_path", tmp_path),
        patch("sigenergy2mqtt.config.active_config.home_assistant.unique_id_prefix", "sigen"),
        patch("sigenergy2mqtt.config.active_config.home_assistant.entity_id_prefix", "sigenergy2mqtt"),
        patch("sigenergy2mqtt.config.active_config.sensor_debug_logging", True),
        patch("sigenergy2mqtt.config.active_config.home_assistant.enabled_by_default", True),
    ):
        # Initialize state_store for tests
        persistence_cfg = PersistenceConfig(mqtt_redundancy=False)
        asyncio.run(state_store.initialise(tmp_path, persistence_cfg))
        yield tmp_path


class TestResettableAccumulationSensorCoverage:
    def _make_sensor(self, source=None, unique_id="sigen_test_uid", **kwargs):
        if source is None:
            source = MagicMock()
            source.unique_id = "sigen_source_id"
            source.data_type = ModbusDataType.UINT32
            source.latest_interval = 3600.0
            source.__getitem__.side_effect = lambda x: "sigenergy2mqtt_source_obj" if x == DiscoveryKeys.OBJECT_ID else MagicMock()
            source.latest_raw_state = 0.0
            source.protocol_version = Protocol.V1_8

        return ResettableAccumulationSensor(
            name="Test",
            unique_id=unique_id,
            object_id="sigenergy2mqtt_test_obj",
            source=source,
            data_type=ModbusDataType.UINT32,
            unit="kWh",
            device_class=DeviceClass.ENERGY,
            state_class=StateClass.TOTAL_INCREASING,
            icon="mdi:icon",
            gain=1.0,
            precision=2,
            **kwargs,
        )

    def test_init_load_success(self, mock_config):
        # Prepare envelope in category dir
        cat_dir = mock_config / "sensor"
        cat_dir.mkdir(parents=True, exist_ok=True)
        state_file = cat_dir / "sigen_test_uid.state"
        state_file.write_text(json.dumps({"v": "123.45", "ts": int(time.time()), "ver": "1.0.0"}))

        sensor = self._make_sensor()
        assert sensor._current_total == 123.45

    def test_load_persisted_state_errors(self, mock_config, caplog):
        with patch.object(state_store, "load_sync", side_effect=OSError("denied")):
            with caplog.at_level(logging.WARNING):
                self._make_sensor()
                assert "denied" in caplog.text

        Sensor._used_unique_ids.clear()
        Sensor._used_object_ids.clear()
        with patch.object(state_store, "load_sync", side_effect=RuntimeError("generic")):
            with caplog.at_level(logging.WARNING):
                self._make_sensor()
                assert "generic" in caplog.text

    def test_discovery_and_attributes(self, mock_config):
        sensor = self._make_sensor()
        disc = sensor.get_discovery_components()
        assert "sigen_test_uid_reset" in disc

        topics = sensor.observable_topics()
        assert sensor._reset_topic in topics

        attrs = sensor.get_attributes()
        assert attrs[SensorAttributeKeys.RESET_TOPIC] == sensor._reset_topic

    @pytest.mark.asyncio
    async def test_notify_reset(self, mock_config):
        sensor = self._make_sensor()
        # Invalid topic (Line 179)
        assert await sensor.notify(None, MagicMock(), "10.0", "invalid/topic", MagicMock()) is False

        # Valid topic
        with patch.object(sensor, "_persist_current_total", new_callable=AsyncMock) as mock_p:
            await sensor.notify(None, MagicMock(), "50.0", sensor._reset_topic, MagicMock())
            assert sensor._current_total == 50.0
            mock_p.assert_called_with(50.0)

    @pytest.mark.asyncio
    async def test_set_source_values_logic(self, mock_config):
        sensor = self._make_sensor()
        now = time.time()
        # Hit 215-216 (wrong sensor)
        other_sensor = MagicMock()
        sensor.set_source_values(other_sensor, deque())

        # Hit 218-219 (len < 2)
        sensor.set_source_values(sensor._source, deque([(now, 100.0)]))

        # Hit 224+
        values = deque([(now - 3600, 100.0), (now, 200.0)])
        sensor.set_source_values(sensor._source, values)
        assert sensor._current_total > 0

        # Negative increase (Line 228-231)
        values = deque([(now - 3600, 300.0), (now, 200.0)])
        sensor.set_source_values(sensor._source, values)

        # Negative interval (Line 216)
        sensor._source.latest_interval = -100.0
        sensor.set_source_values(sensor._source, values)

    @pytest.mark.asyncio
    async def test_persist_errors(self, mock_config, caplog):
        sensor = self._make_sensor()
        with patch.object(state_store, "save_sync", side_effect=PermissionError):
            await sensor._persist_current_total(100.0)
            assert "Failed to persist state" in caplog.text

        with patch.object(state_store, "save_sync", side_effect=RuntimeError):
            await sensor._persist_current_total(100.0)
            assert "Unexpected error persisting state" in caplog.text

    def test_async_cleanup_branches(self, mock_config):
        sensor = self._make_sensor()
        values = deque([(time.time() - 3600, 100.0), (time.time(), 200.0)])
        # Hit 234-254 (asyncio branches)
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("asyncio.get_event_loop") as mock_evt:
                mock_loop = MagicMock()
                mock_loop.is_running.return_value = True
                mock_loop.create_task.side_effect = lambda coro: coro.close()
                mock_evt.return_value = mock_loop
                # Line 245
                with patch("asyncio.get_running_loop", side_effect=RuntimeError):
                    with patch("asyncio.run_coroutine_threadsafe") as mock_threadsafe:
                        mock_threadsafe.side_effect = lambda coro, loop: (coro.close(), MagicMock())[1]
                        sensor.set_source_values(sensor._source, values)
                # Line 248-249 (run_coroutine_threadsafe exception)
                with patch("asyncio.run_coroutine_threadsafe", side_effect=Exception):
                    sensor.set_source_values(sensor._source, values)


class TestEnergyLifetimeAccumulationSensorCoverage:
    def test_init(self, mock_config):
        source = MagicMock()
        source.unique_id = "sigen_source"
        source.data_type = ModbusDataType.UINT32
        source.unit = "kWh"
        source.device_class = DeviceClass.ENERGY
        source.state_class = StateClass.TOTAL_INCREASING
        source.gain = 1.0
        source.precision = 2
        source.protocol_version = Protocol.V1_8
        source.__getitem__.side_effect = lambda x: "sigenergy2mqtt_source_obj"
        sensor = EnergyLifetimeAccumulationSensor("Test", "sigen_life", "sigenergy2mqtt_obj", source)
        assert sensor.state_class == StateClass.TOTAL_INCREASING

    def test_init_invalid_prefix(self, mock_config):
        # Line 75
        source = MagicMock()
        source.unique_id = "sigen_source"
        source.data_type = ModbusDataType.UINT32
        source.protocol_version = Protocol.V1_8
        source.__getitem__.side_effect = lambda x: "sigenergy2mqtt_source_obj"
        with pytest.raises(AssertionError, match="does not start with"):
            EnergyLifetimeAccumulationSensor("Test", "sigen_life", "bad_prefix", source)


class TestEnergyDailyAccumulationSensorCoverageExtended:
    def _make_sensor(self, source=None, **kwargs):
        if source is None:
            source = MagicMock()
            source.unique_id = "sigen_source_id"
            source.data_type = ModbusDataType.UINT32
            source.__getitem__.side_effect = lambda x: "sigenergy2mqtt_source_obj" if x == DiscoveryKeys.OBJECT_ID else MagicMock()
            source.unit = "kWh"
            source.device_class = DeviceClass.ENERGY
            source.state_class = StateClass.TOTAL_INCREASING
            source.gain = 1.0
            source.precision = 2
            source.latest_raw_state = 100.0
            source.protocol_version = Protocol.V1_8

        return EnergyDailyAccumulationSensor(name="Test Daily", unique_id=kwargs.pop("unique_id", "sigen_daily_uid"), object_id="sigenergy2mqtt_daily_obj", source=source, **kwargs)

    def test_init_invalid_prefix(self, mock_config):
        # Line 337
        source = MagicMock()
        source.unique_id = "sigen_source_id"
        source.data_type = ModbusDataType.UINT32
        source.protocol_version = Protocol.V1_8
        source.__getitem__.side_effect = lambda x: "sigenergy2mqtt_source_obj"
        with pytest.raises(AssertionError, match="does not start with"):
            EnergyDailyAccumulationSensor("Test", "sigen_daily", "bad_prefix", source)

    def test_init_load_midnight_success(self, mock_config):
        cat_dir = mock_config / "sensor"
        cat_dir.mkdir(parents=True, exist_ok=True)
        fpath = cat_dir / "sigen_source_id.atmidnight"
        import json

        fpath.write_text(json.dumps({"v": "100.0", "ts": int(time.time()), "ver": "1.0.0"}))
        sensor = self._make_sensor()
        sensor.on_added_to_device()
        assert sensor._state_at_midnight == 100.0

    def test_load_midnight_state_error_types(self, mock_config, caplog):
        # Stale file
        cat_dir = mock_config / "sensor"
        cat_dir.mkdir(parents=True, exist_ok=True)
        fpath = cat_dir / "sigen_source_id.atmidnight"
        import json

        fpath.write_text(json.dumps({"v": "100.0", "ts": int(time.time()) - 90000, "ver": "1.0.0"}))
        with caplog.at_level(logging.DEBUG):
            sensor = self._make_sensor()
            sensor.on_added_to_device()
            assert "discarding stale value" in caplog.text

        # Negative value
        Sensor._used_unique_ids.clear()
        Sensor._used_object_ids.clear()
        fpath.write_text(json.dumps({"v": "-10.0", "ts": int(time.time()), "ver": "1.0.0"}))
        with caplog.at_level(logging.DEBUG):
            sensor = self._make_sensor()
            sensor.on_added_to_device()
            assert "Ignored negative midnight state" in caplog.text

        # Generic Exception
        Sensor._used_unique_ids.clear()
        Sensor._used_object_ids.clear()
        with patch.object(state_store, "load_sync", side_effect=RuntimeError("generic")):
            with caplog.at_level(logging.WARNING):
                sensor = self._make_sensor()
                sensor.on_added_to_device()
                assert "Failed to read" in caplog.text

    @pytest.mark.asyncio
    async def test_update_midnight_success(self, mock_config):
        sensor = self._make_sensor()
        await sensor._update_state_at_midnight(150.0)
        assert sensor._state_at_midnight == 150.0
        # Return none (Line 383)
        await sensor._update_state_at_midnight(None)

    @pytest.mark.asyncio
    async def test_update_midnight_errors(self, mock_config, caplog):
        sensor = self._make_sensor()
        with patch.object(state_store, "save_sync", side_effect=RuntimeError):
            await sensor._update_state_at_midnight(100.0)
            assert "Failed to update" in caplog.text

    @pytest.mark.asyncio
    async def test_notify_extended(self, mock_config, caplog):
        sensor = self._make_sensor()
        sensor.debug_logging = True

        # Wrong topic (Line 408-409)
        assert await sensor.notify(None, MagicMock(), "10.0", "wrong_topic", MagicMock()) is False

        # Successful notify with debug logging (Line 411-428)
        with patch.object(sensor, "_update_state_at_midnight", new_callable=AsyncMock) as mock_u:
            with caplog.at_level(logging.DEBUG):
                assert await sensor.notify(None, MagicMock(), "10.0", sensor._reset_topic, MagicMock()) is True
                assert "notified of updated state 10.0" in caplog.text
                mock_u.assert_called()

    @pytest.mark.asyncio
    async def test_publish_init_midnight(self, mock_config):
        sensor = self._make_sensor()
        sensor.configure_mqtt_topics("device_123")
        # Line 441-443
        with patch.object(Path, "is_file", return_value=False):
            with patch.object(sensor, "_update_state_at_midnight", new_callable=AsyncMock) as mock_u:
                await sensor.publish(MagicMock(), None)
                mock_u.assert_called()

    def test_set_source_values_logic(self, mock_config):
        sensor = self._make_sensor()

        # Wrong sensor (Line 457-458)
        sensor.set_source_values(MagicMock(), deque())

        now = time.time()
        # Day change branches (Line 472, 482-483)
        yesterday_tm = time.localtime(now - 86400)
        today_tm = time.localtime(now)
        yesterday = now - 86400
        today = now

        values = deque([(yesterday, 100.0), (today, 200.0)])

        # Case: asyncio.get_running_loop success (Line 472)
        with patch("time.localtime", side_effect=[yesterday_tm, today_tm, yesterday_tm, today_tm]):
            mock_loop = MagicMock()
            mock_loop.create_task.side_effect = lambda coro: coro.close()
            with patch("asyncio.get_running_loop", return_value=mock_loop):
                sensor.set_source_values(sensor._source, values)
                mock_loop.create_task.assert_called()

        # Case: Generic Exception in day change (Line 482-483)
        Sensor._used_unique_ids.clear()
        Sensor._used_object_ids.clear()
        sensor = self._make_sensor()
        with patch("time.localtime", side_effect=[yesterday_tm, today_tm]):
            with patch("asyncio.get_running_loop", side_effect=RuntimeError):  # Force bypass to next block
                with patch("asyncio.get_event_loop", side_effect=Exception):  # Generic exception
                    sensor.set_source_values(sensor._source, values)

    def test_set_source_values_midnight_init(self, mock_config):
        # Line 489
        sensor = self._make_sensor()
        sensor._state_at_midnight = 0.0  # Force init
        values = deque([(time.time(), 300.0)])
        sensor.set_source_values(sensor._source, values)
        assert sensor._state_at_midnight == 300.0
