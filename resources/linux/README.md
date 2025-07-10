# Linux Installation

## Pre-requisites

- Python 3.11 or later
- An MQTT broker such as [Mosquitto](https://mosquitto.org/), either standalone or installed as an add-on to Home Assistant
- A Linux server (physical hardware, or a virtual machine/container) that runs continuously in which to install `sigenergy2mqtt` (hardware requirements are minimal: I use a Proxmox LXC with 1 cores and 256MiB RAM)

## Installation

Install `sigenergy2mqtt` via `pip`:
```bash
pip install sigenergy2mqtt
```

## Background Service

To run `sigenergy2mqtt` as a service that starts automatically in the background on system boot, create the file `/etc/systemd/system/sigenergy2mqtt.service` using [sigenergy2mqtt.service](sigenergy2mqtt.service) as an example.

Once that is done, run the following commands:
```bash
useradd -m -g 1 sigenergy
systemctl enable sigenergy2mqtt.service
```

When you are ready to start the service, use this command:
```bash
systemctl start sigenergy2mqtt.service
```

## Upgrades

To upgrade to a new release, install using `pip` with the `--upgrade` option:
```bash
pip install sigenergy2mqtt --upgrade
systemctl restart sigenergy2mqtt.service
```
