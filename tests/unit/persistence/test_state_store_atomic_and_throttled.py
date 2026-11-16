"""Atomic disk writes, corrupt-file fallback, throttled saves and same-day loads."""

import asyncio
import json
import os
import threading
import time
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.persistence.state_store import (
    StateStore,
    _DiskBackend,
    _is_same_local_day,
    _make_envelope,
    _parse_envelope,
)


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def persistence_config():
    config = MagicMock()
    config.mqtt_redundancy = False
    config.mqtt_state_prefix = "sigenergy2mqtt/_state"
    config.cache_warmup_timeout = 1.0
    config.disk_primary = True
    config.sync_timeout = 5.0
    return config


async def _store_with_mqtt(state_dir, persistence_config) -> StateStore:
    persistence_config.mqtt_redundancy = True
    client = MagicMock()
    client.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS
    store = StateStore()
    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(client, MagicMock())):
        await store.initialise(state_dir, persistence_config)
    return store


# --------------------------------------------------------------------------- atomic writes


def test_disk_save_is_atomic_and_leaves_no_temp_file(state_dir):
    disk = _DiskBackend(state_dir, "1.0.0")
    disk.save("sensor", "k.state", "1.0")
    disk.save("sensor", "k.state", "2.0")
    assert json.loads((state_dir / "sensor" / "k.state").read_text())["v"] == "2.0"
    assert sorted(p.name for p in (state_dir / "sensor").iterdir()) == ["k.state"]


def test_disk_save_syncs_before_replacing(state_dir):
    disk = _DiskBackend(state_dir, "1.0.0")
    events: list[str] = []
    real_fsync, real_replace = os.fsync, os.replace
    with (
        patch("sigenergy2mqtt.persistence.state_store.os.fsync", side_effect=lambda fd: (events.append("fsync"), real_fsync(fd))[1]),
        patch("sigenergy2mqtt.persistence.state_store.os.replace", side_effect=lambda a, b: (events.append("replace"), real_replace(a, b))[1]),
    ):
        disk.save("sensor", "k.state", "1.0")
    # file contents synced, renamed into place, then the directory entry synced
    assert events == ["fsync", "replace", "fsync"]


def test_disk_save_survives_a_directory_that_cannot_be_synced(state_dir):
    disk = _DiskBackend(state_dir, "1.0.0")
    with patch("sigenergy2mqtt.persistence.state_store.os.open", side_effect=OSError("not supported")):
        disk.save("sensor", "k.state", "1.0")
    loaded = disk.load("sensor", "k.state")
    assert loaded is not None and loaded[0] == "1.0"


def test_interrupted_write_keeps_previous_content(state_dir):
    """A failure before the rename leaves the old file intact and removes the temp file."""
    disk = _DiskBackend(state_dir, "1.0.0")
    disk.save("sensor", "k.state", "1.0")
    with patch("sigenergy2mqtt.persistence.state_store.os.replace", side_effect=OSError("power loss")):
        with pytest.raises(OSError, match="power loss"):
            disk.save("sensor", "k.state", "2.0")
    loaded = disk.load("sensor", "k.state")
    assert loaded is not None and loaded[0] == "1.0"
    assert sorted(p.name for p in (state_dir / "sensor").iterdir()) == ["k.state"]


def test_all_keys_ignores_leftover_temp_files(state_dir):
    disk = _DiskBackend(state_dir, "1.0.0")
    disk.save("sensor", "k.state", "1.0")
    (state_dir / "sensor" / ".k.state.tmp").write_text("partial")
    (state_dir / ".root.tmp").write_text("partial")
    assert disk.all_keys() == [("sensor", "k.state")]


# --------------------------------------------------------------------------- corrupt files


@pytest.mark.parametrize("raw", ["", "   \n", "\x00\x00\x00", '{"v": "12.3", "t', "{"])
def test_parse_envelope_treats_empty_or_truncated_as_absent(raw):
    assert _parse_envelope(raw) is None


def test_parse_envelope_still_accepts_legacy_values():
    assert _parse_envelope("123.4", fallback_ts=5) == ("123.4", 5, True)
    assert _parse_envelope('{"other": 1}', fallback_ts=5) == ('{"other": 1}', 5, True)


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["", '{"v": "9', "\x00\x00"])
async def test_empty_or_corrupt_disk_file_is_absent(state_dir, persistence_config, content):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    await store.save("sensor", "k.state", "42.0")
    (state_dir / "sensor" / "k.state").write_text(content)
    assert await store.load("sensor", "k.state") is None
    store.shutdown()


@pytest.mark.asyncio
async def test_truncated_disk_file_falls_back_to_mqtt(state_dir, persistence_config):
    """Disk is primary, but an empty file must not hide the intact MQTT copy."""
    store = await _store_with_mqtt(state_dir, persistence_config)
    await store.save("sensor", "k.state", "42.0")
    store._mqtt._cache[("sensor", "k.state")] = ("42.0", int(time.time()))
    (state_dir / "sensor" / "k.state").write_text("")

    assert await store.load("sensor", "k.state") == "42.0"
    store.shutdown()


# --------------------------------------------------------------------------- throttled saves


@pytest.mark.asyncio
async def test_throttled_save_defers_then_flushes_on_shutdown(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"

    await store.save("sensor", "k.state", "1.0", min_interval=60)  # first write goes straight to disk
    assert json.loads(path.read_text())["v"] == "1.0"

    await store.save("sensor", "k.state", "2.0", min_interval=60)
    await store.save("sensor", "k.state", "3.0", min_interval=60)
    assert json.loads(path.read_text())["v"] == "1.0"  # held back
    assert await store.load("sensor", "k.state") == "3.0"  # but visible to readers
    assert store.load_sync("sensor", "k.state") == "3.0"

    store.shutdown()
    assert json.loads(path.read_text())["v"] == "3.0"


@pytest.mark.asyncio
async def test_throttled_save_writes_once_interval_has_elapsed(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    with patch("sigenergy2mqtt.persistence.state_store.time.monotonic", return_value=1000.0):
        await store.save("sensor", "k.state", "1.0", min_interval=60)
    with patch("sigenergy2mqtt.persistence.state_store.time.monotonic", return_value=1059.0):
        await store.save("sensor", "k.state", "2.0", min_interval=60)
    assert json.loads(path.read_text())["v"] == "1.0"
    with patch("sigenergy2mqtt.persistence.state_store.time.monotonic", return_value=1060.0):
        await store.save("sensor", "k.state", "3.0", min_interval=60)
    assert json.loads(path.read_text())["v"] == "3.0"
    assert store._deferred == {}
    store.shutdown()


@pytest.mark.asyncio
async def test_deferred_value_is_written_when_the_interval_ends_without_another_save(state_dir, persistence_config):
    """e.g. power drops to zero after a held-back update: the final total must still reach disk."""
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    await store.save("sensor", "k.state", "1.0", min_interval=0.3)
    await store.save("sensor", "k.state", "2.0", min_interval=0.3)
    await store.save("sensor", "k.state", "3.0", min_interval=0.3)
    assert json.loads(path.read_text())["v"] == "1.0"
    assert len(store._flush_timers) == 1

    for _ in range(40):
        await asyncio.sleep(0.05)
        if json.loads(path.read_text())["v"] == "3.0":
            break
    assert json.loads(path.read_text())["v"] == "3.0"
    assert store._deferred == {} and store._flush_timers == {}
    store.shutdown()


@pytest.mark.asyncio
async def test_flush_timer_is_cancelled_by_newer_save_delete_and_shutdown(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"

    async def defer(key: str):
        await store.save("sensor", key, "1.0", min_interval=60)
        await store.save("sensor", key, "2.0", min_interval=60)
        return store._flush_timers[("sensor", key)]

    timer = await defer("k.state")
    await store.save("sensor", "k.state", "9.0")  # immediate save replaces it
    assert timer.finished.is_set() and store._flush_timers == {}
    assert json.loads(path.read_text())["v"] == "9.0"

    timer = await defer("d.state")
    await store.delete("sensor", "d.state")
    assert timer.finished.is_set() and store._flush_timers == {}

    timer = await defer("s.state")
    store.shutdown()
    assert timer.finished.is_set() and store._flush_timers == {}
    assert json.loads((state_dir / "sensor" / "s.state").read_text())["v"] == "2.0"


@pytest.mark.asyncio
async def test_timer_write_cannot_overwrite_a_newer_reset(state_dir, persistence_config):
    """A timer callback that has taken its value must not land after a reset that follows it."""
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    await store.save("sensor", "k.state", "1.0", min_interval=60)
    await store.save("sensor", "k.state", "2.0", min_interval=60)
    store._flush_timers[("sensor", "k.state")].cancel()

    # Capture the write the timer queues instead of running it, then let a reset through first
    queued = []
    real_submit = store._executor.submit
    with patch.object(store._executor, "submit", side_effect=lambda fn, *a: queued.append((fn, a))):
        store._flush_deferred(("sensor", "k.state"))
    assert len(queued) == 1
    await store.save("sensor", "k.state", "0.0")  # reset
    await store.delete("sensor", "other.state")
    fn, args = queued[0]
    real_submit(fn, *args).result()  # the overtaken timer write finally runs

    assert json.loads(path.read_text())["v"] == "0.0"
    store.shutdown()
    assert json.loads(path.read_text())["v"] == "0.0"


@pytest.mark.asyncio
async def test_timer_write_cannot_resurrect_a_deleted_key(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    await store.save("sensor", "k.state", "1.0", min_interval=60)
    await store.save("sensor", "k.state", "2.0", min_interval=60)
    store._flush_timers[("sensor", "k.state")].cancel()
    queued = []
    real_submit = store._executor.submit
    with patch.object(store._executor, "submit", side_effect=lambda fn, *a: queued.append((fn, a))):
        store._flush_deferred(("sensor", "k.state"))
    await store.delete("sensor", "k.state")
    real_submit(queued[0][0], *queued[0][1]).result()
    assert not path.exists()
    store.shutdown()


@pytest.mark.asyncio
async def test_shutdown_waits_for_a_timer_callback_that_has_started(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    await store.save("sensor", "k.state", "1.0", min_interval=0.05)
    await store.save("sensor", "k.state", "2.0", min_interval=0.05)

    # Hold the timer callback inside the lock until shutdown is under way
    started = threading.Event()
    real_flush = store._flush_deferred

    def slow_flush(k):
        started.set()
        time.sleep(0.3)
        real_flush(k)

    timer = store._flush_timers[("sensor", "k.state")]
    timer.function = slow_flush
    assert started.wait(2)
    store.shutdown()
    assert json.loads(path.read_text())["v"] == "2.0"


@pytest.mark.asyncio
async def test_flush_after_executor_stopped_leaves_value_for_shutdown(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    await store.save("sensor", "k.state", "1.0", min_interval=60)
    await store.save("sensor", "k.state", "2.0", min_interval=60)
    store._flush_timers[("sensor", "k.state")].cancel()
    with patch.object(store._executor, "submit", side_effect=RuntimeError("cannot schedule new futures after shutdown")):
        store._flush_deferred(("sensor", "k.state"))
    assert store._deferred[("sensor", "k.state")][0] == "2.0"
    store.shutdown()
    assert json.loads((state_dir / "sensor" / "k.state").read_text())["v"] == "2.0"


@pytest.mark.asyncio
async def test_unthrottled_save_supersedes_deferred_value(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    await store.save("sensor", "k.state", "1.0", min_interval=60)
    await store.save("sensor", "k.state", "2.0", min_interval=60)
    await store.save("sensor", "k.state", "0.0")  # e.g. a reset: always immediate
    assert json.loads(path.read_text())["v"] == "0.0"
    store.shutdown()
    assert json.loads(path.read_text())["v"] == "0.0"


@pytest.mark.asyncio
async def test_delete_and_clean_discard_deferred_values(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    for key in ("a.state", "b.state"):
        await store.save("sensor", key, "1.0", min_interval=60)
        await store.save("sensor", key, "2.0", min_interval=60)

    await store.delete("sensor", "a.state")
    assert await store.load("sensor", "a.state") is None
    await store.clean()
    assert await store.load("sensor", "b.state") is None

    store.shutdown()
    assert not (state_dir / "sensor" / "a.state").exists()
    assert not (state_dir / "sensor" / "b.state").exists()


@pytest.mark.asyncio
async def test_flushed_value_keeps_the_time_it_was_produced(state_dir, persistence_config):
    """A value held back before midnight must not be stamped with the shutdown time."""
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    await store.save("sensor", "k.state", "1.0", min_interval=60)
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=1_700_000_000.0):
        await store.save("sensor", "k.state", "2.0", min_interval=60)
    store.shutdown()
    assert json.loads((state_dir / "sensor" / "k.state").read_text()) == {"v": "2.0", "ts": 1_700_000_000, "ver": store._version}


# --------------------------------------------------------------------------- same local day


def test_is_same_local_day():
    noon = time.mktime((2026, 11, 16, 12, 0, 0, 0, 0, -1))
    assert _is_same_local_day(time.mktime((2026, 11, 16, 0, 0, 1, 0, 0, -1)), noon) is True
    assert _is_same_local_day(time.mktime((2026, 11, 16, 23, 59, 59, 0, 0, -1)), noon) is True
    assert _is_same_local_day(time.mktime((2026, 11, 15, 23, 59, 59, 0, 0, -1)), noon) is False
    assert _is_same_local_day(time.mktime((2025, 11, 16, 12, 0, 0, 0, 0, -1)), noon) is False


@pytest.mark.asyncio
async def test_load_same_local_day(state_dir, persistence_config):
    store = StateStore()
    await store.initialise(state_dir, persistence_config)
    path = state_dir / "sensor" / "k.state"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(_make_envelope("7.0", "1.0.0"))
    assert await store.load("sensor", "k.state", same_local_day=True) == "7.0"

    # Written at 23:00 yesterday, read at 22:40 today: inside 24 hours but not the same day
    now = time.mktime((2026, 11, 16, 22, 40, 0, 0, 0, -1))
    written = time.mktime((2026, 11, 15, 23, 0, 0, 0, 0, -1))
    path.write_text(_make_envelope("7.0", "1.0.0", int(written)))
    with patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=now):
        assert await store.load("sensor", "k.state", same_local_day=True) is None
        assert store.load_sync("sensor", "k.state", same_local_day=True) is None
        assert await store.load("sensor", "k.state") == "7.0"
    store.shutdown()
