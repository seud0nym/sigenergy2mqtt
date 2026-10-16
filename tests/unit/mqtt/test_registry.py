import time

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


def test_record_publish_sets_timestamp():
    """record_publish updates last_publish_at for a registered client."""
    reg = MqttHealthRegistry()
    reg.register('c8')
    entry = reg._clients['c8']
    assert entry.last_publish_at is None
    reg.record_publish('c8')
    assert entry.last_publish_at is not None
    assert entry.oldest_pending_publish_at is not None


def test_record_publish_unknown_client_is_noop():
    """record_publish silently ignores unknown client IDs."""
    reg = MqttHealthRegistry()
    reg.record_publish('unknown')  # must not raise
    assert reg._clients == {}


def test_multiple_publishes_track_oldest_deadline():
    """Subsequent publishes must NOT postpone oldest_pending_publish_at."""
    reg = MqttHealthRegistry()
    reg.register('c9')
    entry = reg._clients['c9']

    # Publish 1 at t0
    reg.record_publish('c9', mid=1)
    t0 = entry.oldest_pending_publish_at
    assert t0 is not None

    # Publish 2 later
    time.sleep(0.01)
    reg.record_publish('c9', mid=2)
    # Oldest pending publish must STILL be t0, not updated to publish 2
    assert entry.oldest_pending_publish_at == t0
    assert entry.last_publish_at > t0

    # Ack for mid=1 arrives -> oldest should now advance to mid=2
    reg.record_publish_ack('c9', mid=1)
    assert entry.oldest_pending_publish_at == entry._pending_publishes[2]
    assert entry.oldest_pending_publish_at > t0

    # Ack for mid=2 arrives -> no more pending publishes
    reg.record_publish_ack('c9', mid=2)
    assert entry.oldest_pending_publish_at is None


def test_ack_arriving_before_publish_is_handled():
    """If an ACK arrives before publish returns (race condition), mid is not left pending."""
    reg = MqttHealthRegistry()
    reg.register('c10')
    entry = reg._clients['c10']

    # Ack arrives first
    reg.record_publish_ack('c10', mid=42)
    assert 42 in entry._seen_ack_mids

    # Publish registers second
    reg.record_publish('c10', mid=42)
    assert 42 not in entry._pending_publishes
    assert entry.oldest_pending_publish_at is None


def test_disconnect_and_reconnect_clears_pending_publishes():
    """Disconnecting or reconnecting clears pending publishes and resets oldest_pending_publish_at."""
    reg = MqttHealthRegistry()
    reg.register('c11')
    entry = reg._clients['c11']

    reg.record_publish('c11', mid=99)
    assert entry.oldest_pending_publish_at is not None

    reg.mark_disconnected('c11')
    assert entry.oldest_pending_publish_at is None
    assert entry._pending_publishes == {}

    reg.record_publish('c11', mid=100)
    assert entry.oldest_pending_publish_at is not None

    reg.mark_connected('c11')
    assert entry.oldest_pending_publish_at is None
    assert entry._pending_publishes == {}


