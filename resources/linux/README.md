# Linux Installation

## Pre-requisites

- A Linux server (physical hardware, or a virtual machine/container) that runs continuously in which to install `sigenergy2mqtt` (hardware requirements are minimal: I use a Proxmox LXC with 1 core and 256MiB RAM)
- Access to an MQTT broker such as [Mosquitto](https://mosquitto.org/)

## Installation

### Install Python 3.12 or later (if required)
```bash
# Debian/Ubuntu
sudo apt update
sudo apt install python3 python3-venv pipx

# Fedora
sudo dnf update
sudo dnf install python3 python3-venv pipx
```

### Install sigenergy2mqtt
```bash
# Create the sigenergy user
useradd -m -g 1 sigenergy
sudo -u sigenergy pipx ensurepath

# Install sigenergy2mqtt
sudo -u sigenergy pipx install sigenergy2mqtt
```

## Create Background Service

To run `sigenergy2mqtt` as a service that starts automatically in the background on system boot, create the file `/etc/systemd/system/sigenergy2mqtt.service` using [sigenergy2mqtt.service](sigenergy2mqtt.service) as an example.

Once that is done, run the following commands:
```bash
systemctl enable sigenergy2mqtt.service
```

## Create Configuration File

Create your configuration file in `/etc/sigenergy2mqtt.yaml`. Use the [sample configuration file](../configuration/sigenergy2mqtt.yaml) _as a guide_. 

If you use the complete sample file, make sure you edit it and update it with your own configuration. It is **sample** file _only_ and should _not_ be used as is.

## Start Background Service

When you are ready to start the service, use this command:
```bash
systemctl start sigenergy2mqtt.service
```

Because the service is enabled, it will start automatically on reboot.

# Upgrades

To upgrade to a new release, use `pipx upgrade`:

```bash
sudo -u sigenergy pipx upgrade sigenergy2mqtt
systemctl restart sigenergy2mqtt.service
```
