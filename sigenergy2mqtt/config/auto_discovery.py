"""Modbus auto-discovery for Sigenergy plants (inverters and chargers)."""

import asyncio
import ipaddress
import logging
import signal
import time
from dataclasses import dataclass, field
from typing import cast

import psutil
from pymodbus import ExceptionResponse, FramerType, ModbusException
from pymodbus.client import AsyncModbusTcpClient


class DiscoveryInterruptedError(Exception):
    """Internal exception to signal that auto-discovery was interrupted."""

    pass


# ---------------------------------------------------------------------------
# Interruption flag
#
# Set to True by an external synchronous signal handler (e.g. _early_exit in
# main()) *before* the asyncio event loop starts.  _check_interrupted() is
# called at discrete checkpoints throughout the scan so that a pre-loop signal
# aborts discovery as soon as the current operation finishes.
# ---------------------------------------------------------------------------

_interrupted: bool = False


def _check_interrupted() -> None:
    """Raise DiscoveryInterruptedError if a pre-loop signal handler set _interrupted."""
    if _interrupted:
        raise DiscoveryInterruptedError("Auto-discovery interrupted by signal")


# ---------------------------------------------------------------------------
# Register address constants
# ---------------------------------------------------------------------------

REG_PLANT_RUNNING_STATE = 30051
REG_INVERTER_RUNNING_STATE = 30578
REG_DC_CHARGER_CHARGING_CURRENT = 31501
REG_AC_CHARGER_SYSTEM_STATE = 32000
REG_SERIAL_NUMBER = 30515
REG_SERIAL_NUMBER_COUNT = 10

# ---------------------------------------------------------------------------
# Module-level serial number registry
#
# Kept at module level so that external callers (tests, main()) can read and
# reset it between scans via auto_discovery.serial_numbers.
# ---------------------------------------------------------------------------

serial_numbers: list[str] = []

# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


@dataclass
class DiscoveredDevice:
    host: str
    port: int
    ac_chargers: list[int] = field(default_factory=list)
    dc_chargers: list[int] = field(default_factory=list)
    inverters: list[int] = field(default_factory=list)

    def has_devices(self) -> bool:
        return bool(self.ac_chargers or self.dc_chargers or self.inverters)

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "ac-chargers": self.ac_chargers,
            "dc-chargers": self.dc_chargers,
            "inverters": self.inverters,
        }


# ---------------------------------------------------------------------------
# TCP ping scan
# ---------------------------------------------------------------------------


async def ping_scan(ip_list: list[str], concurrent: int = 100, timeout: float = 0.5, port: int = 502) -> dict[str, float]:
    """Async TCP port scan. Returns {ip: latency_seconds} for responsive hosts.

    IPs are processed in chunks of `concurrent` so that _interrupted is checked
    between chunks and a pre-loop signal aborts the scan promptly.
    """
    if not ip_list:
        return {}

    # Honour a pre-loop interruption signal immediately.
    if _interrupted:
        return {}

    if concurrent <= 0:
        concurrent = 1

    found: dict[str, float] = {}

    async def check_single_host(ip: str) -> tuple[str, float | None]:
        start = time.perf_counter()
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=float(timeout))
            latency = time.perf_counter() - start
            writer.close()
            await writer.wait_closed()
            logging.debug(f" -> {ip}:{port} responded in {latency:.3f}s")
            return ip, latency
        except (asyncio.TimeoutError, OSError, ConnectionRefusedError):
            logging.debug(f" -> {ip}:{port} did not respond within {timeout:.2f}s")
            return ip, None

    try:
        for i in range(0, len(ip_list), concurrent):
            _check_interrupted()
            chunk = ip_list[i : i + concurrent]

            tasks: list[asyncio.Task] = []
            try:
                for ip in chunk:
                    tasks.append(asyncio.ensure_future(check_single_host(ip)))
                results = await asyncio.gather(*tasks, return_exceptions=True)
            except (DiscoveryInterruptedError, asyncio.CancelledError):
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

            for result in results:
                if isinstance(result, BaseException):
                    logging.debug(f"TCP check raised: {result}")
                    continue
                ip, latency = result
                if latency is not None:
                    found[ip] = latency

    except DiscoveryInterruptedError:
        raise KeyboardInterrupt("Auto-discovery interrupted by signal")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logging.debug(f"TCP port scan failed: {exc}")

    return found


# ---------------------------------------------------------------------------
# Low-level Modbus helpers
# ---------------------------------------------------------------------------


async def probe_register(modbus: AsyncModbusTcpClient, address: int, count: int = 1, device_id: int = 247, max_reconnect_attempts: int = 3) -> bool:
    """Read an input register, returning True if it responds without error."""
    host = modbus.comm_params.host
    port = modbus.comm_params.port
    logging.debug(f" -> Probing modbus://{host}:{port} device_id={device_id} register {address} count={count}")
    try:
        result = await modbus.read_input_registers(address=address, count=count, device_id=device_id)
        if result and not result.isError() and hasattr(result, "registers") and len(result.registers) >= count:
            return True
        return False
    except ModbusException as exc:
        logging.debug(f" -> Probe failed modbus://{host}:{port} device_id={device_id} register {address}: {exc}")
        await _reconnect(modbus, max_attempts=max_reconnect_attempts)
    except Exception as exc:
        logging.debug(f" -> Probe unexpected error modbus://{host}:{port} device_id={device_id} register {address}: {exc}")
    return False


async def _reconnect(modbus: AsyncModbusTcpClient, *, max_attempts: int = 3) -> None:
    """Re-establish a dropped Modbus connection, capped at max_attempts retries."""
    host = modbus.comm_params.host
    port = modbus.comm_params.port
    for attempt in range(1, max_attempts + 1):
        if modbus.connected:
            return
        logging.debug(f"Reconnect attempt {attempt}/{max_attempts} to {host}:{port}")
        modbus.close()
        try:
            await modbus.connect()
        except Exception as exc:
            logging.debug(f"Reconnect attempt {attempt} failed: {exc}")
        if modbus.connected:
            return
        await asyncio.sleep(0.1 * attempt)
    logging.warning(f"Could not reconnect to {host}:{port} after {max_attempts} attempts")


async def get_serial_number(modbus: AsyncModbusTcpClient, device_id: int = 1) -> str | None:
    """Read and decode the serial number string from a device."""
    host = modbus.comm_params.host
    port = modbus.comm_params.port
    logging.debug(f" -> Reading serial number from modbus://{host}:{port} device_id={device_id} register {REG_SERIAL_NUMBER} count={REG_SERIAL_NUMBER_COUNT}")
    try:
        rr = await modbus.read_input_registers(address=REG_SERIAL_NUMBER, count=REG_SERIAL_NUMBER_COUNT, device_id=device_id)
        if rr and not rr.isError() and not isinstance(rr, ExceptionResponse) and hasattr(rr, "registers") and len(rr.registers) >= REG_SERIAL_NUMBER_COUNT:
            return cast(str, modbus.convert_from_registers(rr.registers, AsyncModbusTcpClient.DATATYPE.STRING))
    except ModbusException as exc:
        logging.debug(f" -> Serial number read failed modbus://{host}:{port} device_id={device_id}: {exc}")
    except Exception as exc:
        logging.debug(f" -> Serial number unexpected error modbus://{host}:{port} device_id={device_id}: {exc}")
    return None


# ---------------------------------------------------------------------------
# Device scanning
# ---------------------------------------------------------------------------


async def _probe_device_id(modbus: AsyncModbusTcpClient, device_id: int, device: DiscoveredDevice, max_reconnect_attempts: int = 3) -> None:
    """Probe a single device ID and classify it into the appropriate device list."""
    _check_interrupted()
    host, port = device.host, device.port

    # DC charger + inverter (combined unit)
    if await probe_register(modbus, REG_DC_CHARGER_CHARGING_CURRENT, device_id=device_id):
        serial = await get_serial_number(modbus, device_id=device_id)
        if serial:
            if serial not in serial_numbers:
                serial_numbers.append(serial)
                logging.info(f" -> Found Inverter {device_id} ({serial}) and DC-Charger at {host}:{port}: Device ID={device_id}")
                device.dc_chargers.append(device_id)
                device.inverters.append(device_id)
            else:
                logging.info(f" -> IGNORED Inverter {device_id} at {host}:{port} - serial number {serial} already discovered")
        return

    # Inverter only
    if await probe_register(modbus, REG_INVERTER_RUNNING_STATE, device_id=device_id):
        serial = await get_serial_number(modbus, device_id=device_id)
        if serial:
            if serial not in serial_numbers:
                serial_numbers.append(serial)
                logging.info(f" -> Found Inverter {device_id} ({serial}) at {host}:{port}: Device ID={device_id}")
                device.inverters.append(device_id)
            else:
                logging.info(f" -> IGNORED Inverter {device_id} at {host}:{port} - serial number {serial} already discovered")
        return

    # AC charger (only probe once at least one inverter is confirmed on this host)
    if device.inverters and await probe_register(modbus, REG_AC_CHARGER_SYSTEM_STATE, device_id=device_id):
        logging.info(f" -> Found AC-Charger at {host}:{port}: Device ID={device_id}")
        device.ac_chargers.append(device_id)


async def scan_host(ip: str, port: int, results: list, timeout: float = 0.25, retries: int = 0, max_reconnect_attempts: int = 3, device_id_concurrency: int = 20) -> None:
    """Connect to a single host, enumerate its Sigenergy devices, and append to results."""
    modbus = AsyncModbusTcpClient(host=ip, port=port, framer=FramerType.SOCKET, timeout=timeout, retries=retries)
    try:
        await modbus.connect()
        if not modbus.connected:
            return

        logging.info(f"Found Modbus device at {ip}:{port}")

        # Verify this is a Sigenergy plant before probing all 246 device IDs.
        if not await probe_register(modbus, REG_PLANT_RUNNING_STATE, device_id=247):
            logging.info(f" -> Ignored Modbus device at {ip}: No Plant running state found")
            return

        logging.info(f" -> Found Sigenergy Plant at {ip}:{port}")
        device = DiscoveredDevice(host=ip, port=port)

        # Batch probing of all 246 device IDs
        device_ids = list(range(1, 247))
        for i in range(0, len(device_ids), device_id_concurrency):
            _check_interrupted()
            chunk = device_ids[i : i + device_id_concurrency]
            tasks: list[asyncio.Task] = []
            try:
                for did in chunk:
                    tasks.append(asyncio.ensure_future(_probe_device_id(modbus, did, device, max_reconnect_attempts)))
                await asyncio.gather(*tasks, return_exceptions=False)
            except (DiscoveryInterruptedError, asyncio.CancelledError):
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

        if not device.has_devices():
            logging.info(f" -> Ignored Modbus device at {ip}:{port}: No new inverters or chargers found")
        else:
            results.append(device.to_dict())

    except DiscoveryInterruptedError:
        raise KeyboardInterrupt("Auto-discovery interrupted by signal")
    except ModbusException as exc:
        logging.debug(f"Modbus connection to {ip}:{port} failed: {exc}")
    finally:
        modbus.close()


# ---------------------------------------------------------------------------
# Network enumeration
# ---------------------------------------------------------------------------


def _local_networks() -> dict[str, ipaddress.IPv4Network]:
    """Return {local_ip: subnet} for each relevant non-loopback interface."""
    _excluded_prefixes = ("docker", "br-", "veth")
    _excluded_names = {"lo", "hassio"}
    networks: dict[str, ipaddress.IPv4Network] = {}

    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        if iface_name in _excluded_names or any(iface_name.startswith(p) for p in _excluded_prefixes):
            continue
        for addr in iface_addrs:
            if addr.family.name == "AF_INET" and addr.address and addr.netmask and not addr.address.startswith("127."):
                network = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
                networks[addr.address] = network
                logging.info(f"Found network '{iface_name}' {network} via {addr.address}/{addr.netmask}")
                break

    return networks


# ---------------------------------------------------------------------------
# Top-level scan
# ---------------------------------------------------------------------------


async def scan(
    port: int = 502,
    ping_timeout: float = 0.5,
    modbus_timeout: float = 0.25,
    modbus_retries: int = 0,
    ping_concurrency: int = 100,
    host_concurrency: int = 10,
    device_id_concurrency: int = 20,
    max_reconnect_attempts: int = 3,
) -> list[dict]:
    """Discover all Sigenergy plants reachable from local network interfaces.

    Returns a list of device dicts, each with keys:
        host, port, ac-chargers, dc-chargers, inverters
    """
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    started = time.perf_counter()

    networks = _local_networks()
    own_ips = set(networks.keys())
    candidate_ips: list[str] = [str(host) for subnet in networks.values() for host in subnet.hosts() if str(host) not in own_ips]

    logging.info(f"Scanning for active devices across {len(candidate_ips)} candidate IPs…")
    ping_results = await ping_scan(candidate_ips, concurrent=ping_concurrency, timeout=ping_timeout, port=port)

    # Always include localhost first; sort the rest by ascending latency.
    active_ips: list[str] = ["127.0.0.1"] + sorted(
        (ip for ip in ping_results if ip != "127.0.0.1"),
        key=lambda ip: ping_results[ip],
    )

    results: list[dict] = []
    sem = asyncio.Semaphore(host_concurrency)

    async def scan_with_sem(ip: str) -> None:
        _check_interrupted()
        async with sem:
            await scan_host(ip, port, results, timeout=modbus_timeout, retries=modbus_retries, max_reconnect_attempts=max_reconnect_attempts, device_id_concurrency=device_id_concurrency)

    try:
        await asyncio.gather(
            *[scan_with_sem(ip) for ip in active_ips],
            return_exceptions=False,
        )
    except DiscoveryInterruptedError:
        raise KeyboardInterrupt("Auto-discovery interrupted by signal")
    except Exception as exc:
        logging.debug(f"Scan failed: {exc}")

    elapsed = time.perf_counter() - started
    logging.info(f"Scan completed in {elapsed:.2f}s")
    return results


# ---------------------------------------------------------------------------
# Signal handling helper (used by async entry points after the loop is up)
# ---------------------------------------------------------------------------


def _install_async_signal_handlers(stop_event: asyncio.Event) -> None:
    """Register SIGINT/SIGTERM against a running event loop."""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

    async def _async_main() -> None:
        stop_event = asyncio.Event()
        _install_async_signal_handlers(stop_event)

        scan_task = asyncio.ensure_future(scan())
        done, _ = await asyncio.wait([scan_task, asyncio.ensure_future(stop_event.wait())], return_when=asyncio.FIRST_COMPLETED)

        if stop_event.is_set():
            logging.warning("Scan interrupted by signal")
            scan_task.cancel()
            try:
                await scan_task
            except asyncio.CancelledError:
                pass
        else:
            logging.info(f"Auto-discovered: {scan_task.result()}")

    asyncio.run(_async_main())
