from __future__ import annotations

import asyncio
import logging
from asyncio import sleep
from collections.abc import Callable
from typing import Any

from paho.mqtt import MQTTException

from sigenergy2mqtt.common.outage import outage_tracker
from sigenergy2mqtt.config import active_config

from .client import MqttClient
from .handler import MqttHandler
from .registry import MqttHealthRegistry

__all__ = ["MqttConnectAborted", "MqttHandler", "interrupt_mqtt_reconnection", "mqtt_health_registry", "mqtt_setup", "mqtt_teardown", "reset_mqtt_reconnection_interrupt"]

_MAX_CONNECT_ATTEMPTS: int = 3


class MqttConnectAborted(RuntimeError):
    """Raised when waiting for the MQTT broker is abandoned because the caller is stopping."""

# ---------------------------------------------------------------------------
# Interruption flag
#
# Set to True by an external synchronous signal handler (e.g. _early_exit in
# main()) *before* the asyncio event loop starts.  _check_interrupted() is
# called at discrete checkpoints throughout the scan so that a pre-loop signal
# aborts discovery as soon as the current operation finishes.
# ---------------------------------------------------------------------------
_interrupted: bool = False

logger = logging.getLogger(__name__)


def _check_interrupted(broker_url: str, client_id: str) -> None:
    """Raise KeyboardInterrupt if a pre-loop signal handler set _interrupted."""
    if _interrupted:
        logger.info(f"Reconnection retry to {broker_url} as Client ID '{client_id}' interrupted by signal")
        raise KeyboardInterrupt("MQTT reconnection interrupted by signal")


def interrupt_mqtt_reconnection() -> None:
    """Interrupt the MQTT reconnection attempt."""
    global _interrupted
    _interrupted = True


def reset_mqtt_reconnection_interrupt() -> None:
    """Reset the interruption flag to allow future reconnection attempts."""
    global _interrupted
    _interrupted = False


mqtt_health_registry = MqttHealthRegistry()


def _build_broker_url() -> str:
    """Construct the broker URL string from active config for use in log messages."""
    return f"mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}"


async def _connect_with_retry(mqtt_client: MqttClient, client_id: str, max_attempts: int | None = _MAX_CONNECT_ATTEMPTS, stopping: Callable[[], bool] | None = None) -> None:
    """Connect the given MQTT client to the broker, retrying on failure.

    Failures are reported through the broker's outage tracker, so however many
    clients are waiting, an unreachable broker is logged once when the outage
    starts and once when it ends.

    Args:
        mqtt_client:  The :class:`MqttClient` instance to connect.
        client_id:    The MQTT client ID (also the client's outage member).
        max_attempts: Give up after this many attempts, or ``None`` to retry
            until the broker is reachable. Components that cannot work without
            MQTT wait; those with a fallback (e.g. disk-only persistence) give up.
        stopping:     Optional callable; when it returns ``True`` the wait is
            abandoned by raising :class:`MqttConnectAborted`.

    Raises:
        Exception: Re-raises the last connection exception once
            ``max_attempts`` is exhausted.
        MqttConnectAborted: If ``stopping()`` returned ``True`` while waiting.
        KeyboardInterrupt: If a pre-loop signal interrupted the wait.
    """
    broker_url = _build_broker_url()
    outage = outage_tracker(broker_url)
    delay = active_config.mqtt.retry_delay

    attempt = 0
    while True:
        attempt += 1
        try:
            mqtt_client.connect(
                active_config.mqtt.broker,
                port=active_config.mqtt.port,
                keepalive=active_config.mqtt.keepalive,
            )
            mqtt_client.loop_start()
            logger.info(f"Connected to {broker_url} as Client ID '{client_id}' (keepalive={active_config.mqtt.keepalive}s)")
            outage.success(member=client_id)
            return
        except (MQTTException, OSError, RuntimeError) as e:
            limit = "" if max_attempts is None else f"/{max_attempts}"
            if max_attempts is not None and attempt >= max_attempts:
                # The caller has a fallback; it no longer counts towards the outage ending
                outage.failure(e, member=client_id, detail=f"Failed to connect to {broker_url} as Client ID '{client_id}' after {attempt} attempts: {e!r}")
                outage.forget(client_id)
                raise
            outage.failure(e, member=client_id, detail=f"Error connecting to {broker_url} as Client ID '{client_id}': {e!r} (attempt {attempt}{limit}) - Retrying in {delay}s")
            for _ in range(delay):
                if stopping is not None and stopping():
                    outage.forget(client_id)
                    raise MqttConnectAborted(f"Stopped waiting for {broker_url} (Client ID '{client_id}')") from e
                _check_interrupted(broker_url, client_id)
                await sleep(1)


async def mqtt_setup(
    mqtt_client_id: str,
    transport: Any,
    loop: asyncio.AbstractEventLoop,
    *,
    max_attempts: int | None = _MAX_CONNECT_ATTEMPTS,
    stopping: Callable[[], bool] | None = None,
) -> tuple[MqttClient, MqttHandler]:
    """Create, configure, and connect an MQTT client/handler pair.

    Instantiates an :class:`MqttHandler` and :class:`MqttClient`, applies
    authentication from active config, and establishes a broker connection
    (with retries).  The caller is responsible for managing the returned
    :class:`MqttClient` lifecycle after this point.

    Args:
        mqtt_client_id: A non-empty string used as the MQTT client identifier.
            Must be unique per broker session.
        transport:      An optional transport object passed through to
            the :class:`MqttHandler` for transport read/write operations.
        loop:           The asyncio event loop the handler will schedule
            callbacks on.  Must not be ``None``.
        max_attempts:   Connection attempts before giving up, or ``None`` to
            wait until the broker is reachable.
        stopping:       Optional callable that abandons the wait (raising
            :class:`MqttConnectAborted`) when it returns ``True``.

    Returns:
        A ``(MqttClient, MqttHandler)`` tuple.  The client is already
        connected and its internal paho loop is running.

    Raises:
        ValueError:  If ``mqtt_client_id`` is empty or whitespace-only.
        ValueError:  If ``loop`` is ``None``.
        Exception:   If the broker is unreachable after all retry attempts.
        MqttConnectAborted: If ``stopping()`` returned ``True`` while waiting.
    """
    if not mqtt_client_id or mqtt_client_id.isspace():
        raise ValueError("mqtt_client_id must not be None or an empty string")
    if loop is None:
        raise ValueError("loop must not be None")

    broker_url = _build_broker_url()

    logger.debug(f"Creating MQTT Client ID {mqtt_client_id} for {broker_url} over {active_config.mqtt.transport}")

    mqtt_handler = MqttHandler(mqtt_client_id, transport, loop, mqtt_health_registry)
    mqtt_client = MqttClient(
        client_id=mqtt_client_id,
        userdata=mqtt_handler,
        transport=active_config.mqtt.transport,
        tls=active_config.mqtt.tls,
        tls_insecure=active_config.mqtt.tls_insecure,
    )
    mqtt_health_registry.register(mqtt_client_id)

    if active_config.mqtt.anonymous:
        logger.debug(f"MQTT Client ID {mqtt_client_id} connecting to {broker_url} anonymously")
    else:
        logger.debug(f"MQTT Client ID {mqtt_client_id} connecting to {broker_url} with username {active_config.mqtt.username}")
        mqtt_client.username_pw_set(active_config.mqtt.username, active_config.mqtt.password)

    await _connect_with_retry(mqtt_client, mqtt_client_id, max_attempts=max_attempts, stopping=stopping)

    return mqtt_client, mqtt_handler


async def mqtt_teardown(mqtt_client: MqttClient, mqtt_handler: MqttHandler) -> None:
    """Clean up MQTT client and handler.

    Args:
        mqtt_client: The :class:`MqttClient` instance to clean up.
        mqtt_handler: The :class:`MqttHandler` instance to clean up.
    """
    mqtt_client_id = mqtt_client.client_id_str
    broker_url = _build_broker_url()

    logger.debug(f"Deregistering and unsubscribing MQTT handlers for Client ID {mqtt_client_id} to {broker_url}")
    mqtt_handler.deregister_all(mqtt_client)

    logger.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to {broker_url}")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    await mqtt_handler.close()
