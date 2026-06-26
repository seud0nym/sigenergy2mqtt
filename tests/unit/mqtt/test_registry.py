import time
import pytest
from sigenergy2mqtt.mqtt.registry import MqttHealthRegistry


def test_register_and_snapshot():
    reg = MqttHealthRegistry()
    reg.register('clientA')
    snap = reg.snapshot()
    assert 'clientA' in snap
    # ensure snapshot returns copies
    health_original = reg._clients['clientA']
    health_copy = snap['clientA']
    assert health_original is not health_copy
    # modify copy should not affect original
    health_copy.connected = True
    assert reg._clients['clientA'].connected is False


def test_mark_connected_and_is_connected():
    reg = MqttHealthRegistry()
    reg.register('c1')
    # initially disconnected (False)
    assert reg.is_connected('c1') is False
    reg.mark_connected('c1')
    entry = reg._clients['c1']
    assert entry.connected is True
    assert isinstance(entry.last_connected_at, float)
    assert entry.connect_count == 1
    # calling again increments count
    reg.mark_connected('c1')
    assert entry.connect_count == 2


def test_mark_connected_no_entry():
    reg = MqttHealthRegistry()
    reg.mark_connected('unknown')
    assert reg._clients == {}


def test_mark_disconnected_and_counts():
    reg = MqttHealthRegistry()
    reg.register('c2')
    reg.mark_connected('c2')
    reg.mark_disconnected('c2')
    entry = reg._clients['c2']
    assert entry.connected is False
    assert isinstance(entry.last_disconnected_at, float)
    assert entry.disconnect_count == 1


def test_mark_disconnected_no_entry():
    reg = MqttHealthRegistry()
    reg.mark_disconnected('ghost')
    assert reg._clients == {}


def test_record_message_auto_connect():
    reg = MqttHealthRegistry()
    reg.register('c3')
    entry = reg._clients['c3']
    # simulate older connection timestamp
    entry.last_connected_at = time.monotonic() - 10
    entry.connected = False
    reg.record_message('c3')
    assert entry.connected is True
    assert entry.last_message_at is not None
    # connect_count increments because auto‑connect path runs
    assert entry.connect_count == 2


def test_record_message_no_auto_connect():
    reg = MqttHealthRegistry()
    reg.register('c4')
    entry = reg._clients['c4']
    entry.connected = True
    entry.last_connected_at = time.monotonic()
    reg.record_message('c4')
    # already connected – count should stay at 0 (register does not increment)
    assert entry.connect_count == 0
    assert entry.last_message_at is not None


def test_record_publish_ack_auto_connect():
    reg = MqttHealthRegistry()
    reg.register('c5')
    entry = reg._clients['c5']
    entry.last_connected_at = time.monotonic() - 5
    entry.connected = False
    reg.record_publish_ack('c5')
    assert entry.connected is True
    assert entry.last_publish_ack_at is not None
    assert entry.connect_count == 2


def test_record_publish_ack_no_auto_connect():
    reg = MqttHealthRegistry()
    reg.register('c6')
    entry = reg._clients['c6']
    entry.connected = True
    entry.last_connected_at = time.monotonic()
    reg.record_publish_ack('c6')
    assert entry.connect_count == 0
    assert entry.last_publish_ack_at is not None


def test_repr_and_is_connected_unknown():
    reg = MqttHealthRegistry()
    reg.register('c7')
    reg.mark_connected('c7')
    rep = repr(reg)
    assert 'c7' in rep
    assert 'up' in rep
    # unknown client returns None
    assert reg.is_connected('nonexistent') is None
