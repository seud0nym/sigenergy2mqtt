import json
import logging
import time
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from sigenergy2mqtt.persistence.state_store import _MqttBackend


@pytest.fixture
def empty_backend():
    backend = _MqttBackend()
    backend.configure("sigenergy2mqtt/_state", "1.0.0")
    return backend


def test_topic_to_key(empty_backend):
    # Not our prefix
    assert empty_backend._topic_to_key("not_our_prefix/sensor/key") is None

    # Not enough parts
    assert empty_backend._topic_to_key("sigenergy2mqtt/_state/sensor") is None

    # Sentinel topic
    assert empty_backend._topic_to_key("sigenergy2mqtt/_state/sensor/_sentinel") is None

    # Valid
    assert empty_backend._topic_to_key("sigenergy2mqtt/_state/sensor/my_key") == ("sensor", "my_key")


def test_retry_queue(empty_backend):
    mock_client = MagicMock()

    # Schedule retry manually
    def mock_fn(client, *args, **kwargs):
        raise RuntimeError("failed")

    empty_backend._schedule_retry(3, mock_fn, "arg1")  # Attempt 3 (max), should log warning and drop
    # wait, max_retries is 3, so attempt >= 3 drops it
    assert len(empty_backend._retry_queue) == 0

    empty_backend._schedule_retry(0, mock_fn, "arg1")
    assert len(empty_backend._retry_queue) == 1

    # Drain with time far in future to guarantee execution
    with patch("time.time", return_value=time.time() + 10.0) if "time" in globals() else patch("sigenergy2mqtt.persistence.state_store.time.time", return_value=9999999999.0):
        empty_backend._drain_retries(mock_client)

    assert len(empty_backend._retry_queue) == 0


def test_on_message(empty_backend):
    mock_client = MagicMock()

    # Sentinel message
    msg_sentinel = MagicMock()
    msg_sentinel.topic = "sigenergy2mqtt/_state/_sentinel"
    empty_backend.on_message(mock_client, None, msg_sentinel)
    assert empty_backend._sentinel_event.is_set()

    # Empty payload (delete)
    empty_backend._cache[("sensor", "to_delete")] = ("val", 123)
    msg_delete = MagicMock()
    msg_delete.topic = "sigenergy2mqtt/_state/sensor/to_delete"
    msg_delete.payload = b""
    empty_backend.on_message(mock_client, None, msg_delete)
    assert ("sensor", "to_delete") not in empty_backend._cache

    # Valid payload caching
    msg_valid = MagicMock()
    msg_valid.topic = "sigenergy2mqtt/_state/sensor/my_cached_key"
    msg_valid.payload = json.dumps({"v": "val", "ts": 12345, "ver": "1.0.0"}).encode()

    # Mock active_config for logging
    with patch("sigenergy2mqtt.config.active_config") as mock_config:
        mock_config.sensor_debug_logging = True
        empty_backend.on_message(mock_client, None, msg_valid)

    assert ("sensor", "my_cached_key") in empty_backend._cache
    assert empty_backend._cache[("sensor", "my_cached_key")] == ("val", 12345)

    # Pvoutput logging code path
    msg_pv = MagicMock()
    msg_pv.topic = "sigenergy2mqtt/_state/pvoutput/data"
    msg_pv.payload = json.dumps({"v": "val2", "ts": 12346, "ver": "1.0.0"}).encode()

    with patch("sigenergy2mqtt.config.active_config") as mock_config:
        mock_config.pvoutput.log_level = logging.DEBUG
        empty_backend.on_message(mock_client, None, msg_pv)

    assert ("pvoutput", "data") in empty_backend._cache


def test_publish_delete_retry(empty_backend):
    mock_client = MagicMock()

    # Simulate publish failure
    msg_err = MagicMock()
    msg_err.rc = mqtt.MQTT_ERR_NO_CONN
    mock_client.publish.return_value = msg_err

    empty_backend.publish_delete(mock_client, "sensor", "mykey")

    assert mock_client.publish.call_count == 1
    assert len(empty_backend._retry_queue) == 1
