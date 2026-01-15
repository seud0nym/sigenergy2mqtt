"""Extended tests for sigenergy2mqtt/pvoutput/service_topics.py"""

import json
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

from sigenergy2mqtt.config import Config, OutputField, StatusField
from sigenergy2mqtt.config.pvoutput_config import PVOutputConfiguration
from sigenergy2mqtt.pvoutput.service import Service
from sigenergy2mqtt.pvoutput.service_topics import Calculation, ServiceTopics, TimePeriodServiceTopics
from sigenergy2mqtt.pvoutput.topic import Topic


def make_service_topics(name="test", enabled=True, value_key=OutputField.GENERATION, **kwargs):
    logger = logging.getLogger("test-pvoutput-topics")
    service = MagicMock(spec=Service)
    service.unique_id = "test_service"
    service.__class__.__name__ = "TestService"
    return ServiceTopics(service, enabled, logger, value_key=value_key, **kwargs)


# region register tests


def test_register_ignores_empty_topic():
    """Test that register ignores empty or whitespace-only topics."""
    st = make_service_topics()
    st.register(Topic("", gain=1.0))
    st.register(Topic("   ", gain=1.0))
    assert len(st) == 0


def test_register_with_disabled_service_topics():
    """Test that register does not add topics when service topics is disabled."""
    st = make_service_topics(enabled=False)
    st.register(Topic("test/topic", gain=1.0))
    assert len(st) == 0


def test_register_restores_state_if_needed():
    """Test that register calls restore_state if using DIFFERENCE or PEAK calculation."""
    st = make_service_topics()
    st.calculation = Calculation.DIFFERENCE

    with patch.object(st, "restore_state") as mock_restore:
        st.register(Topic("test/topic", gain=1.0))
        mock_restore.assert_called_once()


def test_register_populates_time_periods():
    """Test that register adds topic to child time periods."""
    st = make_service_topics()
    child = MagicMock(spec=TimePeriodServiceTopics)
    st._time_periods = [child]

    st.register(Topic("test/topic", gain=1.0))

    child.register.assert_called_once()


# endregion


# region restore_state tests


def test_restore_state_from_file():
    """Test restoring state from a valid JSON file."""
    st = make_service_topics(value_key=OutputField.PEAK_POWER)
    topic = Topic("test/topic", gain=1.0)

    # Mock Path constructor to return our mock file
    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file

        mock_file.is_file.return_value = True
        mock_file.stat.return_value.st_mtime = time.time()

        # Mock file content
        saved_topic = Topic("test/topic", state=100.0, timestamp=time.localtime())
        mock_content = json.dumps({"test/topic": saved_topic}, default=Topic.json_encoder)
        mock_file.open = mock_open(read_data=mock_content)

        # We also need to handle obsolete path check in restore_state
        # The code creates another Path object for obsolete file.
        # We can make side_effect to return different mocks or just use same mock if acceptable.
        # restore_state logic:
        # self._persistent_state_file = Path(...)
        # if value_key == PEAK_POWER: obsolete = Path(...)
        # We want persistent file to be found, obsolete not found or doesn't matter.

        # Simplest: return mock_file for all Path() calls, and control behavior based on usage?
        # Or side_effect.
        def path_side_effect(*args, **kwargs):
            # If creating the state file (args contains unique_id)
            if any("test_service" in str(a) for a in args):
                return mock_file
            # Else (obsolete file or config path)
            m = MagicMock()
            m.is_file.return_value = False
            return m

        mock_path_cls.side_effect = path_side_effect

        st.restore_state(topic)

    assert st["test/topic"].state == 100.0


def test_restore_state_stale_file_deleted():
    """Test that stale state file is deleted."""
    st = make_service_topics()
    topic = Topic("test/topic", gain=1.0)

    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file

        mock_file.is_file.return_value = True
        mock_file.stat.return_value.st_mtime = time.time() - 86400  # Stale

        st.restore_state(topic)

        assert mock_file.unlink.call_count == 1
        mock_file.unlink.assert_called_with(missing_ok=True)


def test_restore_state_invalid_json():
    """Test handling of invalid JSON in state file."""
    st = make_service_topics()
    topic = Topic("test/topic", gain=1.0)

    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file

        mock_file.is_file.return_value = True
        mock_file.stat.return_value.st_mtime = time.time()
        mock_file.open = mock_open(read_data="INVALID JSON")

        # Should catch JSONDecodeError and log warning, not crash
        st.restore_state(topic)


def test_restore_state_file_not_found():
    """Test restore_state when file does not exist."""
    st = make_service_topics()
    topic = Topic("test/topic", gain=1.0)

    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file

        mock_file.is_file.return_value = False

        st.restore_state(topic)
        # Should simply return without error
        assert "test/topic" not in st


# endregion


# region reset tests


def test_reset_clears_state():
    """Test that reset clears state of all topics."""
    st = make_service_topics()
    t1 = Topic("t1", state=10.0, previous_state=5.0)
    st.register(t1)

    st.reset()

    assert st["t1"].state == 0.0
    assert st["t1"].previous_state is None
    assert st["t1"].previous_timestamp is None


def test_reset_deletes_persistent_file():
    """Test that reset deletes the persistent state file."""
    st = make_service_topics()
    # Manual setup of _persistent_state_file
    st._persistent_state_file = MagicMock(spec=Path)
    st._persistent_state_file.is_file.return_value = True

    st.reset()

    st._persistent_state_file.unlink.assert_called_with(missing_ok=True)


def test_reset_resets_children():
    """Test that reset calls reset on child periods."""
    st = make_service_topics()
    child = MagicMock(spec=TimePeriodServiceTopics)
    st._time_periods = [child]

    st.reset()

    child.reset.assert_called_once()


# endregion


# region handle_update tests


@pytest.mark.asyncio
async def test_handle_update_simple():
    """Test simple update of a topic."""
    st = make_service_topics()
    t = Topic("t/1", gain=1.0)
    st.register(t)

    mock_handler = MagicMock()
    mock_client = MagicMock()

    # Mock lock
    st._service.lock = MagicMock()
    st._service.lock.return_value.__aenter__.return_value = None
    st._service.lock.return_value.__aexit__.return_value = None

    await st.handle_update(None, mock_client, "123.4", "t/1", mock_handler)

    assert t.state == 123.4


@pytest.mark.asyncio
async def test_handle_update_peak_calculation(monkeypatch):
    """Test update with PEAK calculation where new value is higher."""
    st = make_service_topics(calc=Calculation.PEAK)
    # Patch Path so register->restore_state doesn't crash or overwrite with real path
    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file
        mock_file.is_file.return_value = False  # No previous state
        mock_file.open = mock_open()

        t = Topic("t/1", gain=1.0, state=50.0)
        st.register(t)

        # Ensure _persistent_state_file is set to our mock (register calls restore_state)
        # It should be set automatically by restore_state using mock_path_cls

        mock_handler = MagicMock()
        mock_client = MagicMock()

        # Mock lock properly for async context manager
        lock_mock = MagicMock()

        async def async_lock_enter(*args, **kwargs):
            return None

        async def async_lock_exit(*args, **kwargs):
            return None

        lock_mock.__aenter__ = async_lock_enter
        lock_mock.__aexit__ = async_lock_exit
        st._service.lock.return_value = lock_mock

        # Update with higher value
        await st.handle_update(None, mock_client, 100.0, "t/1", mock_handler)

        assert t.state == 100.0
        # Should save state
        mock_file.open.assert_called()


@pytest.mark.asyncio
async def test_handle_update_peak_calculation_lower_value():
    """Test update with PEAK calculation where new value is lower (should be ignored)."""
    st = make_service_topics(calc=Calculation.PEAK)

    with patch("sigenergy2mqtt.pvoutput.service_topics.Path") as mock_path_cls:
        mock_file = MagicMock()
        mock_path_cls.return_value = mock_file

        t = Topic("t/1", gain=1.0, state=100.0)
        st.register(t)

        mock_handler = MagicMock()
        mock_client = MagicMock()

        await st.handle_update(None, mock_client, 50.0, "t/1", mock_handler)

        assert t.state == 100.0
        # Should NOT save state
        mock_file.open.assert_not_called()


@pytest.mark.asyncio
async def test_handle_update_with_time_periods():
    """Test update propagates to time periods."""
    st = make_service_topics()
    t = Topic("t/1", gain=1.0)
    st.register(t)

    child = MagicMock(spec=TimePeriodServiceTopics)
    child._value_key = OutputField.EXPORT_PEAK
    child.__getitem__.return_value = MagicMock(state=0.0)
    st._time_periods = [child]

    # Manually mock persistent file since we inject time periods
    st._persistent_state_file = MagicMock()

    # Mock current time period on class property
    with patch.object(PVOutputConfiguration, "current_time_period", new_callable=PropertyMock) as mock_prop:
        mock_prop.return_value = [OutputField.EXPORT_PEAK]

        # Mock lock
        lock_mock = MagicMock()

        async def async_lock_enter(*args, **kwargs):
            return None

        async def async_lock_exit(*args, **kwargs):
            return None

        lock_mock.__aenter__ = async_lock_enter
        lock_mock.__aexit__ = async_lock_exit
        st._service.lock.return_value = lock_mock

        await st.handle_update(None, MagicMock(), 100.0, "t/1", MagicMock())

        child.handle_update.assert_called()


# endregion


# region other tests


def test_subscribe_disabled():
    """Test subscribe does not register with handler if disabled."""
    st = make_service_topics(enabled=False)
    t = Topic("t/1", gain=1.0)
    # forcefully add topic
    st["t/1"] = t

    handler = MagicMock()
    client = MagicMock()

    st.subscribe(client, handler)

    handler.register.assert_not_called()


def test_check_is_updating_stale_warning(caplog):
    """Test that check_is_updating logs warning for stale topics."""
    st = make_service_topics()
    t = Topic("t/1", gain=1.0, timestamp=time.localtime(time.time() - 3600))
    st.register(t)

    # Force started long ago
    with patch("sigenergy2mqtt.config.Config.pvoutput.started", time.time() - 4000):
        # Should return False because > scan_interval (default)
        # And log warning
        result = st.check_is_updating(interval_minutes=5, now_struct=time.localtime())

        assert result is False
        assert "has not been updated for" in caplog.text


def test_aggregate_with_never_return_none():
    """Test aggregate returns 0.0 instead of None when no topics."""
    st = make_service_topics()
    # No topics registered

    total, at, count = st.aggregate(exclude_zero=True, never_return_none=True)

    assert total == 0.0
    assert count == 0


def test_time_period_service_subscribe_pass():
    """TimePeriodServiceTopics.subscribe should be a no-op / pass."""
    svc = MagicMock(spec=Service)
    tp = TimePeriodServiceTopics(svc, True, logging.getLogger(), OutputField.EXPORT_PEAK)

    # Should not raise
    tp.subscribe(None, None)


# endregion
