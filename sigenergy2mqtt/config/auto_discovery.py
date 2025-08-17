from pymodbus import FramerType, ModbusException
from pymodbus.client import ModbusTcpClient
from scapy.all import ARP, Ether, srp, IP, ICMP, sr1
import ipaddress
import logging
import psutil
import queue
import threading
import time


def arp_worker(ip_chunk, result_dict, lock, timeout=2) -> None:
    arp = ARP(pdst=ip_chunk)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp

    responses = srp(packet, timeout=timeout, verbose=0)[0]
    with lock:
        for _, received in responses:
            result_dict[received.psrc] = received.hwsrc


def arp_scan(network_cidr, threads=10, timeout=1) -> list[dict[str, str]]:
    ip_list = [str(ip) for ip in ipaddress.IPv4Network(network_cidr, strict=False).hosts()]
    chunk_size = len(ip_list) // threads + 1
    chunks = [ip_list[i : i + chunk_size] for i in range(0, len(ip_list), chunk_size)]

    result_dict = {}
    lock = threading.Lock()
    thread_list = []

    for chunk in chunks:
        t = threading.Thread(target=arp_worker, args=(chunk, result_dict, lock, timeout))
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join()

    return result_dict


def ping_worker(ip_queue, result_list, timeout=0.5) -> None:
    while not ip_queue.empty():
        ip = ip_queue.get()
        pkt = IP(dst=ip) / ICMP()
        reply = sr1(pkt, timeout=timeout, verbose=0)
        if reply:
            result_list.append(ip)
        ip_queue.task_done()


def ping_scan(ip_list, threads=100, timeout=1) -> list[str]:
    ip_queue = queue.Queue()
    result_list = []

    for ip in ip_list:
        ip_queue.put(ip)

    for _ in range(threads):
        t = threading.Thread(target=ping_worker, args=(ip_queue, result_list))
        t.daemon = True
        t.start()

    ip_queue.join()
    return result_list


def register_scan(client: ModbusTcpClient, address: int, count: int = 1, device_id: int = 247) -> bool:
    try:
        result = client.read_input_registers(address=address, count=count, device_id=device_id)
        if result and not result.isError():
            return True
    except ModbusException:
        pass
    return False


def scan(port: int = 502) -> list[dict[str, int, list[int], list[int], list[int]]]:
    started = time.perf_counter()

    networks = {}
    for iface_name, iface_info in psutil.net_if_addrs().items():
        if "docker" not in iface_name:
            for addr in iface_info:
                if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                    ip = addr.address
                    netmask = addr.netmask
                    if ip and netmask:
                        network = f"{ip}/{netmask}"
                        networks[ip] = ipaddress.IPv4Network(network, strict=False)
                        break

    network_scan_elapsed = time.perf_counter() - started
    logging.info(f"Network scan completed in {network_scan_elapsed:.2f} seconds. Found: {networks=}")

    results = []
    for addr, subnet in networks.items():
        logging.info(f"Scanning {subnet.with_prefixlen}...")
        arp_results = arp_scan(subnet.with_netmask, timeout=0.5)
        all_ips = [str(ip) for ip in subnet.hosts()]
        missing_ips = [ip for ip in all_ips if ip not in arp_results and ip != addr]

        ping_results = ping_scan(missing_ips, timeout=0.5)
        active_ips = list(set([addr]) | set(arp_results.keys()) | set(ping_results))

        for ip in active_ips:
            with ModbusTcpClient(host=ip, port=port, framer=FramerType.SOCKET, timeout=0.25, retries=0) as client:
                try:
                    client.connect()
                    if client.connected:
                        logging.info(f"Found Modbus device at {ip}")
                        if register_scan(client, address=30051, device_id=247):  # Plant running state
                            device = {"host": ip, "port": port, "ac-chargers": [], "dc-chargers": [], "inverters": []}
                            for device_id in range(1, 247):
                                logging.info(f"Scanning {ip} for device_id {device_id}...")
                                if register_scan(client, address=31501, device_id=device_id):  # [DC Charger] Charging current
                                    device["dc-chargers"].append(device_id)
                                    device["inverters"].append(device_id)
                                    continue
                                if register_scan(client, address=30578, device_id=device_id):  # Inverter Running state
                                    device["inverters"].append(device_id)
                                    continue
                                if register_scan(client, address=32000, device_id=device_id):  # AC Charger System state
                                    device["ac-chargers"].append(device_id)
                                    continue
                            if len(device["inverters"]) == 0 and len(device["dc-chargers"]) == 0 and len(device["ac-chargers"]) == 0:
                                logging.info(f"Ignored Modbus device at {ip}: no inverters or chargers found")
                            else:
                                results.append(device)
                        else:
                            logging.info(f"Ignored Modbus device at {ip}: no Plant running state found")
                        client.close()
                except ModbusException:
                    pass

    elapsed = time.perf_counter() - started
    print(f"Scan completed in {elapsed:.2f} seconds. Found {len(results)} Sigenergy Modbus device(s)")
    sorted_ips = sorted(results, key=lambda result: ipaddress.ip_address(result["host"]))

    return sorted_ips
