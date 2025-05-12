<img src="https://github.com/seud0nym/sigenergy2mqtt/raw/main/resources/logo.png" alt="sigenergy2mqtt" height="50"><br>
[![License](https://img.shields.io/github/license/seud0nym/sigenergy2mqtt.svg?style=flat)](https://github.com/seud0nym/sigenergy2mqtt/blob/master/LICENSE) 
![Top Language](https://img.shields.io/github/languages/top/seud0nym/sigenergy2mqtt)
[![Latest Release](https://img.shields.io/github/release/seud0nym/sigenergy2mqtt/all.svg?style=flat&label=latest)](https://github.com/seud0nym/sigenergy2mqtt/releases) 

`sigenergy2mmqtt` is a bridge between the Modbus interface of the Sigenergy energy system and the MQTT lightweight publish/subscribe messaging protocol.

In addition, `sigenergy2mqtt` has several optional features: 

1. It can publish the appropriate messages to allow Home Assistant to automatically discover the Sigenergy devices, simplifying Home Assistant configuration. 
1. Production and consumption data can automatically be uploaded to PVOutput. 
1. Third-party solar production can be included in the total production and consumption computations, using either custom code or by subscribing to MQTT topics.

`sigenergy2mqtt` was inspired the Home Assistant integrations developed by [TypQxQ](https://github.com/TypQxQ/).

- [Disclaimer](#disclaimer)
- [Pre-requisites](#pre-requisites)
- [Installation](#installation)
    - [Linux](#linux)
      - [Background Service](#background-service)
      - [Upgrades](#upgrades)
    - [Docker](#docker)
- [Configuration](#configuration)
    - [Configuration File](#configuration-file)
    - [Command Line Options](#command-line-options)
    - [Environment Variables](#environment-variables)
- [Post-Installation](#post-installation)
- [Home Assistant Auto-Discovery](#home-assistant-auto-discovery)
- [Alternatives](#alternatives)

## Disclaimer

`sigenergy2mqtt` was developed for my own use, and as such has only been tested in my single-phase environment without AC or DC chargers. In addition, there has been only cursory testing of the write functions. If you find a problem, please raise an issue.

## Pre-requisites:

- Python 3.11 or later
- An MQTT broker such as [Mosquitto](https://mosquitto.org/), either standalone or installed as an add-on to Home Assistant
- A Linux server (physical hardware, or a virtual machine/container) that runs continuously in which to install `sigenergy2mqtt` (hardware requirements are minimal: I use a Proxmox LXC with 2 cores and 256MiB RAM to run [Mosquitto](https://mosquitto.org/), [SIGENERGY2mqtt](https://github.com/bachya/SIGENERGY2mqtt) and `sigenergy2mqtt`)
- A Sigenergy energy solution with Modbus-TCP enabled by your installer

## Installation

### Linux

Install `sigenergy2mqtt` via `pip`:
```bash
pip install sigenergy2mqtt
```

#### Background Service

To run `sigenergy2mqtt` as a service that starts automatically in the background on system boot, 
create the file `/etc/systemd/system/sigenergy2mqtt.service` with your favourite editor, 
with the following contents:
```
[Unit]
Description=Publish Modbus data from Sigenergy to MQTT
Documentation=https://github.com/seud0nym/sigenergy2mqtt
After=network.target mosquitto.service

[Service]
Type=simple
User=sigenergy
Group=daemon
ExecStart=/usr/local/bin/sigenergy2mqtt
ExecReload=kill -HUP $MAINPID
KillMode=process
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Notes:
- If you are _not_ running `sigenergy2mqtt` on the same host/container as `Mosquitto`, remove _mosquitto.service_ from the `After=` line.

Once that is done, run the following commands:
```bash
useradd -m -g 1 sigenergy
systemctl enable sigenergy2mqtt.service
```

When you are ready to start the service, use this command:
```bash
systemctl start sigenergy2mqtt.service
```

#### Upgrades

To upgrade to a new release, install using `pip` with the `--upgrade` option:
```bash
pip install sigenergy2mqtt --upgrade
systemctl restart sigenergy2mqtt.service
```

### Docker

`sigenergy2mqtt` is available via a Docker image from both Docker Hub and ghcr.io. It can be configured by using the environment variables listed [below](#environment-variables), or by placing your [configuration file](#configuration-file) in the root of the `/data` volume,

Running the image is straightforward:

```
docker run -it \
    -e SIGENERGY2MQTT_MQTT_BROKER=192.168.0.1 \
    -e SIGENERGY2MQTT_MQTT_USERNAME=user \
    -e SIGENERGY2MQTT_MQTT_PASSWORD=password \
    -v /data:/data \
    seud0nym/sigenergy2mqtt:latest
```

Note that you must provide persistent storage via the `-v` option to preserve the state  of calculated accumulation sensors across executions. You can also place your [configuration file](#configuration-file) in the root of this directory, rather than configuring via environment variables.

`docker-compose` users can find an example configuration file at [`docker-compose.yaml`](docker-compose.yaml).


## Configuration

You _can_ configure `sigenergy2mqtt` via the [command line](#command-line-options) and/or [environment variables](#environment-variables), but using a persistent configuration file is a better option, as it provides access to all advanced feature configuration. 

### Configuration File

The complete list of configuration options with associated comments can be found in [sigenergy2mqtt.yaml](sigenergy2mqtt.yaml).

Example:
```
home-assistant:
  enabled: true
  sensors-enabled-by-default: false
mqtt:
  broker: 127.0.0.1
  username: ""
  password: ""
modbus:
  - host: sigenergy.local
    inverters: [ 1 ]
    read-only: true
    read-write: true
    write-only: true
pvoutput:
  enabled: false
  api-key: your_api_key
  system-id: your_system_id
  interval-minutes: 5
  consumption: true
```

Notes:
- Configure your MQTT broker IP address/host name and Sigenergy IP address/host name as appropriate for your environment. 
- The number in square brackets after `inverters` is the Device ID (slave address) as advised by your installer. It is usually `1`. If you have multiple inverters, separate them with commas (e.g. `[ 1,2 ]`)
- If your MQTT broker does not require authentication, add the option `anonymous: true` under `mqtt`.
- By default, only entities relating to production, consumption and battery charging/discharging are enabled (all other entities will still appear in Home Assistant, but will be disabled). All other entities are disabled by default. If you want _all_ entities to be initially enabled, set `sensors-enabled-by-default` to `true`. This setting _only_ applies the first time that Home Assistant auto-discovers devices and entities; changing this configuration after first discovery will have no effect. Entities can be enabled and disabled through the Home Assistant user interface.
- The default location for `sigenergy2mqtt.yaml` is in `/etc/`. However, it will also be found in `/data` or the current directory from which `sigenergy2mqtt` is run. You can also use the `-c` command line option or the `SIGENERGY2MQTT_CONFIG` environment variable to specify a different location and/or filename.

### Command Line Options

Command line options override both environment variables and the configuration file.

```
  -h, --help            show this help message and exit
  -c [SIGENERGY2MQTT_CONFIG], --config [SIGENERGY2MQTT_CONFIG]
                        The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml)
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
  --hass-enabled        Enable auto-discovery in Home Assistant.
  --hass-discovery-prefix [SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX]
                        The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant)
  --hass-entity-id-prefix [SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX]
                        The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs (default: sigen)
  --hass-unique-id-prefix [SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX]
                        The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs (default: sigen). Once you have set this, you should NEVER
                        change it, as it will break existing entities in Home Assistant.
  --hass-device-name-prefix [SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX]
                        The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names (default: '')
  --hass-discovery-only
                        Exit immediately after publishing discovery. Does not read values from the ModBus interface, except to probe for device configuration.
  -b [SIGENERGY2MQTT_MQTT_BROKER], --mqtt-broker [SIGENERGY2MQTT_MQTT_BROKER]
                        The hostname or IP address of an MQTT broker (default: 127.0.0.1)
  --mqtt-port [SIGENERGY2MQTT_MQTT_PORT]
                        The listening port of the MQTT broker (default: 1883)
  --mqtt-anonymous      Connect to MQTT anonomously (i.e. without username/password).
  -u [SIGENERGY2MQTT_MQTT_USERNAME], --mqtt-username [SIGENERGY2MQTT_MQTT_USERNAME]
                        A valid username for the MQTT broker
  -p [SIGENERGY2MQTT_MQTT_PASSWORD], --mqtt-password [SIGENERGY2MQTT_MQTT_PASSWORD]
                        A valid password for the MQTT broker username
  --mqtt-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
  -m [SIGENERGY2MQTT_MODBUS_HOST], --modbus-host [SIGENERGY2MQTT_MODBUS_HOST]
                        The hostname or IP address of the Sigenergy device
  --modbus-port [SIGENERGY2MQTT_MODBUS_PORT]
                        The Sigenergy device Modbus port number (default: 502)
  --modbus-slave [SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE]
                        The Sigenergy Inverter Modbus Device ID (Slave ID). May be specified multiple times.
  --modbus-accharger-slave [SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE]
                        The Sigenergy AC Charger Modbus Device ID (Slave ID).
  --modbus-dccharger-slave [SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE]
                        The Sigenergy DC Charger Modbus Device ID (Slave ID).
  --modbus-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
  --smartport-enabled   Enable interrogation of a third-party device for production data.
  --smartport-module-name [SIGENERGY2MQTT_SMARTPORT_MODULE_NAME]
                        The name of the module which will be used to obtain third-party device production data.
  --smartport-host [SIGENERGY2MQTT_SMARTPORT_HOST]
                        The IP address or hostname of the third-party device.
  --smartport-username [SIGENERGY2MQTT_SMARTPORT_USERNAME]
                        The username to authenticate to the third-party device.
  --smartport-password [SIGENERGY2MQTT_SMARTPORT_PASSWORD]
                        The password to authenticate to the third-party device.
  --smartport-pv-power [SIGENERGY2MQTT_SMARTPORT_PV_POWER]
                        The sensor class to hold the production data obtained from the third-party device.
  --smartport-mqtt-topic [SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC]
                        The MQTT topic to which to subscribe to obtain the production data for the third-party device.
  --smartport-mqtt-gain [SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN]
                        The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. 1000 if the data is in kW) Default is 1 (Watts).
  --pvoutput-enabled    Enable status updates to PVOutput.
  --pvoutput-api-key [SIGENERGY2MQTT_PVOUTPUT_API_KEY]
                        The API Key for PVOutput
  --pvoutput-system-id [SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID]
                        The PVOutput System ID
  --pvoutput-consumption
                        Enable sending consumption status to PVOutput.
  --pvoutput-interval [SIGENERGY2MQTT_PVOUTPUT_INTERVAL]
                        The interval in minutes to send data to PVOutput (default: 5). Valid values are 5, 10 or 15 minutes.
  --pvoutput-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
  --clean               Publish empty discovery to delete existing devices, then exits immediately.
  -v, --version         Shows the version number, then exits immediately.
```

### Environment Variables

Environment variables override the configuration file, but *not* command line options.

- `SIGENERGY2MQTT_CONFIG` : The path to the JSON configuration file (default: /etc/sigenergy2mqtt.yaml)
- `SIGENERGY2MQTT_LOG_LEVEL` : Set the log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
- `SIGENERGY2MQTT_HASS_ENABLED` : Set to 'true' to enable auto-discovery in Home Assistant.
- `SIGENERGY2MQTT_HASS_DISCOVERY_PREFIX` : The Home Assistant MQTT Discovery topic prefix to use (default: homeassistant)
- `SIGENERGY2MQTT_HASS_ENTITY_ID_PREFIX` : The prefix to use for Home Assistant entity IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to entity IDs (default: sigen)
- `SIGENERGY2MQTT_HASS_UNIQUE_ID_PREFIX` : The prefix to use for Home Assistant unique IDs. Example: A prefix of 'prefix' will prepend 'prefix_' to unique IDs (default: sigen). Once you have set this, you should NEVER change it, as it will break existing entities in Home Assistant.
- `SIGENERGY2MQTT_HASS_DEVICE_NAME_PREFIX` : The prefix to use for Home Assistant entity names. Example: A prefix of 'prefix' will prepend 'prefix ' to names (default: '')
- `SIGENERGY2MQTT_HASS_DISCOVERY_ONLY`: Set to 'true' to e xit immediately after publishing discovery. Does not read values from the ModBus interface, except to probe for device configuration.
- `SIGENERGY2MQTT_MQTT_BROKER` : The hostname or IP address of an MQTT broker (default: 127.0.0.1)
- `SIGENERGY2MQTT_MQTT_PORT` : The listening port of the MQTT broker (default: 1883)
- `SIGENERGY2MQTT_MQTT_ANONYMOUS` : Set to 'true' to connect to MQTT anonomously (i.e. without username/password).
- `SIGENERGY2MQTT_MQTT_USERNAME` : A valid username for the MQTT broker
- `SIGENERGY2MQTT_MQTT_PASSWORD` : A valid password for the MQTT broker username
- `SIGENERGY2MQTT_MQTT_LOG_LEVEL` : Set the paho.mqtt log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
- `SIGENERGY2MQTT_MODBUS_HOST` : The hostname or IP address of the Sigenergy device
- `SIGENERGY2MQTT_MODBUS_PORT` : The Sigenergy device Modbus port number (default: 502)
- `SIGENERGY2MQTT_MODBUS_INVERTER_SLAVE` : The Sigenergy device Modbus Device ID (Slave ID). May be specified as a comma separated list. (default: 1)
- `SIGENERGY2MQTT_MODBUS_ACCHARGER_SLAVE` : The Sigenergy AC Charger Modbus Device ID (Slave ID).
- `SIGENERGY2MQTT_MODBUS_DCCHARGER_SLAVE` : The Sigenergy DC Charger Modbus Device ID (Slave ID).
- `SIGENERGY2MQTT_MODBUS_LOG_LEVEL` : Set the pymodbus log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)
- `SIGENERGY2MQTT_SMARTPORT_ENABLED` : Enable interrogation of a third-party device for production data.
- `SIGENERGY2MQTT_SMARTPORT_MODULE_NAME' : The name of the module which will be used to obtain third-party device production data.
- `SIGENERGY2MQTT_SMARTPORT_HOST` : The IP address or hostname of the third-party device.
- `SIGENERGY2MQTT_SMARTPORT_USERNAME` : The username to authenticate to the third-party device.
- `SIGENERGY2MQTT_SMARTPORT_PASSWORD` : The password to authenticate to the third-party device.
- `SIGENERGY2MQTT_SMARTPORT_PV_POWER` : The sensor class to hold the production data obtained from the third-party device.
- `SIGENERGY2MQTT_SMARTPORT_MQTT_TOPIC` : The MQTT topic to which to subscribe to obtain the production data for the third-party device.
- `SIGENERGY2MQTT_SMARTPORT_MQTT_GAIN` : The gain to be applied to the production data for the third-party device obtained from the MQTT topic. (e.g. 1000 if the data is in kW) Default is 1 (Watts).
- `SIGENERGY2MQTT_PVOUTPUT_ENABLED` : Set to 'true' to enable status updates to PVOutput.
- `SIGENERGY2MQTT_PVOUTPUT_API_KEY` : The API Key for PVOutput
- `SIGENERGY2MQTT_PVOUTPUT_SYSTEM_ID` : The PVOutput System ID
- `SIGENERGY2MQTT_PVOUTPUT_CONSUMPTION` : Set to 'true' to enable sending consumption status to PVOutput.
- `SIGENERGY2MQTT_PVOUTPUT_INTERVAL` : The interval in minutes to send data to PVOutput (default: 5). Valid values are 5, 10 or 15 minutes.
- `SIGENERGY2MQTT_PVOUTPUT_LOG_LEVEL` : Set the PVOutput log level. Valid values are: DEBUG, INFO, WARNING, ERROR or CRITICAL. Default is WARNING (warnings, errors and critical failures)

## Post-Installation

If you are using Home Assistant, you can set the current values for the daily and lifetime accumulation sensors from the mySigen app through the MQTT device screen. The screen contains controls for inputting the values. Make sure you enter lifetime values first, because daily sensors use the lifetime numbers as their base.

## Home Assistant Auto-Discovery

For each host defined in the `modbus` section of the configuration file, an MQTT device will be created in Home Assistant. The first device will be called `Sigenergy Plant` (plant is the terminology used in the "Sigenergy Modbus Protocol", and is in the context of a power plant). Each plant will have one or more related devices, such as `Sigenergy Plant Grid Sensor` and if applicable, `Sigenergy Plant Smart-Port`. Plants will also have associated inverters, and their names will include the model and serial number (e.g. `SigenStor CMUxxxxxxxxxx Energy Controller`). Each inverter will have an an Energy Storage System device (e.g. `SigenStor CMUxxxxxxxxxx ESS`) and as many PV String devices as the inverter supports. Chargers will be named `Sigenergy AC Charger` and `Sigenergy DC Charger`.

Example:
```
Sigenergy Plant
   ├─ Sigenergy Plant Grid Sensor
   ├─ SigenStor Plant Smart-Port
   ├─ SigenStor CMUxxxxxxxxxx Energy Controller (ID 1)
   │    ├─ SigenStor CMUxxxxxxxxxx ESS
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 1
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 2
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 3
   │    ├─ SigenStor CMUxxxxxxxxxx PV String 4
   │    └─ Sigenergy DC Charger
   └─ SigenStor CMUyyyyyyyyyy Energy Controller (ID 2)
        ├─ SigenStor CMUyyyyyyyyyy ESS
        ├─ SigenStor CMUyyyyyyyyyy PV String 1
        ├─ SigenStor CMUyyyyyyyyyy PV String 2
        └─ Sigenergy DC Charger
```


## Alternatives

For simple Sigenergy systems, with no integrated legacy solar system or requirement to integrate with PVOutput, the [Sigenergy Local Modbus HACS integration](https://github.com/TypQxQ/Sigenergy-Local-Modbus) may be a better alternative for integration with Home Assistant.

| Feature | Sigenergy-Local-Modbus | sigenergy2mqtt | Comments |
|:--------|:----------------------:|:--------------:|:---------|
| Pre-requisites | None | Python, MQTT broker | |
| Installation | GUI | Manual | |
| Configuration| GUI | Edit configuration file | |
| Home Assistant | HACS Integration | Optional Auto-discovery | |
| PVOutput | No | Optional | |
| Third-Party Solar included in production/consumption | No | Optional | Since the V100R001C00SPC108 firmware update, production systems connected to the Sigenergy Gateway Smart-Port are no longer included in the PV Power reported by the Modbus interface. However, this may change in future firmware releases. |

