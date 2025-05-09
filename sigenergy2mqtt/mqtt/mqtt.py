from collections import namedtuple
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from typing import Any, Awaitable, Callable, Dict
import asyncio
import logging
import os
import paho.mqtt.client as mqtt
import time

logger = logging.getLogger("paho.mqtt")
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])


class MqttHandler:
    def __init__(self, modbus: ModbusClient, loop: asyncio.AbstractEventLoop):
        self._discovery_published = False
        self._mids: Dict[Any, MqttResponse] = {}
        self._topics: Dict[str, list[Callable[[mqtt.Client, str], None]]] = {}
        self._modbus = modbus
        self._loop = loop

    @property
    def is_discovery_published(self) -> bool:
        return self._discovery_published

    def discovery_published(self, client: mqtt.Client, source: str) -> None:
        if source == "publish":
            self._discovery_published = True

    def on_message(self, client: mqtt.Client, topic: str, payload: str) -> None:
        if topic in self._topics:
            for method in self._topics[topic]:
                logger.debug(f"MqttHandler handling topic {topic} with {method}")
                asyncio.run_coroutine_threadsafe(method(self._modbus, client, str(payload), topic), self._loop)
        else:
            logger.warning(f"MqttHandler did not find a handler for topic {topic}")

    def on_response(self, mid: Any, source: str, client: mqtt.Client) -> None:
        if mid in self._mids:
            method = self._mids[mid].handler
            logger.debug(f"MqttHandler handling {source} response mid {mid} with {method}")
            method(client, source)
            del self._mids[mid]
        expires = time.time() - 60
        for mid in list(self._mids.keys()):
            if self._mids[mid].now < expires:
                logger.debug(f"MqttHandler removing expired mid {mid}")
                del self._mids[mid]

    def register(self, client: mqtt.Client, topic: str, handler: Callable[[ModbusClient, mqtt.Client, str, str], Awaitable[bool]]) -> None:
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)
        client.subscribe(topic)

    def wait_for(self, info: Any, handler: Callable[[mqtt.Client, str], None]) -> None:
        if info is None:
            self._discovery_published = True
        else:
            mid = info if not isinstance(info, mqtt.MQTTMessageInfo) else info.mid
            self._mids[mid] = MqttResponse(time.time(), handler)
            logger.debug(f"MqttHandler waiting for response mid {mid}")


# region MQTT Client Callbacks


def on_connect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code) -> None:
    if reason_code == 0:
        logger.debug(f"Connected to MQTT broker {Config.mqtt.broker} (port {Config.mqtt.port}) with username {Config.mqtt.username}")
    else:
        match reason_code:
            case 1:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - Unacceptable protocol version")
            case 2:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - Identifier rejected")
            case 3:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - Server unavailable")
            case 4:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - Bad user name or password")
            case 5:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} REFUSED - Username {Config.mqtt.username} not authorised")
            case _:
                logger.critical(f"Connection to MQTT broker {Config.mqtt.broker} FAILED - Reason Code was {reason_code}")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, reason_code) -> None:
    logger.info(f"Disconnected from sigenergy2mqtt.mqttbroker {Config.mqtt.broker} (Reason Code = {reason_code})")


def on_message(client: mqtt.Client, userdata: MqttHandler, message) -> None:
    logger.debug(f"Received message from sigenergy2mqtt.mqttbroker {Config.mqtt.broker} for topic {message.topic}: Payload = {message.payload}")
    userdata.on_message(client, message.topic, str(message.payload, "utf-8"))


def on_publish(client: mqtt.Client, userdata: MqttHandler, mid) -> None:
    logger.debug(f"Acknowledged publish MID={mid}")
    userdata.on_response(mid, "publish", client)


def on_subscribe(client: mqtt.Client, userdata: MqttHandler, mid, granted_qos) -> None:
    logger.debug(f"Acknowledged subscribe MID={mid}")
    userdata.on_response(mid, "subscribe", client)

def on_unsubscribe(client: mqtt.Client, userdata: MqttHandler, mid, reason_code_list, properties):
    userdata.on_response(mid, "unsubscribe", client)

# endregion


class MqttClient(mqtt.Client):
    def __init__(self, client_id: str = "", clean_session: bool = None, userdata: MqttHandler = None, protocol: int = mqtt.MQTTv311, transport: str = "tcp", reconnect_on_failure: bool = True):
        super().__init__(client_id=client_id, clean_session=clean_session, userdata=userdata, protocol=protocol, transport=transport, reconnect_on_failure=reconnect_on_failure)
        self.enable_logger(logger)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe
