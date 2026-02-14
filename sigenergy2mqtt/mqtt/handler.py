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
