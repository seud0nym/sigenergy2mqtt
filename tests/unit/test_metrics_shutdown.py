from unittest.mock import MagicMock

from sigenergy2mqtt.metrics import metrics as metrics_mod
from sigenergy2mqtt.metrics.metrics import Metrics


def test_shutdown_waits_for_pending_updates(monkeypatch):
    executor = MagicMock()
    original_executor = Metrics._executor
    original_pending = list(Metrics._pending_updates)
    try:
        Metrics._executor = executor
        pending_future = MagicMock()
        Metrics._pending_updates = [pending_future]

        monkeypatch.setattr(metrics_mod, "wait", lambda pending, timeout: (set(pending), set()))

        Metrics.shutdown(timeout=1.5)

        executor.shutdown.assert_called_once_with(wait=True, cancel_futures=False)
        assert Metrics._pending_updates == []
    finally:
        Metrics._executor = original_executor
        Metrics._pending_updates = original_pending


def test_shutdown_cancels_when_timeout(monkeypatch):
    executor = MagicMock()
    original_executor = Metrics._executor
    original_pending = list(Metrics._pending_updates)
    try:
        Metrics._executor = executor
        pending_future = MagicMock()
        Metrics._pending_updates = [pending_future]

        monkeypatch.setattr(metrics_mod, "wait", lambda pending, timeout: (set(), set(pending)))

        Metrics.shutdown(timeout=0.01)

        executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
        assert Metrics._pending_updates == []
    finally:
        Metrics._executor = original_executor
        Metrics._pending_updates = original_pending


def test_shutdown_noop_without_executor():
    original_executor = Metrics._executor
    original_pending = list(Metrics._pending_updates)
    try:
        Metrics._executor = None
        Metrics._pending_updates = []
        Metrics.shutdown(timeout=1.0)
        assert Metrics._executor is None
    finally:
        Metrics._executor = original_executor
        Metrics._pending_updates = original_pending
