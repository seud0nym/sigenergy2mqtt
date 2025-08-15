from scapy.all import ARP, Ether, srp, IP, ICMP, sr1
import ipaddress
import psutil
import queue
import socket
import threading
import time


def arp_worker(ip_chunk, result_dict, lock, timeout=2):
    arp = ARP(pdst=ip_chunk)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp

    responses = srp(packet, timeout=timeout, verbose=0)[0]
    with lock:
        for _, received in responses:
            result_dict[received.psrc] = received.hwsrc


def arp_scan(network_cidr, threads=10, timeout=1):
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


def ping_worker(ip_queue, result_list, timeout=0.5):
    while not ip_queue.empty():
        ip = ip_queue.get()
        pkt = IP(dst=ip) / ICMP()
        reply = sr1(pkt, timeout=timeout, verbose=0)
        if reply:
            result_list.append(ip)
        ip_queue.task_done()


def ping_scan(ip_list, threads=100):
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


# Example usage
if __name__ == "__main__":
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
    print(f"Network scan completed in {network_scan_elapsed:.2f} seconds. Found {len(networks)} networks: {networks}")

    results = []
    for addr, subnet in networks.items():
        print(f"🔍 Scanning {subnet.with_prefixlen}")
        arp_results = arp_scan(subnet.with_netmask)
        all_ips = [str(ip) for ip in subnet.hosts()]
        missing_ips = [ip for ip in all_ips if ip not in arp_results and ip != addr]

        ping_results = ping_scan(missing_ips)
        active_ips = list(set(addr) | set(arp_results.keys()) | set(ping_results))

        for ip in active_ips:
            try:
                with socket.create_connection((ip, 502), timeout=0.2):
                    results.append(ip)
            except Exception:
                pass

    elapsed = time.perf_counter() - started
    print(f"Scan completed in {elapsed:.2f} seconds. Found {len(results)} active hosts.")
    for host in results:
        print(f"{host}")
