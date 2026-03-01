import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Awaitable

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClientFactory
from sigenergy2mqtt.modbus.types import ModbusClientType
from sigenergy2mqtt.mqtt import mqtt_setup

from .thread_config import ThreadConfig

# NOTE: This file must not be named 'threading.py' as it shadows the Python
# stdlib 'threading' module, causing an ImportError. Rename to e.g.
# 'device_thread.py' and update all imports accordingly.


async def read_and_publish_device_sensors(config: ThreadConfig, loop: asyncio.AbstractEventLoop, stop_event: threading.Event | None = None) -> None:
    threading.current_thread().name = f"{config.description}Thread"

    modbus_client: ModbusClientType | None = None
    tasks: list[Awaitable[Any]] = []
    gathered_tasks: asyncio.Future | None = None

    if config.host is not None and not active_config.clean:
        modbus_client = await ModbusClientFactory.get_client(config.host, config.port if config.port else 502, config.timeout, config.retries)

    mqtt_client_id = f"{active_config.mqtt.client_id_prefix}_{config.description}"
    mqtt_client, mqtt_handler = mqtt_setup(mqtt_client_id, modbus_client, loop)

    try:
        device: Device
        for device in config.device_init:
            method = device.publish_discovery if active_config.home_assistant.enabled else device.publish_attributes

            await mqtt_handler.wait_for(5, device.name, method, mqtt_client, clean=active_config.clean)

            if active_config.home_assistant.enabled and (active_config.clean or active_config.home_assistant.discovery_only):
                logging.info(f"{device.name} configured for {'clean' if active_config.clean else 'discovery'} only - shutting down...")
            else:
                logging.debug(f"{device.name} registering MQTT subscriptions")
                device.subscribe(mqtt_client, mqtt_handler)

                if active_config.home_assistant.enabled:
                    device.publish_availability(mqtt_client, "online")

                logging.debug(f"{device.name} scheduling tasks")
                device_tasks = device.schedule(modbus_client, mqtt_client)
                tasks.extend(device_tasks)

        if tasks:
            url_label = config.url if config.host is not None else config.description
            task_word = "task" if len(tasks) == 1 else "tasks"
            logging.info(f"{url_label} scheduled tasks commenced ({len(tasks)} asyncio {task_word} scheduled)")

            gathered_tasks = asyncio.gather(*tasks, return_exceptions=True)
            config.online(gathered_tasks)

            for device in config.devices:
                try:
                    device.on_commencement(modbus_client, mqtt_client)
                except Exception:
                    logging.exception(f"{device.name} on commencement failed")

            try:
                results = await gathered_tasks
            except asyncio.CancelledError:
                logging.info(f"{url_label} scheduled tasks interrupted")
                results = []

            # Surface any exceptions that were swallowed by return_exceptions=True
            for result in results:
                if isinstance(result, BaseException):
                    logging.exception(
                        f"{url_label} a scheduled task raised an exception",
                        exc_info=result,
                    )

            for device in config.devices:
                try:
                    device.on_completion(modbus_client, mqtt_client)
                except Exception:
                    logging.exception(f"{device.name} on completion failed")
                if active_config.home_assistant.enabled:
                    device.publish_availability(mqtt_client, "offline")

    finally:
        if modbus_client is not None:
            url_label = config.url if config.host is not None else config.description
            logging.info(f"Closing Modbus connection to {url_label}")
            modbus_client.close()

        logging.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        await mqtt_handler.close()


def run_modbus_event_loop(config: ThreadConfig, loop: asyncio.AbstractEventLoop, stop_event: threading.Event | None = None) -> None:
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(read_and_publish_device_sensors(config, loop, stop_event))
    except Exception:
        logging.exception(f"{config.description} thread crashed !!!")
        if stop_event is not None:
            stop_event.set()  # Signal other threads to stop on any crash
    finally:
        loop.close()


async def start(configs: list[ThreadConfig]) -> None:
    stop_event = threading.Event()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
        executions: list[concurrent.futures.Future] = [executor.submit(run_modbus_event_loop, config, asyncio.new_event_loop(), stop_event) for config in configs]

        # Poll with a timeout so KeyboardInterrupt and stop_event are both handled
        while True:
            done, pending = concurrent.futures.wait(executions, timeout=1.0)

            if stop_event.is_set() and pending:
                logging.warning("A thread crashed — cancelling remaining threads")
                # Loops are owned by each thread; signal via the event and
                # cancel each loop's running coroutine from within the thread.
                for fut in pending:
                    fut.cancel()
                concurrent.futures.wait(pending)
                break

            if not pending:
                break

        for fut in done:
            try:
                fut.result()
            except Exception:
                logging.exception("Unhandled exception in device thread")
