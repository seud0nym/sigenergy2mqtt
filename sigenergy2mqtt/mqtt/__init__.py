__all__ = ["MqttClient", "MqttHandler", "mqtt_setup"]

from .mqtt import MqttClient, MqttHandler
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from time import sleep
from typing import Tuple
import asyncio
import logging


def mqtt_setup(mqtt_client_id: str, modbus: ModbusClient, loop: asyncio.AbstractEventLoop) -> Tuple[MqttClient, MqttHandler]:
    assert mqtt_client_id and not mqtt_client_id.isspace(), "mqtt_client_id must not be None or an empty string"

    logging.debug(f"Creating MQTT Client ID {mqtt_client_id} for mqtt://{Config.mqtt.broker}:{Config.mqtt.port}")

    mqtt_handler = MqttHandler(mqtt_client_id, modbus, loop)
    mqtt_client = MqttClient(client_id=mqtt_client_id, userdata=mqtt_handler)

    if Config.mqtt.anonymous:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} anonymously")
    else:
        logging.debug(f"MQTT Client ID {mqtt_client_id} connecting to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} with username {Config.mqtt.username}")
        mqtt_client.username_pw_set(Config.mqtt.username, Config.mqtt.password)

    connect_attempts: int = 0
    while True:
        connect_attempts += 1
        try:
            mqtt_client.connect(Config.mqtt.broker, port=Config.mqtt.port)
            mqtt_client.loop_start()

            logging.info(f"Connected to mqtt://{Config.mqtt.broker}:{Config.mqtt.port} as Client ID '{mqtt_client_id}'")
            return mqtt_client, mqtt_handler
        except Exception as e:
            if connect_attempts < 3:
                logging.error(f"Error connecting to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}: {repr(e)} - Retrying in 30s")
                sleep(30)
            else:
                logging.critical(f"Failed to connect to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}: {repr(e)}")
                raise