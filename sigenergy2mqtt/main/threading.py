import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Awaitable

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.devices.device import Device
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.mqtt import mqtt_setup

from .thread_config import ThreadConfig


async def read_and_publish_device_sensors(config: ThreadConfig, loop: asyncio.AbstractEventLoop):
    threading.current_thread().name = f"{config.description}Thread"

    device: Device
    modbus_client: ModbusClientType | None = None
    tasks: list[Awaitable[Any]] = []

    if config.host is None or Config.clean:
        modbus_client = None
    else:
        modbus_client = await ModbusClientFactory.get_client(config.host, config.port if config.port else 502, config.timeout, config.retries)

    mqtt_client_id = f"{Config.mqtt.client_id_prefix}_{config.description}"
    mqtt_client, mqtt_handler = mqtt_setup(mqtt_client_id, modbus_client, loop)

    for device in config.device_init:
        method = device.publish_discovery if Config.home_assistant.enabled else device.publish_attributes
        if Config.clean:
            await mqtt_handler.wait_for(5, device.name, method, mqtt_client, clean=True)
        if not Config.clean:  # Publish HA device
            await mqtt_handler.wait_for(5, device.name, method, mqtt_client, clean=False)

        if Config.home_assistant.enabled and (Config.clean or Config.home_assistant.discovery_only):
            logging.info(f"{device.name} configured for {'clean' if Config.clean else 'discovery'} only - shutting down...")
        else:
            logging.debug(f"{device.name} registering MQTT subscriptions")
            device.subscribe(mqtt_client, mqtt_handler)

            if Config.home_assistant.enabled:
                logging.debug(f"{device.name} publishing online availability")
                device.publish_availability(mqtt_client, "online")

            logging.debug(f"{device.name} scheduling tasks")
            device_tasks = device.schedule(modbus_client, mqtt_client)
            tasks.extend(device_tasks)

    if len(tasks) > 0:
        logging.info(f"{config.url} scheduled tasks commenced ({len(tasks)} asyncio {'task' if len(tasks) == 1 else 'tasks'} scheduled)")
        result = asyncio.gather(*tasks, return_exceptions=True)
        config.online(result)
        try:
            await result
        except asyncio.CancelledError:
            logging.info(f"{config.url} scheduled tasks interrupted")

        if Config.home_assistant.enabled:
            for device in config.devices:
                logging.info(f"{device.name} publishing offline availability")
                device.publish_availability(mqtt_client, "offline")

    if modbus_client is not None:
        logging.info(f"Closing Modbus connection to {config.url}")
        modbus_client.close()

    logging.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to mqtt://{Config.mqtt.broker}:{Config.mqtt.port}")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    await mqtt_handler.close()

    return


def run_modbus_event_loop(device: ThreadConfig, loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(read_and_publish_device_sensors(device, loop))
    except Exception:
        logging.exception(f"{device.description} thread crashed !!!")
    finally:
        loop.close()


async def start(configs: list[ThreadConfig]):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
        executions: list[concurrent.futures.Future] = []
        for config in configs:
            executions.append(executor.submit(run_modbus_event_loop, config, asyncio.new_event_loop()))
        done, pending = concurrent.futures.wait(executions)
        for fut in done:
            try:
                fut.result()  # <-- exception re-raised here
            except Exception:
                logging.exception("Unhandled exception")
