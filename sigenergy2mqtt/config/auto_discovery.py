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

REG_AC_CHARGER_SYSTEM_STATE = 32000
REG_DC_CHARGER_CHARGING_CURRENT = 31501
REG_INVERTER_RUNNING_STATE = 30578
REG_INVERTER_SERIAL_NUMBER = 30515
REG_PID_RUNNING_STATUS = 33041
REG_PID_SERIAL_NUMBER = 33015
REG_PSS_COMMUNICATION_STATUS = 32525
REG_PSS_SERIAL_NUMBER = 32515
REG_PLANT_RUNNING_STATE = 30051
REG_SERIAL_NUMBER_COUNT = 10

# ---------------------------------------------------------------------------
# Module-level inverter serial number registry
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
    pid: list[int] = field(default_factory=list)
    pss: list[int] = field(default_factory=list)

    def has_devices(self) -> bool:
        return bool(self.ac_chargers or self.dc_chargers or self.inverters or self.pid or self.pss)

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "ac-chargers": self.ac_chargers,
            "dc-chargers": self.dc_chargers,
            "inverters": self.inverters,
            "pid": self.pid,
            "pss": self.pss,
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
            _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
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
    """Read an input register, returning True if it responds without error.

    Connection closures (from Pymodbus accumulating 3+ failures) are handled
    transparently—they trigger an automatic reconnect without logging noise.
    """
    _check_interrupted()
    host = modbus.comm_params.host
    port = modbus.comm_params.port
    logging.debug(f" -> Probing modbus://{host}:{port} device_id={device_id} register {address} count={count}")
    try:
        result = await modbus.read_input_registers(address=address, count=count, device_id=device_id)
        if result and not result.isError() and hasattr(result, "registers") and len(result.registers) >= count:
            return True
        return False
    except ModbusException as exc:
        exc_str = str(exc)
        # Connection closures are expected when scanning many non-existent devices.
        # Log at debug level only; reconnection happens transparently.
        if "CLOSING CONNECTION" in exc_str or "ERROR: No response" in exc_str:
            logging.debug(" -> Modbus server closed connection (expected during non-existent device scan)")
        else:
            logging.debug(f" -> Probe failed modbus://{host}:{port} device_id={device_id} register {address}: {exc}")
        await _reconnect(modbus, max_attempts=max_reconnect_attempts)
    except Exception as exc:
        logging.debug(f" -> Probe unexpected error modbus://{host}:{port} device_id={device_id} register {address}: {exc}")
    return False


async def get_serial_number(modbus: AsyncModbusTcpClient, sn_address: int, device_id: int = 1) -> str | None:
    """Read and decode the serial number string from a device."""
    host = modbus.comm_params.host
    port = modbus.comm_params.port
    logging.debug(f" -> Reading serial number from modbus://{host}:{port} device_id={device_id} register {sn_address} count={REG_SERIAL_NUMBER_COUNT}")
    try:
        rr = await modbus.read_input_registers(address=sn_address, count=REG_SERIAL_NUMBER_COUNT, device_id=device_id)
        if rr and not rr.isError() and not isinstance(rr, ExceptionResponse) and hasattr(rr, "registers") and len(rr.registers) >= REG_SERIAL_NUMBER_COUNT:
            return cast(str, modbus.convert_from_registers(rr.registers, AsyncModbusTcpClient.DATATYPE.STRING))
    except ModbusException as exc:
        logging.debug(f" -> Serial number read failed modbus://{host}:{port} device_id={device_id}: {exc}")
    except Exception as exc:
        logging.debug(f" -> Serial number unexpected error modbus://{host}:{port} device_id={device_id}: {exc}")
    return None


async def _reconnect(modbus: AsyncModbusTcpClient, *, max_attempts: int = 3) -> None:
    """Re-establish a dropped Modbus connection, capped at max_attempts retries.

    Pymodbus closes connections after accumulating too many errors. This function
    quickly re-establishes the connection when that happens.
    """
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
    if not modbus.connected:
        logging.warning(f"Could not reconnect to {host}:{port} after {max_attempts} attempts")


async def _probe_device_id(modbus: AsyncModbusTcpClient, device_id: int, device: DiscoveredDevice, max_reconnect_attempts: int = 3, exclude_devices: list[str] = []) -> None:
    """Attempt to identify a device at this device_id. Appends to device."""
    host = device.host
    port = device.port

    # DC charger (probe at lowest device_id first, max 4 devices per host)
    if "DCCharger" not in exclude_devices and len(device.dc_chargers) < 4 and await probe_register(modbus, REG_DC_CHARGER_CHARGING_CURRENT, device_id=device_id):
        logging.info(f" -> Found DC-Charger at {host}:{port}: Device ID={device_id}")
        device.dc_chargers.append(device_id)

    # Inverter
    if await probe_register(modbus, REG_INVERTER_RUNNING_STATE, device_id=device_id):
        serial = await get_serial_number(modbus, REG_INVERTER_SERIAL_NUMBER, device_id=device_id)
        if serial:
            if serial not in serial_numbers:
                serial_numbers.append(serial)
                logging.info(f" -> Found Inverter {device_id} ({serial}) at {host}:{port}: Device ID={device_id}")
                device.inverters.append(device_id)
            else:
                logging.info(f" -> IGNORED Inverter {device_id} at {host}:{port} - serial number {serial} already discovered")
        return

    # AC charger
    if "ACCharger" not in exclude_devices and await probe_register(modbus, REG_AC_CHARGER_SYSTEM_STATE, device_id=device_id):
        logging.info(f" -> Found AC-Charger at {host}:{port}: Device ID={device_id}")
        device.ac_chargers.append(device_id)

    # PSS
    if "PSS" not in exclude_devices and await probe_register(modbus, REG_PSS_COMMUNICATION_STATUS, device_id=device_id):
        serial = await get_serial_number(modbus, REG_PSS_SERIAL_NUMBER, device_id=device_id)
        if serial:
            if serial not in serial_numbers:
                serial_numbers.append(serial)
                logging.info(f" -> Found PSS {device_id} ({serial}) at {host}:{port}: Device ID={device_id}")
                device.pss.append(device_id)
            else:
                logging.info(f" -> IGNORED PSS {device_id} at {host}:{port} - serial number {serial} already discovered")

    # PID
    if "PID" not in exclude_devices and await probe_register(modbus, REG_PID_RUNNING_STATUS, device_id=device_id):
        serial = await get_serial_number(modbus, REG_PID_SERIAL_NUMBER, device_id=device_id)
        if serial:
            if serial not in serial_numbers:
                serial_numbers.append(serial)
                logging.info(f" -> Found PID {device_id} ({serial}) at {host}:{port}: Device ID={device_id}")
                device.pid.append(device_id)
            else:
                logging.info(f" -> IGNORED PID {device_id} at {host}:{port} - serial number {serial} already discovered")


async def scan_host(ip: str, port: int, results: list, timeout: float = 0.25, retries: int = 0, max_reconnect_attempts: int = 3, exclude_devices: list[str] = []) -> None:
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

        # Sequential probing of all 246 device IDs
        # Each probe respects the modbus_timeout, and _check_interrupted() allows
        # keyboard interrupt handling between each device scan.
        total_device_ids = 246
        last_progress_log = 0

        for device_id in range(1, total_device_ids + 1):
            _check_interrupted()
            await _probe_device_id(modbus, device_id, device, max_reconnect_attempts, exclude_devices)

            # Log progress every 25 device IDs scanned
            if device_id - last_progress_log >= 25:
                logging.info(f" -> Scanned {device_id}/{total_device_ids} device IDs on {ip}:{port}")
                last_progress_log = device_id

        if not device.has_devices():
            logging.info(f" -> Ignored Modbus device at {ip}:{port}: No new inverters or chargers found")
        else:
            results.append(device.to_dict())
            logging.info(
                f" -> Scan complete for {ip}:{port}: Found {len(device.inverters)} inverter(s) {sorted(device.inverters)}, "
                f"{len(device.dc_chargers)} DC charger(s) {sorted(device.dc_chargers)}, "
                f"{len(device.ac_chargers)} AC charger(s) {sorted(device.ac_chargers)}, "
                f"{len(device.pid)} PID(s) {sorted(device.pid)}, "
                f"{len(device.pss)} PSS(s) {sorted(device.pss)}"
            )

    except DiscoveryInterruptedError:
        raise KeyboardInterrupt("Auto-discovery interrupted by signal")
    except ModbusException as exc:
        logging.debug(f"Modbus connection to {ip}:{port} failed: {exc}")
    finally:
        modbus.close()


# ---------------------------------------------------------------------------
# Network enumeration
# ---------------------------------------------------------------------------


def _local_networks(include_networks: list[str] | None = None) -> dict[str, ipaddress.IPv4Network]:
    """Return {local_ip: subnet} for each relevant non-loopback interface.

    Includes:
    1. Networks directly attached to network interfaces that match include_networks
    2. Networks from include_networks that are accessible via routing (indirect)
    """
    _excluded_prefixes = ("docker", "br-", "veth")
    _excluded_names = {"lo", "hassio"}
    networks: dict[str, ipaddress.IPv4Network] = {}

    # Parse include_networks into IPv4Network objects for easier comparison
    include_networks_parsed: set[ipaddress.IPv4Network] = set()
    if include_networks:
        for network_str in include_networks:
            try:
                include_networks_parsed.add(ipaddress.IPv4Network(network_str, strict=False))
            except ValueError as e:
                logging.warning(f"Invalid network in include_networks: {network_str} ({e})")

    # Step 1: Find directly attached networks from network interfaces
    directly_attached: set[ipaddress.IPv4Network] = set()

    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        if iface_name in _excluded_names or any(iface_name.startswith(p) for p in _excluded_prefixes):
            logging.info(f"Excluded network interface '{iface_name}' from auto-discovery")
            continue
        for addr in iface_addrs:
            if addr.family.name == "AF_INET" and addr.address and addr.netmask and not addr.address.startswith("127."):
                network = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)

                # If include_networks is specified, only include matching networks
                if include_networks_parsed and network not in include_networks_parsed:
                    logging.info(f"Excluded network interface '{iface_name}' {network} via {addr.address} from auto-discovery (not in specified networks)")
                    continue

                networks[addr.address] = network
                directly_attached.add(network)
                logging.info(f"Included network interface '{iface_name}' {network} via {addr.address} (directly attached)")
                break

    # Step 2: Add indirectly accessible networks from include_networks
    # These are networks specified in include_networks but not directly attached to any interface
    if include_networks_parsed:
        for network in include_networks_parsed:
            if network not in directly_attached:
                # Generate a pseudo-IP for indirect networks (use network address + 1)
                pseudo_ip = str(list(network.hosts())[0]) if list(network.hosts()) else str(network.network_address + 1)
                networks[pseudo_ip] = network
                logging.info(f"Included network {network} via routing (indirectly accessible)")

    return networks


# ---------------------------------------------------------------------------
# Top-level scan
# ---------------------------------------------------------------------------


async def scan(
    include_networks: list[str] | None = None,
    exclude_devices: list[str] | None = None,
    port: int = 502,
    ping_timeout: float = 0.5,
    modbus_timeout: float = 0.25,
    modbus_retries: int = 0,
    ping_concurrency: int = 100,
    host_concurrency: int = 10,
    max_reconnect_attempts: int = 3,
) -> list[dict]:
    """Discover all Sigenergy plants reachable from local network interfaces.

    Returns a list of device dicts, each with keys:
        host, port, ac-chargers, dc-chargers, inverters

    Scans both directly-attached networks and indirectly-accessible networks
    (via routing) that are specified in include_networks.

    Notes:
        Connection closures: Pymodbus closes the connection after retries+3
        consecutive failures. This is handled gracefully with automatic
        reconnection, so brief connection drops during scanning don't block
        the scan. The connection overhead is minimal compared to the time
        saved by failing fast on non-existent device IDs.
    """
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    started = time.perf_counter()

    serial_numbers.clear()

    networks = _local_networks(include_networks)
    if not networks:
        logging.warning("No networks found to be scanned for auto-discovery! Scanning localhost only.")
        networks["127.0.0.1"] = ipaddress.IPv4Network("127.0.0.1/255.255.255.255", strict=False)

    candidate_ips: list[str] = [str(host) for subnet in networks.values() for host in subnet.hosts()]

    logging.info(f"Scanning for active devices across {len(candidate_ips)} candidate IPs…")
    ping_results = await ping_scan(candidate_ips, concurrent=ping_concurrency, timeout=ping_timeout, port=port)

    # Sort by ascending latency.
    active_ips: list[str] = sorted((ip for ip in ping_results), key=lambda ip: ping_results[ip])

    logging.info(f"Found {len(active_ips)} active Modbus device(s), starting detailed scan…")

    results: list[dict] = []
    sem = asyncio.Semaphore(host_concurrency)

    async def scan_with_sem(ip: str) -> None:
        _check_interrupted()
        async with sem:
            await scan_host(ip, port, results, timeout=modbus_timeout, retries=modbus_retries, max_reconnect_attempts=max_reconnect_attempts, exclude_devices=exclude_devices or [])

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

    # Summary of findings
    logging.info(f"Scan completed in {elapsed:.2f}s")
    if results:
        logging.info(
            f"Found {len(results)} Sigenergy plant(s) with "
            f"{sum(len(r.get('inverters', [])) for r in results)} inverter(s), "
            f"{sum(len(r.get('dc-chargers', [])) for r in results)} DC charger(s), "
            f"{sum(len(r.get('ac-chargers', [])) for r in results)} AC charger(s), "
            f"{sum(len(r.get('pid', [])) for r in results)} PID(s), "
            f"{sum(len(r.get('pss', [])) for r in results)} PSS(s)"
        )
    else:
        logging.info("No Sigenergy plants found during auto-discovery.")

    return results


# ---------------------------------------------------------------------------
# Signal handling helper (used by async entry points after the loop is up)
# ---------------------------------------------------------------------------


def _install_async_signal_handlers(stop_event: asyncio.Event) -> None:
    """Register SIGINT/SIGTERM against a running event loop."""
    global _interrupted

    def signal_handler() -> None:
        """Handle SIGINT/SIGTERM by setting the interrupted flag and stop event."""
        global _interrupted
        _interrupted = True
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Use INFO level for normal operation (shows progress)
    # Use DEBUG level to troubleshoot connection issues
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    async def _async_main() -> None:
        stop_event = asyncio.Event()
        _install_async_signal_handlers(stop_event)

        # Scan with improved connection stability (modbus_retries=3 by default)
        # Set modbus_retries higher if you see frequent reconnections,
        # or lower if you want to fail faster on unresponsive servers
        scan_task = asyncio.ensure_future(scan(include_networks=["10.10.20.75/32"]))
        done, _ = await asyncio.wait([scan_task, asyncio.ensure_future(stop_event.wait())], return_when=asyncio.FIRST_COMPLETED)

        if stop_event.is_set():
            logging.warning("Scan interrupted by signal")
            scan_task.cancel()
            try:
                await scan_task
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass
        else:
            logging.info(f"Auto-discovered: {scan_task.result()}")

    asyncio.run(_async_main())
