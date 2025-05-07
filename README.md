### <img src="resources/sigenergy2mqtt.png" alt="sigenergy2mqtt" height="50">
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
    - [Quick Start](#quick-start-configuration)
    - [Background Service](#background-service)
    - [Upgrades](#upgrades)
- [Derived Sensors](#derived-sensors)
- [Home Assistant Auto-Discovery](#home-assistant-auto-discovery)
- [Alternatives](#alternatives)

# Disclaimer

`sigenergy2mqtt` was developed for my own use, and as such has only been tested in my single-phase environment without AC or DC chargers. In addition, there has been only cursory testing of the write functions. If you find a problem, please raise an issue.

## Pre-requisites:

- Python 3.11 or later
- An MQTT broker such as [Mosquitto](https://mosquitto.org/), either standalone or installed as an add-on to Home Assistant
- A Linux server (physical hardware, or a virtual machine/container) that runs continuously in which to install `sigenergy2mqtt` (hardware requirements are minimal: I use a Proxmox LXC with 2 cores and 256MiB RAM to run [Mosquitto](https://mosquitto.org/), [ecowitt2mqtt](https://github.com/bachya/ecowitt2mqtt) and `sigenergy2mqtt`)
- A Sigenergy energy solution with Modbus-TCP enabled by your installer

# Installation

Download the latest release from https://github.com/seud0nym/sigenergy2mqtt/releases, and run the following command (replacing _version_ with the actual version number you download):
```bash
pip install sigenergy2mqtt-version-py3-none-any.whl
```

To confirm that it has been installed correctly, verify the version nunmber with this command:
```bash
sigenergy2mqtt --version
```

## Quick Start Configuration

Create the file `/etc/sigenergy2mqtt.yaml` using your favourite editor, with the following contents:
```
home-assistant:
  enabled: true
  sensors-enabled-by-default: false
mqtt:
  broker: 127.0.0.1
  anonymous: true
  username: ""
  password: ""
modbus:
  - host: sigenergy.local
    inverters: [ 1 ]
    read-only: true
    read-write: true
    write-only: true
```

Notes:
- Configure your MQTT broker IP address/host name and Sigenergy IP address/host name as appropriate for your environment. 
- The number in square brackets after `inverters` is the Device ID (slave address) as advised by your installer. It is usually `1`. If you have multiple inverters, separate them with commas (e.g. `[ 1,2 ]`)
- If your MQTT broker requires authentication, change `anonymous` to false and enter the required username and password.
- By default, only entities relating to production, consumption and battery charging/discharging are enabled (all other entities will still appear in Home Assistant, but will be disabled). All other entities are disabled by default. If you want _all_ entities to be initially enabled, set `sensors-enabled-by-default` to `true`. This setting _only_ applies the first time that Home Assistant auto-discovers devices and entities; changing this configuration after first discovery will have no effect. Entities can be enabled and disabled through the Home Assistant user interface.
- The complete list of configuration options with associated comments can be found in [this file](doc/sigenergy2mqtt.yaml).

## Background Service

To run `sigenergy2mqtt` as a service that starts automatically in the background on system boot, create the file `/etc/systemd/system/sigenergy2mqtt.service` with your favourite editor, with the following contents:
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

## Upgrades

To upgrade to a new release, download the upgraded version and run these commands (replacing _upgrade.version_ with the actual version number you download):
```bash
pip install sigenergy2mqtt-upgrade.version-py3-none-any.whl --upgrade
systemctl restart sigenergy2mqtt.service
```

# Derived Sensors

`sigenergy2mqtt` calculates the following additional sensors:

### Plant

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| BatteryChargingPower | BatteryPower &gt; 0 |
| BatteryDischargingPower | BatteryPower &lt; 0 |
| GridSensorExportPower | GridSensorActivePower &lt; 0 &times; -1 |
| GridSensorLifetimeExportEnergy<sup>3</sup> | Riemann &sum; of GridSensorExportPower |
| GridSensorDailyExportEnergy<sup>3</sup> | GridSensorLifetimeExportEnergy &minus; GridSensorLifetimeExportEnergy at last midnight |
| GridSensorImportPower | GridSensorActivePower &gt; 0 |
| GridSensorLifetimeImportEnergy<sup>3</sup> | Riemann &sum; of GridSensorImportPower |
| GridSensorDailyImportEnergy<sup>3</sup> | GridSensorLifetimeImportEnergy &minus; GridSensorLifetimeImportEnergy at last midnight |
| SmartPort.PVPowerSensor | &sum; of all configured SmartPort MQTT sources and SmartPort modules | 
| TotalPVPower<sup>1</sup> | PlantPVPower &plus; SmartPort.PVPowerSensor |
| PlantConsumedPower | (either PlantPVPower _or_ TotalPVPower)<sup>2</sup> &plus; GridSensorActivePower &minus; BatteryPower |
| PlantLifetimeConsumedEnergy<sup>3</sup> | Riemann &sum; of PlantConsumedPower |
| PlantDailyConsumedEnergy<sup>3</sup> | PlantLifetimeConsumedEnergy &minus PlantLifetimeConsumedEnergy at last midnight |
| PlantLifetimePVEnergy<sup>3</sup> | Riemann &sum; of (either PlantPVPower _or_ TotalPVPower)<sup>2</sup> |
| PlantDailyPVEnergy<sup>3</sup> | PlantLifetimePVEnergy &minus; PlantLifetimePVEnergy at last midnight |
| PlantDailyChargeEnergy<sup>3</sup> | &sum; of DailyChargeEnergy across all Inverters associated with the Plant |
| PlantDailyDischargeEnergy<sup>3</sup> | &sum; of DailyDischargeEnergy across all Inverters associated with the Plant |
| PlantAccumulatedChargeEnergy<sup>3</sup> | &sum; of AccumulatedChargeEnergy across all Inverters associated with the Plant |
| PlantAccumulatedDischargeEnergy<sup>3</sup> | &sum; of AccumulatedDischargeEnergy across all Inverters associated with the Plant |

Notes:
1. TotalPVPower is _only_ calculated when the SmartPort configuration is enabled and a module or MQTT source for the SmartPort PV production has been specified.
1. PlantPVPower is used unless TotalPVPower has been calculated
3. The Sigenergy Modbus Protocol does not define any daily or lifetime accumulation registers, except for charging and discharging at the inverter ESS (Energy Storage System) level.


### Inverters

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| InverterBatteryChargingPower | ChargeDischargePower &gt; 0 |
| InverterBatteryDischargingPower | ChargeDischargePower &lt; 0 &times; -1 |
| InverterDailyPVEnergy | InverterLifetimePVEnergy &minus InverterLifetimePVEnergy at last midnight |
| InverterLifetimePVEnergy | Riemann &sum; of InverterPVPower |

### Inverter Strings

| Cacluated Sensor | Source/Calculation |
|------------------|--------|
| PVStringDailyEnergy | PVStringLifetimeEnergy &minus PVStringLifetimeEnergy at last midnight |
| PVStringLifetimeEnergy | Riemann &sum; of PVStringPower |
| PVStringPower | PVVoltageSensor &times; PVCurrentSensor |

# Home Assistant Auto-Discovery

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


# Alternatives

For simple Sigenergy systems, with no integrated legacy solar system or requirement to integrate with PVOutput, the [Sigenergy Local Modbus HACS integration](https://github.com/TypQxQ/Sigenergy-Local-Modbus) may be a better alternative for integration with Home Assistant.

| Feature | Sigenergy-Local-Modbus | sigenergy2mqtt | Comments |
|:--------|:----------------------:|:--------------:|:---------|
| Pre-requisites | None | Python, MQTT broker | |
| Installation | GUI | Manual | |
| Configuration| GUI | Edit configuration file | |
| Home Assistant | HACS Integration | Optional Auto-discovery | |
| PVOutput | No | Optional | |
| Third-Party Solar included in production/consumption | No | Optional | Since the V100R001C00SPC108 firmware update, production systems connected to the Sigenergy Gateway Smart-Port are no longer included in the PV Power reported by the Modbus interface. However, this may change in future firmware releases. |

