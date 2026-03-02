"""MQTT message and acknowledgement handling for sigenergy2mqtt.

This module provides :class:`MqttHandler`, which bridges the paho-mqtt
callback thread and the asyncio event loop used by the rest of the
application.  Its responsibilities are:

* **Topic dispatch** – maintain a registry of per-topic handler coroutines
  and invoke them when a matching message arrives (``on_message``).
* **Reconnect re-subscription** – re-subscribe to all registered topics
  after the broker connection is restored (``on_reconnect``).
* **Publish acknowledgement** – allow callers to await confirmation that
  a publish or subscribe operation has been acknowledged by the broker
  (``wait_for``).

Thread-safety
-------------
paho-mqtt delivers callbacks on its own network thread.  All shared state
is protected by explicit :class:`threading.Lock` objects so that the MQTT
thread and the asyncio loop can access it concurrently without races:

* ``_state_lock``  – guards ``connected`` and ``_topics``.
* ``_mids_lock``   – guards ``_seen_mids`` and ``_pending_mids``.

``_closing`` is a :class:`threading.Event` so that its value is
immediately visible across threads without relying on the GIL.
"""

import asyncio
import concurrent.futures
import inspect
import logging
import threading
import time
from collections import namedtuple
from typing import Any, Callable, Coroutine

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTErrorCode

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus import ModbusClient

logger = logging.getLogger("paho.mqtt")

# Pending MID record: the wall-clock time it was registered and the response handler.
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])

# MIDs older than this many seconds are considered stale and are purged.
_MID_EXPIRY_SECONDS: float = 60.0


def _get_method_name(method) -> str:
    """Return a human-readable qualified name for *method*.

    Bound methods are rendered as ``ClassName.method_name``; plain
    functions and other callables fall back to their ``__name__``, or
    ``'[Unknown method]'`` if that attribute is absent.
    """
    if hasattr(method, "__self__"):
        return f"{method.__class__.__name__}.{getattr(method, '__name__', '[Unknown method]')}"
    return getattr(method, "__name__", "[Unknown method]")


class MqttHandler:
    """Dispatch incoming MQTT messages and track publish acknowledgements.

    One ``MqttHandler`` instance is created per logical MQTT client
    (identified by *client_id*).  It is not a paho ``Client`` itself; it
    is a helper that the application wires into paho callbacks.

    Parameters
    ----------
    client_id:
        The paho client identifier string, used only for log messages.
    modbus_client:
        Optional Modbus client passed through to every topic handler so
        handlers can issue Modbus reads/writes in response to MQTT
        messages.
    loop:
        The running asyncio event loop.  Coroutines returned by topic
        handlers are scheduled on this loop via
        :func:`asyncio.run_coroutine_threadsafe`.
    """

    def __init__(self, client_id: str, modbus_client: ModbusClient | None, loop: asyncio.AbstractEventLoop):
        """Initialise internal state; no network I/O is performed here."""
        self._loop = loop
        self._modbus = modbus_client
        self.client_id = client_id
        self.connected = False

        # Protects: self.connected, self._topics.
        self._state_lock = threading.Lock()

        # MIDs that arrived *before* wait_for registered a handler (so wait_for
        # can detect the "already acknowledged" case).
        self._seen_mids: set[Any] = set()
        # MIDs that wait_for is actively watching, mapped to their response record.
        self._pending_mids: dict[Any, MqttResponse] = {}
        # Protects: self._seen_mids, self._pending_mids.
        self._mids_lock = threading.Lock()

        self._topics: dict[
            str,
            list[Callable[[ModbusClient | None, mqtt.Client, str, str, "MqttHandler"], Coroutine[Any, Any, bool]]],
        ] = {}

        self._pending_tasks: set[concurrent.futures.Future] = set()
        # Set when close() is called; signals background threads to stop
        # scheduling new coroutines.
        self._closing = threading.Event()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _schedule_coroutine(self, method_result, label: str) -> None:
        """Submit *method_result* to the asyncio event loop from any thread.

        If the handler is already closing, the awaitable is discarded
        (its ``close`` method is called to avoid a
        *coroutine was never awaited* warning).  Otherwise the coroutine
        is submitted via :func:`asyncio.run_coroutine_threadsafe` and its
        :class:`~concurrent.futures.Future` is tracked in
        ``_pending_tasks`` so that :meth:`close` can await completion.

        Parameters
        ----------
        method_result:
            An awaitable (coroutine or other) returned by a topic or
            response handler.
        label:
            Human-readable name of the handler, used only in log
            messages.
        """
        if self._closing.is_set():
            logger.debug(f"MqttHandler is closing – discarding {label} coroutine")
            if hasattr(method_result, "close"):
                method_result.close()
            return
        if not asyncio.iscoroutine(method_result):
            method_result = _wrap(method_result)
        try:
            future = asyncio.run_coroutine_threadsafe(method_result, self._loop)
            self._pending_tasks.add(future)
            future.add_done_callback(self._pending_tasks.discard)
        except RuntimeError as e:
            logger.debug(f"Failed to schedule {label} – loop probably closed: {e}")
            if hasattr(method_result, "close"):
                method_result.close()

    def _purge_expired_mids(self) -> None:
        """Evict stale entries from ``_pending_mids``.

        An entry is considered stale when it was inserted more than
        :data:`_MID_EXPIRY_SECONDS` seconds ago without ever being
        matched by a broker acknowledgement.  This prevents unbounded
        growth of the dict in the unlikely event that a broker never
        sends a ``PUBACK``/``SUBACK``.

        .. warning::
            The caller **must** hold ``_mids_lock`` before calling this
            method.
        """
        cutoff = time.time() - _MID_EXPIRY_SECONDS
        stale = [mid for mid, rec in self._pending_mids.items() if rec.now < cutoff]
        for mid in stale:
            logger.debug(f"Removing expired MID={mid} (client_id={self.client_id})")
            del self._pending_mids[mid]

    # ------------------------------------------------------------------
    # MQTT callbacks
    # ------------------------------------------------------------------

    def on_reconnect(self, client: mqtt.Client) -> None:
        """Handle a (re-)connection event from the MQTT broker.

        Called by the application's paho ``on_connect`` callback.
        Re-subscribes to every previously registered topic so that no
        messages are missed after a disconnect/reconnect cycle.

        The method is idempotent: if ``connected`` is already ``True``
        it returns immediately without re-subscribing.  The
        ``_state_lock`` ensures that only one thread can transition
        ``connected`` from ``False`` to ``True``, preventing duplicate
        subscription bursts if the broker fires multiple connect events
        in quick succession.

        Parameters
        ----------
        client:
            The paho :class:`~paho.mqtt.client.Client` instance that
            just connected.
        """
        with self._state_lock:
            if self.connected:
                return
            self.connected = True
            if self._topics:
                logger.info(f"Reconnected to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} (client_id={self.client_id})")
                for topic in self._topics:
                    result = client.unsubscribe(topic)
                    logger.debug(f"on_reconnect: unsubscribe('{topic}') -> {result} (client_id={self.client_id})")
                    result = client.subscribe(topic)
                    logger.debug(f"on_reconnect: subscribe('{topic}') -> {result} (client_id={self.client_id})")

    def on_message(self, client: mqtt.Client, topic: str, payload: str) -> None:
        """Dispatch an incoming MQTT message to all registered handlers.

        Called by the application's paho ``on_message`` callback.  Empty
        payloads are silently ignored.  For each handler registered for
        *topic*, the handler is invoked synchronously; if it returns an
        awaitable, that awaitable is scheduled on the asyncio loop via
        :meth:`_schedule_coroutine`.

        Parameters
        ----------
        client:
            The paho client that received the message.
        topic:
            The topic on which the message arrived.
        payload:
            Raw payload string (stripped of leading/trailing whitespace
            before being passed to handlers).
        """
        value = str(payload).strip()
        if not value:
            logger.info(f"IGNORED empty payload from topic {topic} (client_id={self.client_id})")
            return

        with self._state_lock:
            handlers = list(self._topics.get(topic, []))

        if not handlers:
            logger.warning(f"No registered handler found for topic {topic} (client_id={self.client_id})")
            return

        for method in handlers:
            method_name = _get_method_name(method)
            logger.debug(f"Handling topic {topic} with {method_name} ({payload=} client_id={self.client_id})")
            method_result = method(self._modbus, client, value, topic, self)
            if inspect.isawaitable(method_result):
                self._schedule_coroutine(method_result, method_name)

    def on_response(self, mid: Any, topic: str, client: mqtt.Client) -> None:
        """Handle a broker acknowledgement (PUBACK / SUBACK).

        Called by the application's paho acknowledgement callbacks.
        Three cases are handled:

        1. **Handler already registered** (``mid`` is in
           ``_pending_mids``): the stored response handler is invoked and
           the entry is removed.
        2. **Duplicate acknowledgement** (``mid`` is in ``_seen_mids``):
           silently ignored.
        3. **Acknowledgement arrived before** :meth:`wait_for` **registered**:
           the MID is parked in ``_seen_mids`` so that :meth:`wait_for`
           can detect the race and return immediately.

        Stale entries in ``_pending_mids`` are purged on every call.

        Parameters
        ----------
        mid:
            The message identifier returned by paho for the publish or
            subscribe operation.
        topic:
            The topic associated with the original operation.
        client:
            The paho client that received the acknowledgement.
        """
        with self._mids_lock:
            if mid in self._pending_mids:
                # wait_for is watching this MID.
                record = self._pending_mids.pop(mid)
                handler = record.handler
            elif mid in self._seen_mids:
                # Already processed once; ignore the duplicate.
                return
            else:
                # wait_for hasn't registered yet – park the MID so wait_for can
                # detect the "already acknowledged" case.
                self._seen_mids.add(mid)
                self._purge_expired_mids()
                return

            self._purge_expired_mids()

        if handler is not None:
            method_name = _get_method_name(handler)
            logger.debug(f"Handling topic {topic} response for MID={mid} with method {method_name} (client_id={self.client_id})")
            method_result = handler(client, topic)
            if inspect.isawaitable(method_result):
                self._schedule_coroutine(method_result, method_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        client: mqtt.Client,
        topic: str,
        handler: Callable[
            [ModbusClient | None, mqtt.Client, str, str, "MqttHandler"],
            Coroutine[Any, Any, bool],
        ],
    ) -> tuple[MQTTErrorCode, int | None]:
        """Register a handler for *topic* and subscribe to it on the broker.

        Multiple handlers may be registered for the same topic; they are
        invoked in registration order by :meth:`on_message`.

        Parameters
        ----------
        client:
            The paho client used to issue the ``SUBSCRIBE`` packet.
        topic:
            The MQTT topic filter to subscribe to.
        handler:
            A callable that accepts
            ``(modbus_client, mqtt_client, payload, topic, mqtt_handler)``
            and returns either a plain value or a coroutine.  Coroutines
            are scheduled on the asyncio loop automatically.

        Returns
        -------
        tuple[MQTTErrorCode, int | None]
            The return value of :pymeth:`paho.mqtt.client.Client.subscribe`,
            i.e. a ``(result, mid)`` pair.
        """
        with self._state_lock:
            self._topics.setdefault(topic, []).append(handler)
        handler_name = _get_method_name(handler)
        logger.debug(f"Registered handler {handler_name} for topic {topic} (client_id={self.client_id})")
        return client.subscribe(topic)

    async def close(self) -> None:
        """Signal shutdown and wait for all in-flight handler coroutines.

        Sets the ``_closing`` event so that no new coroutines are
        scheduled after this point, then awaits every
        :class:`~concurrent.futures.Future` that was tracked in
        ``_pending_tasks``.  Exceptions raised by individual tasks are
        collected rather than propagated, so that a single failing
        handler does not prevent others from being awaited.

        The set of pending tasks is snapshot at the start of the await
        so that done-callbacks removing completed futures from the live
        set do not interfere with iteration.
        """
        self._closing.set()
        if self._pending_tasks:
            # Snapshot before awaiting so that done-callbacks removing items
            # from the live set don't interfere with iteration.
            snapshot = list(self._pending_tasks)
            count = len(snapshot)
            logger.debug(f"Waiting for {count} pending MQTT tasks to complete (client_id={self.client_id})")
            await asyncio.gather(
                *[asyncio.wrap_future(f) for f in snapshot],
                return_exceptions=True,
            )
            logger.debug(f"All {count} pending MQTT tasks completed (client_id={self.client_id})")

    async def wait_for(self, seconds: float, prefix: str, method: Callable, *args, **kwargs) -> bool:
        """Call *method* and wait up to *seconds* for the broker to acknowledge it.

        Invokes *method* (which should perform a paho publish or
        subscribe) and blocks until the broker sends a matching
        ``PUBACK`` / ``SUBACK``, or until the timeout elapses.

        The acknowledgement may arrive *before* this coroutine reaches
        the registration step (e.g. on a very fast local broker).  This
        race is handled by checking ``_seen_mids``: if
        :meth:`on_response` already parked the MID there, this method
        returns ``True`` immediately.

        Parameters
        ----------
        seconds:
            Maximum time to wait for the acknowledgement.  Must be a
            number strictly less than :data:`_MID_EXPIRY_SECONDS`.
        prefix:
            A string prepended to all log messages emitted during the
            wait, to aid in correlating log lines with a specific
            operation.
        method:
            The callable (or coroutine function) to invoke.  It must
            return a :class:`paho.mqtt.client.MQTTMessageInfo` object;
            if it returns anything else the method logs a warning and
            returns ``False``.
        *args, **kwargs:
            Forwarded verbatim to *method*.

        Returns
        -------
        bool
            ``True`` if a broker acknowledgement was received within the
            timeout; ``False`` otherwise (timeout, cancellation, or
            *method* not returning a valid
            :class:`~paho.mqtt.client.MQTTMessageInfo`).

        Raises
        ------
        ValueError
            If *seconds* is not a number or is >= :data:`_MID_EXPIRY_SECONDS`.
        TypeError
            If *method* is not callable.
        """
        if not isinstance(seconds, (int, float)) or seconds >= _MID_EXPIRY_SECONDS:
            raise ValueError(f"'seconds' must be a number less than {_MID_EXPIRY_SECONDS}, got {seconds!r}")
        if not callable(method):
            raise TypeError(f"'method' must be callable, got {type(method)!r}")

        responded = False

        def handle_response(client: mqtt.Client, source: str) -> None:
            nonlocal responded
            responded = True
            logger.debug(f"{prefix} {method.__name__} acknowledged (MID={info.mid} client_id={self.client_id})")

        if inspect.iscoroutinefunction(method):
            info = await method(*args, **kwargs)
        else:
            info = method(*args, **kwargs)

        if not isinstance(info, mqtt.MQTTMessageInfo):
            if info is not None:
                logger.warning(f"{prefix} {method.__name__} did not return a valid MQTTMessageInfo object {info=} so unable to wait for acknowledgement (client_id={self.client_id})")
            return False

        with self._mids_lock:
            already_seen = info.mid in self._seen_mids
            if already_seen:
                self._seen_mids.discard(info.mid)
            else:
                self._pending_mids[info.mid] = MqttResponse(time.time(), handle_response)

        if already_seen:
            logger.debug(f"{prefix} {method.__name__} has already been acknowledged (MID={info.mid} client_id={self.client_id})")
            return True

        until = time.time() + seconds
        logger.debug(f"{prefix} waiting up to {seconds}s for {method.__name__} to be acknowledged (MID={info.mid} client_id={self.client_id})")
        while not responded:
            try:
                await asyncio.sleep(0.5)
                if time.time() >= until:
                    logger.warning(f"{prefix} no acknowledgement of {method.__name__} received?? (client_id={self.client_id})")
                    break
            except asyncio.CancelledError:
                logger.debug(f"{prefix} sleep interrupted before acknowledgement of {method.__name__} received (client_id={self.client_id})")
                break
        return responded


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


async def _wrap(awaitable):
    """Wrap a non-coroutine awaitable so it can be passed to asyncio machinery.

    :func:`asyncio.run_coroutine_threadsafe` requires a *coroutine*
    object, not an arbitrary awaitable.  This thin wrapper promotes any
    awaitable to a proper coroutine.
    """
    return await awaitable
