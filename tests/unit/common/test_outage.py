import logging
import threading

import pytest

from sigenergy2mqtt.common import outage as outage_module
from sigenergy2mqtt.common.outage import OutageTracker, active_outages, clear_outage_trackers, format_duration, outage_tracker

LOGGER = "sigenergy2mqtt.common.outage"


def _records(caplog, level=None):
    return [r for r in caplog.records if r.name == LOGGER and (level is None or r.levelno == level)]


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [(0, "0s"), (0.4, "0s"), (31.2, "31s"), (59.6, "1m 0s"), (252, "4m 12s"), (3600, "1h 0m 0s"), (3725, "1h 2m 5s"), (-5, "0s")],
    )
    def test_format(self, seconds, expected):
        assert format_duration(seconds) == expected


class TestOutageTracker:
    def test_first_failure_starts_outage_at_error(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.failure(TimeoutError("boom"), detail="sensor detail") is True
        assert tracker.active
        warnings = _records(caplog, logging.ERROR)
        assert len(warnings) == 1
        assert warnings[0].getMessage() == "modbus://h:502 outage started: TimeoutError('boom')"
        assert any(r.getMessage() == "sensor detail" for r in _records(caplog, logging.DEBUG))

    def test_repeated_failures_are_suppressed_to_debug(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        tracker.failure(TimeoutError("a"))
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            for i in range(5):
                assert tracker.failure(TimeoutError(f"different text {i}"), detail=f"detail {i}") is False
        assert not _records(caplog, logging.ERROR)
        assert [r.getMessage() for r in _records(caplog, logging.DEBUG)] == [f"detail {i}" for i in range(5)]
        assert tracker.suppressed == 5

    def test_new_kind_of_error_is_reported_once(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        tracker.failure(TimeoutError("a"))
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.failure(ConnectionError("b")) is True
            assert tracker.failure(ConnectionError("c")) is False
        warnings = _records(caplog, logging.ERROR)
        assert len(warnings) == 1
        assert "new error" in warnings[0].getMessage()
        assert "ConnectionError('b')" in warnings[0].getMessage()

    def test_string_errors_are_grouped_by_text(self):
        tracker = OutageTracker("mqtt://b:1883")
        assert tracker.failure("Unspecified error") is True
        assert tracker.failure("Unspecified error") is False
        assert tracker.failure("Keep alive timeout") is True

    def test_success_ends_outage_with_summary(self, caplog, monkeypatch):
        clock = [1000.0]
        monkeypatch.setattr(outage_module.time, "monotonic", lambda: clock[0])
        tracker = OutageTracker("modbus://h:502")
        tracker.failure(TimeoutError("a"))
        tracker.failure(TimeoutError("a"))
        tracker.suppress("x")
        clock[0] += 31
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.success() is True
        info = _records(caplog, logging.INFO)
        assert len(info) == 1
        assert info[0].getMessage() == "modbus://h:502 outage ended after 31s (2 similar messages suppressed)"
        assert not tracker.active
        assert tracker.suppressed == 0
        assert tracker.duration == 0.0

    def test_success_without_outage_is_silent(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.success() is False
            assert tracker.success(member="x") is False
        assert not _records(caplog)

    def test_suppress_only_when_active(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        assert tracker.suppress("ignored") is False
        tracker.failure("down")
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.suppress("demoted") is True
        assert [r.getMessage() for r in _records(caplog, logging.DEBUG)] == ["demoted"]
        assert tracker.suppressed == 1

    def test_outage_ends_only_when_all_members_recover(self):
        tracker = OutageTracker("mqtt://b:1883")
        assert tracker.failure("Unspecified error", member="a") is True
        assert tracker.failure("Unspecified error", member="b") is False
        assert tracker.success(member="a") is False
        assert tracker.active
        assert tracker.success(member="b") is True
        assert not tracker.active

    def test_success_without_member_clears_all_members(self):
        tracker = OutageTracker("mqtt://b:1883")
        tracker.failure("x", member="a")
        tracker.failure("x", member="b")
        assert tracker.success() is True

    def test_reminder_logged_periodically(self, caplog, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(outage_module.time, "monotonic", lambda: clock[0])
        tracker = OutageTracker("modbus://h:502", reminder_interval=60)
        tracker.failure(TimeoutError("a"))
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            clock[0] = 30
            tracker.failure(TimeoutError("a"))
            clock[0] = 61
            tracker.failure(TimeoutError("a"))
            clock[0] = 90
            tracker.failure(TimeoutError("a"))
        warnings = _records(caplog, logging.ERROR)
        assert len(warnings) == 1
        assert warnings[0].getMessage() == "modbus://h:502 outage continuing for 1m 1s (2 similar messages suppressed): TimeoutError('a')"

    def test_reminder_disabled(self, caplog, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(outage_module.time, "monotonic", lambda: clock[0])
        tracker = OutageTracker("modbus://h:502", reminder_interval=0)
        tracker.failure(TimeoutError("a"))
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            clock[0] = 10_000
            tracker.failure(TimeoutError("a"))
        assert not _records(caplog, logging.ERROR)

    def test_new_outage_after_recovery_starts_fresh(self, caplog):
        tracker = OutageTracker("modbus://h:502")
        tracker.failure(TimeoutError("a"))
        tracker.failure(TimeoutError("a"))
        tracker.success()
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            assert tracker.failure(TimeoutError("a")) is True
        assert "outage started" in _records(caplog, logging.ERROR)[0].getMessage()
        assert tracker.suppressed == 0

    def test_custom_logger(self, caplog):
        custom = logging.getLogger("test.outage.custom")
        tracker = OutageTracker("r", log=custom)
        with caplog.at_level(logging.DEBUG, logger="test.outage.custom"):
            tracker.failure("x")
        assert any(r.name == "test.outage.custom" for r in caplog.records)

    def test_thread_safety(self):
        tracker = OutageTracker("modbus://h:502", reminder_interval=0)
        tracker.failure(TimeoutError("first"))

        def worker():
            for _ in range(500):
                tracker.failure(TimeoutError("again"))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert tracker.suppressed == 2000

    def test_repr(self):
        assert repr(OutageTracker("r")) == "OutageTracker(resource='r', active=False, suppressed=0)"


class TestRegistry:
    def test_tracker_is_shared_per_resource(self):
        assert outage_tracker("mqtt://a:1") is outage_tracker("mqtt://a:1")
        assert outage_tracker("mqtt://a:1") is not outage_tracker("mqtt://a:2")

    def test_active_outages_filters_by_prefix_and_state(self):
        mqtt = outage_tracker("mqtt://a:1")
        modbus = outage_tracker("modbus://a:502")
        outage_tracker("modbus://b:502")
        assert active_outages() == []
        mqtt.failure("x")
        modbus.failure("y")
        assert active_outages("modbus://") == [modbus]
        assert active_outages("mqtt://") == [mqtt]
        assert set(active_outages()) == {mqtt, modbus}

    def test_clear(self):
        tracker = outage_tracker("mqtt://a:1")
        clear_outage_trackers()
        assert outage_tracker("mqtt://a:1") is not tracker


def test_records_are_attributed_to_the_caller(caplog):
    tracker = OutageTracker("r")
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        tracker.failure("x", detail="d")
        tracker.success()
    assert {r.filename for r in caplog.records} == {"test_outage.py"}


def test_outage_tracker_uses_logger_given_on_creation(caplog):
    custom = logging.getLogger("test.outage.registry")
    tracker = outage_tracker("r2", log=custom)
    assert outage_tracker("r2") is tracker
    with caplog.at_level(logging.DEBUG, logger="test.outage.registry"):
        tracker.failure("x")
    assert [r.name for r in caplog.records] == ["test.outage.registry"]


def test_custom_kind_groups_different_errors():
    tracker = OutageTracker("modbus://h:502")
    assert tracker.failure("connection lost", kind="connectivity") is True
    assert tracker.failure(TimeoutError("no response"), kind="connectivity") is False
    assert tracker.failure(ConnectionError("refused"), kind="connectivity") is False
    assert tracker.failure(ValueError("other")) is True
