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
import logging
import os
import secrets
import string
import sys
import threading
import time
from typing import Any

# Need to set a Modbus host otherwise configuration initialisation will launch auto-discovery
os.environ["SIGENERGY2MQTT_MODBUS_HOST"] = "127.0.0.1"
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
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

from sigenergy2mqtt.common import Constants, DeviceClass, Protocol
from sigenergy2mqtt.modbus.client import ModbusClient
from sigenergy2mqtt.sensors.ac_charger_read_only import ACChargerInputBreaker, ACChargerRatedCurrent
from sigenergy2mqtt.sensors.inverter_read_only import InverterFirmwareVersion, OutputType, PhaseCurrent, PhaseVoltage, PowerFactor
from sigenergy2mqtt.sensors.plant_read_only import GridStatus
from sigenergy2mqtt.sensors.plant_read_write import RemoteEMS
from tests.utils import get_sensor_instances

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

_logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)

# Simulated Modbus response latency bounds (milliseconds).
# _make_trace_pdu targets DELAY_AVG on average, clamping to DELAY_MIN when
# ahead of budget and sampling uniformly up to DELAY_MAX when behind.
DELAY_AVG: int = 15
DELAY_MIN: int = 5
DELAY_MAX: int = 50


class TestConfig:
    log_level: int = logging.INFO

    initial_firmware: str = "V100R001C00SPC112B107G"
    upgrade_firmware: str = "V100R001C00SPC113"
    protocol_version: Protocol | None = None

    use_simplified_topics: bool = False

    registers_to_debug: list[int] = []

    simulate_grid_outages: bool = False
    simulate_firmware_upgrade: bool = False
    simulate_power_factor_errors: bool = False


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


class LatencyBudget:
    """Internal helper to track simulated latency across all devices on a server."""

    def __init__(self) -> None:
        self.total_sleep_ms: int = 0
        self.request_count: int = 0


def _make_trace_pdu(_context: dict[int, "CustomDataBlock"]) -> Any:
    """Return a synchronous ``trace_pdu`` callback for :class:`ModbusTcpServer`.

    In pymodbus 3.13.0 trace hooks called from the transport layer must be
    synchronous.  Latency simulation and write-lock tracking have been
    moved to the async ``SimDevice.action`` callback returned by
    :meth:`CustomDataBlock._make_device_action`.

    Returns:
        A synchronous callable with signature ``(is_response: bool, pdu) -> pdu``.
    """

    def trace_pdu(_is_response: bool, pdu: Any) -> Any:
        return pdu

    return trace_pdu


class CustomDataBlock:
    """Modbus data store for a single device address.

    Wraps register storage with:

    * Sensor-aware reads and writes — register values are decoded and encoded
      using each sensor's own ``state2raw`` / ``convert_to_registers`` logic.
    * MQTT integration — when an MQTT client is supplied, each publishable
      sensor subscribes to its ``state_topic`` so that live values from a real
      installation flow into the simulated registers.
    * Simulated latency — injected globally via the server's ``trace_pdu``
      callback returned by :func:`_make_trace_pdu`.
    * Write-lock semantics — addresses written through the Modbus protocol are
      permanently shielded from MQTT overwrite (tracked in ``trace_pdu``),
      and addresses written by simulation helpers are locked via
      :meth:`force_set_registers`.
    * Phase mirroring — Phase A voltage and current are automatically mirrored
      to phases B and C via the :class:`SimDevice` ``action`` callback; the
      same mirroring occurs during initialisation in :meth:`_set_value`.
    * RemoteEMS write gate — when the RemoteEMS register is disabled (``0``),
      writes to availability-controlled sensors are rejected.  The
      :class:`SimDevice` ``action`` (see :meth:`_make_device_action`) returns
      :attr:`ExcCodes.ILLEGAL_ADDRESS` directly, which pymodbus translates into
      a Modbus exception response and prevents the write from being committed
      to the register store — matching the behaviour of the real device exactly.
    """

    def __init__(self, device_address: int, mqtt_client: mqtt.Client, latency_budget: LatencyBudget):
        """Initialise an empty data block for *device_address*.

        Args:
            device_address: The Modbus slave/unit ID this block represents.
            mqtt_client: A connected Paho MQTT client used to subscribe to
                sensor state topics, or ``None`` to disable MQTT integration.
            latency_budget: Shared state used to coordinate simulated latency
                across all devices on the same server.
        """
        # Raw uint16 register values used to seed SimData during build_sim_device().
        # Only mutated during the initialisation phase (before the server starts).
        self._initial_registers: dict[int, int] = {}
        self.device_address = device_address
        self.addresses: dict[int, Any] = {}
        self._topics: dict[str, Any] = {}
        # A set of addresses written via the Modbus protocol or test helpers.
        # Once an address is added it is kept for the server's lifetime so that
        # MQTT updates from the real data source never overwrite deliberately set values.
        self._written_addresses: set[int] = set()
        self._mqtt_client = mqtt_client
        self._latency_budget = latency_budget
        # Set to True immediately before internal async_setValues calls (MQTT
        # updates and simulation helpers) so that the SimDevice action bypasses
        # the RemoteEMS gate and does not perform mirroring that is already
        # applied explicitly by the caller.  Safe without locking because
        # asyncio is single-threaded and the call chain from async_setValues to
        # the action contains no I/O suspension points.
        self._internal_write: bool = False
        # Populated in run_async_server() after ModbusTcpServer is created but
        # before serve_forever() is called.  Required by _async_set_value() and
        # force_set_registers() so they can call server.context.async_setValues().
        self._server: ModbusTcpServer | None = None

    # ── SimData / SimDevice construction ──────────────────────────────────────

    def _make_device_action(self) -> Any:
        """Return the async ``action`` callable for the :class:`SimDevice`.

        In pymodbus 3.13.0 the ``action`` lives on :class:`SimDevice`, not on
        individual :class:`SimData` entries.  It is invoked for **every** read
        and write request addressed to the device, receiving the full register
        snapshot for the requested range.

        The action signature required by pymodbus is::

            async def action(
                func_code: int,            # Modbus function code of the request
                start_address: int,        # address of current_registers[0]
                address: int,              # address from the request
                count: int,                # register count from the request
                current_registers: list[int],         # live register values (mutable)
                set_values: list[int] | list[bool] | None,  # None for reads
            ) -> None | ExcCodes

        Returning :attr:`ExcCodes.ILLEGAL_ADDRESS` causes pymodbus to send a
        Modbus exception response to the client **and** discard the write.

        Responsibilities handled here (write path only, i.e. ``set_values is
        not None``):

        * **RemoteEMS write gate** — if the request address maps to a sensor
          that is availability-controlled by :class:`RemoteEMS` and the
          RemoteEMS register currently reads ``0``, returns
          :attr:`ExcCodes.ILLEGAL_ADDRESS`.  Internal writes (MQTT updates,
          simulation helpers) set :attr:`_internal_write` to ``True`` to
          bypass this gate.
        * **Phase A mirroring** — when Phase A voltage or current registers are
          written by an external Modbus client, the same values are replicated
          to the Phase B and C register addresses.  Internal writes skip this
          because :meth:`_async_set_value` performs the mirroring itself.
        * **PV-string mirroring** — PV-string 1 voltage/current writes are
          replicated to all 36 string addresses.  Same internal-write exemption
          applies.

        Returns:
            An async callable matching the pymodbus ``SimDevice.action``
            signature.
        """
        block = self
        dev_addr = self.device_address

        # Pre-compute address sets for fast membership tests inside the action.
        gated_addrs: set[int] = {addr for addr, sensor in block.addresses.items() if hasattr(sensor, "_availability_control_sensor") and isinstance(sensor._availability_control_sensor, RemoteEMS)}
        all_reserved_addrs: dict[int, Any] = {}
        for addr, sensor in block.addresses.items():
            if sensor.__class__.__name__.startswith("Reserved"):
                for i in range(sensor.count):
                    all_reserved_addrs[addr + i] = sensor

        async def _action(
            func_code: int,
            start_address: int,
            address: int,
            count: int,
            current_registers: list[int],
            set_values: list[int] | list[bool] | None,
        ) -> None | ExcCodes:
            # ── Internal writes ────────────────────────────────────────────
            # MQTT updates and simulation helpers bypass latency, write-locking,
            # and the RemoteEMS gate.
            if block._internal_write:
                return None

            # ── Debug logging ──────────────────────────────────────────────
            # Log external Modbus requests if they target a register specified for debugging.
            if _logger.isEnabledFor(logging.DEBUG):
                if 0 in TestConfig.registers_to_debug or any(addr in TestConfig.registers_to_debug for addr in range(address, address + count)):
                    is_write = set_values is not None
                    prefix = f"#{dev_addr} {'WRITE ' if is_write else 'READ  '} @{address}"
                    if count > 1:
                        prefix += f"-{address + count - 1}"

                    if is_write:
                        values_str = f" values={set_values}"
                    else:
                        offset = address - start_address
                        values_str = f" values={current_registers[offset : offset + count]}"

                    _logger.debug(f"{prefix} (count={count}){values_str}")

            # ── Reserved registers ─────────────────────────────────────────
            # Specific requests for reserved registers (not as part of a bulk
            # pre-read) must return ILLEGAL_ADDRESS.  A bulk read is assumed
            # if the request spans beyond the bounds of the reserved sensor.
            if address in all_reserved_addrs:
                sensor = all_reserved_addrs[address]
                # If the request is fully contained within this reserved sensor, reject it.
                if (address + count) <= (sensor.address + sensor.count):
                    return ExcCodes.ILLEGAL_ADDRESS

            # ── Simulated latency ──────────────────────────────────────────
            budget = block._latency_budget
            budget.request_count += 1
            if (budget.total_sleep_ms + DELAY_MIN) / budget.request_count > DELAY_AVG:
                sleep_ms = DELAY_MIN
            else:
                sleep_ms = randint(DELAY_MIN, DELAY_MAX)
            budget.total_sleep_ms += sleep_ms
            await asyncio.sleep(sleep_ms / 1000)

            # ── Write-lock tracking ────────────────────────────────────────
            # For external Modbus-protocol writes, lock the addresses so
            # subsequent MQTT updates cannot overwrite them.
            if set_values is not None:
                for i in range(count):
                    block._written_addresses.add(address + i)

            # ── RemoteEMS write gate ───────────────────────────────────────
            # For external Modbus-protocol writes to gated sensors, check
            # whether RemoteEMS is enabled.  If disabled, reject the write
            # and let pymodbus send ILLEGAL_ADDRESS to the client.
            if set_values is not None and address in gated_addrs and block._server is not None:
                ems = await block._server.context.async_getValues(dev_addr, 0x03, RemoteEMS.ADDRESS, 1)
                if ems and ems[0] == 0:
                    return ExcCodes.ILLEGAL_ADDRESS

            # ── Phase / PV-string mirroring ────────────────────────────────
            # Replicate external Modbus-protocol writes to the mirror
            # addresses.  Internal writes bypass this (handled by the caller).
            if set_values is None or block._server is None:
                return None
            ctx = block._server.context
            reg_values = list(set_values)

            if address == PhaseVoltage.PHASE_A_ADDRESS:
                block._internal_write = True
                try:
                    for i, v in enumerate(reg_values):
                        await ctx.async_setValues(dev_addr, 0x10, PhaseVoltage.PHASE_B_ADDRESS + i, [v])
                        await ctx.async_setValues(dev_addr, 0x10, PhaseVoltage.PHASE_C_ADDRESS + i, [v])
                finally:
                    block._internal_write = False

            elif address == PhaseCurrent.PHASE_A_ADDRESS:
                block._internal_write = True
                try:
                    for i, v in enumerate(reg_values):
                        await ctx.async_setValues(dev_addr, 0x10, PhaseCurrent.PHASE_B_ADDRESS + i, [v])
                        await ctx.async_setValues(dev_addr, 0x10, PhaseCurrent.PHASE_C_ADDRESS + i, [v])
                finally:
                    block._internal_write = False

            elif address == 31027:
                block._internal_write = True
                try:
                    for target_addr, target_sensor in block.addresses.items():
                        if target_addr != address and "PV" in target_sensor.name and "Voltage" in target_sensor.name:
                            await ctx.async_setValues(dev_addr, 0x10, target_addr, reg_values[:1])
                finally:
                    block._internal_write = False

            elif address == 31028:
                block._internal_write = True
                try:
                    for target_addr, target_sensor in block.addresses.items():
                        if target_addr != address and "PV" in target_sensor.name and "Current" in target_sensor.name:
                            await ctx.async_setValues(dev_addr, 0x10, target_addr, reg_values[:1])
                finally:
                    block._internal_write = False

            return None

        return _action

    def build_sim_device(self) -> SimDevice:
        """Build and return a :class:`SimDevice` from all registered sensors.

        Each non-reserved sensor becomes a :class:`SimData` entry using
        ``DataType.REGISTERS`` (raw uint16 register storage) with initial
        values pre-populated from :attr:`_initial_registers`.

        Reserved addresses are intentionally omitted so that pymodbus returns a
        Modbus ``ILLEGAL_ADDRESS`` exception for any client request targeting them.

        The device-level ``action`` callback (produced by
        :meth:`_make_device_action`) is attached to handle RemoteEMS write
        gating and phase/PV-string mirroring for externally-sourced writes.

        Returns:
            A :class:`SimDevice` configured with a shared register block
            covering all non-reserved sensors for this device address.
        """
        sim_data_list: list[SimData] = []
        for address, sensor in self.addresses.items():
            # DataType.REGISTERS packs each value with struct.pack(">h", v),
            # i.e. signed int16.  _initial_registers holds raw uint16 values
            # (0–65535), so values above 32767 must be reinterpreted as their
            # signed two's-complement equivalent before being passed to SimData.
            # count is intentionally omitted (defaults to 1) because it means
            # "repeat the values list N times", not "number of registers" — the
            # values list already contains exactly sensor.count register words.
            values = [v if v < 32768 else v - 65536 for v in (self._initial_registers.get(address + i, 0) for i in range(sensor.count))]
            sim_data_list.append(
                SimData(
                    address,
                    datatype=DataType.REGISTERS,
                    values=values,
                )
            )
        return SimDevice(
            id=self.device_address,
            simdata=sim_data_list,
            action=self._make_device_action(),
        )

    # ── Value encoding / writing ──────────────────────────────────────────────

    def _set_value(self, sensor: Any, value: float | int | str, source: str = "", debug: bool = False) -> None:
        """Encode *value* using *sensor*'s conversion logic and cache it in :attr:`_initial_registers`.

        Called only during the **initialisation** phase (inside :meth:`add_sensor`)
        before the server has started.  The cached values are baked into
        :class:`SimData` objects when :meth:`build_sim_device` is called.

        Post-initialisation writes (MQTT updates, simulation helpers) use
        :meth:`_async_set_value` and :meth:`force_set_registers` respectively,
        both of which write through ``server.context.async_setValues``.

        Addresses that were previously written through the test interface
        (i.e. present in :attr:`_written_addresses`) are silently skipped so
        that MQTT updates from the real data source cannot overwrite test values.

        For :attr:`PhaseVoltage.PHASE_A_ADDRESS` and
        :attr:`PhaseCurrent.PHASE_A_ADDRESS` the encoded registers are also
        mirrored to phases B and C in the initial cache.

        Args:
            sensor: The sensor descriptor whose encoding rules to use.
            value: The human-readable state value to store.
            source: An optional label included in debug log messages to
                identify where the value originated (e.g. ``"mqtt::some/topic"``).
            debug: When ``True``, emit a debug log entry even if the sensor's
                own ``debug_logging`` flag is not set.
        """
        address = sensor.address
        if address in self._written_addresses:
            return
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            registers = ModbusClientMixin.convert_to_registers(value, sensor.data_type)
            if len(registers) < sensor.count:
                registers.extend([0] * (sensor.count - len(registers)))
            elif len(registers) > sensor.count:
                registers = registers[: sensor.count]
        else:
            raw = sensor.state2raw(value)
            registers = ModbusClientMixin.convert_to_registers(raw, sensor.data_type)
        if len(registers) != sensor.count:
            raise ValueError(
                f"#{self.device_address} _set_value({sensor.name}, {value}) [{registers=} address={sensor.address} {source=}] Expected {sensor.count} registers for sensor {sensor.name}, got {len(registers)}"
            )
        if debug or sensor.debug_logging:
            prefix = f"#{self.device_address} UPDATE @{sensor.address}"
            if sensor.count > 1:
                prefix += f"-{sensor.address + sensor.count - 1}"
            _logger.debug(f"{prefix} (count={sensor.count}) values={registers} {source=}")
        for i in range(0, sensor.count):
            self.setValues(address + i, registers[i])

        # Phase mirroring in the initial register cache.  At runtime this is
        # handled by the SimDevice action returned from _make_device_action().
        if address == PhaseVoltage.PHASE_A_ADDRESS:
            for i in range(sensor.count):
                self.setValues(PhaseVoltage.PHASE_B_ADDRESS + i, registers[i])
                self.setValues(PhaseVoltage.PHASE_C_ADDRESS + i, registers[i])
        elif address == PhaseCurrent.PHASE_A_ADDRESS:
            for i in range(sensor.count):
                self.setValues(PhaseCurrent.PHASE_B_ADDRESS + i, registers[i])
                self.setValues(PhaseCurrent.PHASE_C_ADDRESS + i, registers[i])

        # PV string mirroring in the initial register cache.  Safely targets
        # only other PV string sensors using name-based matching.
        if address == 31027:
            for target_addr, target_sensor in self.addresses.items():
                if target_addr != address and "PV" in target_sensor.name and "Voltage" in target_sensor.name:
                    self.setValues(target_addr, registers[0])
        elif address == 31028:
            for target_addr, target_sensor in self.addresses.items():
                if target_addr != address and "PV" in target_sensor.name and "Current" in target_sensor.name:
                    self.setValues(target_addr, registers[0])

    async def _async_set_value(self, sensor: Any, value: float | int | str, source: str = "", debug: bool = False) -> None:
        """Async counterpart to :meth:`_set_value` for **post-initialisation** writes.

        Used exclusively by the MQTT message handler (:meth:`_handle_mqtt_message`)
        to propagate live register values from the real installation into the
        running server's SimData store.

        Skips the write if *sensor*'s address is in :attr:`_written_addresses`
        (i.e. has been written by a Modbus-protocol client or a simulation
        helper) so that test-controlled values are never overwritten.

        Sets :attr:`_internal_write` to ``True`` around the
        ``context.async_setValues`` calls so that the :class:`SimDevice` action
        bypasses the RemoteEMS gate (MQTT updates must always go through) and
        does not re-apply mirroring (handled explicitly below).

        Phase and PV-string mirroring is applied directly here so that the
        mirror addresses are also updated atomically in the same event-loop
        turn as the primary write.

        Args:
            sensor: The sensor descriptor whose encoding rules to use.
            value: The human-readable state value received from MQTT.
            source: Label included in debug log messages (e.g. ``"mqtt::topic"``).
            debug: When ``True``, emit a debug log entry.
        """
        address = sensor.address
        if address in self._written_addresses:
            return
        if self._server is None:
            return
        ctx = self._server.context
        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            registers = ModbusClientMixin.convert_to_registers(value, sensor.data_type)
            if len(registers) < sensor.count:
                registers.extend([0] * (sensor.count - len(registers)))
            elif len(registers) > sensor.count:
                registers = registers[: sensor.count]
        else:
            raw = sensor.state2raw(value)
            registers = ModbusClientMixin.convert_to_registers(raw, sensor.data_type)
        if len(registers) != sensor.count:
            raise ValueError(
                f"#{self.device_address} _async_set_value({sensor.name}, {value}) [{registers=} address={sensor.address} {source=}]"
                f" Expected {sensor.count} registers for sensor {sensor.name}, got {len(registers)}"
            )
        if debug or sensor.debug_logging:
            prefix = f"#{self.device_address} UPDATE @{sensor.address}"
            if sensor.count > 1:
                prefix += f"-{sensor.address + sensor.count - 1}"
            _logger.debug(f"{prefix} (count={sensor.count}) values={registers} {source=}")
        self._internal_write = True
        try:
            await ctx.async_setValues(self.device_address, 0x10, address, registers)
            # Phase / PV-string mirroring for MQTT-sourced updates.
            if address == PhaseVoltage.PHASE_A_ADDRESS:
                for i in range(sensor.count):
                    await ctx.async_setValues(self.device_address, 0x10, PhaseVoltage.PHASE_B_ADDRESS + i, [registers[i]])
                    await ctx.async_setValues(self.device_address, 0x10, PhaseVoltage.PHASE_C_ADDRESS + i, [registers[i]])
            elif address == PhaseCurrent.PHASE_A_ADDRESS:
                for i in range(sensor.count):
                    await ctx.async_setValues(self.device_address, 0x10, PhaseCurrent.PHASE_B_ADDRESS + i, [registers[i]])
                    await ctx.async_setValues(self.device_address, 0x10, PhaseCurrent.PHASE_C_ADDRESS + i, [registers[i]])

            if address == 31027:
                for target_addr, target_sensor in self.addresses.items():
                    if target_addr != address and "PV" in target_sensor.name and "Voltage" in target_sensor.name:
                        await ctx.async_setValues(self.device_address, 0x10, target_addr, [registers[0]])
            elif address == 31028:
                for target_addr, target_sensor in self.addresses.items():
                    if target_addr != address and "PV" in target_sensor.name and "Current" in target_sensor.name:
                        await ctx.async_setValues(self.device_address, 0x10, target_addr, [registers[0]])
        finally:
            self._internal_write = False

    async def force_set_registers(self, address: int, values: list[int]) -> None:
        """Write *values* to *address* directly, bypassing all write-lock checks.

        Intended for test simulation helpers (:func:`simulate_grid_outage`,
        :func:`simulate_firmware_version_upgrade`) that need to override register
        values unconditionally.  The address is added to :attr:`_written_addresses`
        so that subsequent MQTT updates from the live data source do not overwrite it.

        Sets :attr:`_internal_write` to ``True`` around the write so the
        :class:`SimDevice` action bypasses the RemoteEMS gate.

        Args:
            address: Starting register address.
            values: Raw uint16 register values to write.
        """
        if self._server is None:
            _logger.warning(f"#{self.device_address} force_set_registers({address}, {values}) called before server is initialised")
            return
        self._written_addresses.add(address)
        if self.addresses.get(address) and self.addresses[address].debug_logging:
            _logger.debug(f"#{self.device_address} force_set_registers({address}, {values})")
        self._internal_write = True
        try:
            await self._server.context.async_setValues(self.device_address, 0x10, address, values)
        finally:
            self._internal_write = False

    def _handle_mqtt_message(self, topic: str, value: str, debug: bool = False) -> None:
        """Update the register for *topic*'s sensor from an incoming MQTT message.

        Called on the asyncio event-loop thread via
        :pymeth:`CustomMqttHandler.on_message`.  Schedules :meth:`_async_set_value`
        as an asyncio task so the coroutine can await ``server.context.async_setValues``.

        Args:
            topic: The MQTT topic that received a message.
            value: The decoded payload string.
            debug: Forwarded to :meth:`_async_set_value` to control debug logging.
        """
        sensor = self._topics.get(topic)
        if sensor is None:
            return
        asyncio.ensure_future(self._async_set_value(sensor, value, f"mqtt::{topic}", debug=debug))


    def setValues(self, address: int, values: int | list[int] | list[bool]) -> None:
        """Cache raw uint16 values in :attr:`_initial_registers` during initialisation."""
        if not isinstance(values, list):
            values = [values]
        for i, v in enumerate(values):
            self._initial_registers[address + i] = v

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
            return (TestConfig.initial_firmware, "inverter_firmware_version")

        if sensor.data_type == ModbusClientMixin.DATATYPE.STRING:
            return ("string value" if not sensor.latest_raw_state else sensor.latest_raw_state, "string")

        if sensor.address == OutputType.ADDRESS:
            return (2, "output_type")
        if TestConfig.simulate_power_factor_errors and sensor.address == PowerFactor.ADDRESS:
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
        to :attr:`_initial_registers` via :meth:`_set_value`.

        Args:
            sensor: A sensor descriptor object.  Must have at least ``address``,
                ``device_address``, ``publishable``, and ``data_type`` attributes.
        """
        self.addresses[sensor.address] = sensor
        if not sensor.publishable:
            return
        value, source = self._get_initial_value(sensor)
        if sensor.data_type != ModbusClientMixin.DATATYPE.STRING:
            self._register_mqtt_topic(sensor, source)
        self._set_value(sensor, value, source)


async def simulate_firmware_version_upgrade(data_block: CustomDataBlock, wait_for_seconds: int) -> None:
    """Simulate inverter firmware version upgrade on *data_block*.

    Args:
        data_block: The inverter device's data block.
        wait_for_seconds: Idle time before simulating firmware
            update, in seconds.
    """
    try:
        _logger.info(f"Waiting for {wait_for_seconds} seconds before simulating inverter firmware update for device address {data_block.device_address}...")
        await asyncio.sleep(wait_for_seconds)
        _logger.info(f"Simulating inverter firmware update for device address {data_block.device_address}")
        await data_block.force_set_registers(
            InverterFirmwareVersion.ADDRESS,
            ModbusClientMixin.convert_to_registers(TestConfig.upgrade_firmware, ModbusClientMixin.DATATYPE.STRING),
        )
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
            await data_block.force_set_registers(GridStatus.ADDRESS, [1])
            await asyncio.sleep(duration_seconds)
            await data_block.force_set_registers(GridStatus.ADDRESS, [0])
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
) -> None:
    """Build and run the async Modbus TCP test server.

    Performs the following steps:

    1. Instantiates all sensor objects via :func:`~tests.utils.get_sensor_instances`.
    2. Groups sensors into contiguous register ranges for bulk reads.
    3. Optionally pre-populates values from a live *modbus_client*.
    4. Creates a :class:`CustomDataBlock` per device address and calls
       :meth:`~CustomDataBlock.add_sensor` for every sensor.
    5. Calls :meth:`~CustomDataBlock.build_sim_device` to produce a
       :class:`SimDevice` per device address.
    6. Starts :class:`ModbusTcpServer` with a ``trace_pdu`` hook that injects
       latency and tracks write-locked addresses.
    7. Sets :attr:`CustomDataBlock._server` on every data block so that
       post-initialisation writes (MQTT, simulation helpers) can reach the
       server's :class:`SimDevice` context.
    8. Optionally co-schedules :func:`simulate_grid_outage` for the plant device.
    9. Optionally co-schedules :func:`simulate_firmware_version_upgrade` for the
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
        if sensor.address in TestConfig.registers_to_debug or 0 in TestConfig.registers_to_debug:
            sensor.debug_logging = True
        address = sensor.address
        count = sensor.count
        device_address = sensor.device_address
        input_type = sensor.input_type

    if modbus_client is not None:
        await prepopulate(modbus_client, groups)

    if any(TestConfig.registers_to_debug):
        _logger.info(f"Enabling debug logging because registers {TestConfig.registers_to_debug} were specified for debugging...")
        _logger.setLevel(logging.DEBUG)

    _logger.info("Creating data blocks...")
    latency_budget = LatencyBudget()
    for sensor in sorted_sensors:
        if hasattr(sensor, "device_address"):
            if sensor.device_address not in context:
                context[sensor.device_address] = CustomDataBlock(sensor.device_address, mqtt_client, latency_budget)
            context[sensor.device_address].add_sensor(sensor)

    _logger.info("Building SimDevice objects...")
    sim_devices: list[SimDevice] = [block.build_sim_device() for block in context.values()]

    try:
        with open("/app/build_date.txt", "r") as f:
            BUILD_DATE = f.read().strip()
    except FileNotFoundError:
        BUILD_DATE = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

    _logger.info(f"Starting ASYNC Modbus TCP Testing Server (build date: {BUILD_DATE})...")
    if log_level <= logging.INFO:
        logging.getLogger("pymodbus").setLevel(logging.INFO)
    try:
        # ModbusTcpServer is instantiated (not started) first so that we can hand
        # a reference to each CustomDataBlock before serve_forever() is called.
        # The trace_pdu hook handles latency injection and write-lock tracking.
        server = ModbusTcpServer(
            context=sim_devices,
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
            trace_pdu=_make_trace_pdu(context),
        )

        # Hand every data block a server reference so that post-initialisation
        # writes (MQTT updates, simulation helpers) can reach the SimDevice context
        # via server.context.async_setValues().
        for block in context.values():
            block._server = server

        tasks = [server.serve_forever()]
        if TestConfig.simulate_grid_outages:
            tasks.append(simulate_grid_outage(context[Constants.PLANT_DEVICE_ADDRESS], wait_for_seconds=30, duration_seconds=30) if Constants.PLANT_DEVICE_ADDRESS in context else asyncio.sleep(0))
        if TestConfig.simulate_firmware_upgrade:
            tasks.append(simulate_firmware_version_upgrade(context[inverter_device_address], wait_for_seconds=45))
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

    Reads configuration from environment variables and uses it to optionally
    configure an MQTT client and a live Modbus client for register
    pre-population. Falls back to a fully synthetic server (no MQTT, no live
    Modbus source) when no data-source values are provided.

    The MQTT client is always cleanly shut down in a ``finally`` block,
    regardless of how the server exits.
    """

    def _env(name: str) -> str | None:
        value = os.getenv(name)
        return value.strip() if value else None

    def _env_bool(name: str, default: bool) -> bool:
        value = _env(name)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def _env_int(name: str, default: int) -> int:
        value = _env(name)
        if value is None:
            return default
        return int(value)

    def _env_log_level(name: str, default: int) -> int:
        value = _env(name)
        if value is None:
            return default
        return logging.getLevelNamesMapping()[value.upper()]

    def _env_protocol(name: str) -> Protocol | None:
        value = _env(name)
        if value is None:
            return None
        normalized = value.upper()
        if not normalized.startswith("V"):
            normalized = f"V{normalized.replace('.', '_')}"
        return Protocol[normalized]

    def _env_registers(name: str) -> list[int]:
        value = _env(name)
        if value is None:
            return []
        return [int(r) for segment in value.split(",") if segment.strip() for r in (range(int(segment.split("-")[0]), int(segment.split("-")[1]) + 1) if "-" in segment.strip() else [segment.strip()])]

    mqtt_client = None
    modbus_client = None

    mqtt_broker = _env("MODBUS_TEST_SERVER_MQTT_BROKER")
    if mqtt_broker:
        mqtt_port = _env_int("MODBUS_TEST_SERVER_MQTT_PORT", 1883)
        mqtt_username = _env("MODBUS_TEST_SERVER_MQTT_USERNAME")
        mqtt_password = _env("MODBUS_TEST_SERVER_MQTT_PASSWORD")
        mqtt_log_level = _env_log_level("MODBUS_TEST_SERVER_MQTT_LOG_LEVEL", logging.INFO)

        mqtt_client = mqtt.Client(
            CallbackAPIVersion.VERSION2,
            client_id=f"sigenergy2mqtt_modbus_test_server_{''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))}",
            userdata=CustomMqttHandler(asyncio.get_running_loop(), log_level=mqtt_log_level),
        )
        mqtt_client.username_pw_set(mqtt_username, mqtt_password)
        mqtt_client.connect(mqtt_broker, mqtt_port, 60)
        _logger.info(f"Connected to MQTT broker mqtt://{mqtt_broker}:{mqtt_port} as data source")
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()

    modbus_host = _env("MODBUS_TEST_SERVER_MODBUS_HOST")
    if modbus_host:
        modbus_port = _env_int("MODBUS_TEST_SERVER_MODBUS_PORT", 502)
        modbus_client = ModbusClient(modbus_host, port=modbus_port, timeout=1, retries=0)
        _logger.info(f"Using Modbus source modbus://{modbus_host}:{modbus_port}")

    TestConfig.log_level = _env_log_level("MODBUS_TEST_SERVER_LOG_LEVEL", logging.INFO)
    TestConfig.initial_firmware = _env("MODBUS_TEST_SERVER_INITIAL_FIRMWARE") or "V100R001C00SPC112B107G"
    TestConfig.upgrade_firmware = _env("MODBUS_TEST_SERVER_UPGRADE_FIRMWARE") or "V100R001C00SPC113"
    TestConfig.protocol_version = _env_protocol("MODBUS_TEST_SERVER_PROTOCOL_VERSION")
    TestConfig.registers_to_debug = _env_registers("MODBUS_TEST_SERVER_REGISTERS_TO_DEBUG")
    TestConfig.use_simplified_topics = _env_bool("MODBUS_TEST_SERVER_USE_SIMPLIFIED_TOPICS", True)
    TestConfig.simulate_grid_outages = _env_bool("MODBUS_TEST_SERVER_SIMULATE_GRID_OUTAGES", False)
    TestConfig.simulate_firmware_upgrade = _env_bool("MODBUS_TEST_SERVER_SIMULATE_FIRMWARE_UPGRADE", False)
    TestConfig.simulate_power_factor_errors = _env_bool("MODBUS_TEST_SERVER_SIMULATE_POWER_FACTOR_ERRORS", False)

    server_host = _env("MODBUS_TEST_SERVER_HOST") or "0.0.0.0"
    server_port = _env_int("MODBUS_TEST_SERVER_PORT", 502)

    try:
        await run_async_server(
            mqtt_client,
            modbus_client,
            use_simplified_topics=TestConfig.use_simplified_topics,
            protocol_version=TestConfig.protocol_version,
            log_level=TestConfig.log_level,
            host=server_host,
            port=server_port,
        )
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(async_helper(), debug=True)
