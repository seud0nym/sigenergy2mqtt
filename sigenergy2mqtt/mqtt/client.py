"""MQTT client wrapper and callback definitions.

This module provides :class:`MqttClient`, a thin subclass of
:class:`paho.mqtt.client.Client` that wires up the standard paho callbacks to
the :class:`~.handler.MqttHandler` interface, and optionally configures TLS.
"""

import _thread
import logging
import ssl
from typing import Literal

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .handler import MqttHandler

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        client_id: str,
        userdata: MqttHandler,
        transport: Literal["tcp", "websockets"] = "tcp",
        tls: bool = False,
        tls_insecure: bool = False,
    ):
        super().__init__(
            CallbackAPIVersion.VERSION2,
            client_id=client_id,
            userdata=userdata,
            protocol=mqtt.MQTTv311,
            transport=transport,
        )
        self.enable_logger(logger)

        if tls:
            ssl_context = ssl.create_default_context()
            if tls_insecure:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logging.warning(f"Using insecure TLS connection for client_id={client_id} - TLS certificate validation is DISABLED!")
            else:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logging.info(f"Using secure TLS connection for client_id={client_id}")
            self.tls_set_context(ssl_context)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
    subscriptions are (re-)established.  On failure, interrupts the main
    thread so the process can shut down cleanly — this is preferred over
    ``os._exit`` because it allows ``atexit`` handlers and context managers
    to run.

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
    if reason_code == 0:
        logger.debug(f"Connected to mqtt://{client.host}:{client.port} (client_id={userdata.client_id})")
        userdata.on_reconnect(client)
    else:
        logger.critical(f"Connection to mqtt://{client.host}:{client.port} REFUSED - {reason_code} (client_id={userdata.client_id})")
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
    userdata.connected = False
    logger.info(f"Disconnected from mqtt://{client.host}:{client.port} - {reason_code} (client_id={userdata.client_id})")


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

    if succeeded:
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

    if succeeded:
        # Signal once per mid regardless of how many topics succeeded.
        userdata.on_response(mid, "unsubscribe", client)
