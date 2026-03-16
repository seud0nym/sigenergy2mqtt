<img src="https://github.com/seud0nym/sigenergy2mqtt/raw/main/resources/logo.png" alt="sigenergy2mqtt" height="50"><br>

![Dynamic YAML Badge](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fseud0nym%2Fhome-assistant-addons%2Frefs%2Fheads%2Fmain%2Fsigenergy2mqtt%2Fconfig.yaml&query=%24.version&prefix=v&label=add-on)
[![Docker Image Version](https://img.shields.io/docker/v/seud0nym/sigenergy2mqtt?label=docker)](https://hub.docker.com/r/seud0nym/sigenergy2mqtt)
[![PyPI - Version](https://img.shields.io/pypi/v/sigenergy2mqtt)](https://pypi.org/project/sigenergy2mqtt/)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fseud0nym%2Fsigenergy2mqtt%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)
![Coverage - Tests](resources/badges/tests.svg)
![Coverage - Total](resources/badges/coverage-total.svg)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
<br>
![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fseud0nym%2Fhome-assistant-addons%2Fhome-assistant-addon-sigenergy2mqtt-amd64&query=downloadCount&label=add-on%20amd64%20downloads&color=green&link=https%3A%2F%2Fgithub.com%2Fseud0nym%2Fhome-assistant-addons%2Fpkgs%2Fcontainer%2Fhome-assistant-addon-sigenergy2mqtt-amd64)
![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fseud0nym%2Fhome-assistant-addons%2Fhome-assistant-addon-sigenergy2mqtt-aarch64&query=downloadCount&label=add-on%20aarch64%20downloads&color=green&link=https%3A%2F%2Fgithub.com%2Fseud0nym%2Fhome-assistant-addons%2Fpkgs%2Fcontainer%2Fhome-assistant-addon-sigenergy2mqtt-aarch64)
![Docker Pulls](https://img.shields.io/docker/pulls/seud0nym/sigenergy2mqtt?color=green)
![PyPI - Downloads](https://img.shields.io/pypi/dm/sigenergy2mqtt?label=pypi%20downloads)


`sigenergy2mqtt` is a bridge between the Modbus interface of the Sigenergy energy system and the MQTT lightweight publish/subscribe messaging protocol.

In addition, `sigenergy2mqtt` has several optional features: 

1. It can auto-discover Sigenergy devices and their device IDs without having to specify the host IP address.
1. It can publish the appropriate messages to allow Home Assistant to automatically discover the Sigenergy devices, simplifying Home Assistant configuration. 
1. Production and consumption data can automatically be uploaded to PVOutput. 
1. It can directly publish the Modbus data to an InfluxDB (v1/2) time series database for long-term storage and analysis.


## Pre-requisites

- Sigenergy ESS or PV Inverter, with Modbus-TCP enabled by your installer
- MQTT broker such as [Mosquitto](https://mosquitto.org/), either standalone or installed as an app to Home Assistant

## Installation

Follow the installation guides for supported environments:

* [Home Assistant](resources/homeassistant/README.md)
* [Docker](resources/docker/README.md)
* [Linux](resources/linux/README.md)

## Configuration

When parsing configuration options, `sigenergy2mqtt` looks at the configuration sources in the following order:

1. [Configuration File](resources/configuration/FILE.md)
2. [Environment Variables](resources/configuration/ENV.md)
3. [Command Line Options](resources/configuration/CLI.md)<sup>1</sup>
4. [Home Assistant App Configuration](https://github.com/seud0nym/home-assistant-addons/blob/main/sigenergy2mqtt/DOCS.md#configuration-tab)

This means, for example, that the options specified in the configuration file can be overridden by environment variables and command line options.

Click on the links above to see the configuration options available.

<sup>1</sup> <sub>Not applicable to the Home Assistant App</sub>

## MQTT Publish and Subscribe Topics

The topics that are published and subscribed to by `sigenergy2mqtt` can be found [here](resources/sensors/TOPICS.md).

## Disclaimer

`sigenergy2mqtt` was developed for my own use, and as such has only been tested in my single-phase environment without AC or DC chargers, although I have developed a testing environment in software that emulates the chargers and three phase implementations. If you find a problem, please raise an issue.

## Thanks

`sigenergy2mqtt` was inspired the Home Assistant integrations developed by [TypQxQ](https://github.com/TypQxQ/).
