import json
import time
from datetime import timedelta
from unittest.mock import MagicMock

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
    config.mqtt_state_prefix = "sigenergy2mqtt/persistence"
    config.cache_warmup_timeout = 1.0
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
