import asyncio
import logging
import time
from random import uniform
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt
from pymodbus import ModbusException

from sigenergy2mqtt.common import Constants
from sigenergy2mqtt.modbus import ModbusClient, ModbusLock, ModbusLockFactory
from sigenergy2mqtt.sensors.base import EnergyDailyAccumulationSensor, ModbusSensorMixin, ReadableSensorMixin, Sensor

from .scan_groups import ReadableSensorGroup

if TYPE_CHECKING:
    from .device import Device

# Constants for reconnection strategy
MAX_RECONNECTION_ATTEMPTS = 10
INITIAL_RECONNECT_DELAY = 0.5
MAX_RECONNECT_DELAY = 60.0
RECONNECT_BACKOFF_MULTIPLIER = 2.0


class SensorGroupPoller:
    """Drives the runtime polling loop for a single sensor scan group.

    Encapsulates all scheduling, read-ahead optimisation, Modbus reconnection,
    and sleep logic that was previously spread across several private methods of
    Device. One SensorGroupPoller instance is created per scan group by
    Device.schedule(), which then awaits poller.run() as an asyncio Task.

    Args:
        device: The Device that owns this poller. Used for lifecycle state
                (online, shutdown_event), logging context (name), and the
                post-publish rediscover hook.
    """

    def __init__(self, device: "Device") -> None:
        self._device = device

    async def _init_next_publish_times(
        self,
        modbus_client: ModbusClient | None,
        mqtt_client: mqtt.Client,
        *sensors: Sensor,
    ) -> tuple[dict[ReadableSensorMixin, float], list[ReadableSensorMixin], bool]:
        """Initialise per-sensor scheduling state for a new publish_updates loop.

        For each readable sensor, assigns a staggered initial publish time to spread
        load across the first few seconds. Publishes the current cached state
        immediately for any sensor that already has a value. Identifies sensors with
        EnergyDailyAccumulationSensor derived sensors so they can be force-published
        on day change. Determines whether debug logging should be enabled for the
        group.

        Args:
            modbus_client: The Modbus client, passed through to initial publish calls.
            mqtt_client:   The MQTT client, passed through to initial publish calls.
            *sensors:      All sensors in the scan group.

        Returns:
            A tuple of:
            - next_publish_times: dict mapping each ReadableSensorMixin to its next
              scheduled publish timestamp.
            - daily_sensors: list of sensors with EnergyDailyAccumulationSensor
              derived sensors that need special day-rollover handling.
            - debug_logging: True if any sensor in the group has debug logging enabled.
        """
        debug_logging: bool = False
        daily_sensors: list[ReadableSensorMixin] = []
        next_publish_times: dict[ReadableSensorMixin, float] = {}
        now = time.time()
        # Compute a single group-level jitter so that all sensors in the group become
        # due at the same time. Per-sensor jitter would permanently stagger sensors
        # within the group, causing each to be published in a separate loop iteration
        # and defeating the read-ahead optimisation entirely.
        readable_sensors = [s for s in sensors if isinstance(s, ReadableSensorMixin)]
        group_jitter = uniform(0.5, min(5, min((s.scan_interval for s in readable_sensors), default=5))) if readable_sensors else 0.0
        for sensor in sensors:
            debug_logging = debug_logging or sensor.debug_logging or any(ds.debug_logging for ds in sensor.derived_sensors.values())
            if isinstance(sensor, ReadableSensorMixin):
                # Track sensors with EnergyDailyAccumulationSensor derived sensors
                if any(isinstance(ds, EnergyDailyAccumulationSensor) for ds in sensor.derived_sensors.values()):
                    daily_sensors.append(sensor)
                # Initialize all sensors in the group with the same start time so they
                # remain phase-aligned and are always published together in one iteration.
                next_publish_times[sensor] = now + group_jitter
                # Publish initial state if available
                if sensor.publishable and sensor.latest_raw_state is not None:
                    await sensor.publish(mqtt_client, modbus_client, republish=True)
        return next_publish_times, daily_sensors, debug_logging

    def _get_sensors_to_publish_now(
        self,
        next_publish_times: dict[ReadableSensorMixin, float],
        now: float,
        name: str,
        debug_logging: bool,
    ) -> list[ReadableSensorMixin]:
        """Return the subset of sensors that are due for publishing on this iteration.

        A sensor is due if its force_publish flag is set, or if its scheduled next
        publish time is at or before now. Sensors that are not publishable are always
        skipped.

        Args:
            next_publish_times: Mapping of sensor to next scheduled publish timestamp.
            now:                Current timestamp from time.time().
            name:               Scan group name, used in debug log messages.
            debug_logging:      Whether to emit debug logs for force_publish events.

        Returns:
            List of sensors due for publishing on this iteration.
        """
        due_sensors: list[ReadableSensorMixin] = []
        for sensor, next_time in next_publish_times.items():
            if not sensor.publishable:
                continue
            if sensor.force_publish:
                if debug_logging:
                    logging.debug(f"{self._device.log_identity} Sensor Scan Group [{name}] force_publish set on {sensor.__class__.__name__}")
                due_sensors.append(sensor)
            elif next_time <= now:
                due_sensors.append(sensor)
        return due_sensors

    async def _publish_read_ahead(
        self,
        due_sensors: list[ReadableSensorMixin],
        modbus_client: ModbusClient,
        modbus_sensors: ReadableSensorGroup,
        modbus_lock: ModbusLock,
        name: str,
        debug_logging: bool,
    ) -> bool:
        """Perform a single bulk Modbus register read covering all due Modbus sensors.

        Acquires the Modbus lock and calls read_ahead_registers() to pre-populate
        the client's read cache for the entire address range of the group. Individual
        sensor publish() calls issued after this will hit the cache rather than
        generating separate wire requests.

        If exception code 2 (ILLEGAL DATA ADDRESS) is returned, read-ahead is
        permanently disabled for this group by returning False. Other non-zero
        exception codes are logged as warnings but read-ahead remains enabled.

        If no due sensors are Modbus sensors, the read-ahead is skipped and the
        current enabled state is preserved.

        Args:
            due_sensors:    Sensors due for publishing on this iteration.
            modbus_client:  The Modbus client to perform the read against.
            modbus_sensors: The ReadableSensorGroup holding address range metadata.
            modbus_lock:    The lock serialising access to the Modbus client.
            name:           Scan group name, used in log messages.
            debug_logging:  Whether to emit timing debug logs.

        Returns:
            True if read-ahead should remain enabled for future iterations,
            False if it should be permanently disabled (ILLEGAL DATA ADDRESS).
        """
        read_ahead_enabled = True  # Must be currently enabled, otherwise should not have been called (multiple == True in calling method)
        due_modbus = [s for s in due_sensors if isinstance(s, ModbusSensorMixin)]
        if due_modbus:
            debug_read_ahead = any(s.debug_logging for s in due_modbus)
            async with modbus_lock.lock():
                read_ahead_start = 0.0
                if debug_logging:
                    read_ahead_start = time.time()
                exception_code = await modbus_client.read_ahead_registers(
                    modbus_sensors.first_address, count=modbus_sensors.register_count, device_id=modbus_sensors.device_address, input_type=modbus_sensors.input_type, trace=debug_read_ahead
                )
                if exception_code == 0:
                    if debug_read_ahead:
                        logging.debug(
                            f"{self._device.log_identity} Sensor Scan Group [{name}] pre-read {modbus_sensors.first_address} to {modbus_sensors.last_address} ({modbus_sensors.register_count} registers) took {time.time() - read_ahead_start:.2f}s"
                        )
                else:
                    match exception_code:
                        case -1:
                            reason = "NO RESPONSE FROM DEVICE"
                        case 1:
                            reason = "0x01 ILLEGAL FUNCTION"
                        case 2:
                            reason = "0x02 ILLEGAL DATA ADDRESS (pre-reads now disabled)"
                            read_ahead_enabled = False
                        case 3:
                            reason = "0x03 ILLEGAL DATA VALUE"
                        case 4:
                            reason = "0x04 SLAVE DEVICE FAILURE"
                        case _:
                            reason = f"UNKNOWN PROBLEM ({exception_code=})"
                    logging.warning(
                        f"{self._device.log_identity} Sensor Scan Group [{name}] failed to pre-read {modbus_sensors.first_address} to {modbus_sensors.last_address} ({modbus_sensors.register_count} registers) - {reason}"
                    )
        return read_ahead_enabled

    async def _reconnect_modbus_with_backoff(self, modbus_client: ModbusClient) -> bool:
        """Attempt to reconnect to the Modbus server using exponential backoff.

        Makes up to MAX_RECONNECTION_ATTEMPTS connection attempts. The delay between
        attempts starts at INITIAL_RECONNECT_DELAY and doubles after each failure,
        capped at MAX_RECONNECT_DELAY. Returns immediately on success or if the
        device goes offline during reconnection.

        This method is called while holding the Modbus lock, which prevents
        concurrent reconnection attempts from other sensor group tasks on the
        same plant.

        Args:
            modbus_client: The Modbus client to reconnect.

        Returns:
            True if the connection was re-established, False if all attempts were
            exhausted or the device went offline during reconnection.
        """
        attempt = 0
        delay = INITIAL_RECONNECT_DELAY

        logging.info(f"{self._device.log_identity} attempting to reconnect to Modbus...")

        while attempt < MAX_RECONNECTION_ATTEMPTS and self._device.online:
            attempt += 1
            try:
                modbus_client.close()
                logging.debug(f"{self._device.log_identity} Modbus reconnection attempt {attempt}/{MAX_RECONNECTION_ATTEMPTS}")
                await modbus_client.connect()
                if modbus_client.connected:
                    logging.info(f"{self._device.log_identity} successfully reconnected to Modbus on attempt {attempt}")
                    return True
            except asyncio.CancelledError:
                logging.debug(f"{self._device.log_identity} Modbus reconnection cancelled")
                return False
            except Exception as e:
                logging.warning(f"{self._device.log_identity} Modbus reconnection attempt {attempt} failed: {repr(e)}")

            # Exponential backoff with cap
            if attempt < MAX_RECONNECTION_ATTEMPTS and self._device.online:
                sleep_time = min(delay, MAX_RECONNECT_DELAY)
                logging.debug(f"{self._device.log_identity} waiting {sleep_time:.1f}s before next reconnection attempt")
                try:
                    await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    logging.debug(f"{self._device.log_identity} Modbus reconnection backoff cancelled")
                    return False
                delay *= RECONNECT_BACKOFF_MULTIPLIER

        if attempt >= MAX_RECONNECTION_ATTEMPTS:
            logging.error(f"{self._device.log_identity} failed to reconnect to Modbus after {MAX_RECONNECTION_ATTEMPTS} attempts")

        return False

    async def run(self, modbus_client: ModbusClient | None, mqtt_client: mqtt.Client, name: str, *sensors: Sensor) -> None:
        """Main sensor polling loop for a single scan group.

        Runs continuously while the device is online and the shutdown event is not
        set. On each iteration:
        1. Checks for a day change and forces immediate republish of any sensors
           with EnergyDailyAccumulationSensor derived sensors.
        2. Determines which sensors are due (by scheduled time or force_publish flag).
        3. If multiple Modbus sensors are due and read-ahead is enabled, performs a
           single bulk register read via _publish_read_ahead to pre-populate the
           Modbus client's read cache.
        4. Publishes each due sensor and schedules its next publish time.
        5. If rediscover is set on the device, republishes discovery.
        6. On ModbusException, acquires the Modbus lock and attempts reconnection
           via _reconnect_modbus_with_backoff (lock is held for the duration to
           prevent concurrent reconnection attempts from sibling tasks).
        7. Sleeps until the next sensor is due, up to a maximum of 1 second to
           remain responsive to shutdown signals.

        Args:
            modbus_client: The Modbus client for register reads, or None for
                           non-Modbus devices.
            mqtt_client:   The MQTT client for publishing sensor state.
            name:          The scan group name, used in log messages.
            *sensors:      The sensors belonging to this scan group.
        """
        device = self._device

        # Setup for Modbus read-ahead optimization
        modbus_sensors: ReadableSensorGroup = ReadableSensorGroup(*[s for s in sensors if isinstance(s, ModbusSensorMixin)])
        multiple: bool = len(modbus_sensors) > 1 and modbus_sensors.register_count != -1 and 1 <= modbus_sensors.register_count <= Constants.MAX_MODBUS_REGISTERS_PER_REQUEST

        # Initialize per-sensor next publish times, find any daily sensors, and determine if debug logging is needed for this group
        next_publish_times, daily_sensors, debug_logging = await self._init_next_publish_times(modbus_client, mqtt_client, *sensors)

        if debug_logging:
            logging.debug(
                f"{device.log_identity} Sensor Scan Group [{name}] instantiated (multiple={multiple} first_address={modbus_sensors.first_address} last_address={modbus_sensors.last_address} count={modbus_sensors.register_count} sensors={len(sensors)} daily_sensors={len(daily_sensors)})"
            )

        lock = ModbusLockFactory.get(modbus_client)
        last_day = time.localtime(time.time()).tm_yday

        # Main publishing loop - respects shutdown event
        while device.online and not device._shutdown_event.is_set():
            now = time.time()

            # Check for day change (affects daily sensors)
            now_struct = time.localtime(now)
            day_changed = now_struct.tm_yday != last_day
            if day_changed:
                last_day = now_struct.tm_yday
                for sensor in daily_sensors:
                    if sensor.publishable:
                        next_publish_times[sensor] = now  # Force immediate publish
                        if debug_logging:
                            logging.debug(f"{device.log_identity} Sensor Scan Group [{name}] day changed, forcing {sensor.__class__.__name__} to publish")

            # Determine which sensors are due for publishing
            due_sensors: list[ReadableSensorMixin] = self._get_sensors_to_publish_now(next_publish_times, now, name, debug_logging)

            if due_sensors:
                try:
                    if multiple and modbus_client:
                        multiple = await self._publish_read_ahead(due_sensors, modbus_client, modbus_sensors, lock, name, debug_logging)

                    # Publish each due sensor and update its next publish time
                    for sensor in due_sensors:
                        await sensor.publish(mqtt_client, modbus_client)
                        next_publish_times[sensor] = now + sensor.scan_interval
                        sensor.force_publish = False

                    if device.rediscover:
                        device.rediscover = False
                        device.publish_discovery(mqtt_client, clean=False)

                except ModbusException as e:
                    if modbus_client:
                        logging.debug(f"{device.log_identity} Sensor Scan Group [{name}] handling {e!s}: Acquiring lock before attempting to reconnect... ({lock.waiters=})")
                        async with lock.lock(timeout=None):
                            if not modbus_client.connected and device.online:
                                # Retain lock while attempting to reconnect to prevent multiple concurrent reconnection attempts from other tasks
                                reconnected = await self._reconnect_modbus_with_backoff(modbus_client)
                                if not reconnected and device.online:
                                    logging.error(f"{device.log_identity} failed to reconnect to Modbus, sensor updates paused")
                except Exception as e:
                    logging.error(f"{device.log_identity} Sensor Scan Group [{name}] encountered an error: {repr(e)}")

            # Sleep until the next sensor is due (max 1 second to stay responsive to shutdown)
            if next_publish_times:
                next_due = min(next_publish_times.values())
                sleep_duration = max(0.1, min(next_due - time.time(), 1))
            else:
                sleep_duration = 1

            if sleep_duration > 0:
                task = asyncio.create_task(asyncio.sleep(sleep_duration))
                for sensor in sensors:
                    sensor.sleeper_task = task
                try:
                    await task
                except asyncio.CancelledError:
                    if debug_logging:
                        logging.debug(f"{device.log_identity} Sensor Scan Group [{name}] sleep interrupted")
                finally:
                    for sensor in sensors:
                        sensor.sleeper_task = None

        if debug_logging:
            logging.debug(f"{device.log_identity} Sensor Scan Group [{name}] completed - {device.log_identity} completed - flagged as offline ({device.online=})")
