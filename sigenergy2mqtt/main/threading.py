from .thread_config import ThreadConfig
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.mqtt import MqttClient, mqtt_setup
from sigenergy2mqtt.sensors.base import Sensor
from typing import Awaitable, Callable, Iterable, List
import asyncio
import concurrent.futures
import logging
import secrets
import string
import threading


async def read_and_publish_device_sensors(config: ThreadConfig, loop: asyncio.AbstractEventLoop):
    threading.current_thread().name = f"{config.description}Thread"

    device: Device = None
    modbus_client: ModbusClient = None
    tasks: List[Callable[[ModbusClient, MqttClient, Iterable[Sensor]], Awaitable[None]]] = []

    if config.host is None or Config.clean:
        modbus_client = None
    else:
        modbus_client = await ModbusClientFactory.get_client(config.host, config.port)
    mqtt_client_id = f"sigenergy2mqtt_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))}_{config.description}"

    mqtt_client, mqtt_handler = mqtt_setup(mqtt_client_id, modbus_client, loop)

    for device in config.devices:
        if Config.home_assistant.enabled:
            await mqtt_handler.wait_for(5, device.name, device.publish_discovery, mqtt_client, clean=False)

        if Config.home_assistant.enabled and (Config.clean or Config.home_assistant.discovery_only):
            logging.info(f"{device.name} - Configured for {'clean' if Config.clean else 'discovery'} only - shutting down...")
        else:
            logging.debug(f"{device.name} - Registering MQTT subscriptions")
            device.subscribe(mqtt_client, mqtt_handler)

            if Config.home_assistant.enabled:
                logging.debug(f"{device.name} - Publishing online availability")
                device.publish_availability(mqtt_client, "online")

            logging.debug(f"{device.name} - Scheduling sensor updates")
            device_tasks = device.schedule(modbus_client, mqtt_client)
            tasks.extend(device_tasks)

    if len(tasks) > 0:
        logging.info(f"{config.description} - Sensor updates commenced ({len(tasks)} asyncio {'task' if len(tasks) == 1 else 'tasks'} scheduled)")
        result = asyncio.gather(*tasks, return_exceptions=True)
        config.online(result)
        try:
            await result
        except asyncio.CancelledError:
            logging.info(f"{config.description} - Sensor updates interrupted")

        if Config.home_assistant.enabled:
            for device in config.devices:
                logging.info(f"{device.name} - Publishing offline availability")
                device.publish_availability(mqtt_client, "offline")

    if modbus_client is not None:
        logging.info(f"Closing Modbus connection to {config.description}")
        modbus_client.close()
    logging.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    return


def run_modbus_event_loop(device: ThreadConfig, loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_and_publish_device_sensors(device, loop))


async def start(configs: list[ThreadConfig]):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
        executions: list[concurrent.futures.Future] = []
        for config in configs:
            executions.append(executor.submit(run_modbus_event_loop, config, asyncio.new_event_loop()))
        concurrent.futures.wait(executions)
