import logging
import os
import ssl
from collections import namedtuple
from typing import Literal

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .handler import MqttHandler

logger = logging.getLogger("paho.mqtt")
MqttResponse = namedtuple("MqttResponse", ["now", "handler"])


class MqttClient(mqtt.Client):
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
            self.tls_insecure_set(tls_insecure)

        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_publish = on_publish
        self.on_subscribe = on_subscribe
        self.on_unsubscribe = on_unsubscribe


def on_connect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    if reason_code == 0:
        logger.debug(f"Connected to mqtt://{client.host}:{client.port} with username {client.username} (client_id={userdata.client_id})")
        userdata.on_reconnect(client)
    else:
        logger.critical(f"Connection to mqtt://{client.host}:{client.port} REFUSED - {reason_code} (client_id={userdata.client_id})")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: MqttHandler, flags, reason_code, properties) -> None:
    userdata.connected = False
    logger.info(f"Disconnected from mqtt://{client.host}:{client.port} - {reason_code} (client_id={userdata.client_id})")


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
