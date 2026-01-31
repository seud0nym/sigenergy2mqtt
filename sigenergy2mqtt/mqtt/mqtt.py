import asyncio
import concurrent.futures
import inspect
import logging
import os
import ssl
import threading
import time
from collections import namedtuple
from typing import Any, Callable, Coroutine, Literal

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode, MQTTProtocolVersion

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.modbus.types import ModbusClientType

logger = logging.getLogger("paho.mqtt")
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])


async def _wrap(awaitable):
    return await awaitable


def _get_method_name(method) -> str:
    return f"{method.__class__.__name__}.{getattr(method, '__name__', '[Unknown method]')}" if hasattr(method, "__self__") else getattr(method, "__name__", "[Unknown method]")


class MqttHandler:
    def __init__(self, client_id: str, modbus_client: ModbusClientType | None, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._mids: dict[Any, MqttResponse] = {}
        self._modbus = modbus_client
        self._reconnect_lock = threading.Lock()
        self._topics: dict[str, list[Callable[[ModbusClientType | None, mqtt.Client, str, str, "MqttHandler"], Coroutine[Any, Any, bool]]]] = {}
        self.client_id = client_id
        self.connected = False
        self._pending_tasks: set[concurrent.futures.Future] = set()
        self._closing = False

    def on_reconnect(self, client: mqtt.Client) -> None:
        if not self.connected:
            with self._reconnect_lock:
                if not self.connected:
                    self.connected = True
                    if len(self._topics) > 0:
                        logger.info(f"Reconnected to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} (client_id={self.client_id})")
                        for topic in self._topics.keys():
                            result = client.unsubscribe(topic)
                            logger.debug(f"on_reconnect: unsubscribe('{topic}') -> {result} (client_id={self.client_id})")
                            result = client.subscribe(topic)
                            logger.debug(f"on_reconnect: subscribe('{topic}') -> {result} (client_id={self.client_id})")

    def on_message(self, client: mqtt.Client, topic: str, payload: str) -> None:
        value = str(payload).strip()
        if not value:
            logger.info(f"IGNORED empty payload from topic {topic} (client_id={self.client_id})")
        else:
            with self._reconnect_lock:
                if topic in self._topics:
                    for method in self._topics[topic]:
                        method_name = _get_method_name(method)
                        logger.debug(f"Handling topic {topic} with {method_name} ({payload=} client_id={self.client_id})")
                        method_result = method(self._modbus, client, value, topic, self)
                        if inspect.isawaitable(method_result):
                            if self._closing:
                                logger.debug(f"MqttHandler is closing - discarding {method_name} coroutine")
                                if hasattr(method_result, "close"):
                                    method_result.close()
                                continue
                            if not asyncio.iscoroutine(method_result):
                                method_result = _wrap(method_result)
                            try:
                                future = asyncio.run_coroutine_threadsafe(method_result, self._loop)
                                self._pending_tasks.add(future)
                                future.add_done_callback(self._pending_tasks.discard)
                            except RuntimeError as e:
                                logger.debug(f"Failed to schedule {method_name} - loop probably closed: {e}")
                                if hasattr(method_result, "close"):
                                    method_result.close()
                else:
                    logger.warning(f"No registered handler found for topic {topic} (client_id={self.client_id})")

    def on_response(self, mid: Any, topic: str, client: mqtt.Client) -> None:
        if mid in self._mids:
            method = self._mids[mid].handler
            if method is not None:
                method_name = _get_method_name(method)
                logger.debug(f"Handling topic {topic} response for MID={mid} with method {method_name} (client_id={self.client_id})")
                method_result = method(client, topic)
                if inspect.isawaitable(method_result):
                    if self._closing:
                        logger.debug(f"MqttHandler is closing - discarding response handler {method_name} coroutine")
                        if hasattr(method_result, "close"):
                            method_result.close() # type: ignore
                    else:
                        if not asyncio.iscoroutine(method_result):
                            method_result = _wrap(method_result)
                        try:
                            future = asyncio.run_coroutine_threadsafe(method_result, self._loop)
                            self._pending_tasks.add(future)
                            future.add_done_callback(self._pending_tasks.discard)
                        except RuntimeError as e:
                            logger.debug(f"Failed to schedule response handler {method_name} - loop probably closed: {e}")
                            if hasattr(method_result, "close"):
                                method_result.close()
            del self._mids[mid]
        else:
            self._mids[mid] = MqttResponse(time.time(), None)
        expires = time.time() - 60
        for mid in list(self._mids.keys()):
            if self._mids[mid].now < expires:
                logger.debug(f"Removing expired MID={mid} (client_id={self.client_id})")
                del self._mids[mid]

    def register(self, client: mqtt.Client, topic: str, handler: Callable[[ModbusClientType | None, mqtt.Client, str, str, "MqttHandler"], Coroutine[Any, Any, bool]]) -> tuple[MQTTErrorCode, int | None]:
        with self._reconnect_lock:
            if topic not in self._topics:
                self._topics[topic] = []
            self._topics[topic].append(handler)
        handler_name = f"{handler.__class__.__name__}.{getattr(handler, '__name__', '[Unknown method]')}" if hasattr(handler, "__self__") else getattr(handler, "__name__", "[Unknown method]")
        logger.debug(f"Registered handler {handler_name} for topic {topic} (client_id={self.client_id})")
        return client.subscribe(topic)

    async def close(self):
        self._closing = True
        if self._pending_tasks:
            count = len(self._pending_tasks)
            logger.debug(f"Waiting for {count} pending MQTT tasks to complete (client_id={self.client_id})")
            # concurrent.futures.Future doesn't have an async wait, so we wrap them
            await asyncio.gather(
                *[asyncio.wrap_future(f) for f in self._pending_tasks],
                return_exceptions=True,
            )
            logger.debug(f"All {count} pending MQTT tasks completed (client_id={self.client_id})")

    async def wait_for(self, seconds: float, prefix: str, method: Callable, *args, **kwargs) -> bool:
        responded: bool = False

        def handle_response(client: mqtt.Client, source: str):
            nonlocal responded
            responded = True
            logging.debug(f"{prefix} {method.__name__} acknowledged (MID={info.mid} client_id={self.client_id})")

        assert isinstance(seconds, (int, float)) and seconds < 60, "Seconds must be an integer or float and less then 60"
        assert isinstance(method, Callable), "Method must be a Callable or Awaitable"
        if inspect.iscoroutinefunction(method):
            info = await method(*args, **kwargs)
        else:
            info = method(*args, **kwargs)
        if isinstance(info, mqtt.MQTTMessageInfo):
            if info.mid in self._mids:
                logging.debug(f"{prefix} {method.__name__} has already been acknowledged (MID={info.mid} client_id={self.client_id})")
                del self._mids[info.mid]
                return True
            else:
                self._mids[info.mid] = MqttResponse(time.time(), handle_response)
                until = time.time() + seconds
                logging.debug(f"{prefix} waiting up to {seconds}s for {method.__name__} to be acknowledged (MID={info.mid} client_id={self.client_id})")
                while not responded:
                    try:
                        await asyncio.sleep(0.5)
                        if time.time() >= until:
                            logging.warning(f"{prefix} no acknowledgement of {method.__name__} received?? (client_id={self.client_id})")
                            break
                    except asyncio.CancelledError:
                        logging.debug(f"{prefix} sleep interrupted before acknowledgement of {method.__name__} received (client_id={self.client_id})")
                        break
                return responded
        else:
            if info is not None:
                logging.warning(f"{prefix} {method.__name__} did not return a valid MQTTMessageInfo object {info=} so unable to wait for acknowledgement (client_id={self.client_id})")
            return False


# region MQTT Client Callbacks


def on_connect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        logger.debug(f"Connected to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} with username {Config.mqtt.username} (client_id={userdata.client_id})")
        userdata.on_reconnect(client)
    else:
        logger.critical(f"Connection to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} REFUSED - {reason_code} (client_id={userdata.client_id})")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    userdata.connected = False
    logger.info(f"Disconnected from mqtt://{Config.mqtt.broker}:{Config.mqtt.port} - {reason_code} (client_id={userdata.client_id})")


def on_message(client: mqtt.Client, userdata: MqttHandler, message) -> None:
    logger.debug(f"Received message for topic {message.topic} (payload={message.payload} client_id={userdata.client_id})")
    userdata.on_message(client, message.topic, str(message.payload, "utf-8"))
    userdata.on_reconnect(client)


def on_publish(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    logger.debug(f"Acknowledged publish MID={mid} (client_id={userdata.client_id})")
    userdata.on_response(mid, "publish", client)
    userdata.on_reconnect(client)


def on_subscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    if len(reason_codes) == 0:
        userdata.on_response(mid, "subscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"Subscribe FAILED for mid {mid} (reason_code={result} client_id={userdata.client_id})")
            else:
                logger.debug(f"Acknowledged subscribe MID={mid} (reason_code={result} client_id={userdata.client_id})")
                userdata.on_response(mid, "subscribe", client)


def on_unsubscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties):
    if len(reason_codes) == 0:
        userdata.on_response(mid, "unsubscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"Unsubscribe FAILED for mid {mid} (reason_code={result} client_id={userdata.client_id})")
            else:
                logger.debug(f"Acknowledged unsubscribe MID={mid} (reason_code={result} client_id={userdata.client_id})")
                userdata.on_response(mid, "unsubscribe", client)


# endregion


class MqttClient(mqtt.Client):
    def __init__(
        self,
        client_id: str,
        userdata: MqttHandler,
        protocol: MQTTProtocolVersion = mqtt.MQTTv311,
        transport: Literal["tcp", "websockets"] = "tcp",
        reconnect_on_failure: bool = True,
    ):
        super().__init__(
            CallbackAPIVersion.VERSION2,
            client_id=client_id,
            userdata=userdata,
            protocol=protocol,
            transport=transport,
            reconnect_on_failure=reconnect_on_failure,
        )
        self.enable_logger(logger)
        if Config.mqtt.tls:
            ssl_context = ssl.create_default_context()
            if Config.mqtt.tls_insecure:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logging.warning(f"Using insecure TLS connection (not recommended) to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} (client_id={client_id})")
            else:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logging.info(f"Using secure TLS connection to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} (client_id={client_id})")
            self.tls_set_context(ssl_context)
            self.tls_insecure_set(Config.mqtt.tls_insecure)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe
