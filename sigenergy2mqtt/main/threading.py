from .host_config import HostConfig
from pymodbus.client import AsyncModbusTcpClient as ModbusClient
from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.modbus import ClientFactory
from sigenergy2mqtt.mqtt import MqttClient, mqtt_setup
from sigenergy2mqtt.sensors.base import Sensor
from typing import Awaitable, Callable, Iterable, List
import asyncio
import concurrent.futures
import logging
import time
import uuid

async def read_and_publish_device_sensors(config: HostConfig, loop: asyncio.AbstractEventLoop):
    device: Device = None
    modbus_client: ModbusClient = None
    tasks: List[Callable[[ModbusClient, MqttClient, Iterable[Sensor]], Awaitable[None]]] = []

    if config.host is None or Config.clean:
        modbus_client = None
    else:
        modbus_client = await ClientFactory.get_client(config.host, config.port)
    mqtt_client_id = f"sigenergy2mqtt_{uuid.uuid4()}_{config.description}"

    mqtt_client, mqtt_handler = mqtt_setup(mqtt_client_id, loop)

    for device in config.devices:
        if Config.home_assistant.enabled:
            mid = device.publish_discovery(mqtt_client)
            mqtt_handler.wait_for(mid, mqtt_handler.discovery_published)
            until = time.perf_counter() + 30
            while not mqtt_handler.is_discovery_published:
                logging.debug(f"Waiting for '{device.name}' discovery to be acknowledged (mid={mid})")
                await asyncio.sleep(0.5)
                now = time.perf_counter()
                if now >= until:
                    logging.warning(f"No acknowledgement of '{device.name}' discovery received??")
                    break

        if Config.home_assistant.enabled and Config.home_assistant.discovery_only:
            logging.info(f"Configured for discovery only - shutting down '{device.name}'...")
        else:
            logging.info(f"Registering MQTT subscriptions for '{device.name}'")
            device.subscribe(mqtt_client, mqtt_handler)

            if Config.home_assistant.enabled:
                logging.info(f"Publishing online availability for '{device.name}'")
                device.publish_availability(mqtt_client, "online")

            logging.info(f"Scheduling '{device.name}' sensor updates")
            device_tasks = device.schedule(modbus_client, mqtt_client)
            tasks.extend(device_tasks)

    if len(tasks) > 0:
        logging.info(f"Sensor updates for {config.description} commenced")
        result = asyncio.gather(*tasks, return_exceptions=True)
        config.online(result)
        try:
            await result
        except asyncio.CancelledError:
            logging.info(f"Sensor updates for {config.description} interrupted")

        if Config.home_assistant.enabled:
            for device in config.devices:
                logging.info(f"Publishing offline availability for '{device.name}'")
                device.publish_availability(mqtt_client, "offline")

    if modbus_client is not None:
        logging.info(f"Closing Modbus connection to {config.description}")
        modbus_client.close()
    logging.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to broker {Config.mqtt.broker}:{Config.mqtt.port}")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    return


def run_modbus_event_loop(device: HostConfig, loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(read_and_publish_device_sensors(device, loop))


async def start(configs: list[HostConfig]):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
        executions: list[concurrent.futures.Future] = []
        for config in configs:
            executions.append(executor.submit(run_modbus_event_loop, config, asyncio.new_event_loop()))
        concurrent.futures.wait(executions)
