__all__ = ["MqttHandler", "mqtt_setup"]

import asyncio
import logging
from time import sleep
from typing import Tuple

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.modbus.types import ModbusClientType

from .client import MqttClient
from .handler import MqttHandler


def mqtt_setup(mqtt_client_id: str, modbus_client: ModbusClientType | None, loop: asyncio.AbstractEventLoop) -> Tuple[MqttClient, MqttHandler]:
    assert mqtt_client_id and not mqtt_client_id.isspace(), "mqtt_client_id must not be None or an empty string"

    logging.debug(f"Creating MQTT Client ID {mqtt_client_id} for mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} over {active_config.mqtt.transport}")

    mqtt_handler = MqttHandler(mqtt_client_id, modbus_client, loop)
    mqtt_client = MqttClient(client_id=mqtt_client_id, userdata=mqtt_handler, transport=active_config.mqtt.transport, tls=active_config.mqtt.tls, tls_insecure=active_config.mqtt.tls_insecure)

    if active_config.mqtt.anonymous:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} anonymously")
    else:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} with username {active_config.mqtt.username}")
        mqtt_client.username_pw_set(active_config.mqtt.username, active_config.mqtt.password)

    connect_attempts: int = 0
    while True:
        connect_attempts += 1
        try:
            mqtt_client.connect(active_config.mqtt.broker, port=active_config.mqtt.port, keepalive=active_config.mqtt.keepalive)
            mqtt_client.loop_start()

            logging.info(f"Connected to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port} as Client ID '{mqtt_client_id}' (keepalive={active_config.mqtt.keepalive}s)")
            return mqtt_client, mqtt_handler
        except Exception as e:
            if connect_attempts < 3:
                logging.error(f"Error connecting to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}: {repr(e)} - Retrying in {active_config.mqtt.retry_delay}s")
                sleep(active_config.mqtt.retry_delay)
            else:
                logging.critical(f"Failed to connect to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}: {repr(e)}")
                raise
