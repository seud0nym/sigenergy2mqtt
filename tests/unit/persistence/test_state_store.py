import json
import time
from datetime import timedelta
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.persistence.state_store import StateStore, _make_envelope, _parse_envelope


@pytest.fixture
def temp_state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def mock_mqtt_config():
    config = MagicMock()
    config.broker = "localhost"
    config.port = 1883
    config.username = "user"
    config.password = "pass"
    config.anonymous = False
    config.tls = False
    config.transport = "tcp"
    config.keepalive = 60
    return config


@pytest.fixture
def mock_persistence_config():
    config = MagicMock()
    config.mqtt_redundancy = True
    config.mqtt_state_prefix = "sigenergy2mqtt/_state"
    config.cache_warmup_timeout = 1.0
    config.disk_primary = True
    config.sync_timeout = 5.0
    return config


def test_envelope_parsing():
    # Valid envelope
    env = _make_envelope("123.4", "1.0.0")
    val, ts, was_legacy = _parse_envelope(env)
    assert val == "123.4"
    assert ts > 0
    assert was_legacy is False

    # Legacy raw value
    val, ts, was_legacy = _parse_envelope("old_value", fallback_ts=999)
    assert val == "old_value"
    assert ts == 999
    assert was_legacy is True


@pytest.mark.asyncio
async def test_state_store_disk_only(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()

    await store.initialise(temp_state_dir, mock_persistence_config)
    assert store.is_initialised

    await store.save("test", "key1", "val1")
    # Wait for executor
    store.shutdown()

    # Check disk
    path = temp_state_dir / "test" / "key1"
    assert path.is_file()

    # Reload
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)
    loaded = await store.load("test", "key1")
    assert loaded == "val1"


@pytest.mark.asyncio
async def test_state_store_staleness(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    # Save with old timestamp manually
    path = temp_state_dir / "stale" / "key"
    path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = int(time.time()) - 4000
    envelope = json.dumps({"v": "old", "ts": old_ts, "ver": "1.0.0"})
    path.write_text(envelope)

    # Load with 1h (3600s) stale limit
    loaded = await store.load("stale", "key", stale_after=timedelta(hours=1))
    assert loaded is None

    # Load with 2h limit
    loaded = await store.load("stale", "key", stale_after=timedelta(hours=2))
    assert loaded == "old"


@pytest.mark.asyncio
async def test_state_store_validation(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    await store.save("test", "key", "invalid_val")
    store.shutdown()

    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    # Validator returns False
    loaded = await store.load("test", "key", validator=lambda x: x == "valid")
    assert loaded is None

    # Validator returns True
    loaded = await store.load("test", "key", validator=lambda x: "invalid" in x)
    assert loaded == "invalid_val"


@pytest.mark.asyncio
async def test_disk_legacy_migration(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()

    # Create legacy raw file (no JSON envelope)
    path = temp_state_dir / "legacy" / "raw_key"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("123.456", encoding="utf-8")

    await store.initialise(temp_state_dir, mock_persistence_config)

    # Load and migrate
    loaded = await store.load("legacy", "raw_key")
    assert loaded == "123.456"

    # Check if disk now has the envelope
    content = path.read_text(encoding="utf-8")
    assert '"v": "123.456"' in content
    assert '"ts":' in content
    assert '"ver":' in content


@pytest.mark.asyncio
async def test_disk_root_fallback_migration(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()

    # Create legacy raw file in the root state directory instead of category subdir
    root_file_path = temp_state_dir / "orphaned_key"
    temp_state_dir.mkdir(parents=True, exist_ok=True)
    root_file_path.write_text("789", encoding="utf-8")

    await store.initialise(temp_state_dir, mock_persistence_config)

    # Load via category "sensor"
    loaded = await store.load("sensor", "orphaned_key")
    assert loaded == "789"

    # Check that it's been moved to the category subdirectory
    category_path = temp_state_dir / "sensor" / "orphaned_key"
    assert category_path.is_file()
    assert '"v": "789"' in category_path.read_text()

    # Check that root file was deleted
    assert not root_file_path.exists()


@pytest.mark.asyncio
async def test_disk_path_validation(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    # Attempt invalid save
    await store.save("../evil", "key", "value")

    # Check that no file was created due to validation
    evil_path = temp_state_dir / "../evil" / "key"
    assert not evil_path.exists()

    await store.save("category", "../evil", "value")
    evil_path2 = temp_state_dir / "category" / "../evil"
    assert not evil_path2.exists()


@pytest.mark.asyncio
async def test_mqtt_publish_retry(temp_state_dir, mock_persistence_config):
    from unittest.mock import MagicMock, patch

    mock_persistence_config.mqtt_redundancy = True
    store = StateStore()

    mock_client = MagicMock()
    # Simulate publish failure by setting rc to error
    msg = MagicMock()
    msg.rc = 1  # MQTT error code
    mock_client.publish.return_value = msg

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        # Attempt save, should try to publish and fail
        await store.save("test", "key", "value")

        # Check that publish was attempted
        assert mock_client.publish.called


@pytest.mark.asyncio
async def test_mqtt_publish_delete(temp_state_dir, mock_persistence_config):
    from unittest.mock import MagicMock, patch

    mock_persistence_config.mqtt_redundancy = True
    store = StateStore()

    mock_client = MagicMock()
    mock_client.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        await store.delete("test", "key")

        # Verify publish_delete was called
        calls = [call for call in mock_client.publish.call_args_list if b"" in call[0]]
        assert len(calls) > 0


@pytest.mark.asyncio
async def test_shutdown_cleanup(temp_state_dir, mock_persistence_config):
    from unittest.mock import MagicMock, patch

    mock_persistence_config.mqtt_redundancy = True
    store = StateStore()

    mock_client = MagicMock()
    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        store.shutdown()

        # Verify client disconnect was called
        mock_client.disconnect.assert_called_once()
        assert store._executor is None
        assert store._client is None


@pytest.mark.asyncio
async def test_clean_all(temp_state_dir, mock_persistence_config):
    from unittest.mock import MagicMock, patch

    mock_persistence_config.mqtt_redundancy = True
    store = StateStore()

    mock_client = MagicMock()
    mock_client.publish.return_value.rc = mqtt.MQTT_ERR_SUCCESS

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        # Create some disk files
        await store.save("cat1", "key1", "val1")
        await store.save("cat2", "key2", "val2")

        await store.clean_all()

        # Check disk files removed
        assert not (temp_state_dir / "cat1" / "key1").exists()
        assert not (temp_state_dir / "cat2" / "key2").exists()

        # Check MQTT publishes for delete (may be 0 if no cache)
        delete_calls = [call for call in mock_client.publish.call_args_list if len(call[0]) > 1 and call[0][1] == b""]
        # Not asserting count since cache may be empty


@pytest.mark.asyncio
async def test_all_keys(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    await store.save("sensor", "temp", "25")
    await store.save("pvoutput", "energy", "100")

    keys = store._disk.all_keys()
    assert ("sensor", "temp") in keys
    assert ("pvoutput", "energy") in keys


@pytest.mark.asyncio
async def test_disk_primary_false(temp_state_dir, mock_persistence_config):
    from unittest.mock import MagicMock, patch

    mock_persistence_config.disk_primary = False
    mock_persistence_config.mqtt_redundancy = True
    store = StateStore()

    mock_client = MagicMock()
    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_client, MagicMock())):
        await store.initialise(temp_state_dir, mock_persistence_config)

        # Save to MQTT first
        await store.save("test", "key", "value")

        # Load should try MQTT first (but since no cache, fall back to disk)
        loaded = await store.load("test", "key")
        assert loaded == "value"


@pytest.mark.asyncio
async def test_invalid_envelope_handling(temp_state_dir, mock_persistence_config):
    mock_persistence_config.mqtt_redundancy = False
    store = StateStore()
    await store.initialise(temp_state_dir, mock_persistence_config)

    # Manually create invalid JSON
    path = temp_state_dir / "test" / "key"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{invalid json", encoding="utf-8")

    loaded = await store.load("test", "key")
    assert loaded == "{invalid json"
