import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.persistence.state_store import StateStore


@pytest.fixture
def temp_state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def mock_persistence_config():
    config = MagicMock()
    config.mqtt_redundancy = False
    config.mqtt_state_prefix = "sigenergy2mqtt/_state"
    config.cache_warmup_timeout = 1.0
    config.disk_primary = True
    config.sync_timeout = 0.1
    return config


@pytest.mark.asyncio
async def test_sync_wrappers_from_running_loop(temp_state_dir, mock_persistence_config):
    """Test sync wrappers _when called from another thread_ while event loop is running."""
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    loop = asyncio.get_running_loop()

    # Simulate calling sync methods from another thread (different thread id)
    def call_sync_methods():
        # save_sync
        store.save_sync("test", "key", "val")
        # load_sync
        return store.load_sync("test", "key")

    result = await loop.run_in_executor(None, call_sync_methods)
    assert result == "val"

    def call_delete_sync():
        store.delete_sync("test", "key")

    await loop.run_in_executor(None, call_delete_sync)

    # Verify deleted
    def check_deleted():
        return store.load_sync("test", "key")

    res2 = await loop.run_in_executor(None, check_deleted)
    assert res2 is None


def test_sync_wrappers_no_running_loop(temp_state_dir, mock_persistence_config):
    """Test sync wrappers executed directly when there is no running loop but store initialized."""
    store = StateStore()

    # Force initialization without an active loop context to bypass async tests requirements for this specific case
    store._initialised = True
    store._disk = MagicMock()
    store._disk.load.return_value = ("val", 1234567890, False, False)
    # Give it a dummy thread pool so it doesn't fail checks
    store._executor = ThreadPoolExecutor(max_workers=1)

    # Calling save_sync without async context
    store.save_sync("test", "key", "val")
    store._disk.save.assert_called_with("test", "key", "val", debug=True)

    # Calling load_sync without async context
    val = store.load_sync("test", "key")
    assert val == "val"

    # Calling delete_sync without async context
    store.delete_sync("test", "key")
    store._disk.delete.assert_called_with("test", "key", debug=True)


@pytest.mark.asyncio
async def test_sync_wrappers_timeout_exception(temp_state_dir, mock_persistence_config):
    """Test exception handling in sync wrappers when future.result() times out."""
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    loop = asyncio.get_running_loop()

    # Mock the save/load methods to simulate hanging/timeout on future.result
    async def slow_save(*args, **kwargs):
        await asyncio.sleep(1.0)

    async def slow_load(*args, **kwargs):
        await asyncio.sleep(1.0)
        return "slow"

    async def slow_delete(*args, **kwargs):
        await asyncio.sleep(1.0)

    store.save = slow_save
    store.load = slow_load
    store.delete = slow_delete

    def call_sync_timeout():
        # These should timeout because sync_timeout is 0.1
        store.save_sync("test", "key", "val")
        store.load_sync("test", "key")
        store.delete_sync("test", "key")

    # Run from another thread to trigger run_coroutine_threadsafe path
    # They should catch the timeout exception internally and log warning
    with patch("sigenergy2mqtt.persistence.state_store.logging.warning") as mock_log:
        await loop.run_in_executor(None, call_sync_timeout)
        assert mock_log.call_count == 3
