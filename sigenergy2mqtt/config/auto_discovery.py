from pymodbus import ExceptionResponse, FramerType, ModbusException
from pymodbus.client import AsyncModbusTcpClient
from scapy.all import IP, ICMP, sr1
import asyncio
import ipaddress
import logging
import psutil
import queue
import threading
import time


def ping_worker(ip_queue, found_hosts, timeout=0.5) -> None:
    while not ip_queue.empty():
        ip = ip_queue.get()
        pkt = IP(dst=ip) / ICMP()
        ans = sr1(pkt, timeout=timeout, verbose=0)
        if ans:
            rx = ans[0][1]
            tx = ans[0][0]
            found_hosts[ip] = rx.time - (tx.sent_time if tx.sent_time is not None else tx.time)
        ip_queue.task_done()


def ping_scan(ip_list, threads=100, timeout=1) -> dict[float, str]:
    ip_queue = queue.Queue()
    found_hosts = {}

    for ip in ip_list:
        ip_queue.put(ip)

    for _ in range(threads):
        t = threading.Thread(target=ping_worker, args=(ip_queue, found_hosts))
        t.daemon = True
        t.start()

    ip_queue.join()
    return found_hosts


async def probe_register(modbus: AsyncModbusTcpClient, address: int, count: int = 1, device_id: int = 247) -> bool:
    try:
        result = await modbus.read_input_registers(address=address, count=count, device_id=device_id)
        if result and not result.isError():
            return True
    except ModbusException:
        while not modbus.connected:
            modbus.close()
            await modbus.connect()
    except Exception as e:
        logging.debug(f"Unexpected error during Modbus probe for {modbus.comm_params.host}:{modbus.comm_params.port} at address {address} with device_id {device_id}: {e}")
    return False


async def get_serial_number(modbus: AsyncModbusTcpClient, device_id: int = 1) -> str | None:
    try:
        rr = await modbus.read_input_registers(address=30515, count=10, device_id=device_id)
        if rr and not rr.isError() and not isinstance(rr, ExceptionResponse):
            serial = modbus.convert_from_registers(rr.registers, AsyncModbusTcpClient.DATATYPE.STRING)
            return serial
    except ModbusException as e:
        logging.debug(f"Failed to retrieve serial number for {modbus.comm_params.host}:{modbus.comm_params.port} device_id {device_id}: {e}")
    except Exception as e:
        logging.debug(f"Unexpected error when acquiring serial number for {modbus.comm_params.host}:{modbus.comm_params.port} device_id {device_id}: {e}")
    return None


serial_numbers = []


async def scan_host(ip: str, port: int, results: list) -> None:
    modbus = AsyncModbusTcpClient(host=ip, port=port, framer=FramerType.SOCKET, timeout=0.25, retries=0)
    try:
        await modbus.connect()
        if modbus.connected:
            try:
                logging.info(f"Found Modbus device at {ip}:{port}")
                device = {"host": ip, "port": port, "ac-chargers": [], "dc-chargers": [], "inverters": []}
                if await probe_register(modbus, address=30051, device_id=247):  # Plant running state
                    logging.info(f" -> Found Sigenergy Plant at {ip}:{port}")
                    for device_id in range(1, 247):
                        if await probe_register(modbus, address=31501, device_id=device_id):  # [DC Charger] Charging current
                            serial = await get_serial_number(modbus, device_id=device_id)
                            if serial and serial not in serial_numbers:
                                serial_numbers.append(serial)
                                logging.info(f" -> Found Inverter {device_id} ({serial}) and DC-Charger at {ip}:{port}: Device ID={device_id}")
                                device["dc-chargers"].append(device_id)
                                device["inverters"].append(device_id)
                            else:
                                logging.info(f" -> IGNORED Inverter {device_id} at {ip}:{port} - serial number {serial} already discovered")
                            continue
                        if await probe_register(modbus, address=30578, device_id=device_id):  # Inverter Running state
                            serial = await get_serial_number(modbus, device_id=device_id)
                            if serial and serial not in serial_numbers:
                                serial_numbers.append(serial)
                                logging.info(f" -> Found Inverter {device_id} ({serial}) at {ip}:{port}: Device ID={device_id}")
                                device["inverters"].append(device_id)
                            else:
                                logging.info(f" -> IGNORED Inverter {device_id} at {ip}:{port} - serial number {serial} already discovered")
                            continue
                        if len(device["inverters"]) > 0 and await probe_register(modbus, address=32000, device_id=device_id):  # AC Charger System state
                            logging.info(f" -> Found AC-Charger at {ip}:{port}: Device ID={device_id}")
                            device["ac-chargers"].append(device_id)
                            continue
                    if len(device["inverters"]) == 0 and len(device["dc-chargers"]) == 0 and len(device["ac-chargers"]) == 0:
                        logging.info(f" -> Ignored Modbus device at {ip}:{port}: No new inverters or chargers found")
                    else:
                        results.append(device)
                else:
                    logging.info(f" -> Ignored Modbus device at {ip}: No Plant running state found")
            finally:
                modbus.close()
    except ModbusException as e:
        logging.debug(f"Modbus connection to {ip}:{port} failed: {e}")


def scan(port: int = 502) -> list[dict[str, int, list[int], list[int], list[int]]]:
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    logging.getLogger("scapy").setLevel(logging.CRITICAL)

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

    active_ips: dict[str, float] = {}
    for addr, subnet in networks.items():
        logging.info(f"Scanning for active devices in network {subnet.with_prefixlen}...")
        all_ips = [str(ip) for ip in subnet.hosts()]
        missing_ips = [ip for ip in all_ips if ip != addr]
        ping_results = ping_scan(missing_ips, timeout=0.5)
        active_ips[addr] = 0.0  # Scan localhost first
        active_ips.update(ping_results)
    ips_sorted_by_latency = dict(sorted(active_ips.items(), key=lambda item: item[1]))

    loop = asyncio.new_event_loop()
    results = []
    for ip in ips_sorted_by_latency:
        loop.run_until_complete(scan_host(ip, port, results))
    loop.close()

    elapsed = time.perf_counter() - started
    logging.info(f"Scan completed in {elapsed:.2f} seconds")

    return results


if __name__ == "__main__":
    logging.getLogger("root").setLevel(logging.INFO)
    results = scan(port=502)
    logging.info(f"Auto-discovered: {results}")
