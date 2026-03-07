"""
device_thread.py — per-device Modbus polling and MQTT publishing threads.

Each device connection runs in its own OS thread with a dedicated asyncio
event loop.  :func:`start` coordinates all threads and propagates the first
crash to the others via a shared :class:`threading.Event`.
"""

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any, Awaitable

from sigenergy2mqtt.config import active_config
from sigenergy2mqtt.devices import Device
from sigenergy2mqtt.modbus import ModbusClient, ModbusClientFactory
from sigenergy2mqtt.mqtt import mqtt_setup

from .thread_config import ThreadConfig


async def read_and_publish_device_sensors(
    config: ThreadConfig,
    loop: asyncio.AbstractEventLoop,
    stop_event: threading.Event | None = None,
) -> None:
    """Connect to a Modbus host, register all devices, and run their polling tasks.

    For each device in *config* this coroutine will:

    * Publish Home Assistant discovery (or plain attribute) payloads via MQTT.
    * Register MQTT command subscriptions.
    * Schedule the device's asyncio polling tasks.

    Once all tasks are gathered they run until cancelled or an error occurs.
    Commencement and completion hooks are called on each device around the
    task lifetime.  Modbus and MQTT connections are always closed in a
    ``finally`` block, regardless of how the coroutine exits.

    Args:
        config:     Thread-level configuration describing the host, port,
                    devices, and associated metadata.
        loop:       The asyncio event loop running in the current thread.
                    Passed to the MQTT handler so callbacks can schedule
                    coroutines safely from non-async contexts.
        stop_event: Optional shared event used to signal sibling threads that
                    this thread has crashed.  Set by
                    :func:`run_modbus_event_loop` on exception; ignored here.
    """
    threading.current_thread().name = f"{config.description}Thread"

    # Human-readable label used in log messages — fall back to description
    # when host is absent (e.g. clean/discovery-only runs).
    url_label = config.url if config.host is not None else config.description

    modbus_client: ModbusClient | None = None
    tasks: list[Awaitable[Any]] = []

    if config.host is not None and not active_config.clean:
        modbus_client = await ModbusClientFactory.get_client(
            config.host,
            config.port if config.port else 502,
            config.timeout,
            config.retries,
        )

    mqtt_client_id = f"{active_config.mqtt.client_id_prefix}_{config.description}"
    mqtt_client, mqtt_handler = await mqtt_setup(mqtt_client_id, modbus_client, loop)

    try:
        device: Device
        for device in config.devices:
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
                tasks.extend(device.schedule(modbus_client, mqtt_client))

        if tasks:
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

            # asyncio.gather(..., return_exceptions=True) never raises; instead
            # exceptions appear as result values.  Log each one explicitly so
            # they are not silently discarded.
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
            logging.info(f"Closing Modbus connection to {url_label}")
            ModbusClientFactory.remove(modbus_client)

        logging.info(f"Deregistering and unsubscribing MQTT handlers for Client ID {mqtt_client_id} to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}")
        mqtt_handler.deregister_all(mqtt_client)
        logging.info(f"Closing MQTT connection for Client ID {mqtt_client_id} to mqtt://{active_config.mqtt.broker}:{active_config.mqtt.port}")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        await mqtt_handler.close()


def run_modbus_event_loop(
    config: ThreadConfig,
    loop: asyncio.AbstractEventLoop,
    stop_event: threading.Event | None = None,
) -> None:
    """Run :func:`read_and_publish_device_sensors` on *loop* in the current thread.

    This is the thread entry-point submitted to the
    :class:`~concurrent.futures.ThreadPoolExecutor`.  It installs *loop* as
    the current thread's event loop, drives it to completion, and ensures the
    loop is closed on exit.

    If the coroutine raises an unexpected exception the error is logged and
    *stop_event* is set so that :func:`start` can initiate an orderly shutdown
    of sibling threads.

    Args:
        config:     Thread-level configuration for this device connection.
        loop:       A freshly created event loop dedicated to this thread.
        stop_event: Optional shared event.  Set on unhandled exception to
                    signal :func:`start` that this thread has crashed.
    """
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(read_and_publish_device_sensors(config, loop, stop_event))
    except Exception:
        logging.exception(f"{config.description} thread crashed !!!")
        if stop_event is not None:
            stop_event.set()
    finally:
        loop.close()


async def start(configs: list[ThreadConfig]) -> None:
    """Launch one thread per :class:`ThreadConfig` and wait for all to finish.

    Each thread runs its own asyncio event loop via
    :func:`run_modbus_event_loop`.  A shared :class:`threading.Event`
    (``stop_event``) allows any crashing thread to signal the others.

    The wait loop polls every second so that a ``KeyboardInterrupt`` on the
    main thread is not blocked indefinitely.

    .. note::
        When a crash is detected, :meth:`ThreadConfig.offline` is called on
        every config to signal their running coroutines to stop cooperatively,
        then :func:`start` waits for all threads to finish naturally.

    Args:
        configs: One :class:`ThreadConfig` per Modbus host / device group to
                 poll concurrently.
    """
    stop_event = threading.Event()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(configs)) as executor:
        executions: list[concurrent.futures.Future] = [executor.submit(run_modbus_event_loop, config, asyncio.new_event_loop(), stop_event) for config in configs]

        # Poll with a short timeout so KeyboardInterrupt and stop_event are
        # both handled promptly rather than blocking until all threads finish.
        while True:
            done, pending = concurrent.futures.wait(executions, timeout=1.0)

            if stop_event.is_set() and pending:
                logging.warning("A thread crashed — cancelling remaining threads")
                for config in configs:
                    config.offline()
                concurrent.futures.wait(pending)
                done = done | pending  # Ensure pending results are also inspected below
                break

            if not pending:
                break

        for fut in done:
            try:
                fut.result()
            except Exception:
                logging.exception("Unhandled exception in device thread")
