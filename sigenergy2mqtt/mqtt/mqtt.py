from collections import namedtuple
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Dict, Self
import asyncio
import logging
import os
import paho.mqtt.client as mqtt
import ssl
import threading
import time

logger = logging.getLogger("paho.mqtt")
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])


class MqttHandler:
    def __init__(self, client_id: str, modbus: ModbusClient, loop: asyncio.AbstractEventLoop):
        self._client_id = client_id
        self._mids: Dict[Any, MqttResponse] = {}
        self._topics: Dict[str, list[Callable[[mqtt.Client, str], None]]] = {}
        self._modbus = modbus
        self._loop = loop
        self._connected = False
        self._reconnect_lock = threading.Lock()

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value) -> None:
        self._connected = value

    def on_reconnect(self, client: mqtt.Client) -> None:
        if not self._connected:
            with self._reconnect_lock:
                if not self._connected:
                    self._connected = True
                    if len(self._topics) > 0:
                        logger.info(f"[{self._client_id}] Reconnected to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}")
                        for topic in self._topics.keys():
                            result = client.unsubscribe(topic)
                            logger.debug(f"[{self._client_id}] on_reconnect: unsubscribe('{topic}') -> {result}")
                            result = client.subscribe(topic)
                            logger.debug(f"[{self._client_id}] on_reconnect: subscribe('{topic}') -> {result}")

    def on_message(self, client: mqtt.Client, topic: str, payload: str) -> None:
        value = str(payload).strip()
        if not value:
            logger.info(f"[{self._client_id}] IGNORED empty payload from topic {topic}")
        else:
            with self._reconnect_lock:
                if topic in self._topics:
                    for method in self._topics[topic]:
                        logger.debug(f"[{self._client_id}] Handling topic {topic} with {method.__self__.__class__.__name__}.{getattr(method, '__name__', '[Unknown method]')} ({payload=})")
                        asyncio.run_coroutine_threadsafe(method(self._modbus, client, value, topic, self), self._loop)
                else:
                    logger.warning(f"[{self._client_id}] No registered handler found for topic {topic}")

    def on_response(self, mid: Any, source: str, client: mqtt.Client) -> None:
        if mid in self._mids:
            method = self._mids[mid].handler
            logger.debug(f"[{self._client_id}] Handling {source} response for MID={mid} with method {method}")
            if method is not None:
                method(client, source)
            del self._mids[mid]
        else:
            self._mids[mid] = MqttResponse(time.time(), None)
        expires = time.time() - 60
        for mid in list(self._mids.keys()):
            if self._mids[mid].now < expires:
                logger.debug(f"[{self._client_id}] Removing expired MID={mid}")
                del self._mids[mid]

    def register(self, client: mqtt.Client, topic: str, handler: Callable[[ModbusClient, mqtt.Client, str, str, Self], Awaitable[bool]]) -> tuple[int, int]:
        with self._reconnect_lock:
            if topic not in self._topics:
                self._topics[topic] = []
            self._topics[topic].append(handler)
        logger.debug(f"[{self._client_id}] Registered handler {handler.__self__.__class__.__name__}.{getattr(handler, '__name__', '[Unknown method]')} for topic {topic}")
        return client.subscribe(topic)

    async def wait_for(self, seconds: float, prefix: str, method: Callable | Awaitable, *args, **kwargs) -> bool:
        responded: bool = False

        def handle_response(client: mqtt.Client, source: str):
            nonlocal responded
            responded = True
            logging.debug(f"{prefix} - {method.__name__} acknowledged (MID={info.mid})")

        assert isinstance(seconds, (int, float)) and seconds < 60, "Seconds must be an integer or float and less then 60"
        assert isinstance(method, (Callable, Awaitable)), "Method must be a Callable or Awaitable"
        if isinstance(method, Awaitable):
            info = await method(*args, **kwargs)
        else:
            info = method(*args, **kwargs)
        if isinstance(info, mqtt.MQTTMessageInfo):
            if info.mid in self._mids:
                logging.debug(f"{prefix} - {method.__name__} has already been acknowledged (MID={info.mid})")
                del self._mids[info.mid]
            else:
                self._mids[info.mid] = MqttResponse(time.time(), handle_response)
                until = time.time() + seconds
                logging.debug(f"{prefix} - Waiting up to {seconds}s for {method.__name__} to be acknowledged (MID={info.mid})")
                while not responded:
                    await asyncio.sleep(0.5)
                    if time.time() >= until:
                        logging.warning(f"{prefix} - No acknowledgement of {method.__name__} received??")
                        break
                return responded
        else:
            if info is not None:
                logging.warning(f"{prefix} - {method.__name__} did not return a valid MQTTMessageInfo object {info=} (unable to wait for acknowledgement)")
            return False


# region MQTT Client Callbacks


def on_connect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        logger.debug(f"[{userdata.client_id}] Connected to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} with username {Config.mqtt.username}")
        userdata.on_reconnect(client)
    else:
        logger.critical(f"[{userdata.client_id}] Connection to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} REFUSED - {reason_code}")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    userdata.connected = False
    if reason_code == 0:
        logger.info(f"[{userdata.client_id}] Disconnected from mqtt://{Config.mqtt.broker}:{Config.mqtt.port} (Reason Code = {reason_code})")
    else:
        logger.error(f"[{userdata.client_id}] Failed to disconnect from mqtt://{Config.mqtt.broker}:{Config.mqtt.port} (Reason Code = {reason_code})")


def on_message(client: mqtt.Client, userdata: MqttHandler, message) -> None:
    logger.debug(f"[{userdata.client_id}] Received message for topic {message.topic} (payload={message.payload})")
    userdata.on_message(client, message.topic, str(message.payload, "utf-8"))
    userdata.on_reconnect(client)


def on_publish(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    logger.debug(f"[{userdata.client_id}] Acknowledged publish MID={mid}")
    userdata.on_response(mid, "publish", client)
    userdata.on_reconnect(client)


def on_subscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    if len(reason_codes) == 0:
        userdata.on_response(mid, "subscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"[{userdata.client_id}] Subscribe FAILED for mid {mid} (Reason Code = {result})")
            else:
                logger.debug(f"[{userdata.client_id}] Acknowledged subscribe MID={mid} (Reason Code = {result})")
                userdata.on_response(mid, "subscribe", client)


def on_unsubscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties):
    if len(reason_codes) == 0:
        userdata.on_response(mid, "unsubscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"[{userdata.client_id}] Unsubscribe FAILED for mid {mid} (Reason Code = {result})")
            else:
                logger.debug(f"[{userdata.client_id}] Acknowledged unsubscribe MID={mid} (Reason Code = {result})")
                userdata.on_response(mid, "unsubscribe", client)


# endregion


class MqttClient(mqtt.Client):
    def __init__(
        self,
        client_id: str | None = "",
        clean_session: bool | None = None,
        userdata: MqttHandler = None,
        protocol: int = mqtt.MQTTv311,
        transport: str = "tcp",
        reconnect_on_failure: bool = True,
    ):
        super().__init__(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=clean_session,
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
                logging.warning(f"[{client_id}] Using insecure TLS connection (not recommended) to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}:{Config.mqtt.port}")
            else:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logging.info(f"[{client_id}] Using secure TLS connection to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}:{Config.mqtt.port}")
            self.tls_set_context(ssl_context)
            self.tls_insecure_set(Config.mqtt.tls_insecure)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe
