"""MQTT client wrapper and callback definitions.

This module provides :class:`MqttClient`, a thin subclass of
:class:`paho.mqtt.client.Client` that wires up the standard paho callbacks to
the :class:`~.handler.MqttHandler` interface, and optionally configures TLS.
"""

import _thread
import logging
import ssl
import threading
import time
from collections import deque
from typing import Literal

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode

from sigenergy2mqtt.common.outage import OutageTracker, outage_tracker

from .handler import MqttHandler

logger = logging.getLogger(__name__)

STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"

# Set when the broker refuses the very first connection of a client (e.g. bad
# credentials). The process cannot work without MQTT, so it shuts down and the
# entry point uses this flag to exit with a failure status.
_connection_refused = threading.Event()


def connection_refused() -> bool:
    """Whether the broker refused a client's first connection during this process."""
    return _connection_refused.is_set()


def reset_connection_refused() -> None:
    """Clear the refused-connection flag (intended for tests)."""
    _connection_refused.clear()


def status_topic_for(client_id: str) -> str:
    """Return the retained connection status topic for *client_id*.

    The broker publishes ``offline`` to this topic (the client's Last Will) if
    the connection is lost without a clean disconnect, e.g. after a crash or a
    power failure, and the client publishes ``online`` whenever it connects.
    """
    return f"sigenergy2mqtt/status/{client_id}"


class MqttClient(mqtt.Client):
    """MQTT client with optional TLS and pre-wired :class:`MqttHandler` callbacks.

    Parameters
    ----------
    client_id:
        Unique identifier sent to the broker on connect.
    userdata:
        Handler instance that receives all MQTT lifecycle events.
    transport:
        Underlying transport protocol — ``"tcp"`` (default) or
        ``"websockets"``.
    tls:
        Enable TLS for the connection.
    tls_insecure:
        When *True* (and *tls* is also *True*), hostname verification and
        certificate validation are disabled.  **Do not use in production.**
    """

    # Class-level default so instances created without __init__ (e.g. in tests) behave as untracked
    _outage: OutageTracker | None = None

    def __init__(
        self,
        client_id: str,
        userdata: MqttHandler,
        transport: Literal["tcp", "websockets"] = "tcp",
        tls: bool = False,
        tls_insecure: bool = False,
    ):
        self._connection_started: float | None = None
        self._has_connected = False
        self.client_id_str = client_id
        super().__init__(
            CallbackAPIVersion.VERSION2,
            client_id=client_id,
            userdata=userdata,
            protocol=mqtt.MQTTv311,
            transport=transport,
        )
        self.enable_logger(logger)

        # Last Will: without it, retained availability stays "online" forever after an unclean exit
        self.status_topic = status_topic_for(client_id)
        self.will_set(self.status_topic, STATUS_OFFLINE, qos=1, retain=True)
        # Unacknowledged QoS 1/2 publishes, so that teardown can wait for them
        self._unacknowledged: deque[mqtt.MQTTMessageInfo] = deque()
        self._unacknowledged_lock = threading.Lock()

        if tls:
            ssl_context = ssl.create_default_context()
            if tls_insecure:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning(f"Using insecure TLS connection for client_id={client_id} - TLS certificate validation is DISABLED!")
            else:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logger.info(f"Using secure TLS connection for client_id={client_id}")
            self.tls_set_context(ssl_context)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe

    def reconnect(self) -> MQTTErrorCode:
        """Track initial and automatic reconnect attempts through CONNACK."""
        from sigenergy2mqtt.metrics import Metrics

        self._record_connection_result(False)
        self._connection_started = time.monotonic()
        Metrics.mqtt_connection_attempt()
        try:
            result = super().reconnect()
        except Exception:
            self._record_connection_result(False)
            raise
        if result != mqtt.MQTT_ERR_SUCCESS:
            self._record_connection_result(False)
        return result

    def publish(self, topic, payload=None, qos=0, retain=False, properties=None):
        """Record outbound publish before delegating to paho.

        The registry tracks pending publishes by message identifier (MID) to determine
        the oldest unacknowledged publish deadline. This ensures that repeated publishes
        do not postpone the health check timeout if earlier messages remain unacknowledged.
        """
        info = super().publish(topic, payload=payload, qos=qos, retain=retain, properties=properties)
        handler: MqttHandler = self._userdata
        if handler is not None and hasattr(handler, "registry"):
            mid = getattr(info, "mid", None) if getattr(info, "rc", 0) == mqtt.MQTT_ERR_SUCCESS else None
            handler.registry.record_publish(handler.client_id, mid=mid)
        if qos > 0 and getattr(info, "rc", None) == mqtt.MQTT_ERR_SUCCESS:
            with self._unacknowledged_lock:
                while self._unacknowledged and self._unacknowledged[0].is_published():
                    self._unacknowledged.popleft()
                self._unacknowledged.append(info)
        return info

    def unacknowledged_publishes(self) -> int:
        """Number of QoS 1/2 publishes the broker has not yet acknowledged."""
        with self._unacknowledged_lock:
            pending = [info for info in self._unacknowledged if not info.is_published()]
            self._unacknowledged = deque(pending)
            return len(pending)

    def publish_status(self, status: str) -> mqtt.MQTTMessageInfo:
        """Publish the retained connection status (``online``/``offline``, or empty to clear it)."""
        return self.publish(self.status_topic, status, qos=1, retain=True)

    @property
    def outage(self) -> OutageTracker:
        """The outage tracker shared by every client connected to this broker.

        Each client connection is a member of the outage, so it ends only once
        every client that lost its connection has reconnected.
        """
        if self._outage is None:
            self._outage = outage_tracker(f"mqtt://{self.host}:{self.port}")
        return self._outage

    def _record_connection_result(self, success: bool) -> None:
        from sigenergy2mqtt.metrics import Metrics

        started = self._connection_started
        if started is None:
            return
        self._connection_started = None
        Metrics.mqtt_connection_result(time.monotonic() - started, success, self._has_connected)
        if success:
            self._has_connected = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_failure(reason_code) -> bool:
    """Return ``True`` if a disconnect *reason_code* indicates an unexpected disconnection."""
    is_failure = getattr(reason_code, "is_failure", None)
    if isinstance(is_failure, bool):
        return is_failure
    try:
        return int(reason_code) != 0
    except (TypeError, ValueError):
        return False


def _ensure_subscriptions_are_fresh(client: mqtt.Client, userdata: MqttHandler) -> None:
    """Re-subscribe to all topics if the handler has marked itself disconnected.

    This guards against the race where a disconnect occurs between the time a
    message or publish-ack is received and the reconnect callback fires.

    Parameters
    ----------
    client:
        The active paho client instance.
    userdata:
        Handler whose ``connected`` flag is inspected.
    """
    if not userdata.connected:
        userdata.on_reconnect(client)


# ---------------------------------------------------------------------------
# Paho callback implementations
# ---------------------------------------------------------------------------


def on_connect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    """Handle a completed connection attempt.

    On success, delegates to :meth:`MqttHandler.on_reconnect` so that topic
    subscriptions are (re-)established.  If the broker refuses a client that
    has never connected (e.g. bad credentials), the main thread is interrupted
    so the process can shut down cleanly — this is preferred over ``os._exit``
    because it allows ``atexit`` handlers and context managers to run — and
    :func:`connection_refused` reports the failure to the entry point.  A
    refusal after an earlier successful connection is treated as an outage and
    retried.

    Parameters
    ----------
    client:
        The paho client that just connected.
    userdata:
        Associated handler instance.
    flags:
        Connection flags returned by the broker (unused).
    reason_code:
        ``0`` on success; any other value indicates a refused connection.
    properties:
        MQTT v5 properties (unused for MQTTv311).
    """
    previously_connected = isinstance(client, MqttClient) and client._has_connected
    if isinstance(client, MqttClient):
        client._record_connection_result(reason_code == 0)
    if reason_code == 0:
        logger.debug(f"Connected to mqtt://{client.host}:{client.port} (client_id={userdata.client_id})")
        if isinstance(client, MqttClient):
            client.outage.success(member=userdata.client_id)
            # The Last Will may have been published while the connection was down
            client.publish_status(STATUS_ONLINE)
        userdata.registry.mark_connected(userdata.client_id)
        userdata.on_reconnect(client)
    elif previously_connected and isinstance(client, MqttClient):
        # A broker that accepted this client before is most likely restarting or temporarily
        # unavailable. Shutting down would turn a short outage into a permanent one, so report
        # it as an outage and let paho keep retrying.
        message = f"Connection to mqtt://{client.host}:{client.port} REFUSED - {reason_code} (client_id={userdata.client_id}); retrying"
        client.outage.failure(f"connection refused: {reason_code}", member=userdata.client_id, detail=message)
    else:
        logger.critical(f"Connection to mqtt://{client.host}:{client.port} REFUSED - {reason_code} (client_id={userdata.client_id})")
        _connection_refused.set()
        # Raise KeyboardInterrupt in the main thread so that atexit handlers,
        # context managers, and other cleanup code can still run — unlike
        # os._exit(), which terminates the process immediately.
        _thread.interrupt_main()


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, disconnect_flags, reason_code, properties) -> None:
    """Handle a disconnection from the broker.

    Marks the handler as disconnected so that
    :func:`_ensure_subscriptions_are_fresh` can trigger a re-subscription
    after the next reconnect.

    Parameters
    ----------
    client:
        The paho client that disconnected.
    userdata:
        Associated handler instance.
    disconnect_flags:
        Flags describing the disconnect event (unused).
    reason_code:
        Reason for the disconnection (0 = clean disconnect).
    properties:
        MQTT v5 properties (unused for MQTTv311).
    """
    if isinstance(client, MqttClient):
        client._record_connection_result(False)
    userdata.connected = False
    message = f"Disconnected from mqtt://{client.host}:{client.port} - {reason_code} (client_id={userdata.client_id})"
    if isinstance(client, MqttClient) and _is_failure(reason_code):
        # Unexpected disconnection: report once per broker outage rather than once per client
        client.outage.failure(str(reason_code), member=userdata.client_id, detail=message)
    else:
        logger.info(message)
    userdata.registry.mark_disconnected(userdata.client_id)


def on_message(client: mqtt.Client, userdata: MqttHandler, message) -> None:
    """Handle an incoming PUBLISH message.

    Decodes the payload as UTF-8 (replacing any invalid bytes) and forwards
    it to :meth:`MqttHandler.on_message`.

    Parameters
    ----------
    client:
        The paho client that received the message.
    userdata:
        Associated handler instance.
    message:
        Received paho :class:`~paho.mqtt.client.MQTTMessage`.
    """
    logger.debug(f"Received message for topic {message.topic} (payload={message.payload} client_id={userdata.client_id})")
    userdata.on_message(
        client,
        message.topic,
        message.payload.decode("utf-8", errors="replace"),
    )
    userdata.registry.record_message(userdata.client_id)
    _ensure_subscriptions_are_fresh(client, userdata)


def on_publish(client: mqtt.Client, userdata: MqttHandler, mid: int, reason_codes, properties) -> None:
    """Handle a PUBACK / PUBCOMP acknowledgement from the broker.

    Parameters
    ----------
    client:
        The paho client whose publish was acknowledged.
    userdata:
        Associated handler instance.
    mid:
        Message identifier that was acknowledged.
    reason_codes:
        Result codes for the publish (unused; checked by paho internally).
    properties:
        MQTT v5 properties (unused for MQTTv311).
    """
    logger.debug(f"Acknowledged publish MID={mid} (client_id={userdata.client_id})")
    userdata.on_response(mid, "publish", client)
    userdata.registry.record_publish_ack(userdata.client_id, mid=mid)
    _ensure_subscriptions_are_fresh(client, userdata)


def on_subscribe(client: mqtt.Client, userdata: MqttHandler, mid: int, reason_codes, properties) -> None:
    """Handle a SUBACK from the broker.

    Calls :meth:`MqttHandler.on_response` exactly once per ``mid`` — either
    on full success or after logging individual per-topic failures.  This
    avoids signalling the same mid multiple times when a batch subscribe
    contains a mix of successes and failures.

    .. note::
        Paho v2 may deliver an empty ``reason_codes`` list for brokers that
        send a bare SUBACK without per-topic codes (MQTTv311 behaviour).
        This is treated as unconditional success.

    Parameters
    ----------
    client:
        The paho client whose subscribe was acknowledged.
    userdata:
        Associated handler instance.
    mid:
        Message identifier of the original SUBSCRIBE packet.
    reason_codes:
        Per-topic result codes; values ≥ 128 indicate failure.
    properties:
        MQTT v5 properties (unused for MQTTv311).
    """
    if not reason_codes:
        # MQTTv311 broker: no per-topic codes — treat as success.
        userdata.on_response(mid, "subscribe", client)
        return

    failed = [r for r in reason_codes if r >= 128]
    for r in failed:
        logger.error(f"Subscribe FAILED for mid {mid} (reason_code={r} client_id={userdata.client_id})")

    succeeded = [r for r in reason_codes if r < 128]
    for r in succeeded:
        logger.debug(f"Acknowledged subscribe MID={mid} (reason_code={r} client_id={userdata.client_id})")

    # Signal once per mid regardless of how many topics succeeded.
    userdata.on_response(mid, "subscribe", client)


def on_unsubscribe(client: mqtt.Client, userdata: MqttHandler, mid: int, reason_codes, properties) -> None:
    """Handle an UNSUBACK from the broker.

    Calls :meth:`MqttHandler.on_response` exactly once per ``mid``.

    .. note::
        Paho v2 may deliver an empty ``reason_codes`` list for brokers that
        send a bare UNSUBACK without per-topic codes (MQTTv311 behaviour).
        This is treated as unconditional success.

    Parameters
    ----------
    client:
        The paho client whose unsubscribe was acknowledged.
    userdata:
        Associated handler instance.
    mid:
        Message identifier of the original UNSUBSCRIBE packet.
    reason_codes:
        Per-topic result codes; values ≥ 128 indicate failure.  May be empty
        for MQTTv311 brokers.
    properties:
        MQTT v5 properties (unused for MQTTv311).
    """
    if not reason_codes:
        # MQTTv311 broker: no per-topic codes — treat as success.
        userdata.on_response(mid, "unsubscribe", client)
        return

    failed = [r for r in reason_codes if r >= 128]
    for r in failed:
        logger.error(f"Unsubscribe FAILED for mid {mid} (reason_code={r} client_id={userdata.client_id})")

    succeeded = [r for r in reason_codes if r < 128]
    for r in succeeded:
        logger.debug(f"Acknowledged unsubscribe MID={mid} (reason_code={r} client_id={userdata.client_id})")

    # Signal once per mid regardless of how many topics succeeded.
    userdata.on_response(mid, "unsubscribe", client)
