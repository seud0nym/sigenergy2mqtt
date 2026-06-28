"""Tests for MonitorService auto-restart and health-check-enabled behavior."""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from sigenergy2mqtt.monitor.monitor_service import MonitorService


class FakeMqttClient:
    def __init__(self, client_id: bytes = b"test_client"):
        self._client_id = client_id
        self.published: list[tuple] = []
        self.publish = MagicMock(side_effect=self._publish)

    def _publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        info = MagicMock()
        info.rc = 0
        info.wait_for_publish = MagicMock()
        return info


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_svc(tmp_path: Path) -> "tuple[MonitorService, FakeMqttClient]":
    svc = MonitorService([])
    svc._health_file = tmp_path / "health.json"
    svc._check_modbus = MagicMock(return_value=True)
    svc._check_mqtt = MagicMock(return_value=True)
    svc._check_topic_health = AsyncMock(return_value=0)
    return svc, FakeMqttClient()


# ── schedule() ───────────────────────────────────────────────────────────────

@pytest.fixture
def track_tasks():
    tasks_to_clean = []
    yield tasks_to_clean
    # Automatically runs after the test finishes, even if an assert fails!
    for t in tasks_to_clean:
        t.close()

def test_schedule_returns_monitor_when_enabled(monkeypatch, track_tasks):
    """schedule() should return a coroutine when health checks are enabled."""
    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=False):
        svc = MonitorService([])
        # enabled=True is default, _monitor_topic_updates is False by default (non-debug)
        tasks = svc.schedule(None, FakeMqttClient())
        track_tasks.extend(tasks)  # Register them for automatic cleanup
        assert len(tasks) == 1


def test_schedule_returns_empty_when_disabled_and_no_topic_monitoring(monkeypatch, track_tasks):
    """schedule() returns [] when health checks disabled and topic monitoring inactive."""
    svc = MonitorService([])
    svc._monitor_topic_updates = False
    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=False):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = False
            tasks = svc.schedule(None, FakeMqttClient())
            track_tasks.extend(tasks)  # Register them for automatic cleanup
            assert tasks == []


def test_schedule_returns_monitor_when_docker_even_if_disabled(track_tasks):
    """schedule() returns a coroutine when in Docker even if enabled=False."""
    svc = MonitorService([])
    svc._monitor_topic_updates = False
    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=True):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = False
            tasks = svc.schedule(None, FakeMqttClient())
            track_tasks.extend(tasks)  # Register them for automatic cleanup
            assert len(tasks) == 1


def test_schedule_returns_monitor_when_topic_monitoring_active(track_tasks):
    """schedule() returns a coroutine when topic monitoring is active even if health check disabled."""
    svc = MonitorService([])
    svc._monitor_topic_updates = True
    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=False):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = False
            tasks = svc.schedule(None, FakeMqttClient())
            track_tasks.extend(tasks)  # Register them for automatic cleanup
            assert len(tasks) == 1


# ── _publish_health() when disabled ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_health_skipped_when_disabled_non_docker(tmp_path):
    """When disabled and not Docker, _publish_health does not write or publish."""
    svc, mqtt_client = _make_svc(tmp_path)
    with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
        mock_hc.enabled = False
        await svc._publish_health(mqtt_client, is_docker_env=False)
        assert not svc._health_file.exists()
        assert mqtt_client.publish.call_count == 0


@pytest.mark.asyncio
async def test_publish_health_forced_when_docker_even_if_disabled(tmp_path):
    """When disabled but inside Docker, _publish_health still writes and publishes."""
    svc, mqtt_client = _make_svc(tmp_path)
    with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
        mock_hc.enabled = False
        mock_hc.timeout = 5
        mock_hc.retries = 3
        mock_hc.start_period = 45
        await svc._publish_health(mqtt_client, is_docker_env=True)
    assert svc._health_file.exists()
    data = json.loads(svc._health_file.read_text())
    assert data["status"] == "healthy"
    # check that MQTT was published
    published_topics = [c[0][0] for c in mqtt_client.publish.call_args_list]
    assert svc._health_state_topic in published_topics
    assert svc._health_attributes_topic in published_topics


# ── Auto-restart logic ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_restart_when_healthy(tmp_path):
    """restart_controller.request() should NOT be called when health checks pass."""
    svc, mqtt_client = _make_svc(tmp_path)
    with patch("sigenergy2mqtt.main.restart.restart_controller") as mock_rc:
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 5
            mock_hc.retries = 3
            mock_hc.start_period = 0
            await svc._publish_health(mqtt_client, is_docker_env=False)
        mock_rc.request.assert_not_called()


@pytest.mark.asyncio
async def test_no_restart_in_docker_even_after_retries(tmp_path):
    """restart_controller.request() should NOT be called when in Docker."""
    svc, mqtt_client = _make_svc(tmp_path)
    svc._check_modbus = MagicMock(return_value=False)
    svc._started = time.monotonic() - 1000  # well past start period
    with patch("sigenergy2mqtt.main.restart.restart_controller") as mock_rc:
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 5
            mock_hc.retries = 1
            mock_hc.start_period = 0
            for _ in range(3):
                await svc._publish_health(mqtt_client, is_docker_env=True)
        mock_rc.request.assert_not_called()


@pytest.mark.asyncio
async def test_restart_triggered_after_retries_exceeded(tmp_path):
    """restart_controller.request() should be called when retries exceeded outside Docker."""
    svc, mqtt_client = _make_svc(tmp_path)
    svc._check_modbus = MagicMock(return_value=False)
    svc._started = time.monotonic() - 1000  # well past start_period

    with patch("sigenergy2mqtt.main.restart.restart_controller") as mock_rc:
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 5
            mock_hc.retries = 2
            mock_hc.start_period = 0
            # First failure — not yet at retries threshold
            await svc._publish_health(mqtt_client, is_docker_env=False)
            mock_rc.request.assert_not_called()
            # Second failure — hits retries threshold
            await svc._publish_health(mqtt_client, is_docker_env=False)
            mock_rc.request.assert_called_once()


@pytest.mark.asyncio
async def test_no_restart_during_start_period(tmp_path):
    """restart_controller.request() should NOT be called within the start period."""
    svc, mqtt_client = _make_svc(tmp_path)
    svc._check_modbus = MagicMock(return_value=False)
    svc._started = time.monotonic()  # just started — within start period

    with patch("sigenergy2mqtt.main.restart.restart_controller") as mock_rc:
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 5
            mock_hc.retries = 1
            mock_hc.start_period = 9999  # very long start period
            await svc._publish_health(mqtt_client, is_docker_env=False)
        mock_rc.request.assert_not_called()


@pytest.mark.asyncio
async def test_failure_count_resets_on_healthy(tmp_path):
    """_health_check_failures counter resets when status returns to healthy."""
    svc, mqtt_client = _make_svc(tmp_path)
    svc._started = time.monotonic() - 1000

    with patch("sigenergy2mqtt.main.restart.restart_controller"):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 5
            mock_hc.retries = 10
            mock_hc.start_period = 0

            # Cause a failure
            svc._check_modbus = MagicMock(return_value=False)
            await svc._publish_health(mqtt_client, is_docker_env=False)
            assert svc._health_check_failures == 1

            # Recover
            svc._check_modbus = MagicMock(return_value=True)
            await svc._publish_health(mqtt_client, is_docker_env=False)
            assert svc._health_check_failures == 0


# ── on_completion() ───────────────────────────────────────────────────────────

def test_on_completion_publishes_empty_messages():
    """on_completion() should publish b'' to both health topics."""
    svc = MonitorService([])
    mqtt_client = FakeMqttClient()
    svc.on_completion(None, mqtt_client)
    published_topics = {c[0][0]: c[0][1] for c in mqtt_client.publish.call_args_list}
    assert svc._health_state_topic in published_topics
    assert svc._health_attributes_topic in published_topics
    assert published_topics[svc._health_state_topic] == b""
    assert published_topics[svc._health_attributes_topic] == b""


# ── subscribe() when disabled ─────────────────────────────────────────────────

def test_subscribe_clears_retained_messages_when_disabled(monkeypatch):
    """subscribe() should publish b'' to health topics when health checks are disabled."""
    svc = MonitorService([])
    svc._monitor_topic_updates = False
    mqtt_client = FakeMqttClient()
    mqtt_handler = MagicMock()

    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=False):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = False
            svc.subscribe(mqtt_client, mqtt_handler)

    published_topics = {c[0][0]: c[0][1] for c in mqtt_client.publish.call_args_list}
    assert svc._health_state_topic in published_topics
    assert svc._health_attributes_topic in published_topics
    assert published_topics[svc._health_state_topic] == b""
    assert published_topics[svc._health_attributes_topic] == b""


def test_subscribe_does_not_clear_messages_when_enabled():
    """subscribe() should NOT publish b'' when health checks are enabled."""
    svc = MonitorService([])
    svc._monitor_topic_updates = False
    mqtt_client = FakeMqttClient()
    mqtt_handler = MagicMock()

    with patch("sigenergy2mqtt.monitor.monitor_service.is_docker", return_value=False):
        svc.subscribe(mqtt_client, mqtt_handler)

    assert mqtt_client.publish.call_count == 0


# ── Timeout behavior ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_health_timeout_counts_as_failure(tmp_path):
    """A TimeoutError during health check should be treated as degraded."""
    svc, mqtt_client = _make_svc(tmp_path)
    svc._started = time.monotonic() - 1000

    async def slow_check():
        await asyncio.sleep(9999)
        return 0

    svc._check_topic_health = slow_check

    with patch("sigenergy2mqtt.main.restart.restart_controller"):
        with patch("sigenergy2mqtt.config.active_config.health_check") as mock_hc:
            mock_hc.enabled = True
            mock_hc.timeout = 0.01  # very short timeout to trigger TimeoutError
            mock_hc.retries = 10
            mock_hc.start_period = 0
            await svc._publish_health(mqtt_client, is_docker_env=False)
            assert svc._health_check_failures == 1
