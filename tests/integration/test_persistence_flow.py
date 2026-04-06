import json
import shutil
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from sigenergy2mqtt.persistence.state_store import StateStore


@pytest.fixture
def temp_state_dir(tmp_path):
    path = tmp_path / "state"
    path.mkdir()
    return path


@pytest.fixture
def mock_mqtt_client():
    client = MagicMock()
    client.connect_async = MagicMock()
    client.loop_start = MagicMock()
    client.subscribe = MagicMock()
    client.publish = MagicMock()

    # Mock the return value of publish to be an object with wait_for_publish
    msg = MagicMock()
    msg.rc = 0
    client.publish.return_value = msg

    return client


@pytest.mark.asyncio
async def test_persistence_integration_flow(temp_state_dir, mock_mqtt_client):
    """
    Test the full flow:
    1. Initialize StateStore with MQTT enabled.
    2. Save a value (verify disk + MQTT publish).
    3. Simulate a restart (empty disk).
    4. Warming up from MQTT.
    5. Load value from warmed cache.
    """

    # 1. Setup configs
    mqtt_config = MagicMock()
    mqtt_config.broker = "localhost"
    mqtt_config.port = 1883
    mqtt_config.client_id_prefix = "test"
    mqtt_config.username = None
    mqtt_config.password = None
    mqtt_config.anonymous = True
    mqtt_config.tls = False
    mqtt_config.transport = "tcp"
    mqtt_config.keepalive = 60

    persistence_config = MagicMock()
    persistence_config.mqtt_redundancy = True
    persistence_config.mqtt_state_prefix = "sigenergy2mqtt/persistence"
    persistence_config.disk_primary = True
    persistence_config.cache_warmup_timeout = 2.0

    store = StateStore()

    with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_mqtt_client, MagicMock())):
        # First initialization
        await store.initialise(temp_state_dir, persistence_config)

        # 2. Save a value
        await store.save("category", "key", "value")

        # Verify it went to disk
        disk_file = temp_state_dir / "category" / "key"
        assert disk_file.is_file()

        # Verify MQTT publish was called (actual value)
        # Note: initialise also publishes a sentinel
        assert mock_mqtt_client.publish.called

        # 3. Simulate restart with empty disk
        store.shutdown()
        shutil.rmtree(temp_state_dir)
        temp_state_dir.mkdir()

        # 4. Re-initialise and simulate MQTT retained messages
        new_store = StateStore()

        # We need to trigger the on_message callback to simulate retained messages arriving
        topic = "sigenergy2mqtt/persistence/category/key"
        payload = json.dumps({"v": "value", "ts": int(time.time()), "ver": "1.0.0"})

        msg_info = MagicMock()
        msg_info.rc = 0
        msg_info.wait_for_publish = MagicMock()

        def simulate_mqtt_messages(*args, **kwargs):
            # This will be triggered when the sentinel is published
            def trigger():
                time.sleep(0.1)
                on_message = mock_mqtt_client.on_message

                # Message 1: The state
                msg1 = MagicMock()
                msg1.topic = topic
                msg1.payload = payload.encode()
                on_message(mock_mqtt_client, None, msg1)

                # Message 2: The sentinel
                msg2 = MagicMock()
                msg2.topic = "sigenergy2mqtt/persistence/_sentinel"
                msg2.payload = b"1"

                on_message(mock_mqtt_client, None, msg2)

            threading.Thread(target=trigger).start()
            return msg_info

        mock_mqtt_client.publish.side_effect = lambda t, *a, **k: simulate_mqtt_messages() if "_sentinel" in t else msg_info

        with patch("sigenergy2mqtt.mqtt.mqtt_setup", return_value=(mock_mqtt_client, MagicMock())):
            await new_store.initialise(temp_state_dir, persistence_config)

            # 5. Load value - should come from MQTT warmed cache
            val = await new_store.load("category", "key")
            assert val == "value"
