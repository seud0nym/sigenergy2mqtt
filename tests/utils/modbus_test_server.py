"""Async Modbus TCP test server for sigenergy2mqtt integration testing.

This module starts a pymodbus TCP server that simulates a Sigenergy device.
It pre-populates register values either from a live Modbus source (when a
``.debug_modbus_server.yaml`` config file is present) or from synthesised
random values that fall within each sensor's declared valid range.

When an MQTT broker is configured, the server also subscribes to each sensor's
state topic so that register values track live MQTT updates from a real
installation, enabling mixed live/synthetic test scenarios.

Run directly for manual testing::

    python tests/modbus_test_server.py

or import :func:`run_async_server` and :func:`wait_for_server_start` from
automated test fixtures.
"""

import asyncio
import bisect
import logging
import os
import secrets
import string
import sys
import threading
import time
from typing import Any

# sys.path manipulation must precede all project-relative imports so that
# running the file directly (python modbus_test_server.py) resolves them correctly.
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime
from random import randint

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode
from pymodbus import FramerType, ModbusDeviceIdentification
from pymodbus import __version__ as pymodbus_version
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartAsyncTcpServer
from ruamel.yaml import YAML

from sigenergy2mqtt.common import Constants, DeviceClass, Protocol
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, OutputType, PhaseCurrent, PhaseVoltage, PowerFactor
from sigenergy2mqtt.sensors.plant_read_only import GridStatus
from tests.utils import get_sensor_instances

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)

# Simulated Modbus response latency bounds (milliseconds).
# async_getValues targets DELAY_AVG on average, clamping to DELAY_MIN when
# ahead of budget and sampling uniformly up to DELAY_MAX when behind.
DELAY_AVG: int = 15
DELAY_MIN: int = 5
DELAY_MAX: int = 50


class CustomMqttHandler:
    """Thread-safe MQTT event handler shared across all :class:`CustomDataBlock` instances.

    Paho-MQTT delivers callbacks on its own background thread.  This class
    dispatches incoming messages back onto the asyncio event loop via
    :pymeth:`asyncio.AbstractEventLoop.call_soon_threadsafe`, ensuring that all
    mutations to :class:`CustomDataBlock` state occur on the event-loop thread
    and are free of data races.

    Attributes:
        connected: ``True`` once the client has successfully connected to the
            broker (and re-connected after any disconnect).
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, log_level: int = logging.INFO):
        """Initialise the handler.

        Args:
            loop: The running asyncio event loop.  Used to schedule message
                handler callbacks on the correct thread.
            log_level: Logging verbosity for this handler's private logger.
        """
        self.connected = False
        self._topics = {}
        self._loop = loop
        self._reconnect_lock = threading.Lock()
        self._logger = logging.getLogger("CustomMqttHandler")
        self._logger.setLevel(log_level)

    def on_reconnect(self, client: mqtt.Client) -> None:
        """Re-subscribe to all registered topics after a (re-)connection.

        Safe to call from any thread.  Uses a double-checked lock so that only
        the first caller after a disconnect performs the re-subscription work.

        Args:
            client: The connected Paho MQTT client.
        """
        if not self.connected:
            with self._reconnect_lock:
                if not self.connected:
                    self.connected = True
                    if len(self._topics) > 0:
                        self._logger.info("Reconnected to mqtt")
                        for topic in self._topics.keys():
                            result = client.unsubscribe(topic)
                            self._logger.debug(f"on_reconnect: unsubscribe('{topic}') -> {result}")
                            result = client.subscribe(topic)
                            self._logger.debug(f"on_reconnect: subscribe('{topic}') -> {result}")

    def on_message(self, topic: str, payload: str) -> None:
        """Route an incoming MQTT message to all registered handlers for *topic*.

        Called from the Paho background thread.  Each handler is dispatched via
        :pymeth:`asyncio.AbstractEventLoop.call_soon_threadsafe` so that
        :class:`CustomDataBlock` state is only ever mutated on the event-loop
        thread.

        Args:
            topic: The MQTT topic on which the message arrived.
            payload: The decoded message payload as a string.
        """
        value = str(payload).strip()
        if value and topic in self._topics:
            for method in self._topics[topic]:
                self._logger.debug(f"on_message: {method.__func__.__qualname__}('{topic}', {value})")
                # Dispatch back onto the asyncio event loop so that all
                # access to CustomDataBlock state happens on a single thread,
                # eliminating data races between the MQTT thread and asyncio.
                self._loop.call_soon_threadsafe(method, topic, value, self._logger.isEnabledFor(logging.DEBUG))

    def register(self, client: mqtt.Client, topic: str, handler) -> tuple[MQTTErrorCode, int | None]:
        """Subscribe *client* to *topic* and register *handler* for incoming messages.

        Multiple handlers may be registered for the same topic; all will be
        called in registration order for each message.

        Args:
            client: The Paho MQTT client to subscribe.
            topic: The MQTT topic string to subscribe to.
            handler: A bound method with signature
                ``(topic: str, value: str, debug: bool) -> None``.

        Returns:
            The ``(MQTTErrorCode, mid)`` tuple returned by :pymeth:`mqtt.Client.subscribe`.
        """
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(handler)
        return client.subscribe(topic)


class CustomDataBlock(ModbusSparseDataBlock):
    """Modbus data store for a single device address.

    Wraps :class:`pymodbus.datastore.ModbusSparseDataBlock` with:

    * Sensor-aware reads and writes — register values are decoded and encoded
      using each sensor's own ``state2raw`` / ``convert_to_registers`` logic.
    * MQTT integration — when an MQTT client is supplied, each publishable
      sensor subscribes to its ``state_topic`` so that live values from a real
      installation flow into the simulated registers.
    * Simulated latency — :meth:`async_getValues` introduces a randomised
      response delay that mimics real Modbus device behaviour.
    * Write-lock semantics — addresses written through :meth:`async_setValues`
      are permanently shielded from MQTT overwrite, allowing tests to assert on
      the values they set.
    * Phase mirroring — Phase A voltage and current are automatically mirrored
      to phases B and C because the real data source does not expose them
      individually.
    """

    def __init__(self, device_address: int, mqtt_client: mqtt.Client):
        """Initialise an empty data block for *device_address*.

        Args:
            device_address: The Modbus slave/unit ID this block represents.
            mqtt_client: A connected Paho MQTT client used to subscribe to
                sensor state topics, or ``None`` to disable MQTT integration.
        """
        super().__init__(values=None, mutable=True)
        self.device_address = device_address
        self.addresses: dict[int, Any] = {}
        self._reserved: list[int] = []
        self._topics: dict[str, Any] = {}
        # A set of addresses written via the test server.  Using a set avoids
        # unbounded growth from repeated writes and gives O(1) membership tests.
        # Once an address is added here it is intentionally kept for the lifetime
        # of the server so that MQTT updates from the real data source never
        # overwrite a value that was explicitly set through the test interface.
        self._written_addresses: set[int] = set()
        if mqtt_client:
            self._mqtt_client = mqtt_client
        self._total_sleep_time: int = 0
        self._read_count: int = 0

    def _set_value(self, sensor, value: float | int | str, source: str = "", debug: bool = False) -> None:
        """Encode *value* using *sensor*'s conversion logic and write it to the data block.

        Addresses that were previously written through the test interface
        (i.e. present in :attr:`_written_addresses`) are silently skipped so
        that MQTT updates from the real data source cannot overwrite test
        values.

        For :attr:`PhaseVoltage.PHASE_A_ADDRESS` and
        :attr:`PhaseCurrent.PHASE_A_ADDRESS` the encoded registers are also
        mirrored to phases B and C.

        Args:
            sensor: The sensor descriptor whose encoding rules to use.
            value: The human-readable state value to store.
            source: An optional label included in debug log messages to
                identify where the value originated (e.g. ``"mqtt::some/topic"``).
            debug: When ``True``, emit a debug log entry even if the sensor's
                own ``debug_logging`` flag is not set.
        """
        if debug or sensor.debug_logging:
            _logger.debug(f"_set_value({sensor['name']}, {value}) [address={sensor.address} device_address={self.device_address} {source=}]")
        address = sensor.address
        if address in self._written_addresses:  # Ignore MQTT messages from the real data source for addresses that were just written to, so that we can test reading back what we wrote
            return
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            registers = ModbusClientMixin.convert_to_registers(value, sensor.data_type)
            if len(registers) < sensor.count:
                registers.extend([0] * (sensor.count - len(registers)))  # Pad with zeros
            elif len(registers) > sensor.count:
                registers = registers[: sensor.count]  # Truncate to the required length
        else:
            raw = sensor.state2raw(value)
            registers = ModbusClientMixin.convert_to_registers(raw, sensor.data_type)
        super().setValues(address, registers)
        if address == PhaseVoltage.PHASE_A_ADDRESS:  # Use the Phase A Voltage for all three phases, because the real data source does not provide separate values for the three phases
            super().setValues(PhaseVoltage.PHASE_B_ADDRESS, registers)
            super().setValues(PhaseVoltage.PHASE_C_ADDRESS, registers)
        elif address == PhaseCurrent.PHASE_A_ADDRESS:  # Use the Phase A Current for all three phases, because the real data source does not provide separate values for the three phases
            super().setValues(PhaseCurrent.PHASE_B_ADDRESS, registers)
            super().setValues(PhaseCurrent.PHASE_C_ADDRESS, registers)

    def _handle_mqtt_message(self, topic: str, value: str, debug: bool = False) -> None:
        """Update the register for *topic*'s sensor from an incoming MQTT message.

        Called on the asyncio event-loop thread via
        :pymeth:`CustomMqttHandler.on_message`.

        Args:
            topic: The MQTT topic that received a message.
            value: The decoded payload string.
            debug: Forwarded to :meth:`_set_value` to control debug logging.
        """
        sensor = self._topics.get(topic)
        self._set_value(sensor, value, f"mqtt::{topic}", debug=debug)

    def _get_initial_value(self, sensor: Any) -> tuple[Any, str]:
        """Determine the initial register value and its source label for *sensor*.

        Applies the following priority order:

        1. String sensors — uses ``latest_raw_state`` if available, otherwise a
           placeholder string.
        2. Sensor-specific overrides — ``OutputType``, ``PowerFactor``,
           ``ACChargerRatedCurrent``, ``ACChargerInputBreaker``, and alarm sensors
           each have fixed test values (see inline comments for rationale).
        3. ``sensor.latest_raw_state`` — used when already populated by
           :func:`prepopulate`.
        4. Sensor metadata — ``min``/``max`` bounds, ``options``, sanity-check
           bounds, or data-type limits, sampled randomly in that order.

        Args:
            sensor: A publishable sensor descriptor.

        Returns:
            A ``(value, source)`` tuple where *value* is the initial state and
            *source* is a short label used in debug log messages.
        """
        if sensor.address == InverterFirmwareVersion.ADDRESS:
            return ("V100R001C00SPC112B107G", "inverter_firmware_version")

        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            return ("string value" if not sensor.latest_raw_state else sensor.latest_raw_state, "string")

        if sensor.address == OutputType.ADDRESS:
            return (2, "output_type")
        if sensor.address == PowerFactor.ADDRESS:
            # Force a value outside the valid range to exercise sanity-check failure handling.
            return (randint(64572, 65534) / sensor.gain, "power_factor")
        if sensor.address == ACChargerRatedCurrent.ADDRESS:
            return (63, "rated_current")
        if sensor.address == ACChargerInputBreaker.ADDRESS:
            return (64, "input_breaker")
        if hasattr(sensor, "decode_alarm_bit"):  # AlarmSensor
            return (0, "alarm_sensor")

        if sensor.latest_raw_state is not None and isinstance(sensor.latest_raw_state, (int, float)):
            return (sensor.latest_raw_state / sensor.gain, "latest_raw_state")
        if sensor.device_class == DeviceClass.TIMESTAMP:
            return (datetime.now().isoformat(), "timestamp")
        if hasattr(sensor, "state_off") and hasattr(sensor, "state_on"):  # SwitchSensor
            return (0, "switch_sensor")
        if hasattr(sensor, "min") and hasattr(sensor, "max"):
            lo = sensor["min"][0] if isinstance(sensor["min"], (tuple, list)) else sensor["min"]
            hi = sensor["max"][1] if isinstance(sensor["max"], (tuple, list)) else sensor["max"]
            return (randint(lo, hi), "min_max")
        if hasattr(sensor, "options"):
            return (0, "options")
        if sensor.sanity_check.min_raw is not None and sensor.sanity_check.max_raw is not None:
            if sensor.sanity_check.delta:
                raw = sensor.sanity_check.min_raw + randint(0, int(sensor.sanity_check.max_raw - sensor.sanity_check.min_raw) // sensor.sanity_check.delta) * sensor.sanity_check.delta
            else:
                raw = randint(int(sensor.sanity_check.min_raw), int(sensor.sanity_check.max_raw))
            return (raw / sensor.gain, "sanity_check")

        # Fall back to the full range of the sensor's data type.
        lo_raw = sensor.sanity_check.min_raw
        hi_raw = sensor.sanity_check.max_raw
        match sensor.data_type:
            case ModbusClientMixin.DATATYPE.INT16:
                raw = randint(-32768 if lo_raw is None else int(lo_raw), 32767 if hi_raw is None else int(hi_raw))
            case ModbusClientMixin.DATATYPE.UINT16:
                raw = randint(0, 65535 if hi_raw is None else int(hi_raw))
            case ModbusClientMixin.DATATYPE.INT32:
                raw = randint(-2147483648 if lo_raw is None else int(lo_raw), 2147483647 if hi_raw is None else int(hi_raw))
            case ModbusClientMixin.DATATYPE.UINT32:
                raw = randint(0, 4294967295 if hi_raw is None else int(hi_raw))
            case ModbusClientMixin.DATATYPE.INT64:
                raw = randint(-9223372036854775808 if lo_raw is None else int(lo_raw), 9223372036854775807 if hi_raw is None else int(hi_raw))
            case ModbusClientMixin.DATATYPE.UINT64:
                raw = randint(0, 18446744073709551615 if hi_raw is None else int(hi_raw))
            case _:
                raw = randint(0, 255)
        return (raw / sensor.gain, "data_type_default")

    def _register_mqtt_topic(self, sensor: Any, source: str) -> None:
        """Subscribe to *sensor*'s MQTT state topic if appropriate.

        Sensors whose initial value comes from a fixed override (``output_type``,
        ``pv_string_count``, ``mppt_count``, ``alarm_sensor``, ``power_factor``)
        are excluded because live MQTT updates would replace the carefully chosen
        test value.

        Args:
            sensor: A publishable, non-string sensor descriptor.
            source: The source label returned by :meth:`_get_initial_value`.
                Used to determine whether MQTT subscription is appropriate.
        """
        _MQTT_EXCLUDED_SOURCES = {"output_type", "pv_string_count", "mppt_count", "alarm_sensor", "power_factor"}
        if not self._mqtt_client or not sensor.address or source in _MQTT_EXCLUDED_SOURCES:
            return
        if "state_topic" in sensor:
            self._topics[sensor.state_topic] = sensor
            self._mqtt_client.user_data_get().register(self._mqtt_client, sensor.state_topic, self._handle_mqtt_message)
        else:
            _logger.warning(f"Sensor {sensor['name']} does not have a state_topic and cannot be updated via MQTT.")

    def add_sensor(self, sensor: Any) -> None:
        """Register *sensor* with this data block and write its initial value.

        Delegates value selection to :meth:`_get_initial_value` and MQTT
        subscription to :meth:`_register_mqtt_topic`, then writes the result
        via :meth:`_set_value`.

        Args:
            sensor: A sensor descriptor object.  Must have at least ``address``,
                ``device_address``, ``publishable``, and ``data_type`` attributes.
        """
        self.addresses[sensor.address] = sensor
        if sensor.__class__.__name__.startswith("Reserved"):
            self._reserved.append(sensor.address)
        if not sensor.publishable:
            return
        value, source = self._get_initial_value(sensor)
        if sensor.data_type != ModbusClientMixin.DATATYPE.STRING:
            self._register_mqtt_topic(sensor, source)
        self._set_value(sensor, value, source)

    async def async_getValues(self, fc_as_hex: int, address: int, count=1) -> ExcCodes | list[int] | list[bool]:  # pyright: ignore[reportIncompatibleMethodOverride] # pyrefly: ignore
        """Read *count* registers starting at *address*, with simulated latency.

        The delay is sampled from ``[DELAY_MIN, DELAY_MAX]`` ms, clamping to
        ``DELAY_MIN`` whenever the running average would otherwise exceed
        ``DELAY_AVG``.

        Args:
            fc_as_hex: Modbus function code (passed through to :meth:`getValues`
                for logging purposes).
            address: Starting register address.
            count: Number of registers to read.

        Returns:
            A list of register values, or :attr:`ExcCodes.ILLEGAL_ADDRESS` if
            the address range is invalid.
        """
        self._read_count += count
        if (self._total_sleep_time + DELAY_MIN) / self._read_count > DELAY_AVG:
            sleep_time = DELAY_MIN
        else:
            sleep_time = randint(DELAY_MIN, DELAY_MAX)  # Simulate variable response times
        self._total_sleep_time += sleep_time
        await asyncio.sleep(sleep_time / 1000)
        result = self.getValues(address, count)
        if address in self.addresses and self.addresses[address].debug_logging:
            _logger.debug(f"async_getValues({fc_as_hex}, {address}, {count}) -> {result}")
        return result

    async def async_setValues(self, fc_as_hex: int, address: int, values: list[int] | list[bool]) -> ExcCodes | None:  # pyright: ignore[reportIncompatibleMethodOverride] # pyrefly: ignore
        """Write *values* to *address*, enforcing RemoteEMS availability control.

        If the sensor at *address* has an ``_availability_control_sensor`` of
        type ``RemoteEMS`` and that sensor's current raw state is ``0``
        (disabled), the write is rejected with
        :attr:`ExcCodes.ILLEGAL_ADDRESS`.

        Successfully written addresses are added to
        :attr:`_written_addresses` to prevent subsequent MQTT updates from
        overwriting them for the remainder of the server's lifetime.

        Args:
            fc_as_hex: Modbus function code.
            address: Starting register address.
            values: Register values to write.

        Returns:
            ``None`` on success, or :attr:`ExcCodes.ILLEGAL_ADDRESS` if the
            write was rejected by the availability control check.
        """
        if address in self.addresses:
            sensor = self.addresses[address]
            if hasattr(sensor, "_availability_control_sensor") and sensor._availability_control_sensor.__class__.__name__ == "RemoteEMS":
                if sensor._availability_control_sensor.latest_raw_state == 0:
                    return ExcCodes.ILLEGAL_ADDRESS
        else:
            sensor = None
        self._written_addresses.add(address)  # When an address has been written to via the test server, prevent it being reset from the real source server
        if sensor and sensor.debug_logging:
            _logger.debug(f"async_setValues({fc_as_hex}, {address}, {values})")
        return super().setValues(address, values)

    def getValues(self, address, count=1) -> list[int] | list[bool] | ExcCodes:
        """Read *count* registers starting at *address*.

        Handles three cases:

        * **Reserved address** — returns :attr:`ExcCodes.ILLEGAL_ADDRESS`.
        * **Exact sensor match** — delegates directly to the parent block.
        * **Spanning request** — assembles registers from multiple sensors
          using a binary-search over the sorted address list, padding any
          missing sensor reads with zeros.

        Args:
            address: Starting register address.
            count: Number of contiguous registers to read.

        Returns:
            A list of integer register values, or
            :attr:`ExcCodes.ILLEGAL_ADDRESS` if the range cannot be satisfied.
        """
        sensor = None if address not in self.addresses else self.addresses[address]
        last_address = address + count - 1
        if address in self._reserved or last_address - count + 1 in self._reserved:
            # Return ILLEGAL ADDRESS for request for specific address, but not if part of larger chunk
            result = ExcCodes.ILLEGAL_ADDRESS
        elif sensor and sensor.count == count:
            result = super().getValues(address, count)
        else:
            pre_read: list[int | bool] = []
            keys = list(self.addresses.keys())
            start = bisect.bisect_left(keys, address)
            end = bisect.bisect_right(keys, last_address)
            for k in keys[start:end]:
                sensor = self.addresses[k]
                state = super().getValues(sensor.address, sensor.count)
                if isinstance(state, list):
                    pre_read.extend(state)
                else:
                    for _ in range(0, sensor.count):
                        pre_read.append(0)
            result = pre_read if len(pre_read) == count else ExcCodes.ILLEGAL_ADDRESS
        if sensor and sensor.debug_logging:
            _logger.debug(f"getValues({address}, {count}) -> {result}")
        return result


async def simulate_firmware_version_upgrade(data_block: CustomDataBlock, wait_for_seconds: int) -> None:
    """Simulate inverter firmware version upgrade on *data_block*.

    Args:
        data_block: The plant device's data block (unit ID
            ``Constants.PLANT_DEVICE_ADDRESS``).
        wait_for_seconds: Idle time before simulating firmware
            update, in seconds.
    """
    try:
        _logger.info(f"Waiting for {wait_for_seconds} seconds before simulating inverter firmware update for device address {data_block.device_address}...")
        await asyncio.sleep(wait_for_seconds)
        _logger.info(f"Simulating inverter firmware update for device address {data_block.device_address}")
        await data_block.async_setValues(0x06, InverterFirmwareVersion.ADDRESS, ModbusClientMixin.convert_to_registers("V100R001C00SPC113", ModbusClientMixin.DATATYPE.STRING))
    except asyncio.CancelledError:
        pass


async def simulate_grid_outage(data_block: CustomDataBlock, wait_for_seconds: int, duration_seconds: int) -> None:
    """Repeatedly simulate grid outages on *data_block*.

    Waits *wait_for_seconds*, sets the ``GridStatus`` register to ``1``
    (outage), holds for *duration_seconds*, then restores it to ``0``.  Loops
    indefinitely until cancelled.

    Args:
        data_block: The plant device's data block (unit ID
            ``Constants.PLANT_DEVICE_ADDRESS``).
        wait_for_seconds: Idle time between outage cycles, in seconds.
        duration_seconds: Duration of each simulated outage, in seconds.
    """
    while True:
        try:
            _logger.info(f"Waiting for {wait_for_seconds} seconds before simulating grid outage for device address {data_block.device_address}...")
            await asyncio.sleep(wait_for_seconds)
            _logger.info(f"Simulating grid outage for device address {data_block.device_address} for {duration_seconds} seconds...")
            await data_block.async_setValues(0x06, GridStatus.ADDRESS, [1])
            await asyncio.sleep(duration_seconds)
            await data_block.async_setValues(0x06, GridStatus.ADDRESS, [0])
            _logger.info(f"Grid outage simulation ended for device address {data_block.device_address}.")
        except asyncio.CancelledError:
            break


async def prepopulate(modbus_client: ModbusClient, groups: dict[int, list]) -> None:
    """Pre-populate register values from a live Modbus source.

    Reads each sensor group from *modbus_client* in bulk, then calls each
    sensor's ``get_state`` to populate ``latest_raw_state``.  Devices that
    fail to respond are skipped for the remainder of the call; the connection
    is re-established if it drops mid-run.

    Args:
        modbus_client: An initialised :class:`~sigenergy2mqtt.modbus.client.ModbusClient`.
        groups: Sensor groups as produced by :func:`run_async_server` — a
            ``dict`` mapping a sequential integer index to a list of sensors
            that share a contiguous register range.
    """
    _logger.info(f"Pre-populating sensor values from modbus://{modbus_client.comm_params.host}:{modbus_client.comm_params.port}...")
    skip_devices: list[int] = []
    try:
        await modbus_client.connect()
        for group_sensors in groups.values():
            if len(group_sensors) == 1 and (group_sensors[0].device_address in skip_devices or group_sensors[0].__class__.__name__.startswith("Reserved")):
                continue
            first_address: int = min([s.address for s in group_sensors if hasattr(s, "address") and not s.__class__.__name__.startswith("Reserved")])
            last_address: int = max([s.address + s.count - 1 for s in group_sensors if hasattr(s, "address") and not s.__class__.__name__.startswith("Reserved")])
            count: int = sum([s.count for s in group_sensors if hasattr(s, "count") and first_address <= getattr(s, "address") <= last_address])
            assert first_address and last_address and (last_address - first_address + 1) == count
            device_address = group_sensors[0].device_address
            try:
                if await modbus_client.read_ahead_registers(first_address, count, device_id=device_address, input_type=group_sensors[0].input_type) == 0:
                    for sensor in group_sensors:
                        if sensor.publishable:
                            await sensor.get_state(modbus_client=modbus_client)
            except Exception as e:
                _logger.debug(f"Failed to pre-populate device {device_address}, skipping: {e}", exc_info=True)
                if device_address not in skip_devices:
                    skip_devices.append(device_address)
                if not modbus_client.connected:
                    await modbus_client.connect()
    finally:
        if modbus_client.connected:
            modbus_client.close()


async def run_async_server(
    mqtt_client: Any,
    modbus_client: ModbusClient | None,
    use_simplified_topics: bool,
    host: str = "0.0.0.0",
    port: int = 502,
    protocol_version: Protocol = list(Protocol)[-1],
    log_level: int = logging.INFO,
    registers_to_debug: list[int] = [],
    simulate_grid_outages: bool = False,
    simulate_firmware_upgrade: bool = False,
) -> None:
    """Build and run the async Modbus TCP test server.

    Performs the following steps:

    1. Instantiates all sensor objects via :func:`~tests.utils.get_sensor_instances`.
    2. Groups sensors into contiguous register ranges for bulk reads.
    3. Optionally pre-populates values from a live *modbus_client*.
    4. Creates a :class:`CustomDataBlock` per device address and calls
       :meth:`~CustomDataBlock.add_sensor` for every sensor.
    5. Starts the pymodbus ``StartAsyncTcpServer``.
    6. Optionally co-schedules :func:`simulate_grid_outage` for the plant
       device.
    7. Optionally co-schedules :func:`simulate_firmware_version_upgrade` for the
       inverter device.

    Args:
        mqtt_client: A started Paho MQTT client, or ``None`` to disable MQTT
            integration.
        modbus_client: A live :class:`~sigenergy2mqtt.modbus.client.ModbusClient`
            to pre-populate register values from, or ``None`` to use
            synthesised data only.
        use_simplified_topics: When ``False``, sensor topics include
            Home Assistant-style prefixes.
        host: TCP host address for the server to bind to.
        port: TCP port for the server to listen on.
        protocol_version: Sigenergy protocol version to emulate.
        log_level: Logging verbosity for this module's logger.
        registers_to_debug: List of register addresses to enable verbose
            logging for.  Pass ``[0]`` to enable debug logging for all
            registers.
        simulate_grid_outages: When ``True``, periodically toggles the
            ``GridStatus`` register on the plant device to simulate grid
            outages.
        simulate_firmware_upgrade: When ``True``, updates the
            ``InverterFirmwareVersion.
    """
    context: dict[int, CustomDataBlock] = {}
    groups: dict[int, list] = {}
    group_index: int = -1
    address: int | None = None
    count: int | None = None
    device_address: int | None = None
    input_type = None

    _logger.setLevel(log_level)

    _logger.info("Getting sensor instances...")
    inverter_device_address = 3
    sensors: dict = await get_sensor_instances(
        home_assistant_enabled=not use_simplified_topics,
        protocol_version=protocol_version,
        pv_inverter_device_address=inverter_device_address,
        concrete_sensor_check=False,
    )
    sorted_sensors: list = sorted(
        [s for s in sensors.values() if hasattr(s, "address") and s["platform"] != "button" and not hasattr(s, "alarms")],
        key=lambda x: (x.device_address, x.address),
    )
    for sensor in sorted_sensors:
        if (
            device_address != sensor.device_address
            or (address is None or count is None or sensor.address != address + count)
            or input_type != sensor.input_type
            or (group_index != -1 and (sum(s.count for s in groups[group_index]) + sensor.count) > Constants.MAX_MODBUS_REGISTERS_PER_REQUEST)
        ):
            group_index = group_index + 1
            groups[group_index] = []
        groups[group_index].append(sensor)
        if sensor.address in registers_to_debug or 0 in registers_to_debug:
            sensor.debug_logging = True
        address = sensor.address
        count = sensor.count
        device_address = sensor.device_address
        input_type = sensor.input_type

    if modbus_client:
        await prepopulate(modbus_client, groups)

    if any(registers_to_debug):
        _logger.info(f"Enabling debug logging because registers {registers_to_debug} were specified for debugging...")
        _logger.setLevel(logging.DEBUG)

    _logger.info("Creating data blocks...")
    for sensor in sorted_sensors:
        if hasattr(sensor, "device_address"):
            if sensor.device_address not in context:
                context[sensor.device_address] = CustomDataBlock(sensor.device_address, mqtt_client)
            context[sensor.device_address].add_sensor(sensor)

    _logger.info("Starting ASYNC Modbus TCP Testing Server...")
    if log_level <= logging.INFO:
        logging.getLogger("pymodbus").setLevel(logging.INFO)
    try:
        tasks = []
        tasks.append(
            StartAsyncTcpServer(
                context=ModbusServerContext(devices=context, single=False),
                identity=ModbusDeviceIdentification(
                    info_name={
                        "VendorName": "seud0nym",
                        "ProductCode": "sigenergy2mqtt",
                        "VendorUrl": "https://github.com/seud0nym/sigenergy2mqtt/",
                        "ProductName": "sigenergy2mqtt Testing Modbus Server",
                        "ModelName": "sigenergy2mqtt Testing Modbus Server",
                        "MajorMinorRevision": pymodbus_version,
                    }
                ),
                address=(host, port),
                framer=FramerType.SOCKET,
            )
        )
        if simulate_grid_outages:
            tasks.append(simulate_grid_outage(context[Constants.PLANT_DEVICE_ADDRESS], wait_for_seconds=30, duration_seconds=30) if Constants.PLANT_DEVICE_ADDRESS in context else asyncio.sleep(0))
        if simulate_firmware_upgrade:
            tasks.append(simulate_firmware_version_upgrade(context[1], wait_for_seconds=20))
        await asyncio.gather(*tasks)
    except asyncio.CancelledError as e:
        _logger.debug(f"Modbus TCP Testing Server cancelled: {e}")
        # Ensure we don't leave the port bound
        await asyncio.sleep(0.1)


async def wait_for_server_start(host: str, port: int, timeout: float = 10.0) -> bool:
    """Poll until the TCP server at *host*:*port* accepts a connection.

    Intended for use in test fixtures that start :func:`run_async_server` in a
    background task and need to wait before issuing test requests.

    Args:
        host: Server hostname or IP address.
        port: Server TCP port.
        timeout: Maximum time to wait, in seconds.

    Returns:
        ``True`` if the server accepted a connection within *timeout* seconds,
        ``False`` otherwise.
    """
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, ConnectionRefusedError):
            await asyncio.sleep(0.1)
    return False


def on_connect(client: mqtt.Client, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    """Paho ``on_connect`` callback.

    Triggers :meth:`CustomMqttHandler.on_reconnect` on success, or terminates
    the process with exit code ``2`` if the broker refuses the connection.

    Args:
        client: The Paho MQTT client instance.
        userdata: The :class:`CustomMqttHandler` set as client user-data.
        flags: Connection flags (unused).
        reason_code: MQTT reason / return code.
        properties: MQTT v5 properties (unused).
    """
    if reason_code == 0:
        userdata.on_reconnect(client)
    else:
        _logger.critical(f"Connection to mqtt REFUSED - {reason_code}")
        os._exit(2)


def on_disconnect(client: mqtt.Client, userdata: CustomMqttHandler, flags, reason_code, properties) -> None:
    """Paho ``on_disconnect`` callback.

    Marks the handler as disconnected and logs unexpected disconnections.

    Args:
        client: The Paho MQTT client instance.
        userdata: The :class:`CustomMqttHandler` set as client user-data.
        flags: Disconnect flags (unused).
        reason_code: MQTT reason code; non-zero indicates an unexpected drop.
        properties: MQTT v5 properties (unused).
    """
    userdata.connected = False
    if reason_code != 0:
        _logger.error(f"Failed to disconnect from mqtt (Reason Code = {reason_code})")


def on_message(client: mqtt.Client, userdata: CustomMqttHandler, message) -> None:
    """Paho ``on_message`` callback.

    Forwards the decoded payload to :meth:`CustomMqttHandler.on_message` and
    triggers reconnect logic in case this message arrived after an implicit
    reconnection that bypassed the ``on_connect`` callback.

    Args:
        client: The Paho MQTT client instance.
        userdata: The :class:`CustomMqttHandler` set as client user-data.
        message: The received :class:`paho.mqtt.client.MQTTMessage`.
    """
    userdata.on_message(message.topic, str(message.payload, "utf-8"))
    userdata.on_reconnect(client)


async def async_helper() -> None:
    """Entry point for running the server from the command line.

    Loads ``.debug_modbus_server.yaml`` from the current working directory if
    present and uses it to configure an MQTT client and a live Modbus client
    for register pre-population.  Falls back to a fully synthetic server
    (no MQTT, no live Modbus source) if the file is absent.

    The MQTT client is always cleanly shut down in a ``finally`` block,
    regardless of how the server exits.
    """
    # Initialise all variables before the try block so that they are always
    # bound, even when the config file is absent or raises an error.
    config: dict = {}
    mqtt_client: mqtt.Client | None = None
    modbus_client: ModbusClient | None = None
    kwargs: dict = {}

    try:
        _yaml = YAML(typ="safe", pure=True)
        with open(".debug_modbus_server.yaml", "r") as f:
            config = _yaml.load(f)
            mqtt_log_level = logging.getLevelNamesMapping()[config.get("mqtt", {}).get("log-level", "INFO")]
            mqtt_client = mqtt.Client(
                CallbackAPIVersion.VERSION2,
                client_id=f"sigenergy2mqtt_modbus_test_server_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))}",
                userdata=CustomMqttHandler(asyncio.get_running_loop(), log_level=mqtt_log_level),
            )
            mqtt_client.username_pw_set(config.get("mqtt", {}).get("username", None), config.get("mqtt", {}).get("password", None))
            mqtt_broker = config.get("mqtt", {}).get("broker", "localhost")
            mqtt_port = config.get("mqtt", {}).get("port", 1883)
            mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            _logger.info(f"Connected to MQTT broker mqtt://{mqtt_broker}:{mqtt_port} as data source")
            mqtt_client.on_disconnect = on_disconnect
            mqtt_client.on_connect = on_connect
            mqtt_client.on_message = on_message
            mqtt_client.loop_start()
            modbus_client = ModbusClient(config.get("modbus")[0].get("host"), port=config.get("modbus")[0].get("port", 502), timeout=1, retries=0)
            kwargs["log_level"] = logging.getLevelNamesMapping()[config.get("modbus")[0].get("log-level", "INFO")]
            kwargs["registers_to_debug"] = config.get("modbus")[0].get("registers-to-debug", [])
            kwargs["simulate_grid_outages"] = config.get("modbus")[0].get("simulate-grid-outages", False)
            kwargs["simulate_firmware_upgrade"] = config.get("modbus")[0].get("simulate-firmware-upgrade", False)
            protocol_version = config.get("modbus")[0].get("protocol-version", None)
            if protocol_version:
                kwargs["protocol_version"] = Protocol(protocol_version)
    except FileNotFoundError:
        _logger.warning("No .debug_modbus_server.yaml file found, using default configuration...")

    try:
        await run_async_server(mqtt_client, modbus_client, bool(config.get("home-assistant", {}).get("use-simplified-topics", False)), **kwargs)
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
