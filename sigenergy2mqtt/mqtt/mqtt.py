from collections import namedtuple
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Dict, Self
import asyncio
import logging
import os
import paho.mqtt.client as mqtt
import time

logger = logging.getLogger("paho.mqtt")
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])


class MqttHandler:
    def __init__(self, modbus: ModbusClient, loop: asyncio.AbstractEventLoop):
        self._mids: Dict[Any, MqttResponse] = {}
        self._topics: Dict[str, list[Callable[[mqtt.Client, str], None]]] = {}
        self._modbus = modbus
        self._loop = loop

    def on_message(self, client: mqtt.Client, topic: str, payload: str) -> None:
        value = str(payload).strip()
        if not value:
            logger.info(f"MqttHandler IGNORED empty payload from topic {topic}")
        else:
            if topic in self._topics:
                for method in self._topics[topic]:
                    logger.debug(f"MqttHandler handling topic {topic} with {method}")
                    asyncio.run_coroutine_threadsafe(method(self._modbus, client, value, topic, self), self._loop)
            else:
                logger.warning(f"MqttHandler did not find a handler for topic {topic}")

    def on_response(self, mid: Any, source: str, client: mqtt.Client) -> None:
        if mid in self._mids:
            method = self._mids[mid].handler
            logger.debug(f"MqttHandler handling {source} response for MID={mid} with method {method}")
            if method is not None:
                method(client, source)
            del self._mids[mid]
        else:
            self._mids[mid] = MqttResponse(time.time(), None)
        expires = time.time() - 60
        for mid in list(self._mids.keys()):
            if self._mids[mid].now < expires:
                logger.debug(f"MqttHandler removing expired MID={mid}")
                del self._mids[mid]

    def register(self, client: mqtt.Client, topic: str, handler: Callable[[ModbusClient, mqtt.Client, str, str, Self], Awaitable[bool]]) -> tuple[int, int]:
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)
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
        logger.debug(f"Connected to MQTT broker {Config.mqtt.broker} (port {Config.mqtt.port}) with username {Config.mqtt.username}")
    else:
        logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - {reason_code}")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        logger.info(f"Disconnected from {Config.mqtt.broker} (Reason Code = {reason_code})")
    else:
        logger.error(f"Failed to disconnected from {Config.mqtt.broker} (Reason Code = {reason_code})")


def on_message(client: mqtt.Client, userdata: MqttHandler, message) -> None:
    logger.debug(f"Received message from {Config.mqtt.broker} for topic {message.topic}: Payload = {message.payload}")
    userdata.on_message(client, message.topic, str(message.payload, "utf-8"))


def on_publish(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    logger.debug(f"Acknowledged publish MID={mid}")
    userdata.on_response(mid, "publish", client)


def on_subscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties) -> None:
    if len(reason_codes) == 0:
        userdata.on_response(mid, "subscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"Subscribe FAILED message from {Config.mqtt.broker} for mid {mid} (Reason Code = {result})")
            else:
                logger.debug(f"Acknowledged subscribe MID={mid} (Reason Code = {result})")
                userdata.on_response(mid, "subscribe", client)


def on_unsubscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_codes, properties):
    if len(reason_codes) == 0:
        userdata.on_response(mid, "unsubscribe", client)
    else:
        for result in reason_codes:
            if result >= 128:
                logger.error(f"Unsubscribe FAILED message from {Config.mqtt.broker} for mid {mid} (Reason Code = {result})")
            else:
                logger.debug(f"Acknowledged unsubscribe MID={mid} (Reason Code = {result})")
                userdata.on_response(mid, "unsubscribe", client)


# endregion


class MqttClient(mqtt.Client):
    def __init__(self, client_id: str = "", clean_session: bool = None, userdata: MqttHandler = None, protocol: int = mqtt.MQTTv311, transport: str = "tcp", reconnect_on_failure: bool = True):
        super().__init__(
            mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=clean_session, userdata=userdata, protocol=protocol, transport=transport, reconnect_on_failure=reconnect_on_failure
        )
        self.enable_logger(logger)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe
