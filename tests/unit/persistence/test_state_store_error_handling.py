from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.persistence.state_store import Category, StateStore, _DiskBackend


@pytest.fixture
def temp_state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def mock_persistence_config():
    config = MagicMock()
    config.mqtt_redundancy = True
    config.mqtt_state_prefix = "sigenergy2mqtt/_state"
    config.cache_warmup_timeout = 0.01  # Very short for timeout test
    config.disk_primary = True
    config.sync_timeout = 5.0
    return config


def test_disk_backend_errors(temp_state_dir):
    backend = _DiskBackend(temp_state_dir, "1.0.0")

    # OS Error on load
    with patch("pathlib.Path.read_text", side_effect=OSError("denied")):
        # Mock is_file so it tries to read
        with patch("pathlib.Path.is_file", return_value=True):
            assert backend.load("sensor", "key") is None

    # OS Error on delete
    with patch("pathlib.Path.unlink", side_effect=OSError("denied")):
        backend.delete("sensor", "key")

    # OS Error on delete legacy
    with patch("pathlib.Path.unlink", side_effect=OSError("denied")):
        backend.delete_root_legacy("key")

    # all_keys when dir doesn't exist
    assert backend.all_keys() == []


@pytest.mark.asyncio
async def test_statestore_uninitialised():
    store = StateStore()

    # Save before init
    await store.save("sensor", "k", "v")
    await store.save(Category.SENSOR, "k", "v")  # Also test Enum parsing (lines 517, 552, 575)

    # Load before init
    assert await store.load("sensor", "k") is None
    assert await store.load(Category.SENSOR, "k") is None

    # Delete before init
    await store.delete("sensor", "k")
    await store.delete(Category.SENSOR, "k")

    # clean_all before init
    await store.clean_all()


@pytest.mark.asyncio
async def test_initialise_mqtt_failure_and_timeout(temp_state_dir, mock_persistence_config):
    store = StateStore()

    # 1. Connection failure
    with patch("sigenergy2mqtt.mqtt.mqtt_setup", side_effect=Exception("connection refused")):
        await store.initialise(temp_state_dir, mock_persistence_config)
        assert store.is_initialised
        assert store._client is None  # disk only

    store.shutdown()

    # 2. Timeout failure
    store = StateStore()
    mock_client = MagicMock()
    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        # Provide a wait_for_sentinel that times out
        with patch.object(store._mqtt, "wait_for_sentinel", return_value=False):
            await store.initialise(temp_state_dir, mock_persistence_config)
            assert store.is_initialised


@pytest.mark.asyncio
async def test_shutdown_disconnect_error(temp_state_dir, mock_persistence_config):
    store = StateStore()
    mock_client = MagicMock()
    mock_client.disconnect.side_effect = Exception("boom")

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

    store.shutdown()  # Should catch the exception on disconnect


@pytest.mark.asyncio
async def test_mqtt_sync_exceptions(temp_state_dir, mock_persistence_config):
    store = StateStore()
    mock_client = MagicMock()

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        # Force exceptions on mqtt publish
        with patch.object(store._mqtt, "publish", side_effect=Exception("mqtt fail")):
            await store.save("test", "key", "val")

        with patch.object(store._mqtt, "publish_delete", side_effect=Exception("mqtt fail")):
            await store.delete("test", "key")

            # and clean_all mqtt path
            store._mqtt._cache[("test", "key")] = ("val", 123)
            await store.clean_all()
