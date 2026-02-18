import asyncio
import ipaddress
import logging
import time
from typing import cast

import psutil
from pymodbus import ExceptionResponse, FramerType, ModbusException
from pymodbus.client import AsyncModbusTcpClient

_interrupted: bool = False


def _check_interrupted():
    """Raise KeyboardInterrupt if a termination signal was received during auto-discovery."""
    if _interrupted:
        raise KeyboardInterrupt("Auto-discovery interrupted by signal")


async def ping_scan(ip_list: list[str], concurrent: int = 100, timeout: float = 0.5, port: int = 502) -> dict[str, float]:
    """Async TCP port scan to check host reachability.

    Returns a dict mapping responsive IP (str) -> latency in seconds (float).
    The `concurrent` parameter limits the number of hosts checked simultaneously.
    The `timeout` is an int number of seconds for the connection attempt.
    The `port` parameter specifies which TCP port to check (default: 502 for Modbus).
    """
    if not ip_list:
        return {}

    # If interrupted before starting, return immediately with no hosts.
    if _interrupted:
        return {}

    found_hosts: dict[str, float] = {}

    async def check_single_host(ip: str) -> tuple[str, float | None]:
        """Check a single host via TCP and return (ip, latency) or (ip, None) if unreachable."""
        start = time.perf_counter()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=float(timeout)
            )
            latency = time.perf_counter() - start
            writer.close()
            await writer.wait_closed()
            logging.debug(f" -> {ip}:{port} responded in {latency:.2f}s")
            return ip, latency
        except (asyncio.TimeoutError, OSError, ConnectionRefusedError):
            logging.debug(f" -> {ip}:{port} did not respond within {timeout:.2f}s")
            return ip, None

    try:
        if concurrent <= 0:
            concurrent = 1

        # Process in chunks of `concurrent` hosts to limit simultaneous connections
        for i in range(0, len(ip_list), concurrent):
            chunk = ip_list[i : i + concurrent]

            # Run all checks in the chunk concurrently
            tasks = []
            try:
                for ip in chunk:
                    tasks.append(asyncio.ensure_future(check_single_host(ip)))
                results = await asyncio.gather(*tasks, return_exceptions=True)
            except (asyncio.CancelledError, KeyboardInterrupt):
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            
            for result in results:
                # Handle exceptions from gather
                if isinstance(result, BaseException):
                    logging.debug(f"TCP check failed with exception: {result}")
                    continue

                ip, latency = result
                if latency is not None:
                    found_hosts[ip] = latency

        return found_hosts
    except Exception as e:
        logging.debug(f"TCP port scan failed: {e}")
        return found_hosts


async def probe_register(modbus: AsyncModbusTcpClient, address: int, count: int = 1, device_id: int = 247) -> bool:
    try:
        logging.debug(f" -> Probing modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {device_id=} register {address} for {count=}")
        result = await modbus.read_input_registers(address=address, count=count, device_id=device_id)
        if result and not result.isError() and hasattr(result, "registers") and len(result.registers) >= count:
            return True
    except ModbusException as e:
        logging.debug(f" -> Probing modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {device_id=} register {address} for {count=} FAILED : {e}")
        while not modbus.connected:
            modbus.close()
            await modbus.connect()
    except Exception as e:
        logging.debug(f" -> Probing modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {device_id=} register {address} for {count=} FAILED : {e}")
    return False


async def get_serial_number(modbus: AsyncModbusTcpClient, device_id: int = 1) -> str | None:
    try:
        logging.debug(f" -> Reading modbus://{modbus.comm_params.host}:{modbus.comm_params.port} {device_id=} register 30515 for count=10 to retrieve serial number")
        rr = await modbus.read_input_registers(address=30515, count=10, device_id=device_id)
        if rr and not rr.isError() and not isinstance(rr, ExceptionResponse) and hasattr(rr, "registers") and len(rr.registers) >= 10:
            serial = modbus.convert_from_registers(rr.registers, AsyncModbusTcpClient.DATATYPE.STRING)
            return cast(str, serial)
    except ModbusException as e:
        logging.debug(f" -> Failed to retrieve serial number for modbus://{modbus.comm_params.host}:{modbus.comm_params.port} device_id {device_id}: {e}")
    except Exception as e:
        logging.debug(f" -> Unexpected error when acquiring serial number for modbus://{modbus.comm_params.host}:{modbus.comm_params.port} device_id {device_id}: {e}")
    return None


serial_numbers = []


async def scan_host(ip: str, port: int, results: list, timeout: float = 0.25, retries: int = 0) -> None:
    modbus = AsyncModbusTcpClient(host=ip, port=port, framer=FramerType.SOCKET, timeout=timeout, retries=retries)
    try:
        await modbus.connect()
        if modbus.connected:
            try:
                logging.info(f"Found Modbus device at {ip}:{port}")
                ac_chargers: list[int] = []
                dc_chargers: list[int] = []
                inverters: list[int] = []
                device: dict[str, str | int | list[int]] = {"host": ip, "port": port, "ac-chargers": ac_chargers, "dc-chargers": dc_chargers, "inverters": inverters}
                if await probe_register(modbus, address=30051, device_id=247):  # Plant running state
                    logging.info(f" -> Found Sigenergy Plant at {ip}:{port}")
                    for device_id in range(1, 247):
                        _check_interrupted()
                        if await probe_register(modbus, address=31501, device_id=device_id):  # [DC Charger] Charging current
                            serial = await get_serial_number(modbus, device_id=device_id)
                            if serial:
                                if serial not in serial_numbers:
                                    serial_numbers.append(serial)
                                    logging.info(f" -> Found Inverter {device_id} ({serial}) and DC-Charger at {ip}:{port}: Device ID={device_id}")
                                    dc_chargers.append(device_id)
                                    inverters.append(device_id)
                                else:
                                    logging.info(f" -> IGNORED Inverter {device_id} at {ip}:{port} - serial number {serial} already discovered")
                                continue
                        if await probe_register(modbus, address=30578, device_id=device_id):  # Inverter Running state
                            serial = await get_serial_number(modbus, device_id=device_id)
                            if serial:
                                if serial not in serial_numbers:
                                    serial_numbers.append(serial)
                                    logging.info(f" -> Found Inverter {device_id} ({serial}) at {ip}:{port}: Device ID={device_id}")
                                    inverters.append(device_id)
                                else:
                                    logging.info(f" -> IGNORED Inverter {device_id} at {ip}:{port} - serial number {serial} already discovered")
                                continue
                        if len(inverters) > 0 and await probe_register(modbus, address=32000, device_id=device_id):  # AC Charger System state
                            logging.info(f" -> Found AC-Charger at {ip}:{port}: Device ID={device_id}")
                            ac_chargers.append(device_id)
                            continue
                    if len(inverters) == 0 and len(dc_chargers) == 0 and len(ac_chargers) == 0:
                        logging.info(f" -> Ignored Modbus device at {ip}:{port}: No new inverters or chargers found")
                    else:
                        results.append(device)
                else:
                    logging.info(f" -> Ignored Modbus device at {ip}: No Plant running state found")
            finally:
                modbus.close()
    except ModbusException as e:
        logging.debug(f"Modbus connection to {ip}:{port} failed: {e}")


async def scan(port: int = 502, ping_timeout: float = 0.5, modbus_timeout: float = 0.25, modbus_retries: int = 0) -> list[dict[str, str | int | list[int]]]:
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

    started = time.perf_counter()

    networks = {}
    for iface_name, iface_info in psutil.net_if_addrs().items():
        if "docker" not in iface_name and iface_name not in ("lo", "hassio") and not iface_name.startswith("br-") and not iface_name.startswith("veth"):
            for addr in iface_info:
                if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                    ip = addr.address
                    netmask = addr.netmask
                    if ip and netmask:
                        network = f"{ip}/{netmask}"
                        networks[ip] = ipaddress.IPv4Network(network, strict=False)
                        logging.info(f"Found network '{iface_name}' {networks[ip]} via {network}")
                        break

    active_ips: dict[str, float] = {"127.0.0.1": 0.0}  # Scan localhost first
    all_ips: list[str] = []
    missing_ips: list[str] = []
    for addr, subnet in networks.items():
        logging.info(f"Scanning for active devices in network {subnet.with_prefixlen}...")
        all_ips.extend([str(ip) for ip in subnet.hosts()])
        missing_ips.extend([ip for ip in all_ips if ip != addr])
    ping_results: dict[str, float] = await ping_scan(missing_ips, timeout=ping_timeout)
    active_ips.update(ping_results)
    ips_sorted_by_latency = dict(sorted(active_ips.items(), key=lambda item: item[1]))

    results = []
    for ip in ips_sorted_by_latency:
        _check_interrupted()
        await scan_host(ip, port, results, modbus_timeout, modbus_retries)

    elapsed = time.perf_counter() - started
    logging.info(f"Scan completed in {elapsed:.2f} seconds")

    return results


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.DEBUG)
    results = asyncio.run(scan(502, 0.5, 0.25, 0))
    logging.info(f"Auto-discovered: {results}")
